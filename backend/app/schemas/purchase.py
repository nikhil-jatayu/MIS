from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import PurchaseRequestStatus
from app.schemas.common import ORMModel
from app.schemas.project import ProjectRef
from app.schemas.user import UserSummary


class InventoryRef(ORMModel):
    id: UUID
    name: str
    sku: str
    quantity_available: int


class PurchaseRequestCreate(ORMModel):
    item_id: UUID
    quantity: int | None = Field(default=None, gt=0, le=1_000_000)
    reason: str | None = Field(default=None, max_length=2000)


class PurchaseRequestReject(ORMModel):
    reason: str | None = Field(default=None, max_length=2000)


class PurchaseRequestOrder(ORMModel):
    delay_reason: str = Field(min_length=5, max_length=2000)


class PurchaseRequestRead(ORMModel):
    id: UUID
    project_id: UUID
    item_id: UUID
    quantity: int
    requested_by: UUID
    status: PurchaseRequestStatus
    reason: str | None
    review_note: str | None
    approved_by: UUID | None
    approved_at: datetime | None
    ordered_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime
    project: ProjectRef
    item: InventoryRef
    requester: UserSummary
    approver: UserSummary | None
