from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models.enums import (
    OPEN_PURCHASE_STATUSES,
    ProjectStatus,
    PurchaseRequestStatus,
    UserRole,
)
from app.models.inventory import InventoryItem
from app.models.project import Project, ProjectMember
from app.models.purchase import PurchaseRequest
from app.models.user import User
from app.schemas.common import Page
from app.schemas.purchase import (
    PurchaseRequestCreate,
    PurchaseRequestOrder,
    PurchaseRequestRead,
    PurchaseRequestReject,
)
from app.services import audit_service, project_service
from app.services.pagination import build_page, paginate


def request_query():
    return select(PurchaseRequest).options(
        selectinload(PurchaseRequest.project),
        selectinload(PurchaseRequest.item),
        selectinload(PurchaseRequest.requester),
        selectinload(PurchaseRequest.approver),
    )


def get_request(db: Session, request_id: UUID, *, for_update: bool = False) -> PurchaseRequest:
    statement = (
        request_query()
        .where(PurchaseRequest.id == request_id)
        .execution_options(populate_existing=True)
    )
    if for_update:
        statement = statement.with_for_update()
    request = db.scalar(statement)
    if not request:
        raise NotFoundError("Purchase request not found")
    return request


def snapshot(request: PurchaseRequest) -> dict[str, Any]:
    return {
        "id": str(request.id),
        "project_id": str(request.project_id),
        "item_id": str(request.item_id),
        "quantity": request.quantity,
        "status": request.status,
        "reason": request.reason,
        "review_note": request.review_note,
        "approved_by": str(request.approved_by) if request.approved_by else None,
    }


def _open_quantity(db: Session, project_id: UUID, item_id: UUID) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(PurchaseRequest.quantity), 0)).where(
            PurchaseRequest.project_id == project_id,
            PurchaseRequest.item_id == item_id,
            PurchaseRequest.status.in_(list(OPEN_PURCHASE_STATUSES)),
        )
    )
    return int(total or 0)


def create_request(
    db: Session, *, actor: User, project_id: UUID, payload: PurchaseRequestCreate
) -> PurchaseRequest:
    project = project_service.get_project(db, project_id)
    project_service.ensure_project_action_access(db, project, actor)
    if project.status == ProjectStatus.COMPLETED:
        raise ConflictError("Completed projects cannot raise new purchase requests")

    line = next((line for line in project.bom_lines if line.item_id == payload.item_id), None)
    if not line:
        raise UnprocessableError(
            "The selected item is not part of this project's BOM", code="ITEM_NOT_IN_BOM"
        )

    shortage = line.quantity_shortage - _open_quantity(db, project.id, line.item_id)
    if shortage <= 0:
        raise ConflictError(
            "There is no remaining shortage for this item that is not already requested",
            code="NO_SHORTAGE",
        )
    quantity = payload.quantity or shortage
    if quantity > shortage:
        raise UnprocessableError(
            f"Requested quantity exceeds the unrequested shortage of {shortage}",
            code="QUANTITY_EXCEEDS_SHORTAGE",
        )

    request = PurchaseRequest(
        project_id=project.id,
        item_id=line.item_id,
        quantity=quantity,
        requested_by=actor.id,
        status=PurchaseRequestStatus.PENDING,
        reason=payload.reason,
    )
    db.add(request)
    db.flush()
    request = get_request(db, request.id)
    audit_service.record(
        db,
        actor_id=actor.id,
        action="CREATE",
        entity="purchase_request",
        entity_id=request.id,
        after=snapshot(request) | {"project_name": request.project.name},
    )
    db.commit()
    return get_request(db, request.id)


def list_requests(
    db: Session,
    *,
    actor: User,
    page: int,
    page_size: int,
    status: PurchaseRequestStatus | None = None,
    project_id: UUID | None = None,
) -> Page[PurchaseRequestRead]:
    statement = request_query().order_by(PurchaseRequest.created_at.desc())
    if status:
        statement = statement.where(PurchaseRequest.status == status)
    if project_id:
        statement = statement.where(PurchaseRequest.project_id == project_id)
    if actor.role == UserRole.USER:
        statement = statement.where(
            or_(
                PurchaseRequest.requested_by == actor.id,
                PurchaseRequest.project.has(Project.members.any(ProjectMember.user_id == actor.id)),
            )
        )
    items, total = paginate(db, statement, page=page, page_size=page_size)
    return build_page(
        [PurchaseRequestRead.model_validate(item) for item in items], total, page, page_size
    )


def approve_request(db: Session, *, actor: User, request_id: UUID) -> PurchaseRequest:
    request = get_request(db, request_id, for_update=True)
    if request.status != PurchaseRequestStatus.PENDING:
        raise ConflictError(
            "Only pending requests can be approved", code="INVALID_STATUS_TRANSITION"
        )
    before = snapshot(request)
    request.status = PurchaseRequestStatus.APPROVED
    request.approved_by = actor.id
    request.approved_at = datetime.now(UTC)
    db.flush()
    request = get_request(db, request_id)
    audit_service.record(
        db,
        actor_id=actor.id,
        action="APPROVE",
        entity="purchase_request",
        entity_id=request.id,
        before=before,
        after=snapshot(request),
    )
    db.commit()
    return get_request(db, request_id)


def reject_request(
    db: Session, *, actor: User, request_id: UUID, payload: PurchaseRequestReject
) -> PurchaseRequest:
    request = get_request(db, request_id, for_update=True)
    if request.status not in {
        PurchaseRequestStatus.PENDING,
        PurchaseRequestStatus.APPROVED,
    }:
        raise ConflictError(
            "Only pending or approved requests can be rejected",
            code="INVALID_STATUS_TRANSITION",
        )
    before = snapshot(request)
    request.status = PurchaseRequestStatus.REJECTED
    request.review_note = payload.reason
    db.flush()
    request = get_request(db, request_id)
    audit_service.record(
        db,
        actor_id=actor.id,
        action="REJECT",
        entity="purchase_request",
        entity_id=request.id,
        before=before,
        after=snapshot(request),
    )
    db.commit()
    return get_request(db, request_id)


def order_request(
    db: Session, *, actor: User, request_id: UUID, payload: PurchaseRequestOrder
) -> PurchaseRequest:
    request = get_request(db, request_id, for_update=True)
    if request.status != PurchaseRequestStatus.APPROVED:
        raise ConflictError(
            "Only approved requests can be marked as ordered",
            code="INVALID_STATUS_TRANSITION",
        )
    project = project_service.get_project(db, request.project_id, for_update=True)
    if project.status == ProjectStatus.COMPLETED:
        raise ConflictError("Completed projects cannot enter the delivery pause")

    before = snapshot(request)
    project_before = project_service.snapshot(project)
    request.status = PurchaseRequestStatus.ORDERED
    request.ordered_at = datetime.now(UTC)
    request.review_note = payload.delay_reason
    if project.status != ProjectStatus.AWAITING_DELIVERY:
        project.paused_from_status = project.status
        project.status = ProjectStatus.AWAITING_DELIVERY
        project.status_changed_at = datetime.now(UTC)
    project.delay_reason = payload.delay_reason
    db.flush()
    request = get_request(db, request_id)
    project = project_service.get_project(db, project.id)
    audit_service.record(
        db,
        actor_id=actor.id,
        action="ORDER",
        entity="purchase_request",
        entity_id=request.id,
        before=before,
        after=snapshot(request),
    )
    audit_service.record(
        db,
        actor_id=actor.id,
        action="STATUS_CHANGED",
        entity="project",
        entity_id=project.id,
        before=project_before,
        after=project_service.snapshot(project),
    )
    db.commit()
    return get_request(db, request_id)


def deliver_request(db: Session, *, actor: User, request_id: UUID) -> PurchaseRequest:
    request = get_request(db, request_id, for_update=True)
    if request.status != PurchaseRequestStatus.ORDERED:
        raise ConflictError(
            "Only ordered requests can be marked as delivered",
            code="INVALID_STATUS_TRANSITION",
        )
    item = db.scalar(
        select(InventoryItem).where(InventoryItem.id == request.item_id).with_for_update()
    )
    if not item:
        raise NotFoundError("Inventory item not found")
    before_qty = item.quantity_available
    item.quantity_available += request.quantity
    audit_service.record(
        db,
        actor_id=actor.id,
        action="INVENTORY_RECEIVED",
        entity="inventory_item",
        entity_id=item.id,
        before={"quantity_available": before_qty},
        after={
            "quantity_available": item.quantity_available,
            "received": request.quantity,
            "project_id": str(request.project_id),
            "sku": item.sku,
        },
    )

    before = snapshot(request)
    request.status = PurchaseRequestStatus.DELIVERED
    request.delivered_at = datetime.now(UTC)
    db.flush()

    project = project_service.get_project(db, request.project_id, for_update=True)
    project_before = project_service.snapshot(project)
    fully_allocated = project_service.allocate_project_inventory(db, project=project, actor=actor)
    open_requests = db.scalar(
        select(func.count())
        .select_from(PurchaseRequest)
        .where(
            PurchaseRequest.project_id == project.id,
            PurchaseRequest.id != request.id,
            PurchaseRequest.status.in_(list(OPEN_PURCHASE_STATUSES)),
        )
    )
    target_status = project.status
    if fully_allocated:
        if project.paused_from_status in {
            ProjectStatus.IN_PRODUCTION,
            ProjectStatus.IN_TESTING,
        }:
            target_status = project.paused_from_status
        else:
            target_status = ProjectStatus.READY_FOR_PRODUCTION
        project.paused_from_status = None
    elif int(open_requests or 0) == 0:
        target_status = ProjectStatus.PENDING_INVENTORY
        project.paused_from_status = None

    if target_status != project.status:
        project.status = target_status
        project.status_changed_at = datetime.now(UTC)
    db.flush()
    request = get_request(db, request_id)
    project = project_service.get_project(db, project.id)
    audit_service.record(
        db,
        actor_id=actor.id,
        action="DELIVER",
        entity="purchase_request",
        entity_id=request.id,
        before=before,
        after=snapshot(request),
    )
    if project_before != project_service.snapshot(project):
        audit_service.record(
            db,
            actor_id=actor.id,
            action="STATUS_CHANGED",
            entity="project",
            entity_id=project.id,
            before=project_before,
            after=project_service.snapshot(project),
        )
    db.commit()
    return get_request(db, request_id)
