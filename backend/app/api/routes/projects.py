from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import AdminUser, CurrentUser, DatabaseSession, Pagination
from app.models.enums import Priority, ProjectStatus, ProjectType
from app.schemas.common import Page
from app.schemas.project import (
    CompleteProjectRequest,
    ProjectBOMUpdate,
    ProjectCreate,
    ProjectMembersUpdate,
    ProjectRead,
    ProjectUpdate,
    SubmitTestingRequest,
    TestResultRequest,
)
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=Page[ProjectRead])
def list_projects(
    db: DatabaseSession,
    pagination: Pagination,
    user: CurrentUser,
    q: str | None = Query(default=None, max_length=200),
    type: ProjectType | None = None,
    status: ProjectStatus | None = None,
    priority: Priority | None = None,
    deadline_from: date | None = None,
    deadline_to: date | None = None,
    assigned_to_me: bool = False,
    sort: str = Query(default="created_at", max_length=30),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> Page[ProjectRead]:
    return project_service.list_projects(
        db,
        actor=user,
        page=pagination.page,
        page_size=pagination.page_size,
        q=q,
        project_type=type,
        status=status,
        priority=priority,
        deadline_from=deadline_from,
        deadline_to=deadline_to,
        assigned_to_me=assigned_to_me,
        sort=sort,
        order=order,
    )


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(
    payload: ProjectCreate,
    db: DatabaseSession,
    actor: AdminUser,
) -> ProjectRead:
    project = project_service.create_project(db, actor=actor, payload=payload)
    return ProjectRead.model_validate(project)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: UUID,
    db: DatabaseSession,
    _: CurrentUser,
) -> ProjectRead:
    return ProjectRead.model_validate(project_service.get_project(db, project_id))


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    db: DatabaseSession,
    actor: AdminUser,
) -> ProjectRead:
    project = project_service.update_project(
        db, actor=actor, project_id=project_id, payload=payload
    )
    return ProjectRead.model_validate(project)


@router.put("/{project_id}/members", response_model=ProjectRead)
def update_members(
    project_id: UUID,
    payload: ProjectMembersUpdate,
    db: DatabaseSession,
    actor: AdminUser,
) -> ProjectRead:
    project = project_service.update_members(
        db, actor=actor, project_id=project_id, payload=payload
    )
    return ProjectRead.model_validate(project)


@router.put("/{project_id}/bom", response_model=ProjectRead)
def update_bom(
    project_id: UUID,
    payload: ProjectBOMUpdate,
    db: DatabaseSession,
    actor: AdminUser,
) -> ProjectRead:
    project = project_service.update_bom(db, actor=actor, project_id=project_id, payload=payload)
    return ProjectRead.model_validate(project)


@router.post("/{project_id}/start-production", response_model=ProjectRead)
def start_production(
    project_id: UUID,
    db: DatabaseSession,
    actor: AdminUser,
) -> ProjectRead:
    project = project_service.start_production(db, actor=actor, project_id=project_id)
    return ProjectRead.model_validate(project)


@router.post("/{project_id}/submit-testing", response_model=ProjectRead)
def submit_testing(
    project_id: UUID,
    payload: SubmitTestingRequest,
    db: DatabaseSession,
    actor: AdminUser,
) -> ProjectRead:
    project = project_service.submit_for_testing(
        db, actor=actor, project_id=project_id, tester_id=payload.tester_id
    )
    return ProjectRead.model_validate(project)


@router.post("/{project_id}/test-result", response_model=ProjectRead)
def record_test_result(
    project_id: UUID,
    payload: TestResultRequest,
    db: DatabaseSession,
    actor: CurrentUser,
) -> ProjectRead:
    project = project_service.record_test_result(
        db,
        actor=actor,
        project_id=project_id,
        result=payload.result,
        note=payload.note,
    )
    return ProjectRead.model_validate(project)


@router.post("/{project_id}/complete", response_model=ProjectRead)
def complete_project(
    project_id: UUID,
    payload: CompleteProjectRequest,
    db: DatabaseSession,
    actor: AdminUser,
) -> ProjectRead:
    project = project_service.complete_project(
        db, actor=actor, project_id=project_id, note=payload.note
    )
    return ProjectRead.model_validate(project)
