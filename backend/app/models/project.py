from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    Priority,
    ProjectMemberRole,
    ProjectStatus,
    ProjectType,
    TestResult,
)
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.inventory import InventoryItem
    from app.models.user import User


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[ProjectType] = mapped_column(
        enum_type(ProjectType, "project_type", 30), nullable=False
    )
    status: Mapped[ProjectStatus] = mapped_column(
        enum_type(ProjectStatus, "project_status", 40),
        nullable=False,
        default=ProjectStatus.PENDING_INVENTORY,
        index=True,
    )
    priority: Mapped[Priority] = mapped_column(
        enum_type(Priority, "project_priority", 20),
        nullable=False,
        default=Priority.MEDIUM,
        index=True,
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    progress_percent: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    delay_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    paused_from_status: Mapped[ProjectStatus | None] = mapped_column(
        enum_type(ProjectStatus, "paused_project_status", 40), nullable=True
    )
    test_result: Mapped[TestResult | None] = mapped_column(
        enum_type(TestResult, "test_result", 10), nullable=True
    )
    test_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    tested_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creator: Mapped["User"] = relationship(
        back_populates="created_projects", foreign_keys=[created_by], lazy="raise"
    )
    tester: Mapped["User | None"] = relationship(foreign_keys=[tested_by], lazy="raise")
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="ProjectMember.created_at",
    )
    bom_lines: Mapped[list["ProjectBOM"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="ProjectBOM.created_at",
    )

    __table_args__ = (
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="progress_range"),
    )

    @property
    def is_inventory_ready(self) -> bool:
        return all(line.quantity_allocated >= line.quantity_required for line in self.bom_lines)

    @property
    def shortage_count(self) -> int:
        return sum(1 for line in self.bom_lines if line.quantity_shortage > 0)

    @property
    def pending_days(self) -> int:
        from datetime import UTC, datetime

        anchor = self.status_changed_at
        if anchor.tzinfo is None:
            anchor = anchor.replace(tzinfo=UTC)
        return max((datetime.now(UTC).date() - anchor.date()).days, 0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Project {self.name} ({self.status})>"


class ProjectMember(Base):
    __tablename__ = "project_members"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_in_project: Mapped[ProjectMemberRole] = mapped_column(
        enum_type(ProjectMemberRole, "project_member_role", 20), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="members", lazy="raise")
    user: Mapped["User"] = relationship(back_populates="project_memberships", lazy="raise")

    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)


class ProjectBOM(TimestampMixin, Base):
    __tablename__ = "project_bom"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("inventory_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity_required: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_allocated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    project: Mapped["Project"] = relationship(back_populates="bom_lines", lazy="raise")
    item: Mapped["InventoryItem"] = relationship(back_populates="bom_lines", lazy="raise")

    __table_args__ = (
        UniqueConstraint("project_id", "item_id", name="uq_project_bom_item"),
        CheckConstraint("quantity_required > 0", name="bom_required_positive"),
        CheckConstraint("quantity_allocated >= 0", name="bom_allocated_non_negative"),
    )

    @property
    def quantity_shortage(self) -> int:
        return max(self.quantity_required - self.quantity_allocated, 0)
