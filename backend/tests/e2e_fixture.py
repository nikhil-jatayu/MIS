"""Create or remove the accounts and data used by the Playwright E2E suite.

This script is test tooling only. It is invoked by the frontend Playwright
global setup/teardown and deliberately refuses to run when ENVIRONMENT is
``production``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select, text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.user import User  # noqa: E402

ADMIN_EMAIL = "e2e.superadmin@jatayues.com"
MEMBER_EMAIL = "e2e.member@jatayues.com"
FORCED_EMAIL = "e2e.forced@jatayues.com"
E2E_PASSWORD = "E2e!Passw0rd2026"
E2E_PROJECT_PREFIX = "E2E "


def _upsert_user(
    db,
    *,
    name: str,
    email: str,
    role: UserRole,
    password: str,
    must_change_password: bool,
) -> None:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, name=name, role=role, password_hash="")
        db.add(user)
    user.name = name
    user.role = role
    user.is_active = True
    user.must_change_password = must_change_password
    user.password_hash = hash_password(password)


def ensure() -> None:
    db = SessionLocal()
    try:
        _upsert_user(
            db,
            name="E2E Super Admin",
            email=ADMIN_EMAIL,
            role=UserRole.SUPER_ADMIN,
            password=E2E_PASSWORD,
            must_change_password=False,
        )
        _upsert_user(
            db,
            name="E2E Member",
            email=MEMBER_EMAIL,
            role=UserRole.USER,
            password=E2E_PASSWORD,
            must_change_password=False,
        )
        _upsert_user(
            db,
            name="E2E Forced Password",
            email=FORCED_EMAIL,
            role=UserRole.USER,
            password=E2E_PASSWORD,
            must_change_password=True,
        )
        db.commit()
        print(f"E2E fixtures ready for {ADMIN_EMAIL}, {MEMBER_EMAIL} and {FORCED_EMAIL}")
    finally:
        db.close()


def cleanup() -> None:
    db = SessionLocal()
    try:
        # Projects cascade to BOM lines, members, progress logs, purchase
        # requests, attachments and alerts through their foreign keys.
        db.execute(
            text("DELETE FROM projects WHERE name LIKE :prefix"),
            {"prefix": f"{E2E_PROJECT_PREFIX}%"},
        )
        db.execute(text("DELETE FROM inventory_items WHERE sku LIKE 'E2E-%'"))
        db.execute(delete(User).where(User.email.in_([ADMIN_EMAIL, MEMBER_EMAIL, FORCED_EMAIL])))
        db.commit()
        print("E2E fixtures removed")
    finally:
        db.close()


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"ensure", "cleanup"}:
        raise SystemExit("Usage: e2e_fixture.py ensure|cleanup")
    if settings.is_production:
        raise SystemExit("Refusing to run E2E fixtures against production")
    if sys.argv[1] == "ensure":
        ensure()
    else:
        cleanup()


if __name__ == "__main__":
    main()
