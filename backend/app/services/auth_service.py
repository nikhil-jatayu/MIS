from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from threading import Lock
from urllib.parse import quote

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import RateLimitError, UnauthorizedError, UnprocessableError
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    PasswordPolicyError,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.models.enums import UserRole
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services import audit_service
from app.services.email_service import send_password_reset_email

logger = logging.getLogger(__name__)


class LoginThrottle:
    """Small in-process brute-force guard suitable for the single-instance v1 deployment."""

    def __init__(self, max_attempts: int, lock_minutes: int) -> None:
        self.max_attempts = max_attempts
        self.lock_minutes = lock_minutes
        self._failures: dict[str, list[datetime]] = {}
        self._lock = Lock()

    def _prune(self, key: str, now: datetime) -> list[datetime]:
        cutoff = now - timedelta(minutes=self.lock_minutes)
        attempts = [attempt for attempt in self._failures.get(key, []) if attempt > cutoff]
        if attempts:
            self._failures[key] = attempts
        else:
            self._failures.pop(key, None)
        return attempts

    def check(self, key: str) -> None:
        now = datetime.now(UTC)
        with self._lock:
            attempts = self._prune(key, now)
            if len(attempts) >= self.max_attempts:
                retry_after = int(
                    (attempts[0] + timedelta(minutes=self.lock_minutes) - now).total_seconds()
                )
                raise RateLimitError(
                    f"Too many failed login attempts. Try again in {max(retry_after, 1)} seconds."
                )

    def fail(self, key: str) -> None:
        now = datetime.now(UTC)
        with self._lock:
            self._prune(key, now)
            self._failures.setdefault(key, []).append(now)

    def success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


login_throttle = LoginThrottle(settings.login_max_attempts, settings.login_lock_minutes)


class PasswordResetRequestLimiter:
    """Per-process IP throttle for public password-reset requests."""

    def __init__(self) -> None:
        self._attempts: dict[str, list[datetime]] = {}
        self._lock = Lock()

    def allow(self, client_host: str) -> bool:
        now = datetime.now(UTC)
        cutoff = now - timedelta(minutes=settings.password_reset_window_minutes)
        key = client_host or "unknown"
        with self._lock:
            recent = [value for value in self._attempts.get(key, []) if value > cutoff]
            if len(recent) >= settings.password_reset_max_requests:
                self._attempts[key] = recent
                return False
            recent.append(now)
            self._attempts[key] = recent
            return True

    def clear(self) -> None:
        """Clear counters for tests and controlled maintenance."""
        with self._lock:
            self._attempts.clear()


password_reset_limiter = PasswordResetRequestLimiter()


def request_password_reset(db: Session, *, email: str, client_host: str) -> None:
    """Issue a single-use reset link without exposing account existence."""
    if not password_reset_limiter.allow(client_host):
        return

    normalised_email = email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == normalised_email))
    if not user or not user.is_active:
        return

    now = datetime.now(UTC)
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    # A new request invalidates all previous unused links for this account.
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(minutes=settings.password_reset_token_expire_minutes),
            requested_from=(client_host or "unknown")[:64],
        )
    )
    db.flush()

    reset_url = (
        f"{settings.frontend_base_url.rstrip('/')}/reset-password?token={quote(raw_token, safe='')}"
    )
    try:
        send_password_reset_email(recipient=user.email, reset_url=reset_url)
        db.commit()
    except Exception:
        db.rollback()
        # The public response remains identical for configured, unknown and
        # temporarily undeliverable addresses.
        logger.exception("Password-reset email could not be delivered")


def complete_password_reset(db: Session, *, token: str, new_password: str) -> User:
    """Validate and consume a one-time reset token, then change the password."""
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    reset_record = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .with_for_update()
    )
    now = datetime.now(UTC)
    if reset_record is None or reset_record.used_at is not None or reset_record.expires_at <= now:
        raise UnprocessableError(
            "This password-reset link is invalid or has expired",
            code="INVALID_PASSWORD_RESET_TOKEN",
        )

    user = db.get(User, reset_record.user_id)
    if not user or not user.is_active:
        raise UnprocessableError(
            "This password-reset link is invalid or has expired",
            code="INVALID_PASSWORD_RESET_TOKEN",
        )

    try:
        validate_password_strength(new_password)
    except PasswordPolicyError as exc:
        raise UnprocessableError("Password does not meet the policy", details=exc.errors) from exc
    if verify_password(new_password, user.password_hash):
        raise UnprocessableError("New password must be different from the current password")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="PASSWORD_RESET_BY_EMAIL",
        entity="user",
        entity_id=user.id,
        after={"password_reset": True, "must_change_password": False},
    )
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, *, email: str, password: str, client_host: str) -> User:
    normalised_email = email.strip().lower()
    throttle_key = f"{normalised_email}:{client_host}"
    login_throttle.check(throttle_key)

    user = db.scalar(select(User).where(func.lower(User.email) == normalised_email))
    password_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
    password_valid = verify_password(password, password_hash)

    if not user or not password_valid:
        login_throttle.fail(throttle_key)
        raise UnauthorizedError("Invalid email or password", code="INVALID_CREDENTIALS")
    if not user.is_active:
        login_throttle.fail(throttle_key)
        raise UnauthorizedError("This account has been deactivated", code="ACCOUNT_INACTIVE")

    login_throttle.success(throttle_key)
    user.last_login_at = datetime.now(UTC)
    db.commit()
    return user


def change_password(
    db: Session,
    *,
    user: User,
    current_password: str,
    new_password: str,
) -> User:
    if not verify_password(current_password, user.password_hash):
        raise UnauthorizedError("Current password is incorrect", code="INVALID_PASSWORD")
    try:
        validate_password_strength(new_password)
    except PasswordPolicyError as exc:
        raise UnprocessableError("Password does not meet the policy", details=exc.errors)
    if current_password == new_password:
        raise UnprocessableError("New password must be different from the current password")
    if verify_password(new_password, user.password_hash):
        raise UnprocessableError("New password must be different from the current password")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    audit_service.record(
        db,
        actor_id=user.id,
        action="PASSWORD_CHANGED",
        entity="user",
        entity_id=user.id,
        after={"password_changed": True},
    )
    db.commit()
    db.refresh(user)
    return user


def ensure_last_super_admin_guard(
    db: Session,
    *,
    target: User,
    new_role: UserRole | None = None,
    is_active: bool | None = None,
) -> None:
    """Prevent removing the final active Super Admin from the system."""
    losing_super = target.role == UserRole.SUPER_ADMIN and (
        (new_role is not None and new_role != UserRole.SUPER_ADMIN) or is_active is False
    )
    if not losing_super:
        return
    active_super_admins = db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.role == UserRole.SUPER_ADMIN, User.is_active.is_(True))
    )
    if int(active_super_admins or 0) <= 1:
        raise UnprocessableError(
            "At least one active Super Admin must remain", code="LAST_SUPER_ADMIN"
        )
