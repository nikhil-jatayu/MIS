from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportCountBreakdown(BaseModel):
    label: str
    count: int


class AlertsReportFilters(BaseModel):
    date_from: date
    date_to: date
    project_id: UUID | None = None
    alert_type: str | None = None
    is_read: bool | None = None


class AlertTrendPoint(BaseModel):
    period: date
    alerts_created: int


class AlertProjectBreakdown(BaseModel):
    project_id: UUID
    project_name: str
    total_alerts: int
    unread_alerts: int
    escalated_alerts: int


class AlertReportRow(BaseModel):
    id: UUID
    project_id: UUID
    project_name: str
    alert_type: str
    message: str
    alert_date: date
    created_at: datetime
    is_read: bool


class AlertsReportSection(BaseModel):
    total_alerts: int
    unread_alerts: int
    read_alerts: int
    standard_alerts: int
    escalated_alerts: int
    projects_with_alerts: int
    type_breakdown: list[ReportCountBreakdown]
    project_breakdown: list[AlertProjectBreakdown]
    trend: list[AlertTrendPoint]
    items: list[AlertReportRow]
    scope_note: str


class AuditReportFilters(BaseModel):
    date_from: date
    date_to: date
    actor_id: UUID | None = None
    action: str | None = None
    entity: str | None = None


class AuditTrendPoint(BaseModel):
    period: date
    events: int


class AuditActorBreakdown(BaseModel):
    actor_id: UUID | None
    actor_name: str
    events: int


class AuditReportRow(BaseModel):
    id: UUID
    actor_id: UUID | None
    actor_name: str
    action: str
    entity: str
    entity_id: str | None
    created_at: datetime


class AuditReportSection(BaseModel):
    total_events: int
    unique_actors: int
    unique_entity_references: int
    action_breakdown: list[ReportCountBreakdown]
    entity_breakdown: list[ReportCountBreakdown]
    actor_breakdown: list[AuditActorBreakdown]
    trend: list[AuditTrendPoint]
    items: list[AuditReportRow]
    scope_note: str


class AlertsAuditReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alerts_filters: AlertsReportFilters
    alerts: AlertsReportSection
    audit_filters: AuditReportFilters | None = None
    audit: AuditReportSection | None = None
