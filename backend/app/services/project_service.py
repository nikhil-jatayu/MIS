from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, UnprocessableError
from app.models.enums import (
    ACTIVE_PROJECT_STATUSES,
    Priority,
    ProjectMemberRole,
    ProjectStatus,
    ProjectType,
    TestResult,
    UserRole,
)
from app.models.inventory import InventoryItem
from app.models.project import Project, ProjectBOM, ProjectMember
from app.models.purchase import PurchaseRequest
from app.models.user import User
from app.schemas.common import Page
from app.schemas.project import (
    ProjectBOMInput,
    ProjectBOMUpdate,
    ProjectCreate,
    ProjectMemberInput,
    ProjectMembersUpdate,
    ProjectRead,
    ProjectUpdate,
)
from app.services import audit_service
from app.services.pagination import build_page, paginate


def project_load_options() -> tuple:
    return (
        selectinload(Project.creator),
        selectinload(Project.tester),
        selectinload(Project.members).selectinload(ProjectMember.user),
        selectinload(Project.bom_lines).selectinload(ProjectBOM.item),
    )


def project_query():
    return select(Project).options(*project_load_options())


def get_project(db: Session, project_id: UUID, *, for_update: bool = False) -> Project:
    statement = (
        project_query().where(Project.id == project_id).execution_options(populate_existing=True)
    )
    if for_update:
        statement = statement.with_for_update()
    project = db.scalar(statement)
    if not project:
        raise NotFoundError("Project not found")
    return project


def snapshot(project: Project) -> dict[str, Any]:
    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "type": project.type,
        "status": project.status,
        "priority": project.priority,
        "start_date": project.start_date,
        "end_date": project.end_date,
        "progress_percent": project.progress_percent,
        "status_changed_at": project.status_changed_at,
        "delay_reason": project.delay_reason,
        "test_result": project.test_result,
        "test_note": project.test_note,
        "members": [
            {
                "user_id": str(member.user_id),
                "name": member.user.name,
                "role_in_project": member.role_in_project,
            }
            for member in project.members
        ],
        "bom": [
            {
                "item_id": str(line.item_id),
                "sku": line.item.sku,
                "quantity_required": line.quantity_required,
                "quantity_allocated": line.quantity_allocated,
            }
            for line in project.bom_lines
        ],
    }


def _validate_members(db: Session, members: list[ProjectMemberInput]) -> dict[UUID, User]:
    user_ids = [member.user_id for member in members]
    users = list(
        db.scalars(select(User).where(User.id.in_(user_ids), User.is_active.is_(True))).all()
    )
    user_map = {user.id: user for user in users}
    missing = [str(user_id) for user_id in user_ids if user_id not in user_map]
    if missing:
        raise UnprocessableError(
            "One or more selected users do not exist or are inactive",
            code="INVALID_MEMBERS",
            details=missing,
        )
    return user_map


def _validate_items(db: Session, lines: list[ProjectBOMInput]) -> dict[UUID, InventoryItem]:
    item_ids = [line.item_id for line in lines]
    if not item_ids:
        return {}
    items = list(db.scalars(select(InventoryItem).where(InventoryItem.id.in_(item_ids))).all())
    item_map = {item.id: item for item in items}
    missing = [str(item_id) for item_id in item_ids if item_id not in item_map]
    if missing:
        raise UnprocessableError(
            "One or more BOM inventory items do not exist",
            code="INVALID_BOM_ITEMS",
            details=missing,
        )
    return item_map


def _allocate_project(db: Session, *, project: Project, actor: User) -> bool:
    """Reserve available stock for every BOM line. Returns True when fully allocated."""
    lines = sorted(project.bom_lines, key=lambda line: str(line.item_id))
    for line in lines:
        remaining = line.quantity_required - line.quantity_allocated
        if remaining <= 0:
            continue
        item = db.scalar(
            select(InventoryItem).where(InventoryItem.id == line.item_id).with_for_update()
        )
        if not item:
            continue
        allocation = min(remaining, item.quantity_available)
        if allocation <= 0:
            continue
        before_quantity = item.quantity_available
        item.quantity_available -= allocation
        line.quantity_allocated += allocation
        audit_service.record(
            db,
            actor_id=actor.id,
            action="INVENTORY_ALLOCATED",
            entity="inventory_item",
            entity_id=item.id,
            before={"quantity_available": before_quantity},
            after={
                "quantity_available": item.quantity_available,
                "allocated": allocation,
                "project_id": str(project.id),
                "sku": item.sku,
            },
        )
    db.flush()
    return not lines or all(line.quantity_allocated >= line.quantity_required for line in lines)


def allocate_project_inventory(db: Session, *, project: Project, actor: User) -> bool:
    """Public wrapper used by the purchase-request delivery flow."""
    return _allocate_project(db, project=project, actor=actor)


def _set_status(project: Project, status: ProjectStatus) -> None:
    if project.status == status:
        return
    project.status = status
    project.status_changed_at = datetime.now(UTC)


def create_project(db: Session, *, actor: User, payload: ProjectCreate) -> Project:
    _validate_members(db, payload.members)
    _validate_items(db, payload.bom)

    project = Project(
        name=payload.name,
        description=payload.description,
        type=payload.type,
        status=ProjectStatus.PENDING_INVENTORY,
        priority=payload.priority,
        start_date=payload.start_date,
        end_date=payload.end_date,
        created_by=actor.id,
        status_changed_at=datetime.now(UTC),
        progress_percent=0,
    )
    db.add(project)
    db.flush()

    for member in payload.members:
        db.add(
            ProjectMember(
                project_id=project.id,
                user_id=member.user_id,
                role_in_project=member.role_in_project,
            )
        )
    for line in payload.bom:
        db.add(
            ProjectBOM(
                project_id=project.id,
                item_id=line.item_id,
                quantity_required=line.quantity_required,
                quantity_allocated=0,
            )
        )
    db.flush()
    db.refresh(project)

    # Ensure relationship-backed snapshots are populated.
    project = get_project(db, project.id)
    fully_allocated = _allocate_project(db, project=project, actor=actor)
    _set_status(
        project,
        ProjectStatus.READY_FOR_PRODUCTION if fully_allocated else ProjectStatus.PENDING_INVENTORY,
    )
    db.flush()
    project = get_project(db, project.id)
    audit_service.record(
        db,
        actor_id=actor.id,
        action="CREATE",
        entity="project",
        entity_id=project.id,
        after=snapshot(project),
    )
    db.commit()
    return get_project(db, project.id)


def list_projects(
    db: Session,
    *,
    actor: User,
    page: int,
    page_size: int,
    q: str | None = None,
    project_type: ProjectType | None = None,
    status: ProjectStatus | None = None,
    priority: Priority | None = None,
    deadline_from: date | None = None,
    deadline_to: date | None = None,
    assigned_to_me: bool = False,
    sort: str = "created_at",
    order: str = "desc",
) -> Page[ProjectRead]:
    statement = project_query()
    if q:
        pattern = f"%{q.strip().lower()}%"
        statement = statement.where(
            func.lower(Project.name).like(pattern)
            | func.lower(func.coalesce(Project.description, "")).like(pattern)
        )
    if project_type:
        statement = statement.where(Project.type == project_type)
    if status:
        statement = statement.where(Project.status == status)
    if priority:
        statement = statement.where(Project.priority == priority)
    if deadline_from:
        statement = statement.where(Project.end_date >= deadline_from)
    if deadline_to:
        statement = statement.where(Project.end_date <= deadline_to)
    if assigned_to_me:
        statement = statement.where(Project.members.any(ProjectMember.user_id == actor.id))

    sort_columns = {
        "created_at": Project.created_at,
        "updated_at": Project.updated_at,
        "name": Project.name,
        "end_date": Project.end_date,
        "deadline": Project.end_date,
        "priority": Project.priority,
        "status": Project.status,
        "progress_percent": Project.progress_percent,
        "start_date": Project.start_date,
    }
    sort_column = sort_columns.get(sort, Project.created_at)
    statement = statement.order_by(sort_column.desc() if order == "desc" else sort_column.asc())
    items, total = paginate(db, statement, page=page, page_size=page_size)
    return build_page(
        [ProjectRead.model_validate(project) for project in items], total, page, page_size
    )


def update_project(
    db: Session, *, actor: User, project_id: UUID, payload: ProjectUpdate
) -> Project:
    project = get_project(db, project_id)
    before = snapshot(project)
    updates = payload.model_dump(exclude_unset=True)

    new_start = updates.get("start_date", project.start_date)
    new_end = updates.get("end_date", project.end_date)
    if new_start and new_end and new_end < new_start:
        raise UnprocessableError("End date must be on or after the start date")

    deadline_changed = "end_date" in updates and updates["end_date"] != project.end_date
    for field, value in updates.items():
        setattr(project, field, value)
    db.flush()
    project = get_project(db, project_id)
    after = snapshot(project)
    if before != after:
        audit_service.record(
            db,
            actor_id=actor.id,
            action="DEADLINE_CHANGED" if deadline_changed else "UPDATE",
            entity="project",
            entity_id=project.id,
            before=before,
            after=after,
        )
    db.commit()
    return get_project(db, project_id)


def update_members(
    db: Session, *, actor: User, project_id: UUID, payload: ProjectMembersUpdate
) -> Project:
    project = get_project(db, project_id)
    _validate_members(db, payload.members)
    before = snapshot(project)
    project.members.clear()
    db.flush()
    for member in payload.members:
        db.add(
            ProjectMember(
                project_id=project.id,
                user_id=member.user_id,
                role_in_project=member.role_in_project,
            )
        )
    db.flush()
    project = get_project(db, project_id)
    after = snapshot(project)
    if before != after:
        audit_service.record(
            db,
            actor_id=actor.id,
            action="MEMBERS_CHANGED",
            entity="project",
            entity_id=project.id,
            before=before,
            after=after,
        )
    db.commit()
    return get_project(db, project_id)


def update_bom(db: Session, *, actor: User, project_id: UUID, payload: ProjectBOMUpdate) -> Project:
    project = get_project(db, project_id, for_update=True)
    if project.status != ProjectStatus.PENDING_INVENTORY:
        raise ConflictError(
            "The BOM can only be changed while the project is pending inventory",
            code="BOM_LOCKED",
        )
    has_requests = db.scalar(select(exists().where(PurchaseRequest.project_id == project.id)))
    if has_requests:
        raise ConflictError(
            "The BOM cannot be changed after purchase requests have been raised",
            code="BOM_LOCKED",
        )
    _validate_items(db, payload.lines)
    before = snapshot(project)

    for line in list(project.bom_lines):
        if line.quantity_allocated:
            item = db.scalar(
                select(InventoryItem).where(InventoryItem.id == line.item_id).with_for_update()
            )
            if item:
                before_quantity = item.quantity_available
                item.quantity_available += line.quantity_allocated
                audit_service.record(
                    db,
                    actor_id=actor.id,
                    action="INVENTORY_RELEASED",
                    entity="inventory_item",
                    entity_id=item.id,
                    before={"quantity_available": before_quantity},
                    after={
                        "quantity_available": item.quantity_available,
                        "released": line.quantity_allocated,
                        "project_id": str(project.id),
                        "sku": item.sku,
                    },
                )
        db.delete(line)
    db.flush()
    for line in payload.lines:
        db.add(
            ProjectBOM(
                project_id=project.id,
                item_id=line.item_id,
                quantity_required=line.quantity_required,
                quantity_allocated=0,
            )
        )
    db.flush()
    project = get_project(db, project.id)
    fully_allocated = _allocate_project(db, project=project, actor=actor)
    _set_status(
        project,
        ProjectStatus.READY_FOR_PRODUCTION if fully_allocated else ProjectStatus.PENDING_INVENTORY,
    )
    db.flush()
    project = get_project(db, project.id)
    audit_service.record(
        db,
        actor_id=actor.id,
        action="BOM_CHANGED",
        entity="project",
        entity_id=project.id,
        before=before,
        after=snapshot(project),
    )
    db.commit()
    return get_project(db, project.id)


def ensure_project_action_access(db: Session, project: Project, user: User) -> None:
    """Admins can act on any project; Users only on projects they are assigned to."""
    if user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        return
    if not any(member.user_id == user.id for member in project.members):
        raise ForbiddenError("You are not assigned to this project")


def is_project_member(project: Project, user_id: UUID) -> bool:
    return any(member.user_id == user_id for member in project.members)


def start_production(db: Session, *, actor: User, project_id: UUID) -> Project:
    project = get_project(db, project_id, for_update=True)
    if project.status != ProjectStatus.READY_FOR_PRODUCTION:
        raise ConflictError(
            "Project must be ready for production before production can start",
            code="INVALID_STATUS_TRANSITION",
        )
    if not project.is_inventory_ready:
        raise ConflictError(
            "All BOM items must be allocated before production starts",
            code="INVENTORY_NOT_READY",
        )
    before = snapshot(project)
    project.status = ProjectStatus.IN_PRODUCTION
    project.status_changed_at = datetime.now(UTC)
    project.paused_from_status = None
    project.delay_reason = None
    db.flush()
    project = get_project(db, project_id)
    audit_service.record(
        db,
        actor_id=actor.id,
        action="STATUS_CHANGED",
        entity="project",
        entity_id=project.id,
        before=before,
        after=snapshot(project),
    )
    db.commit()
    return get_project(db, project_id)


def submit_for_testing(db: Session, *, actor: User, project_id: UUID, tester_id: UUID) -> Project:
    project = get_project(db, project_id, for_update=True)
    if project.status != ProjectStatus.IN_PRODUCTION:
        raise ConflictError(
            "Only projects in production can be submitted for testing",
            code="INVALID_STATUS_TRANSITION",
        )
    tester = db.scalar(select(User).where(User.id == tester_id, User.is_active.is_(True)))
    if not tester:
        raise UnprocessableError("Tester not found or inactive", code="INVALID_TESTER")

    before = snapshot(project)
    membership = next((member for member in project.members if member.user_id == tester_id), None)
    if membership:
        membership.role_in_project = ProjectMemberRole.TESTER
    else:
        db.add(
            ProjectMember(
                project_id=project.id,
                user_id=tester_id,
                role_in_project=ProjectMemberRole.TESTER,
            )
        )
    project.status = ProjectStatus.IN_TESTING
    project.status_changed_at = datetime.now(UTC)
    project.test_result = None
    project.test_note = None
    project.tested_by = None
    project.tested_at = None
    db.flush()
    project = get_project(db, project_id)
    audit_service.record(
        db,
        actor_id=actor.id,
        action="STATUS_CHANGED",
        entity="project",
        entity_id=project.id,
        before=before,
        after=snapshot(project),
    )
    db.commit()
    return get_project(db, project_id)


def record_test_result(
    db: Session, *, actor: User, project_id: UUID, result: TestResult, note: str
) -> Project:
    project = get_project(db, project_id, for_update=True)
    if project.status != ProjectStatus.IN_TESTING:
        raise ConflictError(
            "Test results can only be recorded while the project is in testing",
            code="INVALID_STATUS_TRANSITION",
        )
    tester_membership = next(
        (
            member
            for member in project.members
            if member.user_id == actor.id and member.role_in_project == ProjectMemberRole.TESTER
        ),
        None,
    )
    if not tester_membership:
        raise ForbiddenError("Only the assigned Tester can record a test result")
    before = snapshot(project)
    project.test_result = result
    project.test_note = note
    project.tested_by = actor.id
    project.tested_at = datetime.now(UTC)
    if result == TestResult.FAIL:
        project.status = ProjectStatus.IN_PRODUCTION
        project.status_changed_at = datetime.now(UTC)
    db.flush()
    project = get_project(db, project_id)
    audit_service.record(
        db,
        actor_id=actor.id,
        action="TEST_RESULT",
        entity="project",
        entity_id=project.id,
        before=before,
        after=snapshot(project),
    )
    db.commit()
    return get_project(db, project_id)


def complete_project(db: Session, *, actor: User, project_id: UUID, note: str | None) -> Project:
    project = get_project(db, project_id, for_update=True)
    if project.status != ProjectStatus.IN_TESTING:
        raise ConflictError(
            "Project must be in testing before it can be completed",
            code="INVALID_STATUS_TRANSITION",
        )
    if project.test_result != TestResult.PASS:
        raise ConflictError(
            "The assigned Tester must mark the project as passed before sign-off",
            code="TEST_NOT_PASSED",
        )
    before = snapshot(project)
    project.status = ProjectStatus.COMPLETED
    project.progress_percent = 100
    project.status_changed_at = datetime.now(UTC)
    if note:
        project.test_note = f"{project.test_note or ''}\nSign-off: {note}".strip()
    db.flush()
    project = get_project(db, project_id)
    audit_service.record(
        db,
        actor_id=actor.id,
        action="STATUS_CHANGED",
        entity="project",
        entity_id=project.id,
        before=before,
        after=snapshot(project),
    )
    db.commit()
    return get_project(db, project_id)


def project_counts(db: Session, *, actor: User | None = None) -> dict[str, int]:
    statement = select(Project.status, func.count(Project.id)).group_by(Project.status)
    rows = dict(db.execute(statement).all())
    result = {
        "total": sum(rows.values()),
        "completed": rows.get(ProjectStatus.COMPLETED, 0),
        "active": sum(count for status, count in rows.items() if status in ACTIVE_PROJECT_STATUSES),
    }
    for status in ProjectStatus:
        result[status.value.lower()] = rows.get(status, 0)
    return result
