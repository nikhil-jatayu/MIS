from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DatabaseSession, Pagination, SuperAdminUser
from app.schemas.common import MessageResponse, Page
from app.schemas.inventory import InventoryItemCreate, InventoryItemRead, InventoryItemUpdate
from app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("", response_model=Page[InventoryItemRead])
def list_inventory(
    db: DatabaseSession,
    pagination: Pagination,
    _: CurrentUser,
    q: str | None = Query(default=None, max_length=200),
    sort: str = Query(default="name", max_length=30),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
) -> Page[InventoryItemRead]:
    return inventory_service.list_items(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        q=q,
        sort=sort,
        order=order,
    )


@router.post("", response_model=InventoryItemRead, status_code=201)
def create_inventory_item(
    payload: InventoryItemCreate,
    db: DatabaseSession,
    actor: SuperAdminUser,
) -> InventoryItemRead:
    item = inventory_service.create_item(db, actor=actor, payload=payload)
    return InventoryItemRead.model_validate(item)


@router.get("/{item_id}", response_model=InventoryItemRead)
def get_inventory_item(
    item_id: UUID,
    db: DatabaseSession,
    _: CurrentUser,
) -> InventoryItemRead:
    return InventoryItemRead.model_validate(inventory_service.get_item(db, item_id))


@router.put("/{item_id}", response_model=InventoryItemRead)
def update_inventory_item(
    item_id: UUID,
    payload: InventoryItemUpdate,
    db: DatabaseSession,
    actor: SuperAdminUser,
) -> InventoryItemRead:
    item = inventory_service.update_item(db, actor=actor, item_id=item_id, payload=payload)
    return InventoryItemRead.model_validate(item)


@router.delete("/{item_id}", response_model=MessageResponse)
def delete_inventory_item(
    item_id: UUID,
    db: DatabaseSession,
    actor: SuperAdminUser,
) -> MessageResponse:
    inventory_service.delete_item(db, actor=actor, item_id=item_id)
    return MessageResponse(message="Inventory item deleted")
