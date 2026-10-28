from __future__ import annotations

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


class DashboardSummary(ORMModel):
    role: UserRole
    stats: DashboardStats
    recent_projects: list[ProjectRead]
    recent_alerts: list[AlertRead]
