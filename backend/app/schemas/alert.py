from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from app.models.enums import AlertType
from app.schemas.common import ORMModel
from app.schemas.project import ProjectRef


class AlertRead(ORMModel):
    id: UUID
    user_id: UUID
    project_id: UUID
    type: AlertType
    message: str
    is_read: bool
    alert_date: date
    created_at: datetime
    project: ProjectRef


class UnreadCount(ORMModel):
    unread: int


class AlertRunResult(ORMModel):
    evaluated_projects: int
    standard_projects: int
    escalated_projects: int
    severe_projects: int
    alerts_created: int
    duplicates_skipped: int
    run_at: datetime
