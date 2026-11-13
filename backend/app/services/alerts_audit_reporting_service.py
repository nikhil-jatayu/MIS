from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import DateTime, case, cast, distinct, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import UnprocessableError
from app.models.alert import Alert
from app.models.audit import AuditLog
from app.models.enums import AlertType
from app.models.project import Project
from app.models.user import User
from app.schemas.alerts_audit_reporting import (
    AlertProjectBreakdown,
    AlertReportRow,
    AlertsReportFilters,
    AlertsReportSection,
    AlertTrendPoint,
    AuditActorBreakdown,
    AuditReportFilters,
    AuditReportRow,
    AuditReportSection,
    AuditTrendPoint,
    ReportCountBreakdown,
)

MAX_REPORT_DAYS = 366
MAX_ALERT_ROWS = 250
MAX_AUDIT_ROWS = 300
MAX_PROJECT_BREAKDOWN = 50
MAX_AUDIT_ACTORS = 30


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


def _trend_granularity(date_from: date, date_to: date) -> str:
    return "day" if (date_to - date_from).days <= 62 else "month"


def _alerts_statement(
    *,
    actor: User,
    date_from: date,
    date_to: date,
    project_id: UUID | None,
    alert_type: AlertType | None,
    is_read: bool | None,
):
    # Alerts are intentionally scoped to the authenticated recipient. A normal user
    # must never be able to infer another user's alert activity through aggregates.
    statement = select(Alert).where(
        Alert.user_id == actor.id,
        Alert.alert_date >= date_from,
        Alert.alert_date <= date_to,
    )
    if project_id:
        statement = statement.where(Alert.project_id == project_id)
    if alert_type:
        statement = statement.where(Alert.type == alert_type)
    if is_read is not None:
        statement = statement.where(Alert.is_read.is_(is_read))
    return statement


def get_alerts_report(
    db: Session,
    *,
    actor: User,
    date_from: date,
    date_to: date,
    project_id: UUID | None = None,
    alert_type: AlertType | None = None,
    is_read: bool | None = None,
) -> tuple[AlertsReportFilters, AlertsReportSection]:
    _window(date_from, date_to)
    statement = _alerts_statement(
        actor=actor,
        date_from=date_from,
        date_to=date_to,
        project_id=project_id,
        alert_type=alert_type,
        is_read=is_read,
    )
    filtered = statement.subquery()
    total = int(db.scalar(select(func.count()).select_from(filtered)) or 0)
    unread = int(
        db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(Alert.id.in_(select(filtered.c.id)), Alert.is_read.is_(False))
        )
        or 0
    )
    read = total - unread
    standard = int(
        db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(Alert.id.in_(select(filtered.c.id)), Alert.type == AlertType.STANDARD)
        )
        or 0
    )
    escalated = total - standard
    projects_count = int(
        db.scalar(
            select(func.count(distinct(Alert.project_id))).where(
                Alert.id.in_(select(filtered.c.id))
            )
        )
        or 0
    )

    type_rows = db.execute(
        select(Alert.type, func.count(Alert.id))
        .where(Alert.id.in_(select(filtered.c.id)))
        .group_by(Alert.type)
        .order_by(Alert.type)
    ).all()
    project_rows = db.execute(
        select(
            Project.id,
            Project.name,
            func.count(Alert.id),
            func.sum(case((Alert.is_read.is_(False), 1), else_=0)),
            func.sum(case((Alert.type == AlertType.ESCALATED, 1), else_=0)),
        )
        .join(Alert, Alert.project_id == Project.id)
        .where(Alert.id.in_(select(filtered.c.id)))
        .group_by(Project.id, Project.name)
        .order_by(func.count(Alert.id).desc(), Project.name.asc())
        .limit(MAX_PROJECT_BREAKDOWN)
    ).all()

    granularity = _trend_granularity(date_from, date_to)
    trend_bucket = func.date_trunc(granularity, cast(Alert.alert_date, DateTime))
    trend_rows = db.execute(
        select(trend_bucket, func.count(Alert.id))
        .where(Alert.id.in_(select(filtered.c.id)))
        .group_by(trend_bucket)
        .order_by(trend_bucket)
    ).all()

    detail_rows = db.scalars(
        select(Alert)
        .options(selectinload(Alert.project))
        .where(Alert.id.in_(select(filtered.c.id)))
        .order_by(Alert.alert_date.desc(), Alert.created_at.desc(), Alert.id)
        .limit(MAX_ALERT_ROWS)
    ).all()

    type_breakdown = [
        ReportCountBreakdown(label=row[0].value, count=int(row[1])) for row in type_rows
    ]
    project_breakdown = [
        AlertProjectBreakdown(
            project_id=row[0],
            project_name=row[1],
            total_alerts=int(row[2] or 0),
            unread_alerts=int(row[3] or 0),
            escalated_alerts=int(row[4] or 0),
        )
        for row in project_rows
    ]
    trend = [
        AlertTrendPoint(period=row[0].date(), alerts_created=int(row[1])) for row in trend_rows
    ]
    items = [
        AlertReportRow(
            id=item.id,
            project_id=item.project_id,
            project_name=item.project.name,
            alert_type=item.type.value,
            message=item.message,
            alert_date=item.alert_date,
            created_at=item.created_at,
            is_read=item.is_read,
        )
        for item in detail_rows
    ]

    capped_note = (
        f" Detailed alert rows are limited to the latest {MAX_ALERT_ROWS} matching alerts."
        if total > MAX_ALERT_ROWS
        else ""
    )
    filters = AlertsReportFilters(
        date_from=date_from,
        date_to=date_to,
        project_id=project_id,
        alert_type=alert_type,
        is_read=is_read,
    )
    section = AlertsReportSection(
        total_alerts=total,
        unread_alerts=unread,
        read_alerts=read,
        standard_alerts=standard,
        escalated_alerts=escalated,
        projects_with_alerts=projects_count,
        type_breakdown=type_breakdown,
        project_breakdown=project_breakdown,
        trend=trend,
        items=items,
        scope_note=(
            "This report includes only alerts addressed to the currently authenticated user. "
            "The selected date range applies to alert_date (the alert's business date). "
            "Read/unread values reflect the current read state, not a historical read-state "
            f"snapshot. Trend buckets use alert creation timestamps.{capped_note}"
        ),
    )
    return filters, section


def get_audit_report(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    actor_id: UUID | None = None,
    action: str | None = None,
    entity: str | None = None,
) -> tuple[AuditReportFilters, AuditReportSection]:
    start, end_exclusive = _window(date_from, date_to)
    statement = select(AuditLog).where(
        AuditLog.created_at >= start,
        AuditLog.created_at < end_exclusive,
    )
    if actor_id:
        statement = statement.where(AuditLog.actor_id == actor_id)
    if action:
        statement = statement.where(AuditLog.action == action)
    if entity:
        statement = statement.where(AuditLog.entity == entity)

    filtered = statement.subquery()
    total = int(db.scalar(select(func.count()).select_from(filtered)) or 0)
    unique_actors = int(
        db.scalar(
            select(func.count(distinct(AuditLog.actor_id))).where(
                AuditLog.id.in_(select(filtered.c.id)), AuditLog.actor_id.is_not(None)
            )
        )
        or 0
    )
    unique_entities = int(
        db.scalar(
            select(
                func.count(
                    distinct(
                        func.concat(
                            AuditLog.entity,
                            ":",
                            func.coalesce(AuditLog.entity_id, "<none>"),
                        )
                    )
                )
            ).where(AuditLog.id.in_(select(filtered.c.id)))
        )
        or 0
    )

    action_rows = db.execute(
        select(AuditLog.action, func.count(AuditLog.id))
        .where(AuditLog.id.in_(select(filtered.c.id)))
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc(), AuditLog.action.asc())
    ).all()
    entity_rows = db.execute(
        select(AuditLog.entity, func.count(AuditLog.id))
        .where(AuditLog.id.in_(select(filtered.c.id)))
        .group_by(AuditLog.entity)
        .order_by(func.count(AuditLog.id).desc(), AuditLog.entity.asc())
    ).all()
    actor_rows = db.execute(
        select(AuditLog.actor_id, User.name, func.count(AuditLog.id))
        .outerjoin(User, User.id == AuditLog.actor_id)
        .where(AuditLog.id.in_(select(filtered.c.id)))
        .group_by(AuditLog.actor_id, User.name)
        .order_by(func.count(AuditLog.id).desc(), User.name.asc().nullslast())
        .limit(MAX_AUDIT_ACTORS)
    ).all()

    granularity = _trend_granularity(date_from, date_to)
    trend_bucket = func.date_trunc(granularity, AuditLog.created_at)
    trend_rows = db.execute(
        select(trend_bucket, func.count(AuditLog.id))
        .where(AuditLog.id.in_(select(filtered.c.id)))
        .group_by(trend_bucket)
        .order_by(trend_bucket)
    ).all()

    detail_rows = db.scalars(
        select(AuditLog)
        .options(selectinload(AuditLog.actor))
        .where(AuditLog.id.in_(select(filtered.c.id)))
        .order_by(AuditLog.created_at.desc(), AuditLog.id)
        .limit(MAX_AUDIT_ROWS)
    ).all()

    filters = AuditReportFilters(
        date_from=date_from,
        date_to=date_to,
        actor_id=actor_id,
        action=action,
        entity=entity,
    )
    capped_note = (
        f" Detailed audit events are limited to the latest {MAX_AUDIT_ROWS} matching events."
        if total > MAX_AUDIT_ROWS
        else ""
    )
    section = AuditReportSection(
        total_events=total,
        unique_actors=unique_actors,
        unique_entity_references=unique_entities,
        action_breakdown=[
            ReportCountBreakdown(label=row[0], count=int(row[1])) for row in action_rows
        ],
        entity_breakdown=[
            ReportCountBreakdown(label=row[0], count=int(row[1])) for row in entity_rows
        ],
        actor_breakdown=[
            AuditActorBreakdown(
                actor_id=row[0],
                actor_name=row[1] or "Deleted or unavailable user",
                events=int(row[2]),
            )
            for row in actor_rows
        ],
        trend=[AuditTrendPoint(period=row[0].date(), events=int(row[1])) for row in trend_rows],
        items=[
            AuditReportRow(
                id=item.id,
                actor_id=item.actor_id,
                actor_name=item.actor.name if item.actor else "Deleted or unavailable user",
                action=item.action,
                entity=item.entity,
                entity_id=item.entity_id,
                created_at=item.created_at,
            )
            for item in detail_rows
        ],
        scope_note=(
            "Audit reporting is restricted to Super Admins. This report summarizes append-only "
            "audit metadata and deliberately excludes before/after payloads; use the Audit Trail "
            "page for authorized record-level inspection. The date range applies to event "
            f"creation timestamps.{capped_note}"
        ),
    )
    return filters, section
