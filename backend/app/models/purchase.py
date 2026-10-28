from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import PurchaseRequestStatus
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.inventory import InventoryItem
    from app.models.project import Project
    from app.models.user import User


class PurchaseRequest(TimestampMixin, Base):
    __tablename__ = "purchase_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[PurchaseRequestStatus] = mapped_column(
        enum_type(PurchaseRequestStatus, "purchase_request_status", 20),
        nullable=False,
        default=PurchaseRequestStatus.PENDING,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(lazy="raise")
    item: Mapped["InventoryItem"] = relationship(lazy="raise")
    requester: Mapped["User"] = relationship(foreign_keys=[requested_by], lazy="raise")
    approver: Mapped["User | None"] = relationship(foreign_keys=[approved_by], lazy="raise")

    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PurchaseRequest {self.id} {self.status}>"
