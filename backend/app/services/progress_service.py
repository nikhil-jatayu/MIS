from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models.enums import ProjectStatus
from app.models.progress import ProgressLog
from app.models.user import User
from app.schemas.common import Page
from app.schemas.progress import ProgressLogCreate, ProgressLogRead
from app.services import audit_service, project_service
from app.services.pagination import build_page, paginate


def _log_query():
    return select(ProgressLog).options(selectinload(ProgressLog.user))


def get_log(db: Session, log_id: UUID) -> ProgressLog:
    log = db.scalar(_log_query().where(ProgressLog.id == log_id))
    if not log:
        raise NotFoundError("Progress log not found")
    return log


def create_log(
    db: Session, *, actor: User, project_id: UUID, payload: ProgressLogCreate
) -> ProgressLog:
    project = project_service.get_project(db, project_id, for_update=True)
    project_service.ensure_project_action_access(db, project, actor)
    if project.status == ProjectStatus.COMPLETED:
        raise ConflictError("Completed projects are read-only", code="PROJECT_COMPLETED")
    if payload.progress_percent < project.progress_percent:
        raise UnprocessableError(
            f"Progress cannot decrease below the current {project.progress_percent}%",
            code="PROGRESS_DECREASE",
        )
    if payload.progress_percent >= 100:
        raise UnprocessableError(
            "Progress is set to 100% only when an Admin signs off the project",
            code="PROGRESS_SIGN_OFF_REQUIRED",
        )

    log = ProgressLog(
        project_id=project.id,
        user_id=actor.id,
        note=payload.note,
        progress_percent=payload.progress_percent,
    )
    db.add(log)
    project.progress_percent = payload.progress_percent
    db.flush()
    log = get_log(db, log.id)
    audit_service.record(
        db,
        actor_id=actor.id,
        action="CREATE",
        entity="progress_log",
        entity_id=log.id,
        after={
            "project_id": str(project.id),
            "progress_percent": log.progress_percent,
            "note": log.note,
        },
    )
    db.commit()
    return get_log(db, log.id)


def list_logs(
    db: Session,
    *,
    project_id: UUID,
    page: int,
    page_size: int,
) -> Page[ProgressLogRead]:
    statement = (
        _log_query()
        .where(ProgressLog.project_id == project_id)
        .order_by(ProgressLog.created_at.desc())
    )
    items, total = paginate(db, statement, page=page, page_size=page_size)
    return build_page(
        [ProgressLogRead.model_validate(log) for log in items], total, page, page_size
    )
