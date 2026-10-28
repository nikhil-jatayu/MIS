from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
import jwt

from app.core.config import settings


class PasswordPolicyError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def _prehash(password: str) -> bytes:
    """SHA-256 pre-hash avoids bcrypt's 72-byte input limit and truncation."""
    return hashlib.sha256(password.encode("utf-8")).digest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode(
        "utf-8"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), password_hash.encode("utf-8"))
    except ValueError, TypeError:
        return False


def validate_password_strength(password: str) -> None:
    errors: list[str] = []
    minimum = settings.password_min_length
    if len(password) < minimum:
        errors.append(f"Password must be at least {minimum} characters long")
    if len(password) > 128:
        errors.append("Password must be at most 128 characters long")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain an uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain a lowercase letter")
    if not re.search(r"\d", password):
        errors.append("Password must contain a number")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("Password must contain a special character")
    if errors:
        raise PasswordPolicyError(errors)


def create_access_token(
    *,
    subject: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, int]:
    now = datetime.now(UTC)
    expires_in = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    expires_at = now + expires_in
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": str(uuid4()),
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, int(expires_in.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "exp", "iat", "type"]},
    )


# Constant dummy hash used to equalise timing when an email does not exist.
DUMMY_PASSWORD_HASH = hash_password("not-a-real-password-9f2!")
