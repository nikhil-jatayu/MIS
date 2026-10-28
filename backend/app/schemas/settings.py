from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from app.schemas.common import ORMModel


class ThresholdSettings(ORMModel):
    safe_threshold_days: int = Field(default=3, ge=0, le=365)
    escalation_threshold_days: int = Field(default=7, ge=1, le=365)
    deadline_reminder_days: int = Field(default=5, ge=0, le=365)
    severe_delay_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)

    @model_validator(mode="after")
    def ordered_thresholds(self) -> "ThresholdSettings":
        if self.escalation_threshold_days <= self.safe_threshold_days:
            raise ValueError("Escalation threshold must be greater than the safe threshold")
        return self


class ThresholdSettingsRead(ThresholdSettings):
    updated_at: datetime | None = None


class SettingRead(ORMModel):
    key: str
    value: str
    updated_at: datetime
