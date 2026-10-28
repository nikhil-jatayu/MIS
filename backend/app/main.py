from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.db.session import SessionLocal, engine
from app.scheduler import shutdown_scheduler, start_scheduler
from app.services.seed_service import seed_database

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            result = seed_database(db)
            logger.info("Seed check complete: %s", result)
        except Exception:
            db.rollback()
            logger.exception("Seed failed; run migrations and the seed script manually")
        finally:
            db.close()
    start_scheduler()
    yield
    shutdown_scheduler()
    engine.dispose()


app = FastAPI(
    title="JES Electronics Systems Pvt Ltd - MIS",
    description=(
        "R&D and Production Management Information System: projects, inventory, "
        "purchase requests, testing, time-counter alerts and audit trail."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Requested-With"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)
app.add_middleware(RequestContextMiddleware)
register_exception_handlers(app)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}
