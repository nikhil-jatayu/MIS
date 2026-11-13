from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DatabaseSession, SuperAdminUser
from app.models.enums import AlertType
from app.schemas.alerts_audit_reporting import AlertsReportSection, AuditReportSection
from app.services import alerts_audit_reporting_service

router = APIRouter(prefix="/reports/alerts-audit", tags=["Alerts & Audit Reports"])


@router.get("/alerts", response_model=AlertsReportSection)
def alerts_report(
    db: DatabaseSession,
    actor: CurrentUser,
    date_from: date,
    date_to: date,
    project_id: UUID | None = None,
    alert_type: AlertType | None = None,
    is_read: bool | None = None,
) -> AlertsReportSection:
    _, report = alerts_audit_reporting_service.get_alerts_report(
        db,
        actor=actor,
        date_from=date_from,
        date_to=date_to,
        project_id=project_id,
        alert_type=alert_type,
        is_read=is_read,
    )
    return report


@router.get("/audit", response_model=AuditReportSection)
def audit_report(
    db: DatabaseSession,
    _: SuperAdminUser,
    date_from: date,
    date_to: date,
    actor_id: UUID | None = None,
    action: str | None = Query(default=None, max_length=50),
    entity: str | None = Query(default=None, max_length=80),
) -> AuditReportSection:
    _, report = alerts_audit_reporting_service.get_audit_report(
        db,
        date_from=date_from,
        date_to=date_to,
        actor_id=actor_id,
        action=action,
        entity=entity,
    )
    return report
