from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.helpers import create_inventory_item, create_project, create_purchase_request


def test_operations_report_includes_project_inventory_and_purchase_sections(
    client: TestClient, auth_headers, standard_users
):
    item = create_inventory_item(
        client,
        auth_headers["super"],
        sku="OPS-REP-001",
        quantity=2,
        name="Operations Report Component",
    )
    project = create_project(
        client,
        auth_headers["admin"],
        name="Operations Reporting Project",
        member_ids=[str(standard_users["user"].id)],
        bom=[(item["id"], 5)],
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() - timedelta(days=1),
    )
    request = create_purchase_request(
        client, auth_headers["user"], project["id"], item["id"]
    )

    response = client.get(
        "/api/v1/operations/reports/summary",
        params={
            "date_from": (date.today() - timedelta(days=7)).isoformat(),
            "date_to": date.today().isoformat(),
        },
        headers=auth_headers["user"],
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["projects"]["total_projects"] == 1
    assert body["projects"]["current_overdue_projects"] == 1
    assert body["projects"]["items"][0]["id"] == project["id"]
    assert body["projects"]["items"][0]["shortage_lines"] == 1

    assert body["inventory"]["total_items"] == 1
    assert body["inventory"]["zero_stock_items"] == 1
    inventory_row = body["inventory"]["items"][0]
    assert inventory_row["sku"] == "OPS-REP-001"
    assert inventory_row["active_project_required"] == 5
    assert inventory_row["active_project_allocated"] == 2
    assert inventory_row["active_project_shortage"] == 3

    assert body["purchases"]["total_requests"] == 1
    assert body["purchases"]["items"][0]["id"] == request["id"]
    assert body["purchases"]["status_breakdown"] == [{"label": "PENDING", "count": 1}]


def test_operations_report_applies_project_and_purchase_filters(
    client: TestClient, auth_headers, standard_users
):
    item = create_inventory_item(
        client, auth_headers["super"], sku="OPS-FLT-001", quantity=0
    )
    project = create_project(
        client,
        auth_headers["admin"],
        name="Filtered Operations Project",
        member_ids=[str(standard_users["user"].id)],
        bom=[(item["id"], 4)],
        project_type="RND",
        priority="CRITICAL",
    )
    request = create_purchase_request(
        client, auth_headers["user"], project["id"], item["id"]
    )

    response = client.get(
        "/api/v1/operations/reports/summary",
        params={
            "date_from": (date.today() - timedelta(days=7)).isoformat(),
            "date_to": date.today().isoformat(),
            "project_id": project["id"],
            "project_type": "RND",
            "priority": "CRITICAL",
            "project_status": "PENDING_INVENTORY",
            "purchase_status": "PENDING",
        },
        headers=auth_headers["admin"],
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["filters"]["project_id"] == project["id"]
    assert body["projects"]["total_projects"] == 1
    assert body["inventory"]["items"][0]["sku"] == "OPS-FLT-001"
    assert body["purchases"]["total_requests"] == 1
    assert body["purchases"]["items"][0]["id"] == request["id"]


def test_operations_report_respects_user_purchase_visibility(
    client: TestClient, auth_headers, standard_users
):
    item = create_inventory_item(
        client, auth_headers["super"], sku="OPS-SEC-001", quantity=0
    )
    project = create_project(
        client,
        auth_headers["admin"],
        name="Private Purchase Scope Project",
        member_ids=[str(standard_users["user"].id)],
        bom=[(item["id"], 2)],
    )
    create_purchase_request(client, auth_headers["user"], project["id"], item["id"])

    response = client.get(
        "/api/v1/operations/reports/summary",
        params={
            "date_from": (date.today() - timedelta(days=7)).isoformat(),
            "date_to": date.today().isoformat(),
        },
        headers=auth_headers["other"],
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["projects"]["total_projects"] == 1
    assert body["purchases"]["total_requests"] == 0


def test_operations_report_rejects_reversed_and_overlong_dates(
    client: TestClient, auth_headers
):
    reversed_response = client.get(
        "/api/v1/operations/reports/summary",
        params={"date_from": "2026-11-04", "date_to": "2026-11-03"},
        headers=auth_headers["admin"],
    )
    assert reversed_response.status_code == 422

    long_response = client.get(
        "/api/v1/operations/reports/summary",
        params={"date_from": "2025-01-01", "date_to": "2026-11-04"},
        headers=auth_headers["admin"],
    )
    assert long_response.status_code == 422
