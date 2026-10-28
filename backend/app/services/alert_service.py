from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.errors import NotFoundError
from app.models.alert import Alert
from app.models.enums import AlertType, ProjectStatus, UserRole
from app.models.progress import ProgressLog
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.schemas.alert import AlertRead, AlertRunResult
from app.schemas.common import Page
from app.services import settings_service
from app.services.pagination import build_page, paginate

logger = logging.getLogger(__name__)


def _local_date(value: datetime, tz: ZoneInfo) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(tz).date()


def _insert_alert(
    db: Session,
    *,
    project_id: UUID,
    user_id: UUID,
    alert_type: AlertType,
    message: str,
    alert_date: date,
) -> bool:
    statement = (
        pg_insert(Alert)
        .values(
            id=uuid.uuid4(),
            project_id=project_id,
            user_id=user_id,
            type=alert_type,
            message=message,
            is_read=False,
            alert_date=alert_date,
        )
        .on_conflict_do_nothing(
            index_elements=[
                Alert.project_id,
                Alert.user_id,
                Alert.type,
                Alert.alert_date,
            ]
        )
        .returning(Alert.id)
    )
    return db.execute(statement).scalar_one_or_none() is not None


def run_time_counter(db: Session, *, now: datetime | None = None) -> AlertRunResult:
    tz = ZoneInfo(settings.scheduler_timezone)
    current = now.astimezone(tz) if now else datetime.now(tz)
    today = current.date()
    thresholds = settings_service.get_thresholds(db)

    projects = list(
        db.scalars(
            select(Project)
            .options(selectinload(Project.members).selectinload(ProjectMember.user))
            .where(Project.status != ProjectStatus.COMPLETED)
        ).all()
    )

    admins = list(
        db.scalars(select(User).where(User.role == UserRole.ADMIN, User.is_active.is_(True))).all()
    )
    super_admins = list(
        db.scalars(
            select(User).where(User.role == UserRole.SUPER_ADMIN, User.is_active.is_(True))
        ).all()
    )

    standard_projects = 0
    escalated_projects = 0
    severe_projects = 0
    created = 0
    duplicates = 0

    for project in projects:
        last_progress = db.scalar(
            select(func.max(ProgressLog.created_at)).where(ProgressLog.project_id == project.id)
        )
        anchor = project.status_changed_at
        if last_progress and last_progress > anchor:
            anchor = last_progress
        pending_days = max((today - _local_date(anchor, tz)).days, 0)
        deadline_days = (project.end_date - today).days if project.end_date else None
        deadline_near = (
            deadline_days is not None and deadline_days <= thresholds.deadline_reminder_days
        )

        severe = pending_days > int(
            thresholds.escalation_threshold_days * thresholds.severe_delay_multiplier
        )
        if pending_days > thresholds.escalation_threshold_days:
            alert_type = AlertType.ESCALATED
            escalated_projects += 1
            if severe:
                severe_projects += 1
            recipients = admins + (super_admins if severe else [])
            severity_label = "severely delayed" if severe else "delayed"
            deadline_text = (
                f" Deadline was {project.end_date.isoformat()}." if project.end_date else ""
            )
            message = (
                f"Project '{project.name}' is {severity_label}: no status or progress "
                f"update for {pending_days} days (escalation threshold "
                f"{thresholds.escalation_threshold_days} days).{deadline_text}"
            )
        elif pending_days > thresholds.safe_threshold_days or deadline_near:
            alert_type = AlertType.STANDARD
            standard_projects += 1
            recipients = [member.user for member in project.members if member.user.is_active]
            if deadline_near and deadline_days is not None:
                if deadline_days < 0:
                    deadline_text = f" The deadline passed {abs(deadline_days)} day(s) ago."
                else:
                    deadline_text = f" The deadline is in {deadline_days} day(s)."
            else:
                deadline_text = ""
            message = (
                f"Project '{project.name}' has had no status or progress update for "
                f"{pending_days} day(s).{deadline_text}"
            )
        else:
            continue

        for recipient in recipients:
            inserted = _insert_alert(
                db,
                project_id=project.id,
                user_id=recipient.id,
                alert_type=alert_type,
                message=message,
                alert_date=today,
            )
            if inserted:
                created += 1
            else:
                duplicates += 1

    db.commit()
    result = AlertRunResult(
        evaluated_projects=len(projects),
        standard_projects=standard_projects,
        escalated_projects=escalated_projects,
        severe_projects=severe_projects,
        alerts_created=created,
        duplicates_skipped=duplicates,
        run_at=current,
    )
    logger.info(
        "Time Counter run: %s projects, %s alerts created, %s duplicates",
        result.evaluated_projects,
        result.alerts_created,
        result.duplicates_skipped,
    )
    return result


def list_alerts(
    db: Session,
    *,
    user: User,
    page: int,
    page_size: int,
    unread_only: bool = False,
) -> Page[AlertRead]:
    statement = (
        select(Alert)
        .options(selectinload(Alert.project))
        .where(Alert.user_id == user.id)
        .order_by(Alert.created_at.desc())
    )
    if unread_only:
        statement = statement.where(Alert.is_read.is_(False))
    items, total = paginate(db, statement, page=page, page_size=page_size)
    return build_page([AlertRead.model_validate(alert) for alert in items], total, page, page_size)


def unread_count(db: Session, *, user: User) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(Alert.user_id == user.id, Alert.is_read.is_(False))
        )
        or 0
    )


def unread_escalated_count(db: Session, *, user: User) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(
                Alert.user_id == user.id,
                Alert.is_read.is_(False),
                Alert.type == AlertType.ESCALATED,
            )
        )
        or 0
    )


def recent_alerts(db: Session, *, user: User, limit: int = 5) -> list[AlertRead]:
    alerts = db.scalars(
        select(Alert)
        .options(selectinload(Alert.project))
        .where(Alert.user_id == user.id)
        .order_by(Alert.created_at.desc())
        .limit(limit)
    ).all()
    return [AlertRead.model_validate(alert) for alert in alerts]


def mark_read(db: Session, *, user: User, alert_id: UUID) -> Alert:
    alert = db.scalar(select(Alert).where(Alert.id == alert_id, Alert.user_id == user.id))
    if not alert:
        raise NotFoundError("Alert not found")
    if not alert.is_read:
        alert.is_read = True
        db.commit()
    return alert


def mark_all_read(db: Session, *, user: User) -> int:
    result = db.execute(
        update(Alert).where(Alert.user_id == user.id, Alert.is_read.is_(False)).values(is_read=True)
    )
    db.commit()
    return int(result.rowcount or 0)
