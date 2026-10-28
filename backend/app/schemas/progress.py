from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import ORMModel
from app.schemas.user import UserSummary


class ProgressLogCreate(ORMModel):
    note: str = Field(min_length=3, max_length=5000)
    progress_percent: int = Field(ge=0, le=100)

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str) -> str:
        return value.strip()


class ProgressLogRead(ORMModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    note: str
    progress_percent: int
    created_at: datetime
    user: UserSummary
