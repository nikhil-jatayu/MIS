from __future__ import annotations

import calendar
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ForbiddenError, NotFoundError, UnprocessableError
from app.models.enums import UserRole
from app.models.production import ProductionAction, ProductionEntry, ProductionMonthlyReview
from app.models.user import User
from app.schemas.common import Page
from app.schemas.production import (
    ProductionActionCreate,
    ProductionActionRead,
    ProductionActionUpdate,
    ProductionEntryCreate,
    ProductionEntryRead,
    ProductionEntryUpdate,
    ProductionMonthlyReviewRead,
    ProductionMonthlyReviewUpsert,
    ProductionSummaryRead,
    ProductionUnitSummary,
)
from app.services import audit_service, project_service
from app.services.pagination import build_page, paginate

OPEN_STATUSES = ("OPEN", "IN_PROGRESS", "ON_HOLD")


def _is_admin(user: User) -> bool:
    return user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}


def _entry_query():
    return select(ProductionEntry).options(selectinload(ProductionEntry.creator))


def _action_query():
    return select(ProductionAction).options(
        selectinload(ProductionAction.creator),
        selectinload(ProductionAction.responsible_user),
        selectinload(ProductionAction.closed_by),
    )


def _review_query():
    return select(ProductionMonthlyReview).options(
        selectinload(ProductionMonthlyReview.prepared_by),
        selectinload(ProductionMonthlyReview.reviewed_by),
    )


def _ensure_project_access(db: Session, project_id: UUID | None, actor: User) -> None:
    if project_id is None:
        return
    project = project_service.get_project(db, project_id)
    project_service.ensure_project_action_access(db, project, actor)


def _ensure_entry_edit_access(entry: ProductionEntry, actor: User) -> None:
    if entry.created_by != actor.id and not _is_admin(actor):
        raise ForbiddenError("You can only edit your own production entries")


def get_entry(db: Session, entry_id: UUID) -> ProductionEntry:
    entry = db.scalar(_entry_query().where(ProductionEntry.id == entry_id))
    if not entry:
        raise NotFoundError("Production entry not found")
    return entry


def list_entries(
    db: Session,
    *,
    page: int,
    page_size: int,
    date_from: date | None = None,
    date_to: date | None = None,
    project_id: UUID | None = None,
    production_line: str | None = None,
    unit_of_measure: str | None = None,
) -> Page[ProductionEntryRead]:
    statement = _entry_query().order_by(
        ProductionEntry.production_date.desc(), ProductionEntry.created_at.desc()
    )
    if date_from:
        statement = statement.where(ProductionEntry.production_date >= date_from)
    if date_to:
        statement = statement.where(ProductionEntry.production_date <= date_to)
    if project_id:
        statement = statement.where(ProductionEntry.project_id == project_id)
    if production_line:
        statement = statement.where(ProductionEntry.production_line.ilike(f"%{production_line}%"))
    if unit_of_measure:
        statement = statement.where(ProductionEntry.unit_of_measure == unit_of_measure)
    items, total = paginate(db, statement, page=page, page_size=page_size)
    return build_page(
        [ProductionEntryRead.model_validate(item) for item in items], total, page, page_size
    )


def create_entry(db: Session, *, actor: User, payload: ProductionEntryCreate) -> ProductionEntry:
    _ensure_project_access(db, payload.project_id, actor)
    entry = ProductionEntry(**payload.model_dump(), created_by=actor.id)
    db.add(entry)
    db.flush()
    audit_service.record(
        db,
        actor_id=actor.id,
        action="CREATE",
        entity="production_entry",
        entity_id=entry.id,
        after={
            "production_date": entry.production_date,
            "production_line": entry.production_line,
            "product_model": entry.product_model,
            "actual_quantity": entry.actual_quantity,
            "unit_of_measure": entry.unit_of_measure,
        },
    )
    db.commit()
    return get_entry(db, entry.id)


def update_entry(
    db: Session, *, actor: User, entry_id: UUID, payload: ProductionEntryUpdate
) -> ProductionEntry:
    entry = get_entry(db, entry_id)
    _ensure_entry_edit_access(entry, actor)
    changes = payload.model_dump(exclude_unset=True)
    if "project_id" in changes:
        _ensure_project_access(db, changes["project_id"], actor)
    new_actual = changes.get("actual_quantity", entry.actual_quantity)
    new_accepted = changes.get("accepted_quantity", entry.accepted_quantity)
    new_rework = changes.get("rework_quantity", entry.rework_quantity)
    if new_accepted > new_actual:
        raise UnprocessableError("Accepted quantity cannot exceed actual quantity")
    if new_rework > new_actual:
        raise UnprocessableError("Rework quantity cannot exceed actual quantity")
    if new_accepted + new_rework > new_actual:
        raise UnprocessableError(
            "First-pass accepted quantity plus rework-sent quantity cannot exceed actual quantity"
        )
    before = {key: getattr(entry, key) for key in changes}
    for key, value in changes.items():
        setattr(entry, key, value)
    db.flush()
    audit_service.record(
        db,
        actor_id=actor.id,
        action="UPDATE",
        entity="production_entry",
        entity_id=entry.id,
        before=before,
        after=changes,
    )
    db.commit()
    return get_entry(db, entry.id)


def get_action(db: Session, action_id: UUID) -> ProductionAction:
    action = db.scalar(_action_query().where(ProductionAction.id == action_id))
    if not action:
        raise NotFoundError("Production action not found")
    return action


def list_actions(
    db: Session,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    responsible_user_id: UUID | None = None,
    project_id: UUID | None = None,
    overdue_only: bool = False,
) -> Page[ProductionActionRead]:
    statement = _action_query().order_by(
        ProductionAction.deadline.asc(), ProductionAction.created_at.desc()
    )
    if status:
        statement = statement.where(ProductionAction.status == status)
    if responsible_user_id:
        statement = statement.where(ProductionAction.responsible_user_id == responsible_user_id)
    if project_id:
        statement = statement.where(ProductionAction.project_id == project_id)
    if overdue_only:
        statement = statement.where(
            ProductionAction.status != "CLOSED", ProductionAction.deadline < date.today()
        )
    items, total = paginate(db, statement, page=page, page_size=page_size)
    return build_page(
        [ProductionActionRead.model_validate(item) for item in items], total, page, page_size
    )


def create_action(db: Session, *, actor: User, payload: ProductionActionCreate) -> ProductionAction:
    if payload.responsible_user_id:
        responsible = db.get(User, payload.responsible_user_id)
        if not responsible or not responsible.is_active:
            raise NotFoundError("Responsible user not found or inactive")
    project_id = payload.project_id
    if payload.production_entry_id:
        entry = get_entry(db, payload.production_entry_id)
        if project_id and entry.project_id and project_id != entry.project_id:
            raise UnprocessableError(
                "Action project must match the linked production entry project"
            )
        if project_id is None:
            project_id = entry.project_id
    _ensure_project_access(db, project_id, actor)
    action_id = uuid.uuid4()
    action_number = f"PA-{payload.date_raised:%Y%m}-{action_id.hex[:8].upper()}"
    action = ProductionAction(
        id=action_id,
        action_number=action_number,
        **{**payload.model_dump(), "project_id": project_id},
        created_by=actor.id,
    )
    db.add(action)
    db.flush()
    audit_service.record(
        db,
        actor_id=actor.id,
        action="CREATE",
        entity="production_action",
        entity_id=action.id,
        after={
            "action_number": action.action_number,
            "status": action.status,
            "deadline": action.deadline,
            "responsible_user_id": action.responsible_user_id,
        },
    )
    db.commit()
    return get_action(db, action.id)


def update_action(
    db: Session, *, actor: User, action_id: UUID, payload: ProductionActionUpdate
) -> ProductionAction:
    action = get_action(db, action_id)
    if actor.id not in {action.created_by, action.responsible_user_id} and not _is_admin(actor):
        raise ForbiddenError(
            "Only the action creator, assigned owner or an Admin can update this action"
        )
    changes = payload.model_dump(exclude_unset=True)
    if "responsible_user_id" in changes and not _is_admin(actor):
        if changes["responsible_user_id"] != action.responsible_user_id:
            raise ForbiddenError("Only an Admin can reassign a production action")
    if changes.get("responsible_user_id"):
        responsible = db.get(User, changes["responsible_user_id"])
        if not responsible or not responsible.is_active:
            raise NotFoundError("Responsible user not found or inactive")
    before = {key: getattr(action, key) for key in changes}
    for key, value in changes.items():
        setattr(action, key, value)
    if changes.get("status") == "CLOSED":
        action.closed_at = datetime.now(UTC)
        action.closed_by_user_id = actor.id
    elif changes.get("status") and changes["status"] != "CLOSED":
        action.closed_at = None
        action.closed_by_user_id = None
        action.closure_evidence = changes.get("closure_evidence")
    db.flush()
    audit_service.record(
        db,
        actor_id=actor.id,
        action="UPDATE",
        entity="production_action",
        entity_id=action.id,
        before=before,
        after=changes,
    )
    db.commit()
    return get_action(db, action.id)


def get_monthly_review(db: Session, *, year: int, month: int) -> ProductionMonthlyReview | None:
    return db.scalar(
        _review_query().where(
            ProductionMonthlyReview.year == year,
            ProductionMonthlyReview.month == month,
        )
    )


def upsert_monthly_review(
    db: Session,
    *,
    actor: User,
    year: int,
    month: int,
    payload: ProductionMonthlyReviewUpsert,
) -> ProductionMonthlyReview:
    review = get_monthly_review(db, year=year, month=month)
    before = None
    if review is None:
        review = ProductionMonthlyReview(
            year=year,
            month=month,
            management_summary=payload.management_summary,
            prepared_by_user_id=actor.id,
        )
        db.add(review)
        action_name = "CREATE"
    else:
        before = {
            "management_summary": review.management_summary,
            "reviewed_at": review.reviewed_at,
        }
        if review.management_summary != payload.management_summary:
            review.reviewed_by_user_id = None
            review.reviewed_at = None
        review.management_summary = payload.management_summary
        action_name = "UPDATE"
    if payload.mark_reviewed:
        review.reviewed_by_user_id = actor.id
        review.reviewed_at = datetime.now(UTC)
    db.flush()
    audit_service.record(
        db,
        actor_id=actor.id,
        action=action_name,
        entity="production_monthly_review",
        entity_id=review.id,
        before=before,
        after={"year": year, "month": month, "mark_reviewed": payload.mark_reviewed},
    )
    db.commit()
    return db.scalar(_review_query().where(ProductionMonthlyReview.id == review.id))


def get_monthly_summary(db: Session, *, year: int, month: int) -> ProductionSummaryRead:
    last_day = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)
    grouped = db.execute(
        select(
            ProductionEntry.unit_of_measure,
            func.count(ProductionEntry.id),
            func.coalesce(func.sum(ProductionEntry.planned_quantity), 0),
            func.coalesce(func.sum(ProductionEntry.actual_quantity), 0),
            func.coalesce(func.sum(ProductionEntry.accepted_quantity), 0),
            func.coalesce(func.sum(ProductionEntry.rework_quantity), 0),
            func.coalesce(func.sum(ProductionEntry.production_hours), 0),
            func.coalesce(func.sum(ProductionEntry.downtime_hours), 0),
        )
        .where(ProductionEntry.production_date >= start, ProductionEntry.production_date <= end)
        .group_by(ProductionEntry.unit_of_measure)
        .order_by(ProductionEntry.unit_of_measure)
    ).all()

    units: list[ProductionUnitSummary] = []
    for unit, count, planned, actual, accepted, rework, production_hours, downtime_hours in grouped:
        planned = Decimal(planned)
        actual = Decimal(actual)
        accepted = Decimal(accepted)
        rework = Decimal(rework)
        production_hours = Decimal(production_hours)
        downtime_hours = Decimal(downtime_hours)
        rejected = max(actual - accepted, Decimal("0"))
        denominator = production_hours + downtime_hours
        units.append(
            ProductionUnitSummary(
                unit_of_measure=unit,
                entries_count=count,
                planned_quantity=float(planned),
                actual_quantity=float(actual),
                accepted_quantity=float(accepted),
                rejected_quantity=float(rejected),
                rework_quantity=float(rework),
                production_hours=float(production_hours),
                downtime_hours=float(downtime_hours),
                plan_achievement_percent=float(actual / planned * 100) if planned else None,
                first_pass_yield_percent=float(accepted / actual * 100) if actual else None,
                rejection_percent=float(rejected / actual * 100) if actual else None,
                downtime_percent=float(downtime_hours / denominator * 100) if denominator else None,
            )
        )

    open_actions = (
        db.scalar(
            select(func.count(ProductionAction.id)).where(
                ProductionAction.status.in_(OPEN_STATUSES),
                ProductionAction.date_raised <= end,
            )
        )
        or 0
    )
    overdue_actions = (
        db.scalar(
            select(func.count(ProductionAction.id)).where(
                ProductionAction.status != "CLOSED", ProductionAction.deadline < date.today()
            )
        )
    ) or 0
    month_start = datetime.combine(start, datetime.min.time(), tzinfo=UTC)
    next_month = datetime.combine(
        date(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1),
        datetime.min.time(),
        tzinfo=UTC,
    )
    closed_this_month = (
        db.scalar(
            select(func.count(ProductionAction.id)).where(
                ProductionAction.status == "CLOSED",
                ProductionAction.closed_at >= month_start,
                ProductionAction.closed_at < next_month,
            )
        )
        or 0
    )
    review = get_monthly_review(db, year=year, month=month)
    review_read = ProductionMonthlyReviewRead.model_validate(review) if review else None
    return ProductionSummaryRead(
        year=year,
        month=month,
        units=units,
        open_actions=int(open_actions),
        overdue_actions=int(overdue_actions),
        closed_this_month=int(closed_this_month),
        monthly_review=review_read,
    )
