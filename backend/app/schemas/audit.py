from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.schemas.common import ORMModel
from app.schemas.user import UserSummary


class AuditLogRead(ORMModel):
    id: UUID
    actor_id: UUID | None
    action: str
    entity: str
    entity_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    created_at: datetime
    actor: UserSummary | None
