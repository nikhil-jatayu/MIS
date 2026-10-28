from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse

from app.core.deps import CurrentUser, DatabaseSession
from app.schemas.attachment import AttachmentRead
from app.services import attachment_service

router = APIRouter(tags=["Attachments"])


@router.get("/projects/{project_id}/attachments", response_model=list[AttachmentRead])
def list_attachments(
    project_id: UUID,
    db: DatabaseSession,
    actor: CurrentUser,
) -> list[AttachmentRead]:
    return attachment_service.list_attachments(db, actor=actor, project_id=project_id)


@router.post(
    "/projects/{project_id}/attachments",
    response_model=AttachmentRead,
    status_code=201,
)
def upload_attachment(
    project_id: UUID,
    db: DatabaseSession,
    actor: CurrentUser,
    file: UploadFile = File(...),
) -> AttachmentRead:
    return attachment_service.save_attachment(db, actor=actor, project_id=project_id, upload=file)


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: UUID,
    db: DatabaseSession,
    actor: CurrentUser,
) -> FileResponse:
    path, attachment = attachment_service.get_download(db, actor=actor, attachment_id=attachment_id)
    return FileResponse(
        path=path,
        filename=attachment.filename,
        media_type=attachment.content_type,
        headers={"Content-Disposition": f'attachment; filename="{attachment.filename}"'},
    )
