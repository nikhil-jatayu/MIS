from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel
from app.schemas.user import UserSummary


class AttachmentRead(ORMModel):
    id: UUID
    project_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    uploaded_by: UUID
    created_at: datetime
    uploader: UserSummary
    download_url: str = ""
