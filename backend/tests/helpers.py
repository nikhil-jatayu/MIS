from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient


def create_inventory_item(
    client: TestClient,
    headers: dict[str, str],
    *,
    sku: str,
    quantity: int,
    name: str | None = None,
) -> dict:
    response = client.post(
        "/api/v1/inventory",
        headers=headers,
        json={"name": name or f"Item {sku}", "sku": sku, "quantity_available": quantity},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_project(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str,
    member_ids: list[str],
    bom: list[tuple[str, int]] | None = None,
    project_type: str = "PRODUCTION",
    priority: str = "HIGH",
    end_date: date | None = None,
) -> dict:
    payload = {
        "name": name,
        "description": "Project created by the automated test suite",
        "type": project_type,
        "priority": priority,
        "start_date": date.today().isoformat(),
        "end_date": (end_date or (date.today() + timedelta(days=30))).isoformat(),
        "members": [
            {"user_id": member_id, "role_in_project": "DEVELOPER"} for member_id in member_ids
        ],
        "bom": [
            {"item_id": item_id, "quantity_required": quantity} for item_id, quantity in (bom or [])
        ],
    }
    response = client.post("/api/v1/projects", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_purchase_request(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    item_id: str,
    quantity: int | None = None,
    reason: str = "Stock shortage",
) -> dict:
    body: dict = {"item_id": item_id, "reason": reason}
    if quantity is not None:
        body["quantity"] = quantity
    response = client.post(
        f"/api/v1/projects/{project_id}/purchase-requests", headers=headers, json=body
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_only(headers: dict[str, str]) -> dict[str, str]:
    return {"Authorization": headers["Authorization"]}
