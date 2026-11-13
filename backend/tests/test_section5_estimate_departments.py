from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.helpers import create_project


def test_estimate_is_editable_once_by_assigned_member(
    client: TestClient, auth_headers, standard_users
):
    project = create_project(
        client,
        auth_headers["admin"],
        name="Estimate workflow",
        member_ids=[str(standard_users["user"].id)],
    )
    estimate_url = f"/api/v1/projects/{project['id']}/estimate"
    first_estimate = date.today() + timedelta(days=20)
    revised_estimate = date.today() + timedelta(days=25)

    first = client.patch(
        estimate_url,
        headers=auth_headers["user"],
        json={"estimated_completion_date": first_estimate.isoformat()},
    )
    assert first.status_code == 200, first.text
    assert first.json()["estimated_completion_date"] == first_estimate.isoformat()
    assert first.json()["estimated_completion_edited_by_member"] is True
    assert first.json()["estimate_setter"]["email"] == "member@jatayues.com"

    second = client.patch(
        estimate_url,
        headers=auth_headers["user"],
        json={"estimated_completion_date": revised_estimate.isoformat()},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ESTIMATE_LOCKED"

    override = client.patch(
        estimate_url,
        headers=auth_headers["admin"],
        json={"estimated_completion_date": revised_estimate.isoformat()},
    )
    assert override.status_code == 200, override.text
    assert override.json()["estimated_completion_date"] == revised_estimate.isoformat()
    assert override.json()["estimate_setter"]["email"] == "admin@jatayues.com"

    audit = client.get(
        "/api/v1/audit-logs?entity=project&action=ESTIMATE_CHANGED",
        headers=auth_headers["super"],
    )
    assert audit.status_code == 200
    assert audit.json()["total"] >= 2


def test_estimate_requires_project_membership(client: TestClient, auth_headers, standard_users):
    project = create_project(
        client,
        auth_headers["admin"],
        name="Estimate permissions",
        member_ids=[str(standard_users["user"].id)],
    )
    response = client.patch(
        f"/api/v1/projects/{project['id']}/estimate",
        headers=auth_headers["other"],
        json={"estimated_completion_date": (date.today() + timedelta(days=10)).isoformat()},
    )
    assert response.status_code == 403


def test_estimate_rejects_date_before_start(client: TestClient, auth_headers, standard_users):
    project = create_project(
        client,
        auth_headers["admin"],
        name="Estimate validation",
        member_ids=[str(standard_users["user"].id)],
        estimated_completion_date=date.today(),
    )
    response = client.patch(
        f"/api/v1/projects/{project['id']}/estimate",
        headers=auth_headers["user"],
        json={"estimated_completion_date": (date.today() - timedelta(days=5)).isoformat()},
    )
    assert response.status_code == 422


def test_users_can_be_filtered_by_department(client: TestClient, auth_headers, standard_users):
    updated = client.patch(
        f"/api/v1/users/{standard_users['user'].id}",
        headers=auth_headers["super"],
        json={"department": "R_D"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["department"] == "R_D"

    response = client.get(
        "/api/v1/users?department=R_D&page_size=50", headers=auth_headers["super"]
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert all(item["department"] == "R_D" for item in items)
    assert any(item["email"] == "member@jatayues.com" for item in items)


def test_department_other_requires_description(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/users",
        headers=auth_headers["super"],
        json={
            "name": "Other Dept User",
            "email": "other.dept@jatayues.com",
            "role": "USER",
            "department": "other",
            "temporary_password": "OtherDept@123",
        },
    )
    assert response.status_code == 422

    created = client.post(
        "/api/v1/users",
        headers=auth_headers["super"],
        json={
            "name": "Other Dept User",
            "email": "other.dept@jatayues.com",
            "role": "USER",
            "department": "other",
            "department_other": "Fabrication",
            "temporary_password": "OtherDept@123",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["department"] == "other"
    assert created.json()["department_other"] == "Fabrication"


def test_member_department_defaults_to_user_profile(
    client: TestClient, auth_headers, standard_users
):
    user_id = standard_users["user"].id
    updated = client.patch(
        f"/api/v1/users/{user_id}",
        headers=auth_headers["super"],
        json={"department": "R_D"},
    )
    assert updated.status_code == 200, updated.text

    response = client.post(
        "/api/v1/projects",
        headers=auth_headers["admin"],
        json={
            "name": "Department autofill",
            "type": "PRODUCTION",
            "priority": "MEDIUM",
            "start_date": date.today().isoformat(),
            "members": [{"user_id": str(user_id)}],
            "bom": [],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["members"][0]["department"] == "R_D"


def test_department_can_be_cleared(client: TestClient, auth_headers, standard_users):
    user_id = standard_users["user"].id
    client.patch(
        f"/api/v1/users/{user_id}",
        headers=auth_headers["super"],
        json={"department": "store"},
    )
    cleared = client.patch(
        f"/api/v1/users/{user_id}",
        headers=auth_headers["super"],
        json={"department": None},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["department"] is None
