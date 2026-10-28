from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.models.project import Project
from app.services.alert_service import run_time_counter
from tests.helpers import create_project


def _shift_project_age(db, project_id: str, *, days: int, now: datetime) -> None:
    project = db.get(Project, UUID(project_id))
    assert project is not None
    project.status_changed_at = now - timedelta(days=days)
    db.commit()


def test_threshold_settings_validation_and_audit(client: TestClient, auth_headers):
    initial = client.get("/api/v1/settings/thresholds", headers=auth_headers["super"])
    assert initial.status_code == 200
    assert initial.json()["safe_threshold_days"] == 3

    assert (
        client.get("/api/v1/settings/thresholds", headers=auth_headers["admin"]).status_code == 403
    )

    update = client.put(
        "/api/v1/settings/thresholds",
        headers=auth_headers["super"],
        json={
            "safe_threshold_days": 4,
            "escalation_threshold_days": 10,
            "deadline_reminder_days": 7,
            "severe_delay_multiplier": 2.5,
        },
    )
    assert update.status_code == 200, update.text
    assert update.json()["escalation_threshold_days"] == 10

    invalid = client.put(
        "/api/v1/settings/thresholds",
        headers=auth_headers["super"],
        json={
            "safe_threshold_days": 10,
            "escalation_threshold_days": 5,
            "deadline_reminder_days": 7,
            "severe_delay_multiplier": 2.0,
        },
    )
    assert invalid.status_code == 422

    audit = client.get(
        "/api/v1/audit-logs?entity=settings&action=UPDATE",
        headers=auth_headers["super"],
    )
    assert audit.status_code == 200
    assert audit.json()["total"] == 1
    assert audit.json()["items"][0]["after"]["escalation_threshold_days"] == 10


def test_time_counter_standard_escalated_severe_and_deduplication(
    client: TestClient, auth_headers, standard_users, db
):
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    member_id = str(standard_users["user"].id)
    standard = create_project(
        client,
        auth_headers["admin"],
        name="Standard Delay",
        member_ids=[member_id],
        bom=[],
    )
    escalated = create_project(
        client,
        auth_headers["admin"],
        name="Escalated Delay",
        member_ids=[member_id],
        bom=[],
    )
    severe = create_project(
        client,
        auth_headers["admin"],
        name="Severe Delay",
        member_ids=[member_id],
        bom=[],
    )
    _shift_project_age(db, standard["id"], days=5, now=now)
    _shift_project_age(db, escalated["id"], days=10, now=now)
    _shift_project_age(db, severe["id"], days=20, now=now)

    result = run_time_counter(db, now=now)
    assert result.evaluated_projects == 3
    assert result.standard_projects == 1
    assert result.escalated_projects == 2
    assert result.severe_projects == 1
    # 1 standard member + 1 escalated admin + 1 escalated admin + 1 severe super admin
    assert result.alerts_created == 4

    user_alerts = client.get("/api/v1/alerts?page_size=50", headers=auth_headers["user"]).json()
    assert user_alerts["total"] == 1
    assert user_alerts["items"][0]["type"] == "STANDARD"
    assert user_alerts["items"][0]["project_id"] == standard["id"]

    admin_alerts = client.get("/api/v1/alerts?page_size=50", headers=auth_headers["admin"]).json()
    assert admin_alerts["total"] == 2
    assert {item["project_id"] for item in admin_alerts["items"]} == {
        escalated["id"],
        severe["id"],
    }
    assert all(item["type"] == "ESCALATED" for item in admin_alerts["items"])

    super_alerts = client.get("/api/v1/alerts?page_size=50", headers=auth_headers["super"]).json()
    assert super_alerts["total"] == 1
    assert super_alerts["items"][0]["project_id"] == severe["id"]
    assert super_alerts["items"][0]["type"] == "ESCALATED"

    second = run_time_counter(db, now=now)
    assert second.alerts_created == 0
    assert second.duplicates_skipped == 4

    count = client.get("/api/v1/alerts/unread-count", headers=auth_headers["user"])
    assert count.status_code == 200
    assert count.json()["unread"] == 1

    read = client.post(
        f"/api/v1/alerts/{user_alerts['items'][0]['id']}/read",
        headers=auth_headers["user"],
    )
    assert read.status_code == 200
    assert (
        client.get("/api/v1/alerts/unread-count", headers=auth_headers["user"]).json()["unread"]
        == 0
    )

    admin_read_all = client.post("/api/v1/alerts/read-all", headers=auth_headers["admin"])
    assert admin_read_all.status_code == 200
    assert "2 alert" in admin_read_all.json()["message"]

    forbidden = client.post(
        f"/api/v1/alerts/{admin_alerts['items'][0]['id']}/read",
        headers=auth_headers["user"],
    )
    assert forbidden.status_code == 404


def test_deadline_reminder_window_and_safe_project(
    client: TestClient, auth_headers, standard_users, db
):
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    member_id = str(standard_users["user"].id)
    today = now.date()
    due_soon = create_project(
        client,
        auth_headers["admin"],
        name="Due Soon",
        member_ids=[member_id],
        bom=[],
        end_date=today + timedelta(days=2),
    )
    safe = create_project(
        client,
        auth_headers["admin"],
        name="Comfortably Safe",
        member_ids=[member_id],
        bom=[],
        end_date=today + timedelta(days=30),
    )
    _shift_project_age(db, due_soon["id"], days=1, now=now)
    _shift_project_age(db, safe["id"], days=1, now=now)

    result = run_time_counter(db, now=now)
    assert result.standard_projects == 1
    assert result.alerts_created == 1

    alerts = client.get("/api/v1/alerts?page_size=50", headers=auth_headers["user"]).json()
    assert alerts["total"] == 1
    assert alerts["items"][0]["project_id"] == due_soon["id"]
    assert "deadline" in alerts["items"][0]["message"].lower()


def test_audit_viewer_filters_and_permissions(client: TestClient, auth_headers, standard_users):
    project = create_project(
        client,
        auth_headers["admin"],
        name="Audited Project",
        member_ids=[str(standard_users["user"].id)],
        bom=[],
    )
    client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=auth_headers["admin"],
        json={"end_date": (datetime.now().date() + timedelta(days=90)).isoformat()},
    )

    admin = client.get("/api/v1/audit-logs", headers=auth_headers["admin"])
    assert admin.status_code == 403

    filtered = client.get(
        f"/api/v1/audit-logs?entity=project&entity_id={project['id']}",
        headers=auth_headers["super"],
    )
    assert filtered.status_code == 200
    actions = {item["action"] for item in filtered.json()["items"]}
    assert "CREATE" in actions
    assert "DEADLINE_CHANGED" in actions
    assert all(item["entity_id"] == project["id"] for item in filtered.json()["items"])
    assert filtered.json()["items"][0]["actor"] is not None

    no_match = client.get(
        "/api/v1/audit-logs?entity=project&action=DELETE",
        headers=auth_headers["super"],
    )
    assert no_match.status_code == 200
    assert no_match.json()["total"] == 0


def test_time_counter_endpoint_permissions(client: TestClient, auth_headers):
    assert client.post("/api/v1/alerts/run-check", headers=auth_headers["admin"]).status_code == 403
    response = client.post("/api/v1/alerts/run-check", headers=auth_headers["super"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert "evaluated_projects" in body
    assert "alerts_created" in body
