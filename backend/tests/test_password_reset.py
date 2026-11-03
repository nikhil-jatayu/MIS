from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.models.password_reset import PasswordResetToken
from app.models.production import ProductionAction, ProductionEntry
from app.services import auth_service


def test_forgot_password_response_does_not_disclose_account_existence(
    client: TestClient, standard_users, monkeypatch
):
    auth_service.password_reset_limiter.clear()
    delivered: list[tuple[str, str]] = []

    def capture_email(*, recipient: str, reset_url: str) -> None:
        delivered.append((recipient, reset_url))

    monkeypatch.setattr(auth_service, "send_password_reset_email", capture_email)

    known = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "super@jatayues.com"},
    )
    unknown = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nobody@jatayues.com"},
    )

    assert known.status_code == 202
    assert unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(delivered) == 1
    assert delivered[0][0] == "super@jatayues.com"
    auth_service.password_reset_limiter.clear()


def test_password_reset_token_is_single_use_and_changes_password(
    client: TestClient, standard_users, db: Session, monkeypatch
):
    auth_service.password_reset_limiter.clear()
    delivered: list[str] = []

    def capture_email(*, recipient: str, reset_url: str) -> None:
        delivered.append(reset_url)

    monkeypatch.setattr(auth_service, "send_password_reset_email", capture_email)
    requested = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "super@jatayues.com"},
    )
    assert requested.status_code == 202
    assert len(delivered) == 1
    token = parse_qs(urlparse(delivered[0]).query)["token"][0]
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    stored = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    assert stored is not None
    assert stored.expires_at > datetime.now(UTC)

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewSecurePass@456"},
    )
    assert reset.status_code == 200
    assert reset.json()["message"]

    replay = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "AnotherSecurePass@789"},
    )
    assert replay.status_code == 422
    assert replay.json()["error"]["code"] == "INVALID_PASSWORD_RESET_TOKEN"

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "super@jatayues.com", "password": "SuperPass@123"},
    )
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "super@jatayues.com", "password": "NewSecurePass@456"},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200
    auth_service.password_reset_limiter.clear()


def test_dashboard_includes_production_metrics_by_unit(
    client: TestClient, auth_headers, standard_users, db: Session
):
    actor = standard_users["super"]
    today = datetime.now(UTC).date()
    entry = ProductionEntry(
        production_date=today,
        production_line="Assembly Line A",
        product_model="Dashboard Test Unit",
        process_stage="Assembly",
        unit_of_measure="pcs",
        planned_quantity=110,
        actual_quantity=100,
        accepted_quantity=94,
        rework_quantity=3,
        production_hours=8,
        downtime_hours=1,
        created_by=actor.id,
    )
    db.add(entry)
    db.flush()
    db.add(
        ProductionAction(
            action_number="DASHBOARD-OVERDUE-TEST",
            date_raised=today,
            issue_observation="Dashboard test action",
            corrective_action="Complete the dashboard test action",
            deadline=today,
            status="OPEN",
            created_by=actor.id,
            production_entry_id=entry.id,
        )
    )
    db.commit()

    response = client.get("/api/v1/dashboard", headers=auth_headers["super"])
    assert response.status_code == 200, response.text
    production = response.json()["production"]
    assert production["entries_count"] == 1
    assert production["open_actions"] == 1
    assert production["overdue_actions"] == 0  # due today is not overdue
    assert production["units"] == [
        {
            "unit_of_measure": "pcs",
            "entries_count": 1,
            "planned_quantity": 110.0,
            "actual_quantity": 100.0,
            "accepted_first_pass_quantity": 94.0,
            "rework_quantity": 3.0,
            "plan_achievement_percent": 90.91,
            "first_pass_yield_percent": 94.0,
            "rework_rate_percent": 3.0,
        }
    ]
