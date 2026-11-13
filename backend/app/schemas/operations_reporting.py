from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OperationsReportFilters(BaseModel):
    date_from: date
    date_to: date
    project_id: UUID | None = None
    project_status: str | None = None
    project_type: str | None = None
    priority: str | None = None
    purchase_status: str | None = None


class CountBreakdown(BaseModel):
    label: str
    count: int


class ProjectTrendPoint(BaseModel):
    period: date
    projects_created: int


class ProjectReportRow(BaseModel):
    id: UUID
    name: str
    type: str
    status: str
    priority: str
    start_date: date | None
    end_date: date | None
    progress_percent: int
    shortage_lines: int
    created_at: datetime


class ProjectsReportSection(BaseModel):
    total_projects: int
    average_progress_percent: float | None
    current_overdue_projects: int
    progress_updates_in_period: int
    status_breakdown: list[CountBreakdown]
    priority_breakdown: list[CountBreakdown]
    creation_trend: list[ProjectTrendPoint]
    items: list[ProjectReportRow]
    scope_note: str


class InventoryItemReportRow(BaseModel):
    id: UUID
    name: str
    sku: str
    quantity_available: int
    active_project_count: int
    active_project_required: int
    active_project_allocated: int
    active_project_shortage: int


class InventoryReportSection(BaseModel):
    as_of: date
    total_items: int
    zero_stock_items: int
    items_with_active_project_demand: int
    items_with_active_project_shortage: int
    items: list[InventoryItemReportRow]
    scope_note: str


class PurchaseItemBreakdown(BaseModel):
    sku: str
    item_name: str
    request_count: int
    requested_quantity: int


class PurchaseRequestReportRow(BaseModel):
    id: UUID
    project_name: str
    item_name: str
    sku: str
    quantity: int
    status: str
    requester_name: str
    created_at: datetime
    approved_at: datetime | None
    ordered_at: datetime | None
    delivered_at: datetime | None


class PurchasesReportSection(BaseModel):
    total_requests: int
    status_breakdown: list[CountBreakdown]
    average_approval_hours: float | None
    average_delivery_days: float | None
    by_item: list[PurchaseItemBreakdown]
    items: list[PurchaseRequestReportRow]
    scope_note: str


class OperationsReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    filters: OperationsReportFilters
    projects: ProjectsReportSection
    inventory: InventoryReportSection
    purchases: PurchasesReportSection
