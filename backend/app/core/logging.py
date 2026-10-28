from __future__ import annotations

import logging

from app.core.config import settings


def configure_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )
    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
