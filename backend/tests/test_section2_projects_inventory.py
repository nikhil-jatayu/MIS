from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.helpers import create_inventory_item, create_project, create_purchase_request


def test_project_creation_allocates_available_inventory(
    client: TestClient, auth_headers, standard_users
):
    item = create_inventory_item(client, auth_headers["super"], sku="MCU-001", quantity=10)
    project = create_project(
        client,
        auth_headers["admin"],
        name="Controller Board",
        member_ids=[str(standard_users["user"].id)],
        bom=[(item["id"], 4)],
    )
    assert project["status"] == "READY_FOR_PRODUCTION"
    assert project["is_inventory_ready"] is True
    assert project["shortage_count"] == 0
    assert project["bom_lines"][0]["quantity_allocated"] == 4
    assert project["bom_lines"][0]["quantity_shortage"] == 0
    assert project["creator"]["email"] == "admin@jatayues.com"

    stock = client.get(f"/api/v1/inventory/{item['id']}", headers=auth_headers["user"])
    assert stock.status_code == 200
    assert stock.json()["quantity_available"] == 6

    audit = client.get(
        "/api/v1/audit-logs?entity=inventory_item&action=INVENTORY_ALLOCATED",
        headers=auth_headers["super"],
    )
    assert audit.status_code == 200
    assert audit.json()["total"] >= 1


def test_shortage_purchase_request_order_delivery_workflow(
    client: TestClient, auth_headers, standard_users
):
    item = create_inventory_item(client, auth_headers["super"], sku="SEN-001", quantity=2)
    project = create_project(
        client,
        auth_headers["admin"],
        name="Sensor Assembly",
        member_ids=[str(standard_users["user"].id)],
        bom=[(item["id"], 5)],
    )
    assert project["status"] == "PENDING_INVENTORY"
    assert project["bom_lines"][0]["quantity_allocated"] == 2
    assert project["bom_lines"][0]["quantity_shortage"] == 3

    request = create_purchase_request(client, auth_headers["user"], project["id"], item["id"])
    assert request["status"] == "PENDING"
    assert request["quantity"] == 3
    assert request["requested_by"] == str(standard_users["user"].id)

    duplicate = client.post(
        f"/api/v1/projects/{project['id']}/purchase-requests",
        headers=auth_headers["user"],
        json={"item_id": item["id"]},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "NO_SHORTAGE"

    user_approve = client.post(
        f"/api/v1/purchase-requests/{request['id']}/approve",
        headers=auth_headers["user"],
    )
    assert user_approve.status_code == 403

    approved = client.post(
        f"/api/v1/purchase-requests/{request['id']}/approve",
        headers=auth_headers["admin"],
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["approved_by"] == str(standard_users["admin"].id)

    ordered = client.post(
        f"/api/v1/purchase-requests/{request['id']}/order",
        headers=auth_headers["admin"],
        json={"delay_reason": "Supplier lead time is 10 working days"},
    )
    assert ordered.status_code == 200, ordered.text
    assert ordered.json()["status"] == "ORDERED"

    paused = client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers["user"])
    assert paused.json()["status"] == "AWAITING_DELIVERY"
    assert paused.json()["delay_reason"] == "Supplier lead time is 10 working days"
    assert paused.json()["paused_from_status"] == "PENDING_INVENTORY"

    delivered = client.post(
        f"/api/v1/purchase-requests/{request['id']}/deliver",
        headers=auth_headers["admin"],
    )
    assert delivered.status_code == 200, delivered.text
    assert delivered.json()["status"] == "DELIVERED"

    ready = client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers["user"])
    body = ready.json()
    assert body["status"] == "READY_FOR_PRODUCTION"
    assert body["bom_lines"][0]["quantity_allocated"] == 5
    assert body["bom_lines"][0]["quantity_shortage"] == 0

    stock = client.get(f"/api/v1/inventory/{item['id']}", headers=auth_headers["super"])
    assert stock.json()["quantity_available"] == 0


def test_purchase_request_rejection_keeps_project_pending(
    client: TestClient, auth_headers, standard_users
):
    item = create_inventory_item(client, auth_headers["super"], sku="CAP-001", quantity=0)
    project = create_project(
        client,
        auth_headers["admin"],
        name="Capacitor Batch",
        member_ids=[str(standard_users["user"].id)],
        bom=[(item["id"], 2)],
    )
    assert project["status"] == "PENDING_INVENTORY"
    request = create_purchase_request(client, auth_headers["user"], project["id"], item["id"])
    rejected = client.post(
        f"/api/v1/purchase-requests/{request['id']}/reject",
        headers=auth_headers["admin"],
        json={"reason": "Use the alternate approved supplier"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    assert rejected.json()["review_note"] == "Use the alternate approved supplier"

    still_pending = client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers["admin"])
    assert still_pending.json()["status"] == "PENDING_INVENTORY"

    retry = create_purchase_request(client, auth_headers["user"], project["id"], item["id"])
    assert retry["quantity"] == 2


def test_bom_replacement_releases_and_reallocates_inventory(
    client: TestClient, auth_headers, standard_users
):
    item_a = create_inventory_item(client, auth_headers["super"], sku="RES-100", quantity=10)
    item_b = create_inventory_item(client, auth_headers["super"], sku="RES-200", quantity=1)
    project = create_project(
        client,
        auth_headers["admin"],
        name="Mixed BOM",
        member_ids=[str(standard_users["user"].id)],
        bom=[(item_a["id"], 2), (item_b["id"], 5)],
    )
    assert project["status"] == "PENDING_INVENTORY"
    assert project["shortage_count"] == 1

    updated = client.put(
        f"/api/v1/projects/{project['id']}/bom",
        headers=auth_headers["admin"],
        json={"lines": [{"item_id": item_a["id"], "quantity_required": 3}]},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "READY_FOR_PRODUCTION"
    assert len(updated.json()["bom_lines"]) == 1
    assert updated.json()["bom_lines"][0]["quantity_allocated"] == 3

    stock_a = client.get(f"/api/v1/inventory/{item_a['id']}", headers=auth_headers["super"])
    stock_b = client.get(f"/api/v1/inventory/{item_b['id']}", headers=auth_headers["super"])
    assert stock_a.json()["quantity_available"] == 7
    assert stock_b.json()["quantity_available"] == 1

    locked = client.put(
        f"/api/v1/projects/{project['id']}/bom",
        headers=auth_headers["admin"],
        json={"lines": []},
    )
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "BOM_LOCKED"


def test_project_updates_deadline_audit_and_role_restrictions(
    client: TestClient, auth_headers, standard_users
):
    project = create_project(
        client,
        auth_headers["admin"],
        name="Deadline Project",
        member_ids=[str(standard_users["user"].id)],
        bom=[],
    )
    forbidden = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=auth_headers["user"],
        json={"priority": "LOW"},
    )
    assert forbidden.status_code == 403

    new_deadline = (date.today() + timedelta(days=45)).isoformat()
    changed = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=auth_headers["admin"],
        json={"end_date": new_deadline, "priority": "CRITICAL"},
    )
    assert changed.status_code == 200
    assert changed.json()["end_date"] == new_deadline
    assert changed.json()["priority"] == "CRITICAL"

    audit = client.get(
        "/api/v1/audit-logs?action=DEADLINE_CHANGED&entity=project",
        headers=auth_headers["super"],
    )
    assert audit.status_code == 200
    assert audit.json()["total"] == 1
    entry = audit.json()["items"][0]
    assert entry["before"]["end_date"] != entry["after"]["end_date"]
    assert entry["actor"]["email"] == "admin@jatayues.com"

    user_create = client.post(
        "/api/v1/projects",
        headers=auth_headers["user"],
        json={
            "name": "Not allowed",
            "type": "PRODUCTION",
            "priority": "LOW",
            "members": [
                {"user_id": str(standard_users["user"].id), "role_in_project": "DEVELOPER"}
            ],
            "bom": [],
        },
    )
    assert user_create.status_code == 403


def test_unassigned_user_cannot_act_and_request_visibility(
    client: TestClient, auth_headers, standard_users
):
    item = create_inventory_item(client, auth_headers["super"], sku="PCB-001", quantity=0)
    project = create_project(
        client,
        auth_headers["admin"],
        name="PCB Prototype",
        member_ids=[str(standard_users["user"].id)],
        bom=[(item["id"], 4)],
    )
    forbidden = client.post(
        f"/api/v1/projects/{project['id']}/purchase-requests",
        headers=auth_headers["other"],
        json={"item_id": item["id"]},
    )
    assert forbidden.status_code == 403

    request = create_purchase_request(client, auth_headers["user"], project["id"], item["id"])
    member_list = client.get("/api/v1/purchase-requests", headers=auth_headers["user"])
    other_list = client.get("/api/v1/purchase-requests", headers=auth_headers["other"])
    admin_list = client.get("/api/v1/purchase-requests", headers=auth_headers["admin"])
    assert member_list.json()["total"] == 1
    assert other_list.json()["total"] == 0
    assert admin_list.json()["total"] == 1
    assert request["status"] == "PENDING"


def test_inventory_validation_delete_guard_and_project_list_filters(
    client: TestClient, auth_headers, standard_users
):
    item = create_inventory_item(client, auth_headers["super"], sku="LED-001", quantity=20)
    duplicate = client.post(
        "/api/v1/inventory",
        headers=auth_headers["super"],
        json={"name": "Duplicate LED", "sku": "led-001", "quantity_available": 1},
    )
    assert duplicate.status_code == 409

    project = create_project(
        client,
        auth_headers["admin"],
        name="LED Panel",
        member_ids=[str(standard_users["user"].id)],
        bom=[(item["id"], 5)],
        priority="CRITICAL",
    )
    delete = client.delete(f"/api/v1/inventory/{item['id']}", headers=auth_headers["super"])
    assert delete.status_code == 422
    assert delete.json()["error"]["code"] == "ITEM_IN_USE"

    filtered = client.get(
        "/api/v1/projects?type=PRODUCTION&status=READY_FOR_PRODUCTION&priority=CRITICAL&sort=end_date&order=asc&page=1&page_size=1",
        headers=auth_headers["user"],
    )
    assert filtered.status_code == 200
    body = filtered.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == project["id"]
    assert body["pages"] == 1

    assigned = client.get("/api/v1/projects?assigned_to_me=true", headers=auth_headers["user"])
    not_assigned = client.get("/api/v1/projects?assigned_to_me=true", headers=auth_headers["other"])
    assert assigned.json()["total"] == 1
    assert not_assigned.json()["total"] == 0
