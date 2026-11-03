from __future__ import annotations

from datetime import date

from pydantic import Field

from app.models.enums import UserRole
from app.schemas.alert import AlertRead
from app.schemas.common import ORMModel
from app.schemas.project import ProjectRead


class DashboardStats(ORMModel):
    projects_total: int = 0
    projects_active: int = 0
    projects_completed: int = 0
    projects_assigned: int = 0
    pending_inventory: int = 0
    ready_for_production: int = 0
    awaiting_delivery: int = 0
    in_production: int = 0
    in_testing: int = 0
    pending_purchase_requests: int = 0
    unread_alerts: int = 0
    escalated_alerts: int = 0
    users_total: int = 0
    inventory_items: int = 0


class ProductionUnitDashboard(ORMModel):
    unit_of_measure: str
    entries_count: int = 0
    planned_quantity: float = 0
    actual_quantity: float = 0
    accepted_first_pass_quantity: float = 0
    rework_quantity: float = 0
    plan_achievement_percent: float | None = None
    first_pass_yield_percent: float | None = None
    rework_rate_percent: float | None = None


class DashboardProductionSummary(ORMModel):
    period_start: date
    period_end: date
    entries_count: int = 0
    open_actions: int = 0
    overdue_actions: int = 0
    units: list[ProductionUnitDashboard] = Field(default_factory=list)


class DashboardSummary(ORMModel):
    role: UserRole
    stats: DashboardStats
    recent_projects: list[ProjectRead]
    recent_alerts: list[AlertRead]
    production: DashboardProductionSummary
