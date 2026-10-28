from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.models.inventory import InventoryItem
from app.models.project import ProjectBOM
from app.models.purchase import PurchaseRequest
from app.models.user import User
from app.schemas.common import Page
from app.schemas.inventory import InventoryItemCreate, InventoryItemRead, InventoryItemUpdate
from app.services import audit_service
from app.services.pagination import build_page, paginate


def snapshot(item: InventoryItem) -> dict:
    return {
        "id": str(item.id),
        "name": item.name,
        "sku": item.sku,
        "quantity_available": item.quantity_available,
    }


def get_item(db: Session, item_id: UUID, *, for_update: bool = False) -> InventoryItem:
    statement = select(InventoryItem).where(InventoryItem.id == item_id)
    if for_update:
        statement = statement.with_for_update()
    item = db.scalar(statement)
    if not item:
        raise NotFoundError("Inventory item not found")
    return item


def list_items(
    db: Session,
    *,
    page: int,
    page_size: int,
    q: str | None = None,
    sort: str = "name",
    order: str = "asc",
) -> Page[InventoryItemRead]:
    statement = select(InventoryItem)
    if q:
        pattern = f"%{q.strip().lower()}%"
        statement = statement.where(
            or_(
                func.lower(InventoryItem.name).like(pattern),
                func.lower(InventoryItem.sku).like(pattern),
            )
        )
    sort_columns = {
        "name": InventoryItem.name,
        "sku": InventoryItem.sku,
        "quantity_available": InventoryItem.quantity_available,
        "created_at": InventoryItem.created_at,
    }
    sort_column = sort_columns.get(sort, InventoryItem.name)
    statement = statement.order_by(sort_column.desc() if order == "desc" else sort_column.asc())
    items, total = paginate(db, statement, page=page, page_size=page_size)
    return build_page(
        [InventoryItemRead.model_validate(item) for item in items], total, page, page_size
    )


def _assert_unique_sku(db: Session, sku: str, exclude_id: UUID | None = None) -> None:
    statement = select(InventoryItem).where(func.lower(InventoryItem.sku) == sku.lower())
    if exclude_id:
        statement = statement.where(InventoryItem.id != exclude_id)
    if db.scalar(statement):
        raise ConflictError("An inventory item with this SKU already exists", code="SKU_EXISTS")


def create_item(db: Session, *, actor: User, payload: InventoryItemCreate) -> InventoryItem:
    _assert_unique_sku(db, payload.sku)
    item = InventoryItem(
        name=payload.name,
        sku=payload.sku.upper(),
        quantity_available=payload.quantity_available,
    )
    db.add(item)
    db.flush()
    audit_service.record(
        db,
        actor_id=actor.id,
        action="CREATE",
        entity="inventory_item",
        entity_id=item.id,
        after=snapshot(item),
    )
    db.commit()
    db.refresh(item)
    return item


def update_item(
    db: Session, *, actor: User, item_id: UUID, payload: InventoryItemUpdate
) -> InventoryItem:
    item = get_item(db, item_id)
    before = snapshot(item)
    if payload.sku is not None and payload.sku.upper() != item.sku:
        _assert_unique_sku(db, payload.sku, exclude_id=item.id)
        item.sku = payload.sku.upper()
    if payload.name is not None:
        item.name = payload.name
    if payload.quantity_available is not None:
        item.quantity_available = payload.quantity_available
    after = snapshot(item)
    if before != after:
        quantity_changed = before["quantity_available"] != after["quantity_available"]
        action = "INVENTORY_ADJUSTED" if quantity_changed else "UPDATE"
        audit_service.record(
            db,
            actor_id=actor.id,
            action=action,
            entity="inventory_item",
            entity_id=item.id,
            before=before,
            after=after,
        )
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, *, actor: User, item_id: UUID) -> None:
    item = get_item(db, item_id)
    bom_references = db.scalar(
        select(func.count()).select_from(ProjectBOM).where(ProjectBOM.item_id == item.id)
    )
    pr_references = db.scalar(
        select(func.count()).select_from(PurchaseRequest).where(PurchaseRequest.item_id == item.id)
    )
    if int(bom_references or 0) or int(pr_references or 0):
        raise UnprocessableError(
            "This item is referenced by a project BOM or purchase request and cannot be deleted",
            code="ITEM_IN_USE",
        )
    before = snapshot(item)
    db.delete(item)
    audit_service.record(
        db,
        actor_id=actor.id,
        action="DELETE",
        entity="inventory_item",
        entity_id=item.id,
        before=before,
    )
    db.commit()
