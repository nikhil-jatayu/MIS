from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from app.models.alert import Alert
from app.models.audit import AuditLog
from app.models.enums import AlertType
from tests.helpers import create_project


def test_alerts_report_is_scoped_to_current_recipient_and_supports_filters(
    client: TestClient, db, auth_headers, standard_users
):
    project = create_project(
        client,
        auth_headers["admin"],
        name="Alerts Reporting Scope Project",
        member_ids=[str(standard_users["user"].id)],
    )
    project_id = UUID(project["id"])
    today = date.today()
    db.add_all(
        [
            Alert(
                user_id=standard_users["user"].id,
                project_id=project_id,
                type=AlertType.STANDARD,
                message="Standard reminder for report test",
                is_read=False,
                alert_date=today,
            ),
            Alert(
                user_id=standard_users["user"].id,
                project_id=project_id,
                type=AlertType.ESCALATED,
                message="Escalated reminder for report test",
                is_read=True,
                alert_date=today,
            ),
            Alert(
                user_id=standard_users["other"].id,
                project_id=project_id,
                type=AlertType.ESCALATED,
                message="This belongs to another recipient",
                is_read=False,
                alert_date=today,
            ),
        ]
    )
    db.flush()

    response = client.get(
        "/api/v1/reports/alerts-audit/alerts",
        params={
            "date_from": today.isoformat(),
            "date_to": today.isoformat(),
            "project_id": project_id,
        },
        headers=auth_headers["user"],
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_alerts"] == 2
    assert body["unread_alerts"] == 1
    assert body["read_alerts"] == 1
    assert body["standard_alerts"] == 1
    assert body["escalated_alerts"] == 1
    assert body["projects_with_alerts"] == 1
    assert {item["message"] for item in body["items"]} == {
        "Standard reminder for report test",
        "Escalated reminder for report test",
    }

    filtered = client.get(
        "/api/v1/reports/alerts-audit/alerts",
        params={
            "date_from": today.isoformat(),
            "date_to": today.isoformat(),
            "alert_type": "ESCALATED",
            "is_read": "true",
        },
        headers=auth_headers["user"],
    )
    assert filtered.status_code == 200, filtered.text
    filtered_body = filtered.json()
    assert filtered_body["total_alerts"] == 1
    assert filtered_body["items"][0]["alert_type"] == "ESCALATED"
    assert filtered_body["items"][0]["is_read"] is True


def test_audit_report_is_super_admin_only_and_supports_filters(
    client: TestClient, db, auth_headers, standard_users
):
    today = date.today()
    db.add_all(
        [
            AuditLog(
                actor_id=standard_users["super"].id,
                action="REPORT_TEST_CREATE",
                entity="report_test_entity",
                entity_id="report-test-1",
                before=None,
                after={"safe": True},
                created_at=datetime.now(UTC),
            ),
            AuditLog(
                actor_id=standard_users["user"].id,
                action="REPORT_TEST_UPDATE",
                entity="report_test_entity",
                entity_id="report-test-1",
                before={"safe": True},
                after={"safe": False},
                created_at=datetime.now(UTC),
            ),
        ]
    )
    db.flush()

    forbidden = client.get(
        "/api/v1/reports/alerts-audit/audit",
        params={"date_from": today.isoformat(), "date_to": today.isoformat()},
        headers=auth_headers["admin"],
    )
    assert forbidden.status_code == 403

    response = client.get(
        "/api/v1/reports/alerts-audit/audit",
        params={
            "date_from": today.isoformat(),
            "date_to": today.isoformat(),
            "action": "REPORT_TEST_CREATE",
            "entity": "report_test_entity",
        },
        headers=auth_headers["super"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_events"] == 1
    assert body["unique_actors"] == 1
    assert body["unique_entity_references"] == 1
    assert body["action_breakdown"] == [{"label": "REPORT_TEST_CREATE", "count": 1}]
    assert body["items"][0]["actor_name"] == "Super Admin"
    assert "before" not in body["items"][0]
    assert "after" not in body["items"][0]


def test_alert_and_audit_reports_reject_reversed_and_overlong_ranges(
    client: TestClient, auth_headers
):
    reversed_alerts = client.get(
        "/api/v1/reports/alerts-audit/alerts",
        params={
            "date_from": date.today().isoformat(),
            "date_to": (date.today() - timedelta(days=1)).isoformat(),
        },
        headers=auth_headers["user"],
    )
    assert reversed_alerts.status_code == 422

    overlong_audit = client.get(
        "/api/v1/reports/alerts-audit/audit",
        params={"date_from": "2025-01-01", "date_to": date.today().isoformat()},
        headers=auth_headers["super"],
    )
    assert overlong_audit.status_code == 422
