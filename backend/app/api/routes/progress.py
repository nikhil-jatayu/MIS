from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentUser, DatabaseSession, Pagination
from app.schemas.common import Page
from app.schemas.progress import ProgressLogCreate, ProgressLogRead
from app.services import progress_service

router = APIRouter(prefix="/projects/{project_id}/progress-logs", tags=["Progress"])


@router.get("", response_model=Page[ProgressLogRead])
def list_progress_logs(
    project_id: UUID,
    db: DatabaseSession,
    pagination: Pagination,
    _: CurrentUser,
) -> Page[ProgressLogRead]:
    return progress_service.list_logs(
        db, project_id=project_id, page=pagination.page, page_size=pagination.page_size
    )


@router.post("", response_model=ProgressLogRead, status_code=201)
def create_progress_log(
    project_id: UUID,
    payload: ProgressLogCreate,
    db: DatabaseSession,
    actor: CurrentUser,
) -> ProgressLogRead:
    log = progress_service.create_log(db, actor=actor, project_id=project_id, payload=payload)
    return ProgressLogRead.model_validate(log)
