from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.setting import Setting
from app.models.user import User
from app.services import settings_service

logger = logging.getLogger(__name__)

SEED_SUPER_ADMINS = (
    ("Ashmant", "ashmant@jatayues.com", "ashmant@123"),
    ("Ratna", "ratna@jatayues.com", "ratna@123"),
)


def seed_database(db: Session) -> dict[str, Any]:
    created = 0
    for name, email, password in SEED_SUPER_ADMINS:
        existing = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if existing:
            logger.info("Seed user already exists: %s", email)
            continue
        db.add(
            User(
                name=name,
                email=email.lower(),
                role=UserRole.SUPER_ADMIN,
                password_hash=hash_password(password),
                is_active=True,
                must_change_password=True,
            )
        )
        created += 1
        logger.info("Seeded Super Admin: %s", email)

    settings_service.ensure_defaults(db)
    db.commit()

    settings_count = int(db.scalar(select(func.count()).select_from(Setting)) or 0)
    return {"super_admins_created": created, "settings_rows": settings_count}
