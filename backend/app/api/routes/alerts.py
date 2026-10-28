from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DatabaseSession, Pagination, SuperAdminUser
from app.schemas.alert import AlertRead, AlertRunResult, UnreadCount
from app.schemas.common import MessageResponse, Page
from app.services import alert_service

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=Page[AlertRead])
def list_alerts(
    db: DatabaseSession,
    pagination: Pagination,
    user: CurrentUser,
    unread_only: bool = Query(default=False),
) -> Page[AlertRead]:
    return alert_service.list_alerts(
        db,
        user=user,
        page=pagination.page,
        page_size=pagination.page_size,
        unread_only=unread_only,
    )


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(db: DatabaseSession, user: CurrentUser) -> UnreadCount:
    return UnreadCount(unread=alert_service.unread_count(db, user=user))


@router.post("/read-all", response_model=MessageResponse)
def mark_all_read(db: DatabaseSession, user: CurrentUser) -> MessageResponse:
    count = alert_service.mark_all_read(db, user=user)
    return MessageResponse(message=f"{count} alert(s) marked as read")


@router.post("/run-check", response_model=AlertRunResult)
def run_check(db: DatabaseSession, _: SuperAdminUser) -> AlertRunResult:
    return alert_service.run_time_counter(db)


@router.post("/{alert_id}/read", response_model=MessageResponse)
def mark_read(
    alert_id: UUID,
    db: DatabaseSession,
    user: CurrentUser,
) -> MessageResponse:
    alert_service.mark_read(db, user=user, alert_id=alert_id)
    return MessageResponse(message="Alert marked as read")
