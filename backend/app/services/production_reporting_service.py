from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime, cast, func, select
from sqlalchemy.orm import Session

from app.models.production import ProductionAction, ProductionEntry
from app.schemas.production_reporting import (
    ProductionReportActionSummary,
    ProductionReportDimensionMetric,
    ProductionReportFilters,
    ProductionReportMetric,
    ProductionReportRead,
    ProductionReportTrendPoint,
)
from app.services.reporting_utils import safe_percent, validate_report_date_range

OPEN_STATUSES = ("OPEN", "IN_PROGRESS", "ON_HOLD")
REPORT_TIMEZONE = ZoneInfo("Asia/Kolkata")


def calculate_quality_metrics(
    *,
    actual_quantity: Decimal,
    accepted_first_pass_quantity: Decimal,
    rework_sent_quantity: Decimal,
) -> dict[str, Decimal | float | None]:
    """Calculate quality measures without misclassifying rework as final scrap.

    Rework-sent quantity is a separate disposition within first-pass non-acceptance.
    Final scrap/rejection cannot be calculated because the current production schema
    does not capture the outcome after rework.
    """
    actual = Decimal(actual_quantity)
    accepted = Decimal(accepted_first_pass_quantity)
    rework = Decimal(rework_sent_quantity)
    not_accepted = max(actual - accepted, Decimal("0"))
    return {
        "first_pass_non_acceptance_quantity": not_accepted,
        "first_pass_yield_percent": safe_percent(accepted, actual),
        "rework_rate_percent": safe_percent(rework, actual),
        "first_pass_non_acceptance_rate_percent": safe_percent(not_accepted, actual),
    }


def _filters(
    *,
    date_from: date,
    date_to: date,
    production_line: str | None,
    product_model: str | None,
    project_id: UUID | None,
    unit_of_measure: str | None,
):
    clauses = [
        ProductionEntry.production_date >= date_from,
        ProductionEntry.production_date <= date_to,
    ]
    if production_line:
        clauses.append(ProductionEntry.production_line.ilike(f"%{production_line.strip()}%"))
    if product_model:
        clauses.append(ProductionEntry.product_model.ilike(f"%{product_model.strip()}%"))
    if project_id:
        clauses.append(ProductionEntry.project_id == project_id)
    if unit_of_measure:
        clauses.append(ProductionEntry.unit_of_measure == unit_of_measure.strip().lower())
    return clauses


def _metric_values(row) -> dict:
    planned = Decimal(row["planned_quantity"] or 0)
    actual = Decimal(row["actual_quantity"] or 0)
    accepted = Decimal(row["accepted_first_pass_quantity"] or 0)
    rework = Decimal(row["rework_sent_quantity"] or 0)
    production_hours = Decimal(row["production_hours"] or 0)
    downtime_hours = Decimal(row["downtime_hours"] or 0)
    quality = calculate_quality_metrics(
        actual_quantity=actual,
        accepted_first_pass_quantity=accepted,
        rework_sent_quantity=rework,
    )
    return {
        "entries_count": int(row["entries_count"] or 0),
        "planned_quantity": float(planned),
        "actual_quantity": float(actual),
        "accepted_first_pass_quantity": float(accepted),
        "rework_sent_quantity": float(rework),
        "first_pass_non_acceptance_quantity": float(quality["first_pass_non_acceptance_quantity"]),
        "plan_achievement_percent": safe_percent(actual, planned),
        "first_pass_yield_percent": quality["first_pass_yield_percent"],
        "rework_rate_percent": quality["rework_rate_percent"],
        "first_pass_non_acceptance_rate_percent": quality[
            "first_pass_non_acceptance_rate_percent"
        ],
        "production_hours": float(production_hours),
        "downtime_hours": float(downtime_hours),
        "downtime_percent": safe_percent(downtime_hours, production_hours + downtime_hours),
    }


def _aggregate_by_unit(db: Session, clauses: list) -> list[ProductionReportMetric]:
    rows = db.execute(
        select(
            ProductionEntry.unit_of_measure.label("unit_of_measure"),
            func.count(ProductionEntry.id).label("entries_count"),
            func.coalesce(func.sum(ProductionEntry.planned_quantity), 0).label("planned_quantity"),
            func.coalesce(func.sum(ProductionEntry.actual_quantity), 0).label("actual_quantity"),
            func.coalesce(func.sum(ProductionEntry.accepted_quantity), 0).label(
                "accepted_first_pass_quantity"
            ),
            func.coalesce(func.sum(ProductionEntry.rework_quantity), 0).label(
                "rework_sent_quantity"
            ),
            func.coalesce(func.sum(ProductionEntry.production_hours), 0).label(
                "production_hours"
            ),
            func.coalesce(func.sum(ProductionEntry.downtime_hours), 0).label("downtime_hours"),
        )
        .where(*clauses)
        .group_by(ProductionEntry.unit_of_measure)
        .order_by(ProductionEntry.unit_of_measure)
    ).mappings().all()
    return [
        ProductionReportMetric(unit_of_measure=row["unit_of_measure"], **_metric_values(row))
        for row in rows
    ]


def _aggregate_dimension(
    db: Session, clauses: list, dimension_column
) -> list[ProductionReportDimensionMetric]:
    rows = db.execute(
        select(
            dimension_column.label("dimension_value"),
            ProductionEntry.unit_of_measure.label("unit_of_measure"),
            func.count(ProductionEntry.id).label("entries_count"),
            func.coalesce(func.sum(ProductionEntry.planned_quantity), 0).label("planned_quantity"),
            func.coalesce(func.sum(ProductionEntry.actual_quantity), 0).label("actual_quantity"),
            func.coalesce(func.sum(ProductionEntry.accepted_quantity), 0).label(
                "accepted_first_pass_quantity"
            ),
            func.coalesce(func.sum(ProductionEntry.rework_quantity), 0).label(
                "rework_sent_quantity"
            ),
            func.coalesce(func.sum(ProductionEntry.production_hours), 0).label(
                "production_hours"
            ),
            func.coalesce(func.sum(ProductionEntry.downtime_hours), 0).label("downtime_hours"),
        )
        .where(*clauses)
        .group_by(dimension_column, ProductionEntry.unit_of_measure)
        .order_by(dimension_column, ProductionEntry.unit_of_measure)
    ).mappings().all()
    return [
        ProductionReportDimensionMetric(
            dimension_value=row["dimension_value"],
            unit_of_measure=row["unit_of_measure"],
            **_metric_values(row),
        )
        for row in rows
    ]


def _aggregate_trend(
    db: Session, clauses: list, *, granularity: str
) -> list[ProductionReportTrendPoint]:
    period_expression = func.date_trunc(
        granularity, cast(ProductionEntry.production_date, DateTime)
    )
    rows = db.execute(
        select(
            period_expression.label("period_start"),
            ProductionEntry.unit_of_measure.label("unit_of_measure"),
            func.count(ProductionEntry.id).label("entries_count"),
            func.coalesce(func.sum(ProductionEntry.planned_quantity), 0).label("planned_quantity"),
            func.coalesce(func.sum(ProductionEntry.actual_quantity), 0).label("actual_quantity"),
            func.coalesce(func.sum(ProductionEntry.accepted_quantity), 0).label(
                "accepted_first_pass_quantity"
            ),
            func.coalesce(func.sum(ProductionEntry.rework_quantity), 0).label(
                "rework_sent_quantity"
            ),
            func.coalesce(func.sum(ProductionEntry.production_hours), 0).label(
                "production_hours"
            ),
            func.coalesce(func.sum(ProductionEntry.downtime_hours), 0).label("downtime_hours"),
        )
        .where(*clauses)
        .group_by(period_expression, ProductionEntry.unit_of_measure)
        .order_by(period_expression, ProductionEntry.unit_of_measure)
    ).mappings().all()
    points: list[ProductionReportTrendPoint] = []
    for row in rows:
        period_start = row["period_start"]
        period = period_start.strftime("%Y-%m-%d" if granularity == "day" else "%Y-%m")
        points.append(
            ProductionReportTrendPoint(
                period=period,
                unit_of_measure=row["unit_of_measure"],
                **_metric_values(row),
            )
        )
    return points


def _action_summary(
    db: Session, *, date_from: date, date_to: date, project_id: UUID | None
) -> ProductionReportActionSummary:
    base = [ProductionAction.date_raised <= date_to]
    if project_id:
        base.append(ProductionAction.project_id == project_id)
    created_clauses = [*base, ProductionAction.date_raised >= date_from]
    open_clauses = [*base, ProductionAction.status.in_(OPEN_STATUSES)]
    overdue_clauses = [
        *open_clauses,
        ProductionAction.deadline < datetime.now(REPORT_TIMEZONE).date(),
    ]
    start_at = datetime.combine(date_from, time.min, tzinfo=REPORT_TIMEZONE)
    end_exclusive = datetime.combine(
        date_to + timedelta(days=1), time.min, tzinfo=REPORT_TIMEZONE
    )
    closed_clauses = [
        *base,
        ProductionAction.status == "CLOSED",
        ProductionAction.closed_at >= start_at,
        ProductionAction.closed_at < end_exclusive,
    ]

    def count(clauses: list) -> int:
        return int(db.scalar(select(func.count(ProductionAction.id)).where(*clauses)) or 0)

    return ProductionReportActionSummary(
        actions_created_in_period=count(created_clauses),
        current_open_actions=count(open_clauses),
        current_overdue_actions=count(overdue_clauses),
        closed_actions_in_period=count(closed_clauses),
        scope_note=(
            "Action counts use the reporting dates and optional project filter. "
            "Production-line, product and unit filters apply to production metrics only. "
            "Open and overdue counts reflect current status, not historical status at period end."
        ),
    )


def get_production_report(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    production_line: str | None = None,
    product_model: str | None = None,
    project_id: UUID | None = None,
    unit_of_measure: str | None = None,
) -> ProductionReportRead:
    validate_report_date_range(date_from, date_to)
    clauses = _filters(
        date_from=date_from,
        date_to=date_to,
        production_line=production_line,
        product_model=product_model,
        project_id=project_id,
        unit_of_measure=unit_of_measure,
    )
    granularity = "day" if (date_to - date_from).days <= 62 else "month"
    inconsistent_quality_record_count = int(
        db.scalar(
            select(func.count(ProductionEntry.id)).where(
                *clauses,
                ProductionEntry.accepted_quantity + ProductionEntry.rework_quantity
                > ProductionEntry.actual_quantity,
            )
        )
        or 0
    )
    return ProductionReportRead(
        date_from=date_from,
        date_to=date_to,
        granularity=granularity,
        filters=ProductionReportFilters(
            production_line=production_line,
            product_model=product_model,
            project_id=str(project_id) if project_id else None,
            unit_of_measure=unit_of_measure.strip().lower() if unit_of_measure else None,
        ),
        totals_by_unit=_aggregate_by_unit(db, clauses),
        by_line=_aggregate_dimension(db, clauses, ProductionEntry.production_line),
        by_product=_aggregate_dimension(db, clauses, ProductionEntry.product_model),
        trend=_aggregate_trend(db, clauses, granularity=granularity),
        actions=_action_summary(db, date_from=date_from, date_to=date_to, project_id=project_id),
        inconsistent_quality_record_count=inconsistent_quality_record_count,
        quality_definition=(
            "Accepted quantity means accepted at first inspection. Rework quantity means units "
            "sent for rework and is reported separately. First-pass non-acceptance equals actual "
            "minus first-pass accepted; it can include rework and other pending dispositions. "
            "Final scrap/rejection is unavailable because the current data model does not record "
            "post-rework disposition."
        ),
    )
