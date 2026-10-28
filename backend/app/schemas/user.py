from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator, model_validator

from app.core.security import PasswordPolicyError, validate_password_strength
from app.models.enums import UserRole
from app.schemas.common import ORMModel


def _validate_password(value: str) -> str:
    try:
        validate_password_strength(value)
    except PasswordPolicyError as exc:
        raise ValueError("; ".join(exc.errors)) from exc
    return value


class LoginRequest(ORMModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserSummary(ORMModel):
    id: UUID
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool


class UserRead(UserSummary):
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AuthResponse(ORMModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class ChangePasswordRequest(ORMModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    _validate_new_password = field_validator("new_password")(_validate_password)

    @model_validator(mode="after")
    def password_must_change(self) -> "ChangePasswordRequest":
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from the current password")
        return self


class UserCreate(ORMModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    role: UserRole = UserRole.USER
    temporary_password: str = Field(min_length=8, max_length=128)

    _validate_temporary_password = field_validator("temporary_password")(_validate_password)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class UserUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class PasswordResetRequest(ORMModel):
    new_password: str = Field(min_length=8, max_length=128)

    _validate_new_password = field_validator("new_password")(_validate_password)
