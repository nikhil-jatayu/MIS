from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter

from app.core.deps import CurrentUser, DatabaseSession
from app.models.enums import Priority, ProjectStatus, ProjectType, PurchaseRequestStatus
from app.schemas.operations_reporting import OperationsReportRead
from app.services import operations_reporting_service

router = APIRouter(prefix="/operations/reports", tags=["Operations Reports"])


@router.get("/summary", response_model=OperationsReportRead)
def operations_report_summary(
    db: DatabaseSession,
    actor: CurrentUser,
    date_from: date,
    date_to: date,
    project_id: UUID | None = None,
    project_status: ProjectStatus | None = None,
    project_type: ProjectType | None = None,
    priority: Priority | None = None,
    purchase_status: PurchaseRequestStatus | None = None,
) -> OperationsReportRead:
    return operations_reporting_service.get_operations_report(
        db,
        actor=actor,
        date_from=date_from,
        date_to=date_to,
        project_id=project_id,
        project_status=project_status.value if project_status else None,
        project_type=project_type.value if project_type else None,
        priority=priority.value if priority else None,
        purchase_status=purchase_status.value if purchase_status else None,
    )
