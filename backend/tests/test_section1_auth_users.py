from __future__ import annotations

from sqlalchemy import func, select

from app.models.user import User
from app.services.seed_service import seed_database


def test_seed_is_idempotent_and_first_login_forces_password_change(client, db):
    first = seed_database(db)
    second = seed_database(db)
    assert first["super_admins_created"] == 2
    assert second["super_admins_created"] == 0
    assert db.scalar(select(func.count()).select_from(User)) == 2

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "ashmant@jatayues.com", "password": "ashmant@123"},
    )
    assert login.status_code == 200, login.text
    payload = login.json()
    assert payload["user"]["must_change_password"] is True
    headers = {"Authorization": f"Bearer {payload['access_token']}"}

    blocked = client.get("/api/v1/users", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"

    changed = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": "ashmant@123",
            "new_password": "NewAshmant@456",
        },
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["must_change_password"] is False

    allowed = client.get("/api/v1/users", headers=headers)
    assert allowed.status_code == 200
    assert allowed.json()["total"] == 2

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "ashmant@jatayues.com", "password": "ashmant@123"},
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "ashmant@jatayues.com", "password": "NewAshmant@456"},
    )
    assert new_login.status_code == 200


def test_cookie_auth_and_logout(client, standard_users):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "super@jatayues.com", "password": "SuperPass@123"},
    )
    assert login.status_code == 200
    assert "jes_access_token" in client.cookies
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "SUPER_ADMIN"

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_role_guards_on_super_admin_routes(client, auth_headers):
    assert client.get("/api/v1/users", headers=auth_headers["user"]).status_code == 403
    assert client.get("/api/v1/users", headers=auth_headers["admin"]).status_code == 200

    inventory_payload = {"name": "Resistor", "sku": "RES-001", "quantity_available": 10}
    assert (
        client.post(
            "/api/v1/inventory", headers=auth_headers["admin"], json=inventory_payload
        ).status_code
        == 403
    )
    created = client.post(
        "/api/v1/inventory", headers=auth_headers["super"], json=inventory_payload
    )
    assert created.status_code == 201, created.text

    assert client.get("/api/v1/audit-logs", headers=auth_headers["user"]).status_code == 403
    assert client.get("/api/v1/audit-logs", headers=auth_headers["admin"]).status_code == 403
    assert client.get("/api/v1/audit-logs", headers=auth_headers["super"]).status_code == 200


def test_inactive_user_cannot_login(client, user_factory):
    user_factory(is_active=False, email="inactive@jatayues.com", password="Inactive@123")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@jatayues.com", "password": "Inactive@123"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCOUNT_INACTIVE"


def test_error_envelope_and_validation(client, auth_headers):
    missing = client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000",
        headers=auth_headers["user"],
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
    assert "request_id" in missing.json()["error"]

    invalid = client.post("/api/v1/auth/login", json={"email": "not-an-email"})
    assert invalid.status_code == 422
    body = invalid.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert any(item["field"] == "password" for item in body["details"])

    client.cookies.clear()
    unauthorized = client.get("/api/v1/projects")
    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "UNAUTHORIZED"
    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "UNAUTHORIZED"


def test_super_admin_user_management_and_password_reset(client, auth_headers):
    create = client.post(
        "/api/v1/users",
        headers=auth_headers["super"],
        json={
            "name": "New Engineer",
            "email": "engineer@jatayues.com",
            "role": "USER",
            "temporary_password": "TempPass@123",
        },
    )
    assert create.status_code == 201, create.text
    user_id = create.json()["id"]
    assert create.json()["must_change_password"] is True

    duplicate = client.post(
        "/api/v1/users",
        headers=auth_headers["super"],
        json={
            "name": "Duplicate",
            "email": "engineer@jatayues.com",
            "role": "USER",
            "temporary_password": "TempPass@123",
        },
    )
    assert duplicate.status_code == 409

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "engineer@jatayues.com", "password": "TempPass@123"},
    )
    assert login.status_code == 200
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/v1/projects", headers=user_headers).status_code == 403

    reset = client.post(
        f"/api/v1/users/{user_id}/reset-password",
        headers=auth_headers["super"],
        json={"new_password": "ResetPass@456"},
    )
    assert reset.status_code == 200
    assert reset.json()["must_change_password"] is True

    role_change = client.patch(
        f"/api/v1/users/{user_id}",
        headers=auth_headers["super"],
        json={"role": "ADMIN"},
    )
    assert role_change.status_code == 200
    assert role_change.json()["role"] == "ADMIN"


def test_password_policy_and_self_protection(client, auth_headers, standard_users):
    user = standard_users["super"]
    weak = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers["super"],
        json={"current_password": "SuperPass@123", "new_password": "weakpass"},
    )
    assert weak.status_code == 422

    self_deactivate = client.patch(
        f"/api/v1/users/{user.id}",
        headers=auth_headers["super"],
        json={"is_active": False},
    )
    assert self_deactivate.status_code == 422
    assert self_deactivate.json()["error"]["code"] == "SELF_DEACTIVATION"


def test_user_list_pagination_and_filters(client, auth_headers):
    response = client.get(
        "/api/v1/users?page=1&page_size=2&role=USER&is_active=true",
        headers=auth_headers["super"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["page_size"] == 2
    assert body["total"] >= 2
    assert body["pages"] >= 1
    assert all(item["role"] == "USER" for item in body["items"])
