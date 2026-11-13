from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, validate_password_strength
from app.models.enums import Department, UserRole
from app.models.setting import Setting
from app.models.user import User
from app.services import settings_service

logger = logging.getLogger(__name__)

SEED_SUPER_ADMINS = (
    ("Ashmant", "ashmant@jatayues.com", "Ashmant@123", Department.MANAGEMENT),
    ("Ratna", "ratna@jatayues.com", "Ratna@123", Department.MANAGEMENT),
)

SEED_DEPARTMENTS = {
    "kartik@jatayues.com": Department.R_D,
}


def _capitalise_first_character(value: str) -> str:
    """Return a trimmed name with its first character capitalised."""
    value = value.strip()
    return value[:1].upper() + value[1:]


def seed_database(db: Session) -> dict[str, Any]:
    created = 0
    for name, email, password, department in SEED_SUPER_ADMINS:
        validate_password_strength(password)
        existing = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if existing:
            if existing.department is None:
                existing.department = department
            logger.info("Seed user already exists: %s", email)
            continue
        db.add(
            User(
                name=_capitalise_first_character(name),
                email=email.lower(),
                role=UserRole.SUPER_ADMIN,
                department=department,
                password_hash=hash_password(password),
                is_active=True,
                must_change_password=True,
            )
        )
        created += 1
        logger.info("Seeded Super Admin: %s", email)

    for email, department in SEED_DEPARTMENTS.items():
        existing = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if existing and existing.department is None:
            existing.department = department
            logger.info("Backfilled department for %s", email)

    settings_service.ensure_defaults(db)
    db.commit()

    settings_count = int(db.scalar(select(func.count()).select_from(Setting)) or 0)
    return {"super_admins_created": created, "settings_rows": settings_count}
