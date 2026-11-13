from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, UnprocessableError
from app.core.security import PasswordPolicyError, hash_password, validate_password_strength
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import audit_service
from app.services.auth_service import ensure_last_super_admin_guard
from app.services.pagination import build_page, paginate


def get_user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("User not found")
    return user


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def list_users(
    db: Session,
    *,
    page: int,
    page_size: int,
    q: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> Page[UserRead]:
    statement = select(User).order_by(User.name.asc())
    if q:
        pattern = f"%{q.strip().lower()}%"
        statement = statement.where(
            func.lower(User.name).like(pattern) | func.lower(User.email).like(pattern)
        )
    if role:
        statement = statement.where(User.role == role)
    if is_active is not None:
        statement = statement.where(User.is_active.is_(is_active))
    items, total = paginate(db, statement, page=page, page_size=page_size)
    return build_page([UserRead.model_validate(user) for user in items], total, page, page_size)


def create_user(db: Session, *, actor: User, payload: UserCreate) -> User:
    if get_by_email(db, payload.email):
        raise ConflictError("A user with this email already exists", code="EMAIL_EXISTS")
    try:
        validate_password_strength(payload.temporary_password)
    except PasswordPolicyError as exc:
        raise UnprocessableError("Temporary password does not meet the policy", details=exc.errors)

    user = User(
        name=payload.name,
        email=payload.email.strip().lower(),
        role=payload.role,
        password_hash=hash_password(payload.temporary_password),
        is_active=True,
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    audit_service.record(
        db,
        actor_id=actor.id,
        action="CREATE",
        entity="user",
        entity_id=user.id,
        after=audit_service.user_snapshot(user),
    )
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, *, actor: User, user_id: UUID, payload: UserUpdate) -> User:
    user = get_user(db, user_id)
    before = audit_service.user_snapshot(user)

    if user.id == actor.id and payload.is_active is False:
        raise UnprocessableError("You cannot deactivate your own account", code="SELF_DEACTIVATION")
    if user.id == actor.id and payload.role is not None and payload.role != user.role:
        raise UnprocessableError("You cannot change your own role", code="SELF_ROLE_CHANGE")

    ensure_last_super_admin_guard(
        db,
        target=user,
        new_role=payload.role,
        is_active=payload.is_active,
    )

    if payload.name is not None:
        user.name = payload.name
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active

    after = audit_service.user_snapshot(user)
    if before != after:
        audit_service.record(
            db,
            actor_id=actor.id,
            action="UPDATE",
            entity="user",
            entity_id=user.id,
            before=before,
            after=after,
        )
    db.commit()
    db.refresh(user)
    return user


def reset_password(
    db: Session,
    *,
    actor: User,
    user_id: UUID,
    new_password: str,
) -> User:
    user = get_user(db, user_id)
    try:
        validate_password_strength(new_password)
    except PasswordPolicyError as exc:
        raise UnprocessableError("Password does not meet the policy", details=exc.errors)
    user.password_hash = hash_password(new_password)
    user.must_change_password = True
    audit_service.record(
        db,
        actor_id=actor.id,
        action="PASSWORD_RESET",
        entity="user",
        entity_id=user.id,
        after={"must_change_password": True},
    )
    db.commit()
    db.refresh(user)
    return user


def active_users_for_assignment(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.name)).all())
