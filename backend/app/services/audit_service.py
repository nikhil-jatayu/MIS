from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.audit import AuditLog
from app.models.enums import json_safe
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.schemas.common import Page
from app.services.pagination import build_page, paginate


def record(
    db: Session,
    *,
    actor_id: UUID | None,
    action: str,
    entity: str,
    entity_id: str | UUID | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        before=json_safe(before) if before is not None else None,
        after=json_safe(after) if after is not None else None,
    )
    db.add(entry)
    return entry


def list_audit_logs(
    db: Session,
    *,
    page: int,
    page_size: int,
    actor_id: UUID | None = None,
    action: str | None = None,
    entity: str | None = None,
    entity_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Page[AuditLogRead]:
    statement = (
        select(AuditLog).options(selectinload(AuditLog.actor)).order_by(AuditLog.created_at.desc())
    )
    if actor_id:
        statement = statement.where(AuditLog.actor_id == actor_id)
    if action:
        statement = statement.where(AuditLog.action == action)
    if entity:
        statement = statement.where(AuditLog.entity == entity)
    if entity_id:
        statement = statement.where(AuditLog.entity_id == entity_id)
    if date_from:
        statement = statement.where(AuditLog.created_at >= date_from)
    if date_to:
        end = datetime.combine(date_to, datetime.max.time())
        statement = statement.where(AuditLog.created_at <= end)
    items, total = paginate(db, statement, page=page, page_size=page_size)
    return build_page([AuditLogRead.model_validate(item) for item in items], total, page, page_size)


def user_snapshot(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "must_change_password": user.must_change_password,
    }
