from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import ACTIVE_PROJECT_STATUSES, ProjectStatus, PurchaseRequestStatus, UserRole
from app.models.inventory import InventoryItem
from app.models.production import ProductionAction, ProductionEntry
from app.models.project import Project, ProjectMember
from app.models.purchase import PurchaseRequest
from app.models.user import User
from app.schemas.alert import AlertRead
from app.schemas.dashboard import (
    DashboardProductionSummary,
    DashboardStats,
    DashboardSummary,
    ProductionUnitDashboard,
)
from app.schemas.project import ProjectRead
from app.services import alert_service
from app.services.project_service import project_load_options


def _count(db: Session, statement) -> int:
    return int(db.scalar(statement) or 0)


def build_production_summary(db: Session) -> DashboardProductionSummary:
    today = date.today()
    period_start = today.replace(day=1)
    grouped = db.execute(
        select(
            ProductionEntry.unit_of_measure,
            func.count(ProductionEntry.id),
            func.coalesce(func.sum(ProductionEntry.planned_quantity), 0),
            func.coalesce(func.sum(ProductionEntry.actual_quantity), 0),
            func.coalesce(func.sum(ProductionEntry.accepted_quantity), 0),
            func.coalesce(func.sum(ProductionEntry.rework_quantity), 0),
        )
        .where(
            ProductionEntry.production_date >= period_start,
            ProductionEntry.production_date <= today,
        )
        .group_by(ProductionEntry.unit_of_measure)
        .order_by(ProductionEntry.unit_of_measure)
    ).all()

    units: list[ProductionUnitDashboard] = []
    entries_count = 0
    for unit, count, planned, actual, accepted, rework in grouped:
        count = int(count)
        entries_count += count
        planned_value = float(planned or 0)
        actual_value = float(actual or 0)
        accepted_value = float(accepted or 0)
        rework_value = float(rework or 0)
        units.append(
            ProductionUnitDashboard(
                unit_of_measure=unit,
                entries_count=count,
                planned_quantity=planned_value,
                actual_quantity=actual_value,
                accepted_first_pass_quantity=accepted_value,
                rework_quantity=rework_value,
                plan_achievement_percent=(
                    round(actual_value * 100 / planned_value, 2) if planned_value else None
                ),
                first_pass_yield_percent=(
                    round(accepted_value * 100 / actual_value, 2) if actual_value else None
                ),
                rework_rate_percent=(
                    round(rework_value * 100 / actual_value, 2) if actual_value else None
                ),
            )
        )

    open_statuses = ("OPEN", "IN_PROGRESS", "ON_HOLD")
    open_actions = _count(
        db,
        select(func.count())
        .select_from(ProductionAction)
        .where(ProductionAction.status.in_(open_statuses)),
    )
    overdue_actions = _count(
        db,
        select(func.count())
        .select_from(ProductionAction)
        .where(
            ProductionAction.status.in_(open_statuses),
            ProductionAction.deadline < today,
        ),
    )
    return DashboardProductionSummary(
        period_start=period_start,
        period_end=today,
        entries_count=entries_count,
        open_actions=open_actions,
        overdue_actions=overdue_actions,
        units=units,
    )


def build_summary(db: Session, *, user: User) -> DashboardSummary:
    rows = dict(
        db.execute(select(Project.status, func.count(Project.id)).group_by(Project.status)).all()
    )
    total = sum(int(count) for count in rows.values())
    active = sum(int(count) for status, count in rows.items() if status in ACTIVE_PROJECT_STATUSES)
    assigned = _count(
        db,
        select(func.count(func.distinct(Project.id)))
        .select_from(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id),
    )
    stats = DashboardStats(
        projects_total=total,
        projects_active=active,
        projects_completed=int(rows.get(ProjectStatus.COMPLETED, 0)),
        projects_assigned=assigned,
        pending_inventory=int(rows.get(ProjectStatus.PENDING_INVENTORY, 0)),
        ready_for_production=int(rows.get(ProjectStatus.READY_FOR_PRODUCTION, 0)),
        awaiting_delivery=int(rows.get(ProjectStatus.AWAITING_DELIVERY, 0)),
        in_production=int(rows.get(ProjectStatus.IN_PRODUCTION, 0)),
        in_testing=int(rows.get(ProjectStatus.IN_TESTING, 0)),
        unread_alerts=alert_service.unread_count(db, user=user),
        escalated_alerts=alert_service.unread_escalated_count(db, user=user),
    )

    if user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        stats.pending_purchase_requests = _count(
            db,
            select(func.count())
            .select_from(PurchaseRequest)
            .where(PurchaseRequest.status == PurchaseRequestStatus.PENDING),
        )
    else:
        stats.pending_purchase_requests = _count(
            db,
            select(func.count())
            .select_from(PurchaseRequest)
            .where(
                PurchaseRequest.requested_by == user.id,
                PurchaseRequest.status == PurchaseRequestStatus.PENDING,
            ),
        )

    if user.role == UserRole.SUPER_ADMIN:
        stats.users_total = _count(db, select(func.count()).select_from(User))
        stats.inventory_items = _count(db, select(func.count()).select_from(InventoryItem))

    recent_projects = db.scalars(
        select(Project)
        .options(*project_load_options())
        .order_by(Project.updated_at.desc())
        .limit(5)
    ).all()
    recent_alerts: list[AlertRead] = alert_service.recent_alerts(db, user=user, limit=5)

    return DashboardSummary(
        role=user.role,
        stats=stats,
        recent_projects=[ProjectRead.model_validate(project) for project in recent_projects],
        recent_alerts=recent_alerts,
        production=build_production_summary(db),
    )
