from __future__ import annotations

from fastapi import Response

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User


def set_auth_cookie(response: Response, user: User) -> tuple[str, int]:
    token, expires_in = create_access_token(subject=str(user.id), role=user.role)
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=expires_in,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )
    return token, expires_in


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
