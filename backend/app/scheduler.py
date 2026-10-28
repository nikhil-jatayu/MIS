from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.alert_service import run_time_counter

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_alert_job() -> None:
    db = SessionLocal()
    try:
        run_time_counter(db)
    except Exception:
        db.rollback()
        logger.exception("Scheduled Time Counter run failed")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.scheduler_enabled:
        logger.info("Alert scheduler disabled")
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)
    _scheduler.add_job(
        _run_alert_job,
        trigger=IntervalTrigger(minutes=settings.scheduler_interval_minutes),
        id="time_counter",
        name="MIS Time Counter",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=(
            None  # APScheduler computes the first run from the interval
        ),
    )
    _scheduler.start()
    if settings.scheduler_run_on_startup:
        _run_alert_job()
    logger.info(
        "Alert scheduler started (every %s minutes, timezone %s)",
        settings.scheduler_interval_minutes,
        settings.scheduler_timezone,
    )
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Alert scheduler stopped")
    _scheduler = None
