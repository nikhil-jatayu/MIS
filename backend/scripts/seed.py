from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.seed_service import seed_database  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        result = seed_database(db)
        print(
            "Seed complete: "
            f"{result['super_admins_created']} Super Admin(s) created, "
            f"{result['settings_rows']} settings row(s)."
        )
        print(f"Total users: {len(db.scalars(select(User)).all())}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
