from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.core.deps import AdminUser, CurrentUser, DatabaseSession, Pagination
from app.models.enums import PurchaseRequestStatus
from app.schemas.common import Page
from app.schemas.purchase import (
    PurchaseRequestCreate,
    PurchaseRequestOrder,
    PurchaseRequestRead,
    PurchaseRequestReject,
)
from app.services import purchase_service

router = APIRouter(prefix="/purchase-requests", tags=["Purchase requests"])
project_router = APIRouter(prefix="/projects", tags=["Purchase requests"])


@project_router.post(
    "/{project_id}/purchase-requests", response_model=PurchaseRequestRead, status_code=201
)
def create_purchase_request(
    project_id: UUID,
    payload: PurchaseRequestCreate,
    db: DatabaseSession,
    actor: CurrentUser,
) -> PurchaseRequestRead:
    request = purchase_service.create_request(
        db, actor=actor, project_id=project_id, payload=payload
    )
    return PurchaseRequestRead.model_validate(request)


@router.get("", response_model=Page[PurchaseRequestRead])
def list_purchase_requests(
    db: DatabaseSession,
    pagination: Pagination,
    actor: CurrentUser,
    status: PurchaseRequestStatus | None = None,
    project_id: UUID | None = None,
) -> Page[PurchaseRequestRead]:
    return purchase_service.list_requests(
        db,
        actor=actor,
        page=pagination.page,
        page_size=pagination.page_size,
        status=status,
        project_id=project_id,
    )


@router.post("/{request_id}/approve", response_model=PurchaseRequestRead)
def approve_purchase_request(
    request_id: UUID,
    db: DatabaseSession,
    actor: AdminUser,
) -> PurchaseRequestRead:
    request = purchase_service.approve_request(db, actor=actor, request_id=request_id)
    return PurchaseRequestRead.model_validate(request)


@router.post("/{request_id}/reject", response_model=PurchaseRequestRead)
def reject_purchase_request(
    request_id: UUID,
    payload: PurchaseRequestReject,
    db: DatabaseSession,
    actor: AdminUser,
) -> PurchaseRequestRead:
    request = purchase_service.reject_request(
        db, actor=actor, request_id=request_id, payload=payload
    )
    return PurchaseRequestRead.model_validate(request)


@router.post("/{request_id}/order", response_model=PurchaseRequestRead)
def order_purchase_request(
    request_id: UUID,
    payload: PurchaseRequestOrder,
    db: DatabaseSession,
    actor: AdminUser,
) -> PurchaseRequestRead:
    request = purchase_service.order_request(
        db, actor=actor, request_id=request_id, payload=payload
    )
    return PurchaseRequestRead.model_validate(request)


@router.post("/{request_id}/deliver", response_model=PurchaseRequestRead)
def deliver_purchase_request(
    request_id: UUID,
    db: DatabaseSession,
    actor: AdminUser,
) -> PurchaseRequestRead:
    request = purchase_service.deliver_request(db, actor=actor, request_id=request_id)
    return PurchaseRequestRead.model_validate(request)
