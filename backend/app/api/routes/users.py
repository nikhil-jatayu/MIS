from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import AdminUser, DatabaseSession, Pagination, SuperAdminUser
from app.models.enums import UserRole
from app.schemas.common import Page
from app.schemas.user import (
    PasswordResetRequest,
    UserCreate,
    UserRead,
    UserSummary,
    UserUpdate,
)
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/options", response_model=list[UserSummary])
def user_options(
    db: DatabaseSession,
    _: AdminUser,
) -> list[UserSummary]:
    users = user_service.active_users_for_assignment(db)
    return [UserSummary.model_validate(user) for user in users]


@router.get("", response_model=Page[UserRead])
def list_users(
    db: DatabaseSession,
    pagination: Pagination,
    _: AdminUser,
    q: str | None = Query(default=None, max_length=200),
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> Page[UserRead]:
    return user_service.list_users(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        q=q,
        role=role,
        is_active=is_active,
    )


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    payload: UserCreate,
    db: DatabaseSession,
    actor: SuperAdminUser,
) -> UserRead:
    user = user_service.create_user(db, actor=actor, payload=payload)
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: UUID,
    db: DatabaseSession,
    _: SuperAdminUser,
) -> UserRead:
    return UserRead.model_validate(user_service.get_user(db, user_id))


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: DatabaseSession,
    actor: SuperAdminUser,
) -> UserRead:
    user = user_service.update_user(db, actor=actor, user_id=user_id, payload=payload)
    return UserRead.model_validate(user)


@router.post("/{user_id}/reset-password", response_model=UserRead)
def reset_password(
    user_id: UUID,
    payload: PasswordResetRequest,
    db: DatabaseSession,
    actor: SuperAdminUser,
) -> UserRead:
    user = user_service.reset_password(
        db, actor=actor, user_id=user_id, new_password=payload.new_password
    )
    return UserRead.model_validate(user)
