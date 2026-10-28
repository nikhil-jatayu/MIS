"""End-to-end business workflow tests.

These tests exercise the complete project lifecycle from both directions:

* stock already on hand -> instant allocation, no purchase request possible;
* missing stock -> purchase request -> approval -> order -> delivery -> allocation.

They also cover the Time Counter alert lifecycle (generation, de-duplication,
recipients and read state) and the audit trail/role restrictions around the
workflow.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.project import Project
from app.services.alert_service import run_time_counter
from tests.helpers import (
    create_inventory_item,
    create_project,
    create_purchase_request,
)

DELAY_REASON = "Supplier confirmed a two week lead time"


def _get_project(client: TestClient, headers: dict[str, str], project_id: str) -> dict:
    response = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _inventory_quantity(client: TestClient, headers: dict[str, str], sku: str) -> int:
    response = client.get(f"/api/v1/inventory?q={sku}", headers=headers)
    assert response.status_code == 200, response.text
    items = [item for item in response.json()["items"] if item["sku"] == sku]
    assert len(items) == 1, items
    return items[0]["quantity_available"]


def _audit_ids(
    client: TestClient, headers: dict[str, str], *, entity: str, entity_id: str
) -> set[str]:
    response = client.get(
        f"/api/v1/audit-logs?entity={entity}&entity_id={entity_id}&page_size=100",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return {item["action"] for item in response.json()["items"]}


def _age_project(db, project_id: str, *, days: int, now: datetime) -> None:
    project = db.get(Project, UUID(project_id))
    assert project is not None
    project.status_changed_at = now - timedelta(days=days)
    db.commit()


def test_workflow_stock_on_hand_needs_no_purchase_and_completes(
    client: TestClient, auth_headers, standard_users, db
):
    """Available inventory is allocated on creation and no purchase is required."""
    item = create_inventory_item(client, auth_headers["super"], sku="E2E-ONHAND-01", quantity=100)
    project = create_project(
        client,
        auth_headers["admin"],
        name="E2E On-hand Build",
        member_ids=[str(standard_users["user"].id)],
        bom=[(item["id"], 20)],
    )

    # Stock was reserved immediately, so the project skips the purchase stage.
    assert project["status"] == "READY_FOR_PRODUCTION"
    assert project["is_inventory_ready"] is True
    assert project["shortage_count"] == 0
    line = project["bom_lines"][0]
    assert line["quantity_required"] == 20
    assert line["quantity_allocated"] == 20
    assert line["quantity_shortage"] == 0
    assert _inventory_quantity(client, auth_headers["super"], "E2E-ONHAND-01") == 80

    # A purchase request is impossible because there is no remaining shortage.
    unnecessary = client.post(
        f"/api/v1/projects/{project['id']}/purchase-requests",
        headers=auth_headers["user"],
        json={"item_id": item["id"], "reason": "Just in case"},
    )
    assert unnecessary.status_code == 409
    assert unnecessary.json()["error"]["code"] == "NO_SHORTAGE"

    # Production cannot start before a progress update, but can start directly
    # once the project is ready.
    progress = client.post(
        f"/api/v1/projects/{project['id']}/progress-logs",
        headers=auth_headers["user"],
        json={"note": "Schematic and PCB layout complete", "progress_percent": 45},
    )
    assert progress.status_code == 201, progress.text
    assert progress.json()["progress_percent"] == 45

    started = client.post(
        f"/api/v1/projects/{project['id']}/start-production", headers=auth_headers["admin"]
    )
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "IN_PRODUCTION"

    testing = client.post(
        f"/api/v1/projects/{project['id']}/submit-testing",
        headers=auth_headers["admin"],
        json={"tester_id": str(standard_users["tester"].id)},
    )
    assert testing.status_code == 200, testing.text
    assert testing.json()["status"] == "IN_TESTING"

    passed = client.post(
        f"/api/v1/projects/{project['id']}/test-result",
        headers=auth_headers["tester"],
        json={"result": "PASS", "note": "Functional and thermal tests passed"},
    )
    assert passed.status_code == 200, passed.text
    assert passed.json()["test_result"] == "PASS"

    completed = client.post(
        f"/api/v1/projects/{project['id']}/complete",
        headers=auth_headers["admin"],
        json={"note": "Delivered to customer"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["progress_percent"] == 100

    # Completed projects are excluded from the Time Counter.
    now = datetime.now(ZoneInfo(settings.scheduler_timezone))
    result = run_time_counter(db, now=now)
    assert result.evaluated_projects == 0
    assert result.alerts_created == 0

    project_actions = _audit_ids(
        client,
        auth_headers["super"],
        entity="project",
        entity_id=project["id"],
    )
    assert {"CREATE", "STATUS_CHANGED", "TEST_RESULT"} <= project_actions
    inventory_actions = _audit_ids(
        client,
        auth_headers["super"],
        entity="inventory_item",
        entity_id=item["id"],
    )
    assert "INVENTORY_ALLOCATED" in inventory_actions


def test_workflow_shortage_purchase_delivery_alerts_and_retest(
    client: TestClient, auth_headers, standard_users, db
):
    """A shortage blocks production until purchase requests are delivered."""
    partial = create_inventory_item(client, auth_headers["super"], sku="E2E-SHORT-A", quantity=5)
    empty = create_inventory_item(client, auth_headers["super"], sku="E2E-SHORT-B", quantity=0)
    member_id = str(standard_users["user"].id)

    project = create_project(
        client,
        auth_headers["admin"],
        name="E2E Shortage Build",
        member_ids=[member_id],
        bom=[(partial["id"], 8), (empty["id"], 4)],
    )

    # Partial stock is reserved, but the project cannot leave inventory hold.
    assert project["status"] == "PENDING_INVENTORY"
    assert project["is_inventory_ready"] is False
    assert project["shortage_count"] == 2
    lines = {line["item"]["sku"]: line for line in project["bom_lines"]}
    assert lines["E2E-SHORT-A"]["quantity_allocated"] == 5
    assert lines["E2E-SHORT-A"]["quantity_shortage"] == 3
    assert lines["E2E-SHORT-B"]["quantity_allocated"] == 0
    assert lines["E2E-SHORT-B"]["quantity_shortage"] == 4

    # The member raises requests; the default quantity is exactly the shortage.
    over_request = client.post(
        f"/api/v1/projects/{project['id']}/purchase-requests",
        headers=auth_headers["user"],
        json={"item_id": empty["id"], "quantity": 5},
    )
    assert over_request.status_code == 422
    assert over_request.json()["error"]["code"] == "QUANTITY_EXCEEDS_SHORTAGE"

    request_a = create_purchase_request(
        client, auth_headers["user"], project["id"], partial["id"], reason="PCB shortage"
    )
    assert request_a["quantity"] == 3
    assert request_a["status"] == "PENDING"
    assert request_a["requested_by"] == str(standard_users["user"].id)

    request_b = create_purchase_request(client, auth_headers["user"], project["id"], empty["id"])
    assert request_b["quantity"] == 4

    duplicate = client.post(
        f"/api/v1/projects/{project['id']}/purchase-requests",
        headers=auth_headers["user"],
        json={"item_id": partial["id"]},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "NO_SHORTAGE"

    # Users outside the project cannot raise or review requests.
    outsider = client.post(
        f"/api/v1/projects/{project['id']}/purchase-requests",
        headers=auth_headers["other"],
        json={"item_id": empty["id"]},
    )
    assert outsider.status_code == 403
    user_approval = client.post(
        f"/api/v1/purchase-requests/{request_a['id']}/approve", headers=auth_headers["user"]
    )
    assert user_approval.status_code == 403

    # The BOM is frozen once a purchase request exists.
    locked_bom = client.put(
        f"/api/v1/projects/{project['id']}/bom",
        headers=auth_headers["admin"],
        json={"lines": []},
    )
    assert locked_bom.status_code == 409
    assert locked_bom.json()["error"]["code"] == "BOM_LOCKED"

    approved_a = client.post(
        f"/api/v1/purchase-requests/{request_a['id']}/approve", headers=auth_headers["admin"]
    )
    assert approved_a.status_code == 200, approved_a.text
    assert approved_a.json()["status"] == "APPROVED"
    approved_b = client.post(
        f"/api/v1/purchase-requests/{request_b['id']}/approve", headers=auth_headers["admin"]
    )
    assert approved_b.status_code == 200, approved_b.text

    # Ordering pauses the project and records the delivery delay reason.
    ordered_a = client.post(
        f"/api/v1/purchase-requests/{request_a['id']}/order",
        headers=auth_headers["admin"],
        json={"delay_reason": DELAY_REASON},
    )
    assert ordered_a.status_code == 200, ordered_a.text
    assert ordered_a.json()["status"] == "ORDERED"
    paused = _get_project(client, auth_headers["user"], project["id"])
    assert paused["status"] == "AWAITING_DELIVERY"
    assert paused["paused_from_status"] == "PENDING_INVENTORY"
    assert paused["delay_reason"] == DELAY_REASON

    member_order = client.post(
        f"/api/v1/purchase-requests/{request_b['id']}/order",
        headers=auth_headers["user"],
        json={"delay_reason": DELAY_REASON},
    )
    assert member_order.status_code == 403

    ordered_b = client.post(
        f"/api/v1/purchase-requests/{request_b['id']}/order",
        headers=auth_headers["admin"],
        json={"delay_reason": DELAY_REASON},
    )
    assert ordered_b.status_code == 200, ordered_b.text
    still_paused = _get_project(client, auth_headers["user"], project["id"])
    assert still_paused["status"] == "AWAITING_DELIVERY"
    assert still_paused["paused_from_status"] == "PENDING_INVENTORY"

    # A partially delivered order keeps the project waiting for the rest.
    delivered_a = client.post(
        f"/api/v1/purchase-requests/{request_a['id']}/deliver", headers=auth_headers["admin"]
    )
    assert delivered_a.status_code == 200, delivered_a.text
    assert delivered_a.json()["status"] == "DELIVERED"
    # The 3 received units are allocated straight to the BOM, leaving no free stock.
    assert _inventory_quantity(client, auth_headers["super"], "E2E-SHORT-A") == 0
    waiting = _get_project(client, auth_headers["user"], project["id"])
    assert waiting["status"] == "AWAITING_DELIVERY"
    assert waiting["is_inventory_ready"] is False

    # Time Counter escalation while the project waits for the second delivery.
    now = datetime.now(ZoneInfo(settings.scheduler_timezone))
    _age_project(db, project["id"], days=10, now=now)
    first_run = run_time_counter(db, now=now)
    assert first_run.evaluated_projects == 1
    assert first_run.escalated_projects == 1
    assert first_run.severe_projects == 0
    assert first_run.alerts_created == 1  # the admin, not a regular member

    admin_alerts = client.get("/api/v1/alerts?page_size=50", headers=auth_headers["admin"]).json()
    assert admin_alerts["total"] == 1
    assert admin_alerts["items"][0]["type"] == "ESCALATED"
    assert admin_alerts["items"][0]["project_id"] == project["id"]
    assert "10 days" in admin_alerts["items"][0]["message"]

    member_alerts = client.get("/api/v1/alerts?page_size=50", headers=auth_headers["user"]).json()
    assert member_alerts["total"] == 0

    second_run = run_time_counter(db, now=now)
    assert second_run.alerts_created == 0
    assert second_run.duplicates_skipped == 1
    assert (
        client.get("/api/v1/alerts/unread-count", headers=auth_headers["admin"]).json()["unread"]
        == 1
    )
    read = client.post(
        f"/api/v1/alerts/{admin_alerts['items'][0]['id']}/read", headers=auth_headers["admin"]
    )
    assert read.status_code == 200
    assert (
        client.get("/api/v1/alerts/unread-count", headers=auth_headers["admin"]).json()["unread"]
        == 0
    )

    # The final delivery allocates everything and restores the paused status.
    delivered_b = client.post(
        f"/api/v1/purchase-requests/{request_b['id']}/deliver", headers=auth_headers["admin"]
    )
    assert delivered_b.status_code == 200, delivered_b.text
    # 4 units received and immediately allocated, leaving no free stock.
    assert _inventory_quantity(client, auth_headers["super"], "E2E-SHORT-B") == 0

    ready = _get_project(client, auth_headers["user"], project["id"])
    assert ready["status"] == "READY_FOR_PRODUCTION"
    assert ready["is_inventory_ready"] is True
    assert ready["shortage_count"] == 0
    assert ready["paused_from_status"] is None
    assert all(
        line["quantity_allocated"] == line["quantity_required"] for line in ready["bom_lines"]
    )

    # Production -> failed test -> re-test -> sign-off.
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/start-production", headers=auth_headers["admin"]
        ).json()["status"]
        == "IN_PRODUCTION"
    )
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/submit-testing",
            headers=auth_headers["admin"],
            json={"tester_id": str(standard_users["tester"].id)},
        ).status_code
        == 200
    )
    failed = client.post(
        f"/api/v1/projects/{project['id']}/test-result",
        headers=auth_headers["tester"],
        json={"result": "FAIL", "note": "Connector misalignment on unit 2"},
    )
    assert failed.status_code == 200, failed.text
    assert failed.json()["status"] == "IN_PRODUCTION"

    early_signoff = client.post(
        f"/api/v1/projects/{project['id']}/complete",
        headers=auth_headers["admin"],
        json={"note": "Should be rejected"},
    )
    assert early_signoff.status_code == 409

    resubmitted = client.post(
        f"/api/v1/projects/{project['id']}/submit-testing",
        headers=auth_headers["admin"],
        json={"tester_id": str(standard_users["tester"].id)},
    )
    assert resubmitted.status_code == 200, resubmitted.text
    assert (
        client.post(
            f"/api/v1/projects/{project['id']}/test-result",
            headers=auth_headers["tester"],
            json={"result": "PASS", "note": "Re-test passed after connector fix"},
        ).json()["test_result"]
        == "PASS"
    )
    completed = client.post(
        f"/api/v1/projects/{project['id']}/complete",
        headers=auth_headers["admin"],
        json={"note": "Signed off"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["progress_percent"] == 100

    # Audit trail for the whole purchase flow.
    request_actions = _audit_ids(
        client, auth_headers["super"], entity="purchase_request", entity_id=request_a["id"]
    )
    assert {"CREATE", "APPROVE", "ORDER", "DELIVER"} <= request_actions
    item_actions = _audit_ids(
        client, auth_headers["super"], entity="inventory_item", entity_id=partial["id"]
    )
    assert {"INVENTORY_ALLOCATED", "INVENTORY_RECEIVED"} <= item_actions

    # Completed work is no longer evaluated and the audit viewer stays restricted.
    assert run_time_counter(db, now=now).evaluated_projects == 0
    assert client.get("/api/v1/audit-logs", headers=auth_headers["admin"]).status_code == 403


def test_workflow_rejected_purchase_can_be_replaced(
    client: TestClient, auth_headers, standard_users
):
    """A rejected request releases the shortage for a replacement request."""
    item = create_inventory_item(client, auth_headers["super"], sku="E2E-REJECT-01", quantity=0)
    project = create_project(
        client,
        auth_headers["admin"],
        name="E2E Rejection Build",
        member_ids=[str(standard_users["user"].id)],
        bom=[(item["id"], 2)],
    )
    assert project["status"] == "PENDING_INVENTORY"

    first = create_purchase_request(client, auth_headers["user"], project["id"], item["id"])
    rejected = client.post(
        f"/api/v1/purchase-requests/{first['id']}/reject",
        headers=auth_headers["admin"],
        json={"reason": "Use the approved vendor catalogue instead"},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "REJECTED"
    assert rejected.json()["review_note"] == "Use the approved vendor catalogue instead"

    invalid_order = client.post(
        f"/api/v1/purchase-requests/{first['id']}/order",
        headers=auth_headers["admin"],
        json={"delay_reason": DELAY_REASON},
    )
    assert invalid_order.status_code == 409
    assert invalid_order.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"

    # The rejected quantity is available again, so a replacement can be raised.
    replacement = create_purchase_request(
        client, auth_headers["user"], project["id"], item["id"], reason="Correct vendor"
    )
    assert replacement["quantity"] == 2
    assert replacement["status"] == "PENDING"

    assert (
        client.post(
            f"/api/v1/purchase-requests/{replacement['id']}/approve", headers=auth_headers["admin"]
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/purchase-requests/{replacement['id']}/order",
            headers=auth_headers["admin"],
            json={"delay_reason": DELAY_REASON},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/purchase-requests/{replacement['id']}/deliver", headers=auth_headers["admin"]
        ).status_code
        == 200
    )

    ready = _get_project(client, auth_headers["user"], project["id"])
    assert ready["status"] == "READY_FOR_PRODUCTION"
    assert ready["is_inventory_ready"] is True
    # Stock received for the replacement was allocated straight to the BOM.
    assert ready["bom_lines"][0]["quantity_allocated"] == 2
    assert _inventory_quantity(client, auth_headers["super"], "E2E-REJECT-01") == 0

    request_actions = _audit_ids(
        client, auth_headers["super"], entity="purchase_request", entity_id=first["id"]
    )
    assert {"CREATE", "REJECT"} <= request_actions, request_actions
    item_actions = _audit_ids(
        client, auth_headers["super"], entity="inventory_item", entity_id=item["id"]
    )
    assert {"INVENTORY_RECEIVED", "INVENTORY_ALLOCATED"} <= item_actions
