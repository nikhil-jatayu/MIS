from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DatabaseSession
from app.schemas.dashboard import DashboardSummary
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardSummary)
def dashboard(db: DatabaseSession, user: CurrentUser) -> DashboardSummary:
    return dashboard_service.build_summary(db, user=user)
