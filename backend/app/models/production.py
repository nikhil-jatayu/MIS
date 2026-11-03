from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class ProductionEntry(TimestampMixin, Base):
    """A daily production record for one product, line and process stage."""

    __tablename__ = "production_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    production_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    production_line: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    product_model: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    work_order_customer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    process_stage: Mapped[str] = mapped_column(String(120), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    planned_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=Decimal("0"), server_default="0"
    )
    actual_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=Decimal("0"), server_default="0"
    )
    accepted_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=Decimal("0"), server_default="0"
    )
    rework_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=Decimal("0"), server_default="0"
    )
    production_hours: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    downtime_hours: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0"), server_default="0"
    )

    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    project: Mapped["Project | None"] = relationship(lazy="raise")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by], lazy="raise")

    __table_args__ = (
        CheckConstraint("planned_quantity >= 0", name="planned_quantity_non_negative"),
        CheckConstraint("actual_quantity >= 0", name="actual_quantity_non_negative"),
        CheckConstraint("accepted_quantity >= 0", name="accepted_quantity_non_negative"),
        CheckConstraint("accepted_quantity <= actual_quantity", name="accepted_not_over_actual"),
        CheckConstraint("rework_quantity >= 0", name="rework_quantity_non_negative"),
        CheckConstraint("rework_quantity <= actual_quantity", name="rework_not_over_actual"),
        CheckConstraint("production_hours >= 0", name="production_hours_non_negative"),
        CheckConstraint("downtime_hours >= 0", name="downtime_hours_non_negative"),
        Index("ix_production_entries_date_line", "production_date", "production_line"),
    )


class ProductionAction(TimestampMixin, Base):
    """A corrective/preventive action tracked against production work."""

    __tablename__ = "production_actions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    action_number: Mapped[str] = mapped_column(String(30), nullable=False, unique=True, index=True)
    date_raised: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    issue_observation: Mapped[str] = mapped_column(Text, nullable=False)
    corrective_action: Mapped[str] = mapped_column(Text, nullable=False)
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    deadline: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="OPEN", server_default="OPEN", index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    closure_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    production_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("production_entries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    responsible_user: Mapped["User | None"] = relationship(
        foreign_keys=[responsible_user_id], lazy="raise"
    )
    closed_by: Mapped["User | None"] = relationship(foreign_keys=[closed_by_user_id], lazy="raise")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by], lazy="raise")

    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'IN_PROGRESS', 'ON_HOLD', 'CLOSED')",
            name="valid_status",
        ),
        CheckConstraint(
            "(status = 'CLOSED' AND closed_at IS NOT NULL) OR "
            "(status <> 'CLOSED' AND closed_at IS NULL)",
            name="closed_timestamp_consistent",
        ),
    )


class ProductionMonthlyReview(TimestampMixin, Base):
    """Management commentary and sign-off metadata for a reporting month."""

    __tablename__ = "production_monthly_reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    management_summary: Mapped[str] = mapped_column(Text, nullable=False)
    prepared_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    prepared_by: Mapped["User"] = relationship(foreign_keys=[prepared_by_user_id], lazy="raise")
    reviewed_by: Mapped["User | None"] = relationship(
        foreign_keys=[reviewed_by_user_id], lazy="raise"
    )

    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_production_monthly_review_period"),
        CheckConstraint("year >= 2000 AND year <= 2200", name="review_year_range"),
        CheckConstraint("month >= 1 AND month <= 12", name="review_month_range"),
    )
