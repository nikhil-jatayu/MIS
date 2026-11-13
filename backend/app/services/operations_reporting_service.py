from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import case, distinct, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import UnprocessableError
from app.models.enums import ACTIVE_PROJECT_STATUSES, ProjectStatus, UserRole
from app.models.inventory import InventoryItem
from app.models.progress import ProgressLog
from app.models.project import Project, ProjectBOM, ProjectMember
from app.models.purchase import PurchaseRequest
from app.models.user import User
from app.schemas.operations_reporting import (
    CountBreakdown,
    InventoryItemReportRow,
    InventoryReportSection,
    OperationsReportFilters,
    OperationsReportRead,
    ProjectReportRow,
    ProjectsReportSection,
    ProjectTrendPoint,
    PurchaseItemBreakdown,
    PurchaseRequestReportRow,
    PurchasesReportSection,
)

MAX_REPORT_DAYS = 366
MAX_PROJECT_ROWS = 250
MAX_PURCHASE_ROWS = 500


def _window(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    if date_to < date_from:
        raise UnprocessableError("The report end date must be on or after the start date")
    if (date_to - date_from).days + 1 > MAX_REPORT_DAYS:
        raise UnprocessableError(
            f"The report range cannot exceed {MAX_REPORT_DAYS} days",
            code="REPORT_RANGE_TOO_LARGE",
        )
    start = datetime.combine(date_from, time.min, tzinfo=UTC)
    end_exclusive = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
    return start, end_exclusive


def _project_statement(
    *,
    start: datetime,
    end_exclusive: datetime,
    project_id: UUID | None,
    project_status: str | None,
    project_type: str | None,
    priority: str | None,
):
    statement = select(Project).where(
        Project.created_at >= start,
        Project.created_at < end_exclusive,
    )
    if project_id:
        statement = statement.where(Project.id == project_id)
    if project_status:
        statement = statement.where(Project.status == project_status)
    if project_type:
        statement = statement.where(Project.type == project_type)
    if priority:
        statement = statement.where(Project.priority == priority)
    return statement


def _project_report(
    db: Session,
    *,
    today: date,
    date_from: date,
    date_to: date,
    start: datetime,
    end_exclusive: datetime,
    project_id: UUID | None,
    project_status: str | None,
    project_type: str | None,
    priority: str | None,
) -> ProjectsReportSection:
    base = _project_statement(
        start=start,
        end_exclusive=end_exclusive,
        project_id=project_id,
        project_status=project_status,
        project_type=project_type,
        priority=priority,
    )
    project_ids = base.with_only_columns(Project.id).order_by(None).subquery()

    total_projects = int(db.scalar(select(func.count()).select_from(project_ids)) or 0)
    average_progress = db.scalar(
        select(func.avg(Project.progress_percent)).where(Project.id.in_(select(project_ids.c.id)))
    )
    overdue_count = int(
        db.scalar(
            select(func.count()).select_from(Project).where(
                Project.id.in_(select(project_ids.c.id)),
                Project.status != ProjectStatus.COMPLETED,
                Project.end_date.is_not(None),
                Project.end_date < today,
            )
        )
        or 0
    )
    progress_updates = int(
        db.scalar(
            select(func.count()).select_from(ProgressLog).where(
                ProgressLog.project_id.in_(select(project_ids.c.id)),
                ProgressLog.created_at >= start,
                ProgressLog.created_at < end_exclusive,
            )
        )
        or 0
    )

    status_rows = db.execute(
        select(Project.status, func.count(Project.id))
        .where(Project.id.in_(select(project_ids.c.id)))
        .group_by(Project.status)
        .order_by(Project.status)
    ).all()
    priority_rows = db.execute(
        select(Project.priority, func.count(Project.id))
        .where(Project.id.in_(select(project_ids.c.id)))
        .group_by(Project.priority)
        .order_by(Project.priority)
    ).all()

    granularity = "day" if (date_to - date_from).days <= 62 else "month"
    bucket_expr = func.date_trunc(granularity, Project.created_at)
    trend_rows = db.execute(
        select(bucket_expr, func.count(Project.id))
        .where(Project.id.in_(select(project_ids.c.id)))
        .group_by(bucket_expr)
        .order_by(bucket_expr)
    ).all()
    trend = [
        ProjectTrendPoint(period=row[0].date(), projects_created=int(row[1])) for row in trend_rows
    ]

    projects = list(
        db.scalars(
            base.order_by(Project.created_at.desc(), Project.id).limit(MAX_PROJECT_ROWS)
        ).all()
    )
    project_row_ids = [project.id for project in projects]
    shortage_counts: dict[UUID, int] = defaultdict(int)
    if project_row_ids:
        shortage_rows = db.execute(
            select(ProjectBOM.project_id, func.count(ProjectBOM.id))
            .where(
                ProjectBOM.project_id.in_(project_row_ids),
                ProjectBOM.quantity_required > ProjectBOM.quantity_allocated,
            )
            .group_by(ProjectBOM.project_id)
        ).all()
        shortage_counts = {row[0]: int(row[1]) for row in shortage_rows}

    items = [
        ProjectReportRow(
            id=project.id,
            name=project.name,
            type=project.type.value,
            status=project.status.value,
            priority=project.priority.value,
            start_date=project.start_date,
            end_date=project.end_date,
            progress_percent=int(project.progress_percent),
            shortage_lines=shortage_counts.get(project.id, 0),
            created_at=project.created_at,
        )
        for project in projects
    ]
    capped_note = (
        f" The project detail table is limited to the latest {MAX_PROJECT_ROWS} matching projects."
        if total_projects > MAX_PROJECT_ROWS
        else ""
    )
    return ProjectsReportSection(
        total_projects=total_projects,
        average_progress_percent=round(float(average_progress), 2)
        if average_progress is not None
        else None,
        current_overdue_projects=overdue_count,
        progress_updates_in_period=progress_updates,
        status_breakdown=[
            CountBreakdown(label=row[0].value, count=int(row[1])) for row in status_rows
        ],
        priority_breakdown=[
            CountBreakdown(label=row[0].value, count=int(row[1])) for row in priority_rows
        ],
        creation_trend=trend,
        items=items,
        scope_note=(
            "Projects are selected by their creation timestamp within the chosen inclusive date "
            "range. Status, progress, priority and overdue figures reflect their current values, "
            "not reconstructed historical snapshots. Progress updates count log entries created "
            f"inside the selected range.{capped_note}"
        ),
    )


def _inventory_report(
    db: Session,
    *,
    today: date,
    project_id: UUID | None,
) -> InventoryReportSection:
    inventory_items = list(db.scalars(select(InventoryItem).order_by(InventoryItem.sku)).all())
    demand_statement = (
        select(
            ProjectBOM.item_id,
            func.sum(ProjectBOM.quantity_required),
            func.sum(ProjectBOM.quantity_allocated),
            func.sum(
                case(
                    (
                        ProjectBOM.quantity_required > ProjectBOM.quantity_allocated,
                        ProjectBOM.quantity_required - ProjectBOM.quantity_allocated,
                    ),
                    else_=0,
                )
            ),
            func.count(distinct(ProjectBOM.project_id)),
        )
        .join(Project, Project.id == ProjectBOM.project_id)
        .where(Project.status.in_(list(ACTIVE_PROJECT_STATUSES)))
        .group_by(ProjectBOM.item_id)
    )
    if project_id:
        demand_statement = demand_statement.where(Project.id == project_id)
    demand_rows = db.execute(demand_statement).all()
    demand = {
        row[0]: {
            "required": int(row[1] or 0),
            "allocated": int(row[2] or 0),
            "shortage": int(row[3] or 0),
            "project_count": int(row[4] or 0),
        }
        for row in demand_rows
    }

    items = [
        InventoryItemReportRow(
            id=item.id,
            name=item.name,
            sku=item.sku,
            quantity_available=int(item.quantity_available),
            active_project_count=demand.get(item.id, {}).get("project_count", 0),
            active_project_required=demand.get(item.id, {}).get("required", 0),
            active_project_allocated=demand.get(item.id, {}).get("allocated", 0),
            active_project_shortage=demand.get(item.id, {}).get("shortage", 0),
        )
        for item in inventory_items
    ]
    return InventoryReportSection(
        as_of=today,
        total_items=len(items),
        zero_stock_items=sum(1 for item in items if item.quantity_available == 0),
        items_with_active_project_demand=sum(1 for item in items if item.active_project_count),
        items_with_active_project_shortage=sum(
            1 for item in items if item.active_project_shortage > 0
        ),
        items=items,
        scope_note=(
            "Inventory is a current stock snapshot as of the report date; the selected date "
            "range does not create historical stock balances because the MIS inventory model has "
            "no stock-movement ledger. BOM demand and allocated quantities include active "
            "projects only. The project selector can scope BOM demand. Project "
            "status/type/priority filters apply to the Projects section only. Quantities are "
            "shown per SKU and are not "
            "summed across different items because the inventory model does not store a "
            "unit of measure."
            + (" BOM demand is restricted to the selected project." if project_id else "")
        ),
    )


def _purchase_report(
    db: Session,
    *,
    actor: User,
    start: datetime,
    end_exclusive: datetime,
    project_id: UUID | None,
    purchase_status: str | None,
) -> PurchasesReportSection:
    statement = (
        select(PurchaseRequest)
        .options(
            selectinload(PurchaseRequest.project),
            selectinload(PurchaseRequest.item),
            selectinload(PurchaseRequest.requester),
        )
        .where(
            PurchaseRequest.created_at >= start,
            PurchaseRequest.created_at < end_exclusive,
        )
    )
    if project_id:
        statement = statement.where(PurchaseRequest.project_id == project_id)
    if purchase_status:
        statement = statement.where(PurchaseRequest.status == purchase_status)
    if actor.role == UserRole.USER:
        statement = statement.where(
            (PurchaseRequest.requested_by == actor.id)
            | PurchaseRequest.project.has(Project.members.any(ProjectMember.user_id == actor.id))
        )

    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total_requests = int(db.scalar(count_statement) or 0)
    rows = list(
        db.scalars(
            statement.order_by(PurchaseRequest.created_at.desc()).limit(MAX_PURCHASE_ROWS)
        ).all()
    )

    status_statement = select(PurchaseRequest.status, func.count(PurchaseRequest.id)).where(
        PurchaseRequest.created_at >= start,
        PurchaseRequest.created_at < end_exclusive,
    )
    if project_id:
        status_statement = status_statement.where(PurchaseRequest.project_id == project_id)
    if purchase_status:
        status_statement = status_statement.where(PurchaseRequest.status == purchase_status)
    if actor.role == UserRole.USER:
        status_statement = status_statement.where(
            (PurchaseRequest.requested_by == actor.id)
            | PurchaseRequest.project.has(Project.members.any(ProjectMember.user_id == actor.id))
        )
    status_rows = db.execute(
        status_statement.group_by(PurchaseRequest.status).order_by(PurchaseRequest.status)
    ).all()

    by_item: dict[str, dict[str, Any]] = {}
    approval_hours: list[float] = []
    delivery_days: list[float] = []
    request_items: list[PurchaseRequestReportRow] = []
    for request in rows:
        key = request.item.sku
        if key not in by_item:
            by_item[key] = {
                "sku": key,
                "item_name": request.item.name,
                "request_count": 0,
                "requested_quantity": 0,
            }
        by_item[key]["request_count"] += 1
        by_item[key]["requested_quantity"] += int(request.quantity)
        if request.approved_at:
            approval_hours.append(
                max((request.approved_at - request.created_at).total_seconds() / 3600, 0.0)
            )
        if request.delivered_at:
            delivery_days.append(
                max((request.delivered_at - request.created_at).total_seconds() / 86400, 0.0)
            )
        request_items.append(
            PurchaseRequestReportRow(
                id=request.id,
                project_name=request.project.name,
                item_name=request.item.name,
                sku=request.item.sku,
                quantity=int(request.quantity),
                status=request.status.value,
                requester_name=request.requester.name,
                created_at=request.created_at,
                approved_at=request.approved_at,
                ordered_at=request.ordered_at,
                delivered_at=request.delivered_at,
            )
        )
    capped_note = (
        " Detail, item breakdowns and average durations use the latest "
        f"{MAX_PURCHASE_ROWS} matching requests."
        if total_requests > MAX_PURCHASE_ROWS
        else ""
    )
    return PurchasesReportSection(
        total_requests=total_requests,
        status_breakdown=[
            CountBreakdown(label=row[0].value, count=int(row[1])) for row in status_rows
        ],
        average_approval_hours=round(sum(approval_hours) / len(approval_hours), 2)
        if approval_hours
        else None,
        average_delivery_days=round(sum(delivery_days) / len(delivery_days), 2)
        if delivery_days
        else None,
        by_item=[
            PurchaseItemBreakdown(**row)
            for row in sorted(by_item.values(), key=lambda item: item["sku"])
        ],
        items=request_items,
        scope_note=(
            "Purchase requests are selected by request creation timestamp within the chosen "
            "inclusive date range. Status reflects the current request status; historical status "
            "transitions are not reconstructed. Average approval/delivery durations use requests "
            "in this created-date cohort that have the corresponding timestamp. Project "
            "status/type/priority filters apply to the Projects section only. The purchase schema "
            "does not store unit prices, so spend/value cannot be calculated."
            f"{capped_note}"
        ),
    )


def get_operations_report(
    db: Session,
    *,
    actor: User,
    date_from: date,
    date_to: date,
    project_id: UUID | None = None,
    project_status: str | None = None,
    project_type: str | None = None,
    priority: str | None = None,
    purchase_status: str | None = None,
    today: date | None = None,
) -> OperationsReportRead:
    start, end_exclusive = _window(date_from, date_to)
    current_date = today or date.today()

    projects = _project_report(
        db,
        today=current_date,
        date_from=date_from,
        date_to=date_to,
        start=start,
        end_exclusive=end_exclusive,
        project_id=project_id,
        project_status=project_status,
        project_type=project_type,
        priority=priority,
    )
    inventory = _inventory_report(db, today=current_date, project_id=project_id)
    purchases = _purchase_report(
        db,
        actor=actor,
        start=start,
        end_exclusive=end_exclusive,
        project_id=project_id,
        purchase_status=purchase_status,
    )
    return OperationsReportRead(
        filters=OperationsReportFilters(
            date_from=date_from,
            date_to=date_to,
            project_id=project_id,
            project_status=project_status,
            project_type=project_type,
            priority=priority,
            purchase_status=purchase_status,
        ),
        projects=projects,
        inventory=inventory,
        purchases=purchases,
    )
