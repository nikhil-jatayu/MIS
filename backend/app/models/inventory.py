from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.project import ProjectBOM


class InventoryItem(TimestampMixin, Base):
    __tablename__ = "inventory_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    quantity_available: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    bom_lines: Mapped[list["ProjectBOM"]] = relationship(back_populates="item", lazy="raise")

    __table_args__ = (CheckConstraint("quantity_available >= 0", name="quantity_non_negative"),)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<InventoryItem {self.sku} qty={self.quantity_available}>"
