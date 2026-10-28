from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Query, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login", auto_error=False
)

DatabaseSession = Annotated[Session, Depends(get_db)]

PASSWORD_CHANGE_ALLOWED_SUFFIXES = (
    "/auth/me",
    "/auth/change-password",
    "/auth/logout",
)


def get_current_user(
    request: Request,
    db: DatabaseSession,
    bearer_token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User:
    token = bearer_token or request.cookies.get(settings.cookie_name)
    if not token:
        raise UnauthorizedError()
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Your session has expired", code="TOKEN_EXPIRED") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid authentication token", code="INVALID_TOKEN") from exc

    subject = payload.get("sub")
    try:
        user_id = UUID(subject)
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid authentication token", code="INVALID_TOKEN") from exc

    user = db.scalar(select(User).where(User.id == user_id))
    if not user or not user.is_active:
        raise UnauthorizedError("Your account is not active", code="ACCOUNT_INACTIVE")

    if user.must_change_password and not request.url.path.endswith(
        PASSWORD_CHANGE_ALLOWED_SUFFIXES
    ):
        raise ForbiddenError(
            "You must change your temporary password before continuing",
            code="PASSWORD_CHANGE_REQUIRED",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    allowed = set(roles)

    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise ForbiddenError()
        return user

    return dependency


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN))]
SuperAdminUser = Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN))]


class PaginationParams:
    def __init__(
        self,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(
            default=settings.default_page_size,
            ge=1,
            le=settings.max_page_size,
        ),
    ) -> None:
        self.page = page
        self.page_size = page_size


Pagination = Annotated[PaginationParams, Depends(PaginationParams)]
