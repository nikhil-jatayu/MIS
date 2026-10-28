from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import ACTIVE_PROJECT_STATUSES, ProjectStatus, PurchaseRequestStatus, UserRole
from app.models.inventory import InventoryItem
from app.models.project import Project, ProjectMember
from app.models.purchase import PurchaseRequest
from app.models.user import User
from app.schemas.alert import AlertRead
from app.schemas.dashboard import DashboardStats, DashboardSummary
from app.schemas.project import ProjectRead
from app.services import alert_service
from app.services.project_service import project_load_options


def _count(db: Session, statement) -> int:
    return int(db.scalar(statement) or 0)


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
    )
