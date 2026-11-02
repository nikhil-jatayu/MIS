"""add production logging, action tracking and monthly reviews

Revision ID: 4b9d3f71a2c0
Revises: 7c4ccfc85951
Create Date: 2026-10-30
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "4b9d3f71a2c0"
down_revision: Union[str, None] = "7c4ccfc85951"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "production_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("production_date", sa.Date(), nullable=False),
        sa.Column("production_line", sa.String(length=120), nullable=False),
        sa.Column("product_model", sa.String(length=200), nullable=False),
        sa.Column("work_order_customer", sa.String(length=200), nullable=True),
        sa.Column("process_stage", sa.String(length=120), nullable=False),
        sa.Column("unit_of_measure", sa.String(length=30), nullable=False),
        sa.Column("planned_quantity", sa.Numeric(precision=14, scale=3), server_default="0", nullable=False),
        sa.Column("actual_quantity", sa.Numeric(precision=14, scale=3), server_default="0", nullable=False),
        sa.Column("accepted_quantity", sa.Numeric(precision=14, scale=3), server_default="0", nullable=False),
        sa.Column("rework_quantity", sa.Numeric(precision=14, scale=3), server_default="0", nullable=False),
        sa.Column("production_hours", sa.Numeric(precision=10, scale=2), server_default="0", nullable=False),
        sa.Column("downtime_hours", sa.Numeric(precision=10, scale=2), server_default="0", nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("planned_quantity >= 0", name=op.f("ck_production_entries_planned_quantity_non_negative")),
        sa.CheckConstraint("actual_quantity >= 0", name=op.f("ck_production_entries_actual_quantity_non_negative")),
        sa.CheckConstraint("accepted_quantity >= 0", name=op.f("ck_production_entries_accepted_quantity_non_negative")),
        sa.CheckConstraint("accepted_quantity <= actual_quantity", name=op.f("ck_production_entries_accepted_not_over_actual")),
        sa.CheckConstraint("rework_quantity >= 0", name=op.f("ck_production_entries_rework_quantity_non_negative")),
        sa.CheckConstraint("rework_quantity <= actual_quantity", name=op.f("ck_production_entries_rework_not_over_actual")),
        sa.CheckConstraint("production_hours >= 0", name=op.f("ck_production_entries_production_hours_non_negative")),
        sa.CheckConstraint("downtime_hours >= 0", name=op.f("ck_production_entries_downtime_hours_non_negative")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("production_entries_project_id_fkey"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("production_entries_created_by_fkey"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("production_entries_pkey")),
    )
    op.create_index(op.f("ix_production_entries_created_by"), "production_entries", ["created_by"], unique=False)
    op.create_index(op.f("ix_production_entries_production_date"), "production_entries", ["production_date"], unique=False)
    op.create_index(op.f("ix_production_entries_production_line"), "production_entries", ["production_line"], unique=False)
    op.create_index(op.f("ix_production_entries_product_model"), "production_entries", ["product_model"], unique=False)
    op.create_index(op.f("ix_production_entries_project_id"), "production_entries", ["project_id"], unique=False)
    op.create_index(op.f("ix_production_entries_unit_of_measure"), "production_entries", ["unit_of_measure"], unique=False)
    op.create_index("ix_production_entries_date_line", "production_entries", ["production_date", "production_line"], unique=False)

    op.create_table(
        "production_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("action_number", sa.String(length=30), nullable=False),
        sa.Column("date_raised", sa.Date(), nullable=False),
        sa.Column("issue_observation", sa.Text(), nullable=False),
        sa.Column("corrective_action", sa.Text(), nullable=False),
        sa.Column("responsible_user_id", sa.Uuid(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="OPEN", nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("closure_evidence", sa.Text(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("production_entry_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('OPEN', 'IN_PROGRESS', 'ON_HOLD', 'CLOSED')", name=op.f("ck_production_actions_valid_status")),
        sa.CheckConstraint("(status = 'CLOSED' AND closed_at IS NOT NULL) OR (status <> 'CLOSED' AND closed_at IS NULL)", name=op.f("ck_production_actions_closed_timestamp_consistent")),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"], name=op.f("production_actions_responsible_user_id_fkey"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["closed_by_user_id"], ["users.id"], name=op.f("production_actions_closed_by_user_id_fkey"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("production_actions_project_id_fkey"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["production_entry_id"], ["production_entries.id"], name=op.f("production_actions_production_entry_id_fkey"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("production_actions_created_by_fkey"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("production_actions_pkey")),
    )
    op.create_index(op.f("ix_production_actions_action_number"), "production_actions", ["action_number"], unique=True)
    op.create_index(op.f("ix_production_actions_created_by"), "production_actions", ["created_by"], unique=False)
    op.create_index(op.f("ix_production_actions_date_raised"), "production_actions", ["date_raised"], unique=False)
    op.create_index(op.f("ix_production_actions_deadline"), "production_actions", ["deadline"], unique=False)
    op.create_index(op.f("ix_production_actions_production_entry_id"), "production_actions", ["production_entry_id"], unique=False)
    op.create_index(op.f("ix_production_actions_project_id"), "production_actions", ["project_id"], unique=False)
    op.create_index(op.f("ix_production_actions_responsible_user_id"), "production_actions", ["responsible_user_id"], unique=False)
    op.create_index(op.f("ix_production_actions_status"), "production_actions", ["status"], unique=False)

    op.create_table(
        "production_monthly_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("month", sa.SmallInteger(), nullable=False),
        sa.Column("management_summary", sa.Text(), nullable=False),
        sa.Column("prepared_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("year >= 2000 AND year <= 2200", name=op.f("ck_production_monthly_reviews_review_year_range")),
        sa.CheckConstraint("month >= 1 AND month <= 12", name=op.f("ck_production_monthly_reviews_review_month_range")),
        sa.ForeignKeyConstraint(["prepared_by_user_id"], ["users.id"], name=op.f("production_monthly_reviews_prepared_by_user_id_fkey"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], name=op.f("production_monthly_reviews_reviewed_by_user_id_fkey"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("production_monthly_reviews_pkey")),
        sa.UniqueConstraint("year", "month", name="uq_production_monthly_review_period"),
    )


def downgrade() -> None:
    op.drop_table("production_monthly_reviews")
    op.drop_index(op.f("ix_production_actions_status"), table_name="production_actions")
    op.drop_index(op.f("ix_production_actions_responsible_user_id"), table_name="production_actions")
    op.drop_index(op.f("ix_production_actions_project_id"), table_name="production_actions")
    op.drop_index(op.f("ix_production_actions_production_entry_id"), table_name="production_actions")
    op.drop_index(op.f("ix_production_actions_deadline"), table_name="production_actions")
    op.drop_index(op.f("ix_production_actions_date_raised"), table_name="production_actions")
    op.drop_index(op.f("ix_production_actions_created_by"), table_name="production_actions")
    op.drop_index(op.f("ix_production_actions_action_number"), table_name="production_actions")
    op.drop_table("production_actions")
    op.drop_index("ix_production_entries_date_line", table_name="production_entries")
    op.drop_index(op.f("ix_production_entries_unit_of_measure"), table_name="production_entries")
    op.drop_index(op.f("ix_production_entries_project_id"), table_name="production_entries")
    op.drop_index(op.f("ix_production_entries_product_model"), table_name="production_entries")
    op.drop_index(op.f("ix_production_entries_production_line"), table_name="production_entries")
    op.drop_index(op.f("ix_production_entries_production_date"), table_name="production_entries")
    op.drop_index(op.f("ix_production_entries_created_by"), table_name="production_entries")
    op.drop_table("production_entries")
