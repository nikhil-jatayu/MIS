from __future__ import annotations

import re
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.errors import (
    NotFoundError,
    PayloadTooLargeError,
    UnprocessableError,
    UnsupportedMediaTypeError,
)
from app.models.attachment import Attachment
from app.models.user import User
from app.schemas.attachment import AttachmentRead
from app.services import audit_service, project_service

CHUNK_SIZE = 1024 * 1024


def sanitize_filename(filename: str) -> str:
    name = Path(filename or "upload").name
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    name = name.replace("\\", "_").replace("/", "_")
    if not name or name in {".", ".."}:
        raise UnprocessableError("Invalid file name", code="INVALID_FILENAME")
    return name[:200]


def _validate_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if not suffix or suffix not in settings.allowed_extensions:
        raise UnsupportedMediaTypeError(
            f"Allowed file types: {', '.join(sorted(settings.allowed_extensions))}"
        )
    return suffix


def _serialise(attachment: Attachment) -> AttachmentRead:
    data = AttachmentRead.model_validate(attachment)
    return data.model_copy(
        update={"download_url": f"{settings.api_v1_prefix}/attachments/{attachment.id}/download"}
    )


def list_attachments(db: Session, *, actor: User, project_id: UUID) -> list[AttachmentRead]:
    project = project_service.get_project(db, project_id)
    project_service.ensure_project_action_access(db, project, actor)
    attachments = db.scalars(
        select(Attachment)
        .options(selectinload(Attachment.uploader))
        .where(Attachment.project_id == project_id)
        .order_by(Attachment.created_at.desc())
    ).all()
    return [_serialise(attachment) for attachment in attachments]


def save_attachment(
    db: Session, *, actor: User, project_id: UUID, upload: UploadFile
) -> AttachmentRead:
    project = project_service.get_project(db, project_id)
    project_service.ensure_project_action_access(db, project, actor)

    filename = sanitize_filename(upload.filename or "upload")
    suffix = _validate_extension(filename)
    content_type = (upload.content_type or "application/octet-stream")[:150]
    project_dir = settings.upload_path / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{suffix}"
    destination = project_dir / stored_name
    relative_path = f"{project_id}/{stored_name}"

    total = 0
    upload.file.seek(0)
    try:
        with destination.open("wb") as output:
            while chunk := upload.file.read(CHUNK_SIZE):
                total += len(chunk)
                if total > settings.max_upload_bytes:
                    raise PayloadTooLargeError(
                        f"File exceeds the {settings.max_upload_size_mb} MB limit"
                    )
                output.write(chunk)
        if total == 0:
            raise UnprocessableError("Empty files cannot be uploaded", code="EMPTY_FILE")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        upload.file.close()

    attachment = Attachment(
        project_id=project.id,
        filename=filename,
        stored_path=relative_path,
        content_type=content_type,
        size_bytes=total,
        uploaded_by=actor.id,
    )
    db.add(attachment)
    db.flush()
    audit_service.record(
        db,
        actor_id=actor.id,
        action="CREATE",
        entity="attachment",
        entity_id=attachment.id,
        after={
            "project_id": str(project.id),
            "filename": filename,
            "size_bytes": total,
            "content_type": content_type,
        },
    )
    db.commit()
    attachment = db.scalar(
        select(Attachment)
        .options(selectinload(Attachment.uploader))
        .where(Attachment.id == attachment.id)
    )
    if not attachment:
        raise NotFoundError("Attachment not found after upload")
    return _serialise(attachment)


def get_download(db: Session, *, actor: User, attachment_id: UUID) -> tuple[Path, Attachment]:
    attachment = db.scalar(select(Attachment).where(Attachment.id == attachment_id))
    if not attachment:
        raise NotFoundError("Attachment not found")
    project = project_service.get_project(db, attachment.project_id)
    project_service.ensure_project_action_access(db, project, actor)

    upload_root = settings.upload_path
    file_path = (upload_root / attachment.stored_path).resolve()
    if not file_path.is_relative_to(upload_root):
        raise NotFoundError("Attachment file not found")
    if not file_path.is_file():
        raise NotFoundError("Attachment file not found on disk")
    return file_path, attachment
