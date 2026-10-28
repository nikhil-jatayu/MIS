from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import DatabaseSession, Pagination, SuperAdminUser
from app.schemas.audit import AuditLogRead
from app.schemas.common import Page
from app.services import audit_service

router = APIRouter(prefix="/audit-logs", tags=["Audit"])


@router.get("", response_model=Page[AuditLogRead])
def list_audit_logs(
    db: DatabaseSession,
    pagination: Pagination,
    _: SuperAdminUser,
    actor_id: UUID | None = None,
    action: str | None = Query(default=None, max_length=50),
    entity: str | None = Query(default=None, max_length=80),
    entity_id: str | None = Query(default=None, max_length=100),
    date_from: date | None = None,
    date_to: date | None = None,
) -> Page[AuditLogRead]:
    return audit_service.list_audit_logs(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        actor_id=actor_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        date_from=date_from,
        date_to=date_to,
    )
