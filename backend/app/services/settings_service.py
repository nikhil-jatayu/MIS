from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.setting import Setting
from app.models.user import User
from app.schemas.settings import ThresholdSettings, ThresholdSettingsRead
from app.services import audit_service

DEFAULT_SETTINGS: dict[str, str] = {
    "safe_threshold_days": "3",
    "escalation_threshold_days": "7",
    "deadline_reminder_days": "5",
    "severe_delay_multiplier": "2.0",
}


def ensure_defaults(db: Session) -> None:
    existing = {
        setting.key: setting
        for setting in db.scalars(
            select(Setting).where(Setting.key.in_(list(DEFAULT_SETTINGS.keys())))
        ).all()
    }
    changed = False
    for key, value in DEFAULT_SETTINGS.items():
        if key not in existing:
            db.add(Setting(key=key, value=value))
            changed = True
    if changed:
        db.commit()


def get_thresholds(db: Session) -> ThresholdSettingsRead:
    rows = {setting.key: setting for setting in db.scalars(select(Setting)).all()}
    values = {
        key: rows[key].value if key in rows else default
        for key, default in DEFAULT_SETTINGS.items()
    }
    updated_at = max((row.updated_at for row in rows.values()), default=None)
    return ThresholdSettingsRead(
        safe_threshold_days=int(values["safe_threshold_days"]),
        escalation_threshold_days=int(values["escalation_threshold_days"]),
        deadline_reminder_days=int(values["deadline_reminder_days"]),
        severe_delay_multiplier=float(values["severe_delay_multiplier"]),
        updated_at=updated_at,
    )


def update_thresholds(
    db: Session, *, actor: User, payload: ThresholdSettings
) -> ThresholdSettingsRead:
    before = get_thresholds(db).model_dump(exclude={"updated_at"})
    values = {
        "safe_threshold_days": str(payload.safe_threshold_days),
        "escalation_threshold_days": str(payload.escalation_threshold_days),
        "deadline_reminder_days": str(payload.deadline_reminder_days),
        "severe_delay_multiplier": str(payload.severe_delay_multiplier),
    }
    now = datetime.now(UTC)
    for key, value in values.items():
        setting = db.get(Setting, key)
        if setting:
            setting.value = value
            setting.updated_at = now
        else:
            db.add(Setting(key=key, value=value, updated_at=now))
    after = payload.model_dump()
    audit_service.record(
        db,
        actor_id=actor.id,
        action="UPDATE",
        entity="settings",
        entity_id="time_counter",
        before=before,
        after=after,
    )
    db.commit()
    return get_thresholds(db)
