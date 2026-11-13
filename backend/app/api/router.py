from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    alerts,
    alerts_audit_reports,
    attachments,
    audit,
    auth,
    dashboard,
    inventory,
    operations_reports,
    production,
    production_reports,
    progress,
    projects,
    purchases,
    settings,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(inventory.router)
api_router.include_router(projects.router)
api_router.include_router(purchases.router)
api_router.include_router(purchases.project_router)
api_router.include_router(progress.router)
api_router.include_router(production.router)
api_router.include_router(production_reports.router)
api_router.include_router(operations_reports.router)
api_router.include_router(alerts_audit_reports.router)
api_router.include_router(attachments.router)
api_router.include_router(alerts.router)
api_router.include_router(audit.router)
api_router.include_router(settings.router)
api_router.include_router(dashboard.router)
