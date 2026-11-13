from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel


class ProductionReportMetric(BaseModel):
    """Aggregated production measurements for one unit of measure."""

    unit_of_measure: str
    entries_count: int
    planned_quantity: float
    actual_quantity: float
    accepted_first_pass_quantity: float
    rework_sent_quantity: float
    first_pass_non_acceptance_quantity: float
    plan_achievement_percent: float | None
    first_pass_yield_percent: float | None
    rework_rate_percent: float | None
    first_pass_non_acceptance_rate_percent: float | None
    production_hours: float
    downtime_hours: float
    downtime_percent: float | None


class ProductionReportDimensionMetric(ProductionReportMetric):
    dimension_value: str


class ProductionReportTrendPoint(ProductionReportMetric):
    period: str


class ProductionReportActionSummary(BaseModel):
    actions_created_in_period: int
    current_open_actions: int
    current_overdue_actions: int
    closed_actions_in_period: int
    scope_note: str


class ProductionReportFilters(BaseModel):
    production_line: str | None = None
    product_model: str | None = None
    project_id: str | None = None
    unit_of_measure: str | None = None


class ProductionReportRead(BaseModel):
    date_from: date
    date_to: date
    granularity: Literal["day", "month"]
    filters: ProductionReportFilters
    totals_by_unit: list[ProductionReportMetric]
    by_line: list[ProductionReportDimensionMetric]
    by_product: list[ProductionReportDimensionMetric]
    trend: list[ProductionReportTrendPoint]
    actions: ProductionReportActionSummary
    inconsistent_quality_record_count: int
    quality_definition: str


__all__ = [
    "ProductionReportActionSummary",
    "ProductionReportDimensionMetric",
    "ProductionReportFilters",
    "ProductionReportMetric",
    "ProductionReportRead",
    "ProductionReportTrendPoint",
]
