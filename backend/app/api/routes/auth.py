from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.core.cookies import clear_auth_cookie, set_auth_cookie
from app.core.deps import CurrentUser, DatabaseSession
from app.schemas.common import MessageResponse
from app.schemas.user import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    UserRead,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DatabaseSession,
) -> AuthResponse:
    client_host = request.client.host if request.client else "unknown"
    user = auth_service.authenticate(
        db,
        email=str(payload.email),
        password=payload.password,
        client_host=client_host,
    )
    token, expires_in = set_auth_cookie(response, user)
    return AuthResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserRead.model_validate(user),
    )


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response) -> MessageResponse:
    clear_auth_cookie(response)
    return MessageResponse(message="Signed out")


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.post("/change-password", response_model=UserRead)
def change_password(
    payload: ChangePasswordRequest,
    user: CurrentUser,
    db: DatabaseSession,
) -> UserRead:
    updated = auth_service.change_password(
        db,
        user=user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return UserRead.model_validate(updated)
