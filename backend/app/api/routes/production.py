from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.deps import AdminUser, CurrentUser, DatabaseSession, Pagination
from app.schemas.common import Page
from app.models.user import User
from app.schemas.production import (
    ProductionActionCreate,
    ProductionActionRead,
    ProductionActionUpdate,
    ProductionAssigneeRead,
    ProductionEntryCreate,
    ProductionEntryRead,
    ProductionEntryUpdate,
    ProductionMonthlyReviewRead,
    ProductionMonthlyReviewUpsert,
    ProductionSummaryRead,
)
from app.services import production_service

router = APIRouter(prefix="/production", tags=["Production"])


@router.get("/assignees", response_model=list[ProductionAssigneeRead])
def list_production_assignees(
    db: DatabaseSession, _: CurrentUser
) -> list[ProductionAssigneeRead]:
    users = db.scalars(
        select(User).where(User.is_active.is_(True)).order_by(User.name.asc())
    ).all()
    return [ProductionAssigneeRead(id=user.id, name=user.name) for user in users]


@router.get("/entries", response_model=Page[ProductionEntryRead])
def list_production_entries(
    db: DatabaseSession,
    pagination: Pagination,
    _: CurrentUser,
    date_from: date | None = None,
    date_to: date | None = None,
    project_id: UUID | None = None,
    production_line: str | None = Query(default=None, max_length=120),
    unit_of_measure: str | None = Query(default=None, max_length=30),
) -> Page[ProductionEntryRead]:
    return production_service.list_entries(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        date_from=date_from,
        date_to=date_to,
        project_id=project_id,
        production_line=production_line,
        unit_of_measure=unit_of_measure,
    )


@router.get("/entries/{entry_id}", response_model=ProductionEntryRead)
def read_production_entry(
    entry_id: UUID, db: DatabaseSession, _: CurrentUser
) -> ProductionEntryRead:
    return ProductionEntryRead.model_validate(production_service.get_entry(db, entry_id))


@router.post("/entries", response_model=ProductionEntryRead, status_code=201)
def create_production_entry(
    payload: ProductionEntryCreate, db: DatabaseSession, actor: CurrentUser
) -> ProductionEntryRead:
    return ProductionEntryRead.model_validate(
        production_service.create_entry(db, actor=actor, payload=payload)
    )


@router.patch("/entries/{entry_id}", response_model=ProductionEntryRead)
def update_production_entry(
    entry_id: UUID,
    payload: ProductionEntryUpdate,
    db: DatabaseSession,
    actor: CurrentUser,
) -> ProductionEntryRead:
    return ProductionEntryRead.model_validate(
        production_service.update_entry(db, actor=actor, entry_id=entry_id, payload=payload)
    )


@router.get("/actions", response_model=Page[ProductionActionRead])
def list_production_actions(
    db: DatabaseSession,
    pagination: Pagination,
    _: CurrentUser,
    status: str | None = Query(default=None, pattern="^(OPEN|IN_PROGRESS|ON_HOLD|CLOSED)$"),
    responsible_user_id: UUID | None = None,
    project_id: UUID | None = None,
    overdue_only: bool = False,
) -> Page[ProductionActionRead]:
    return production_service.list_actions(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        status=status,
        responsible_user_id=responsible_user_id,
        project_id=project_id,
        overdue_only=overdue_only,
    )


@router.post("/actions", response_model=ProductionActionRead, status_code=201)
def create_production_action(
    payload: ProductionActionCreate, db: DatabaseSession, actor: CurrentUser
) -> ProductionActionRead:
    return ProductionActionRead.model_validate(
        production_service.create_action(db, actor=actor, payload=payload)
    )


@router.patch("/actions/{action_id}", response_model=ProductionActionRead)
def update_production_action(
    action_id: UUID,
    payload: ProductionActionUpdate,
    db: DatabaseSession,
    actor: CurrentUser,
) -> ProductionActionRead:
    return ProductionActionRead.model_validate(
        production_service.update_action(db, actor=actor, action_id=action_id, payload=payload)
    )


@router.get("/summary", response_model=ProductionSummaryRead)
def production_summary(
    db: DatabaseSession,
    _: CurrentUser,
    year: int = Query(ge=2000, le=2200),
    month: int = Query(ge=1, le=12),
) -> ProductionSummaryRead:
    return production_service.get_monthly_summary(db, year=year, month=month)


@router.get("/monthly-review/{year}/{month}", response_model=ProductionMonthlyReviewRead | None)
def read_monthly_review(
    year: int,
    month: int,
    db: DatabaseSession,
    _: CurrentUser,
) -> ProductionMonthlyReviewRead | None:
    if not 1 <= month <= 12 or not 2000 <= year <= 2200:
        from app.core.errors import UnprocessableError

        raise UnprocessableError("Invalid reporting period")
    review = production_service.get_monthly_review(db, year=year, month=month)
    return ProductionMonthlyReviewRead.model_validate(review) if review else None


@router.put("/monthly-review/{year}/{month}", response_model=ProductionMonthlyReviewRead)
def save_monthly_review(
    year: int,
    month: int,
    payload: ProductionMonthlyReviewUpsert,
    db: DatabaseSession,
    actor: AdminUser,
) -> ProductionMonthlyReviewRead:
    if not 1 <= month <= 12 or not 2000 <= year <= 2200:
        from app.core.errors import UnprocessableError

        raise UnprocessableError("Invalid reporting period")
    return ProductionMonthlyReviewRead.model_validate(
        production_service.upsert_monthly_review(
            db, actor=actor, year=year, month=month, payload=payload
        )
    )
