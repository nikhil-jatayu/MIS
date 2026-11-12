from __future__ import annotations

from datetime import date
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.deps import CurrentUser, DatabaseSession
from app.schemas.production_reporting import ProductionReportRead
from app.services import (
    production_excel_export_service,
    production_pdf_export_service,
    production_reporting_service,
)

router = APIRouter(prefix="/production/reports", tags=["Production Reports"])

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
PDF_MEDIA_TYPE = "application/pdf"


@router.get("/summary", response_model=ProductionReportRead)
def production_report_summary(
    db: DatabaseSession,
    _: CurrentUser,
    date_from: date,
    date_to: date,
    production_line: str | None = Query(default=None, max_length=120),
    product_model: str | None = Query(default=None, max_length=200),
    project_id: UUID | None = None,
    unit_of_measure: str | None = Query(default=None, max_length=30),
) -> ProductionReportRead:
    return production_reporting_service.get_production_report(
        db,
        date_from=date_from,
        date_to=date_to,
        production_line=production_line,
        product_model=product_model,
        project_id=project_id,
        unit_of_measure=unit_of_measure,
    )


@router.get("/export.xlsx", response_class=StreamingResponse)
def export_production_report_excel(
    db: DatabaseSession,
    actor: CurrentUser,
    date_from: date,
    date_to: date,
    production_line: str | None = Query(default=None, max_length=120),
    product_model: str | None = Query(default=None, max_length=200),
    project_id: UUID | None = None,
    unit_of_measure: str | None = Query(default=None, max_length=30),
) -> StreamingResponse:
    content, filename = production_excel_export_service.build_production_excel_export(
        db,
        actor=actor,
        date_from=date_from,
        date_to=date_to,
        production_line=production_line,
        product_model=product_model,
        project_id=project_id,
        unit_of_measure=unit_of_measure,
    )
    return StreamingResponse(
        BytesIO(content),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export.pdf", response_class=StreamingResponse)
def export_production_report_pdf(
    db: DatabaseSession,
    actor: CurrentUser,
    date_from: date,
    date_to: date,
    production_line: str | None = Query(default=None, max_length=120),
    product_model: str | None = Query(default=None, max_length=200),
    project_id: UUID | None = None,
    unit_of_measure: str | None = Query(default=None, max_length=30),
) -> StreamingResponse:
    content, filename = production_pdf_export_service.build_production_pdf_export(
        db,
        actor=actor,
        date_from=date_from,
        date_to=date_to,
        production_line=production_line,
        product_model=product_model,
        project_id=project_id,
        unit_of_measure=unit_of_measure,
    )
    return StreamingResponse(
        BytesIO(content),
        media_type=PDF_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, private",
        },
    )
