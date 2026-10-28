from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import DatabaseSession, SuperAdminUser
from app.schemas.settings import ThresholdSettings, ThresholdSettingsRead
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/thresholds", response_model=ThresholdSettingsRead)
def get_thresholds(db: DatabaseSession, _: SuperAdminUser) -> ThresholdSettingsRead:
    return settings_service.get_thresholds(db)


@router.put("/thresholds", response_model=ThresholdSettingsRead)
def update_thresholds(
    payload: ThresholdSettings,
    db: DatabaseSession,
    actor: SuperAdminUser,
) -> ThresholdSettingsRead:
    return settings_service.update_thresholds(db, actor=actor, payload=payload)
