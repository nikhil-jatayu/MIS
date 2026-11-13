from __future__ import annotations

from copy import copy
from datetime import date, datetime, time, timedelta
from io import BytesIO
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.production import ProductionAction, ProductionEntry, ProductionMonthlyReview
from app.models.project import Project
from app.models.user import User
from app.services.production_reporting_service import get_production_report

OPEN_STATUSES = ("OPEN", "IN_PROGRESS", "ON_HOLD")
REPORT_TIMEZONE = ZoneInfo("Asia/Kolkata")
TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "templates"
    / "JESES_Monthly_Production_MIS_Template.xlsx"
)


def _entry_filters(
    *,
    date_from: date,
    date_to: date,
    production_line: str | None,
    product_model: str | None,
    project_id: UUID | None,
    unit_of_measure: str | None,
) -> list:
    clauses = [
        ProductionEntry.production_date >= date_from,
        ProductionEntry.production_date <= date_to,
    ]
    if production_line:
        clauses.append(
            ProductionEntry.production_line.ilike(f"%{production_line.strip()}%")
        )
    if product_model:
        clauses.append(ProductionEntry.product_model.ilike(f"%{product_model.strip()}%"))
    if project_id:
        clauses.append(ProductionEntry.project_id == project_id)
    if unit_of_measure:
        clauses.append(ProductionEntry.unit_of_measure == unit_of_measure.strip().lower())
    return clauses


def _get_actions(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    project_id: UUID | None,
) -> list[ProductionAction]:
    start_at = datetime.combine(date_from, time.min, tzinfo=REPORT_TIMEZONE)
    end_exclusive = datetime.combine(
        date_to + timedelta(days=1), time.min, tzinfo=REPORT_TIMEZONE
    )
    action_scope = [ProductionAction.date_raised <= date_to]
    if project_id:
        action_scope.append(ProductionAction.project_id == project_id)
    period_or_active = or_(
        ProductionAction.date_raised >= date_from,
        ProductionAction.status.in_(OPEN_STATUSES),
        and_(
            ProductionAction.status == "CLOSED",
            ProductionAction.closed_at >= start_at,
            ProductionAction.closed_at < end_exclusive,
        ),
    )
    statement = (
        select(ProductionAction)
        .options(
            selectinload(ProductionAction.responsible_user),
            selectinload(ProductionAction.closed_by),
        )
        .where(*action_scope, period_or_active)
        .order_by(ProductionAction.date_raised.desc(), ProductionAction.action_number.asc())
    )
    return list(db.scalars(statement).all())


def _get_monthly_review(
    db: Session, *, date_from: date, date_to: date
) -> ProductionMonthlyReview | None:
    # A monthly sign-off is only attached when the export represents the whole month.
    if date_from.year != date_to.year or date_from.month != date_to.month:
        return None
    first = date(date_from.year, date_from.month, 1)
    next_month = date(
        date_from.year + (1 if date_from.month == 12 else 0),
        1 if date_from.month == 12 else date_from.month + 1,
        1,
    )
    if date_from != first or date_to != next_month - timedelta(days=1):
        return None
    statement = (
        select(ProductionMonthlyReview)
        .options(
            selectinload(ProductionMonthlyReview.prepared_by),
            selectinload(ProductionMonthlyReview.reviewed_by),
        )
        .where(
            ProductionMonthlyReview.year == date_from.year,
            ProductionMonthlyReview.month == date_from.month,
        )
    )
    return db.scalar(statement)


def _copy_row_style(sheet, source_row: int, target_row: int, max_col: int) -> None:
    if target_row == source_row:
        return
    source_dimension = sheet.row_dimensions[source_row]
    target_dimension = sheet.row_dimensions[target_row]
    if source_dimension.height is not None:
        target_dimension.height = source_dimension.height
    for column in range(1, max_col + 1):
        source_cell = sheet.cell(source_row, column)
        target_cell = sheet.cell(target_row, column)
        if source_cell.has_style:
            target_cell._style = copy(source_cell._style)
        if source_cell.number_format:
            target_cell.number_format = source_cell.number_format
        if source_cell.alignment:
            target_cell.alignment = copy(source_cell.alignment)


def _write_production_log(sheet, entries: list[ProductionEntry]) -> int:
    original_capacity = 200  # The supplied template is preformatted for rows 5–204.
    needed_capacity = max(original_capacity, len(entries))
    last_row = 4 + needed_capacity

    if needed_capacity > original_capacity:
        for row in range(205, last_row + 1):
            _copy_row_style(sheet, 204, row, 21)

    for merged in list(sheet.merged_cells.ranges):
        if str(merged) in {"A1:Q1", "A2:Q2"}:
            sheet.unmerge_cells(str(merged))
    sheet.merge_cells("A1:U1")
    sheet.merge_cells("A2:U2")

    headers = {
        1: "Date",
        2: "Month",
        3: "Product / Model",
        4: "Work Order / Customer",
        5: "Process Stage",
        6: "Planned Qty",
        7: "Actual Qty",
        8: "Accepted Qty (First Pass)",
        9: "First-pass Non-acceptance Qty",
        10: "Rework Qty (Sent)",
        11: "Production Hours",
        12: "Downtime Hours",
        13: "Plan Achievement %",
        14: "First Pass Yield %",
        15: "First-pass Non-acceptance %",
        16: "Downtime %",
        17: "Remarks",
        18: "Production Line",
        19: "Unit of Measure",
        20: "Project",
        21: "Rework Rate %",
    }
    for column, value in headers.items():
        cell = sheet.cell(4, column, value)
        if column >= 18:
            cell._style = copy(sheet.cell(4, 17)._style)
    extra_widths = {18: 22, 19: 16, 20: 28, 21: 16}
    for column, width in extra_widths.items():
        sheet.column_dimensions[get_column_letter(column)].width = width

    for index, entry in enumerate(entries, start=5):
        sheet.cell(index, 1, entry.production_date)
        sheet.cell(index, 2, f'=IF(A{index}="","",TEXT(A{index},"mmm-yyyy"))')
        sheet.cell(index, 3, entry.product_model)
        sheet.cell(index, 4, entry.work_order_customer or "")
        sheet.cell(index, 5, entry.process_stage)
        sheet.cell(index, 6, float(entry.planned_quantity))
        sheet.cell(index, 7, float(entry.actual_quantity))
        sheet.cell(index, 8, float(entry.accepted_quantity))
        sheet.cell(
            index,
            9,
            f'=IF(OR(G{index}="",H{index}=""),"",MAX(0,G{index}-H{index}))',
        )
        sheet.cell(index, 10, float(entry.rework_quantity))
        sheet.cell(index, 11, float(entry.production_hours))
        sheet.cell(index, 12, float(entry.downtime_hours))
        sheet.cell(index, 13, f"=IFERROR(G{index}/F{index},0)")
        sheet.cell(index, 14, f"=IFERROR(H{index}/G{index},0)")
        sheet.cell(index, 15, f"=IFERROR(I{index}/G{index},0)")
        sheet.cell(index, 16, f"=IFERROR(L{index}/(K{index}+L{index}),0)")
        sheet.cell(index, 17, entry.remarks or "")
        sheet.cell(index, 18, entry.production_line)
        sheet.cell(index, 19, entry.unit_of_measure)
        sheet.cell(index, 20, entry.project.name if entry.project else "")
        sheet.cell(index, 21, f"=IFERROR(J{index}/G{index},0)")

        for column in (18, 19, 20):
            sheet.cell(index, column)._style = copy(sheet.cell(index, 17)._style)
        sheet.cell(index, 21)._style = copy(sheet.cell(index, 16)._style)
        for column in (13, 14, 15, 16, 21):
            sheet.cell(index, column).number_format = "0.0%"
        for column in (6, 7, 8, 9, 10):
            sheet.cell(index, column).number_format = "#,##0.###"
        for column in (11, 12):
            sheet.cell(index, column).number_format = "0.00"

    # Formula cells remain available for unused template rows, matching the original workbook.
    for row in range(5 + len(entries), last_row + 1):
        sheet.cell(row, 2, f'=IF(A{row}="","",TEXT(A{row},"mmm-yyyy"))')
        sheet.cell(
            row,
            9,
            f'=IF(OR(G{row}="",H{row}=""),"",MAX(0,G{row}-H{row}))',
        )
        sheet.cell(row, 13, f"=IFERROR(G{row}/F{row},0)")
        sheet.cell(row, 14, f"=IFERROR(H{row}/G{row},0)")
        sheet.cell(row, 15, f"=IFERROR(I{row}/G{row},0)")
        sheet.cell(row, 16, f"=IFERROR(L{row}/(K{row}+L{row}),0)")
        sheet.cell(row, 21, f"=IFERROR(J{row}/G{row},0)")
        sheet.cell(row, 21)._style = copy(sheet.cell(row, 16)._style)
        sheet.cell(row, 21).number_format = "0.0%"

    sheet.auto_filter.ref = f"A4:U{max(5, 4 + len(entries))}"
    sheet.freeze_panes = "A5"
    sheet.sheet_view.showGridLines = False
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.print_title_rows = "1:4"
    return last_row


def _write_action_tracker(sheet, actions: list[ProductionAction]) -> int:
    original_capacity = 100  # The supplied template is preformatted for rows 5–104.
    capacity = max(original_capacity, len(actions))
    last_row = 4 + capacity
    if capacity > original_capacity:
        for row in range(105, last_row + 1):
            _copy_row_style(sheet, 104, row, 9)

    for index, action in enumerate(actions, start=5):
        sheet.cell(index, 1, action.action_number)
        sheet.cell(index, 2, action.date_raised)
        sheet.cell(index, 3, action.issue_observation)
        sheet.cell(index, 4, action.corrective_action)
        sheet.cell(
            index,
            5,
            action.responsible_user.name if action.responsible_user else "Unassigned",
        )
        sheet.cell(index, 6, action.deadline)
        status_labels = {
            "OPEN": "Open",
            "IN_PROGRESS": "In Progress",
            "ON_HOLD": "On Hold",
            "CLOSED": "Closed",
        }
        sheet.cell(index, 7, status_labels.get(action.status, action.status))
        closed_date = None
        if action.closed_at:
            closed_date = (
                action.closed_at.astimezone(REPORT_TIMEZONE).date()
                if action.closed_at.tzinfo
                else action.closed_at.date()
            )
        sheet.cell(index, 8, closed_date)
        sheet.cell(index, 9, action.closure_evidence or action.remarks or "")
        for column in (2, 6, 8):
            sheet.cell(index, column).number_format = "dd-mmm-yyyy"
        for column in (3, 4, 5, 9):
            sheet.cell(index, column).alignment = Alignment(
                vertical="top", wrap_text=True
            )

    sheet.auto_filter.ref = f"A4:I{max(5, 4 + len(actions))}"
    sheet.freeze_panes = "A5"
    sheet.sheet_view.showGridLines = False
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.print_title_rows = "1:4"
    return last_row


def _style_summary_table(sheet, last_col: int) -> None:
    header_style = copy(sheet["A9"]._style)
    label_style = copy(sheet["A10"]._style)
    number_style = copy(sheet["B10"]._style)
    percent_style = copy(sheet["B13"]._style)
    for column in range(1, last_col + 1):
        cell = sheet.cell(9, column)
        cell._style = copy(header_style)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in range(10, 22):
        sheet.cell(row, 1)._style = copy(label_style)
        for column in range(2, last_col + 1):
            sheet.cell(row, column)._style = copy(
                percent_style if row in (15, 16, 18, 21) else number_style
            )
            sheet.cell(row, column).alignment = Alignment(
                horizontal="right", vertical="center"
            )
            if row in (15, 16, 18, 21):
                sheet.cell(row, column).number_format = "0.0%"
            elif row not in (10,):
                sheet.cell(row, column).number_format = "#,##0.###"
    sheet.row_dimensions[9].height = 34
    for row in range(10, 22):
        sheet.row_dimensions[row].height = 22
    sheet.column_dimensions["A"].width = 39
    for column in range(2, last_col + 1):
        sheet.column_dimensions[get_column_letter(column)].width = 19


def _write_management_summary(
    sheet,
    *,
    date_from: date,
    date_to: date,
    actor: User,
    review: ProductionMonthlyReview | None,
    units: list[str],
    log_last_row: int,
    action_summary,
    filter_summary: str,
) -> None:
    # Remove template merges so the KPI block can become a unit-by-unit matrix.
    for merged_range in list(sheet.merged_cells.ranges):
        sheet.unmerge_cells(str(merged_range))

    last_col = max(8, len(units) + 1)
    last_letter = get_column_letter(last_col)
    sheet.merge_cells(f"A1:{last_letter}1")
    sheet.merge_cells(f"A2:{last_letter}2")
    sheet.merge_cells(f"B7:{last_letter}7")
    sheet.merge_cells(f"A23:{last_letter}23")
    sheet.merge_cells(f"A24:{last_letter}26")
    sheet.merge_cells(f"A27:{last_letter}27")
    sheet.merge_cells(f"E29:{last_letter}29")

    sheet["A1"] = "MIS | Monthly Production Management Report"
    sheet["A2"] = (
        "JES Electronics Systems Pvt Ltd | Unit-wise results; quantities in different units "
        "are never added together."
    )
    sheet["A4"] = "Reporting Period"
    sheet["B4"] = f"{date_from:%d-%b-%Y} to {date_to:%d-%b-%Y} (inclusive)"
    sheet["A5"] = "Prepared By"
    sheet["B5"] = actor.name
    sheet["A6"] = "Reviewed By"
    sheet["B6"] = (
        review.reviewed_by.name
        if review and review.reviewed_at and review.reviewed_by
        else "Not reviewed"
    )
    sheet["A7"] = "Applied Filters"
    sheet["B7"] = filter_summary
    sheet["A7"]._style = copy(sheet["A4"]._style)
    sheet["B7"]._style = copy(sheet["B4"]._style)

    for row in sheet.iter_rows(min_row=9, max_row=21, min_col=1, max_col=max(8, last_col)):
        for cell in row:
            cell.value = None

    sheet["A9"] = "Metric"
    for index, unit in enumerate(units, start=2):
        sheet.cell(9, index, unit)
    if not units:
        sheet["B9"] = "No matching units"

    labels = {
        10: "Production entries",
        11: "Planned quantity",
        12: "Actual quantity",
        13: "Accepted at first pass",
        14: "First-pass non-acceptance (not final scrap)",
        15: "Plan achievement",
        16: "First-pass yield",
        17: "Rework quantity sent",
        18: "Rework rate",
        19: "Production hours",
        20: "Downtime hours",
        21: "Downtime %",
    }
    for row, label in labels.items():
        sheet.cell(row, 1, label)

    log_end = max(5, log_last_row)
    unit_range = f"'Production Log'!$S$5:$S${log_end}"
    sum_ranges = {
        11: f"'Production Log'!$F$5:$F${log_end}",
        12: f"'Production Log'!$G$5:$G${log_end}",
        13: f"'Production Log'!$H$5:$H${log_end}",
        14: f"'Production Log'!$I$5:$I${log_end}",
        17: f"'Production Log'!$J$5:$J${log_end}",
        19: f"'Production Log'!$K$5:$K${log_end}",
        20: f"'Production Log'!$L$5:$L${log_end}",
    }
    for column in range(2, len(units) + 2):
        letter = get_column_letter(column)
        sheet.cell(10, column, f"=COUNTIF({unit_range},{letter}$9)")
        for row, sum_range in sum_ranges.items():
            sheet.cell(row, column, f"=SUMIF({unit_range},{letter}$9,{sum_range})")
        sheet.cell(15, column, f"=IFERROR({letter}12/{letter}11,0)")
        sheet.cell(16, column, f"=IFERROR({letter}13/{letter}12,0)")
        sheet.cell(18, column, f"=IFERROR({letter}17/{letter}12,0)")
        sheet.cell(21, column, f"=IFERROR({letter}20/({letter}19+{letter}20),0)")

    sheet["A23"] = "Management Summary / Key Observations"
    sheet["A24"]._style = copy(sheet["A19"]._style)
    sheet["A24"].alignment = Alignment(vertical="top", wrap_text=True)
    if review:
        sheet["A24"] = review.management_summary
    else:
        sheet["A24"] = (
            "No full-month management review is recorded for this selection. "
            "Add observations in MIS Production > Monthly Summary."
        )
    sheet["A27"] = "Priority Actions — Reporting Period"
    action_headers = [
        "Currently Open",
        "Currently Overdue",
        "Closed in Period",
        "Created in Period",
        "Management Attention",
    ]
    for column, label in enumerate(action_headers, start=1):
        sheet.cell(28, column, label)
    sheet["A29"] = action_summary.current_open_actions
    sheet["B29"] = action_summary.current_overdue_actions
    sheet["C29"] = action_summary.closed_actions_in_period
    sheet["D29"] = action_summary.actions_created_in_period
    sheet["E29"]._style = copy(sheet["D29"]._style)
    sheet["E29"] = (
        f"Review {action_summary.current_overdue_actions} overdue action(s) at the next "
        "production review."
        if action_summary.current_overdue_actions
        else "No currently overdue production actions."
    )

    _style_summary_table(sheet, last_col)
    # Style the action summary using the template's existing header and value styles.
    action_header_style = copy(sheet["A9"]._style)
    action_value_style = copy(sheet["B25"]._style)
    section_style = copy(sheet["A23"]._style)
    sheet["A27"]._style = copy(section_style)
    sheet["A24"].alignment = Alignment(vertical="top", wrap_text=True)
    sheet.row_dimensions[23].height = 24
    sheet.row_dimensions[27].height = 24
    for column in range(1, 6):
        sheet.cell(28, column)._style = copy(action_header_style)
        sheet.cell(28, column).alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )
    for column in range(1, 5):
        sheet.cell(29, column)._style = copy(action_value_style)
        sheet.cell(29, column).alignment = Alignment(horizontal="center", vertical="center")
    sheet["E29"].alignment = Alignment(vertical="center", wrap_text=True)
    sheet.row_dimensions[28].height = 34
    sheet.row_dimensions[29].height = 42
    sheet.row_dimensions[24].height = 42
    sheet.row_dimensions[25].height = 20
    sheet.row_dimensions[26].height = 20
    sheet.freeze_panes = "B10"
    sheet.sheet_view.showGridLines = False
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 1
    sheet.print_area = f"A1:{last_letter}29"


def _update_reference_sheets(workbook) -> None:
    log = workbook["Production Log"]
    log["A1"] = "MIS | Monthly Production Log"
    log["A2"] = (
        "One row per product / production line / reporting date. "
        "Blue input cells are supplied from MIS; formula cells calculate automatically."
    )

    actions = workbook["Action Tracker"]
    actions["A1"] = "MIS | Production Action Tracker"
    actions["A2"] = (
        "Includes actions raised in the selected period, plus unresolved actions carried "
        "into the period and actions closed during it."
    )

    definitions = workbook["KPI Definitions"]
    definitions["A1"] = "MIS | Production KPI Definitions"
    definitions["A2"] = (
        "Use consistent definitions month to month. Targets are illustrative and require "
        "management approval."
    )
    definitions["A6"] = "First Pass Yield (FPY)"
    definitions["B6"] = "Accepted quantity at first inspection ÷ actual quantity × 100"
    definitions["E6"] = "Higher is better; accepted quantity means first-pass accepted output."
    definitions["A7"] = "First-pass Non-acceptance Rate"
    definitions["B7"] = "(Actual quantity − accepted first-pass quantity) ÷ actual quantity × 100"
    definitions["D7"] = "Monitor trend"
    definitions["E7"] = (
        "Includes units sent for rework and other pending dispositions. This is not final "
        "scrap/rejection."
    )
    definitions["A11"] = "Rework Quantity Sent"
    definitions["B11"] = "Quantity sent for repair / reprocessing"
    definitions["E11"] = (
        "Reported separately; rework sent is already part of first-pass non-acceptance. "
        "Do not add it again."
    )
    definitions["A12"] = "Rework Rate"
    definitions["B12"] = "Rework quantity sent ÷ actual quantity × 100"
    definitions["C12"] = "%"
    definitions["D12"] = "Trend down"
    definitions["E12"] = "Shows the share of actual output sent for rework."
    definitions["A13"] = "Final Scrap / Rejection"
    definitions["B13"] = "Not available in the current MIS production record"
    definitions["C13"] = "—"
    definitions["D13"] = "Not calculated"
    definitions["E13"] = (
        "Post-rework disposition is not recorded, so final scrap/rejection cannot be derived."
    )
    for row in (12, 13):
        for column in range(1, 6):
            definitions.cell(row, column)._style = copy(definitions.cell(11, column)._style)
            definitions.cell(row, column).alignment = Alignment(vertical="top", wrap_text=True)
        definitions.row_dimensions[row].height = 48

    guide = workbook["Instructions"]
    guide["A1"] = "MIS | How to Use the Monthly Production Report"
    guide["A2"] = "Workbook guide and reporting discipline"
    instructions = {
        4: (
            "1. Set reporting period",
            "Choose the date range and optional production line, product, project and unit filters "
            "on MIS Reports > Production. The workbook contains the same filtered selection.",
        ),
        5: (
            "2. Production Log",
            "Each row is one production entry. Production Line, Unit of Measure and Project are "
            "included so records can be traced and units are not mixed.",
        ),
        6: (
            "3. Formula columns",
            "Month, first-pass non-acceptance quantity, plan achievement, first-pass yield, "
            "first-pass non-acceptance rate, rework rate and downtime percentage are "
            "formula-driven.",
        ),
        7: (
            "4. Quality definitions",
            "Accepted quantity means accepted at first inspection. Rework quantity means units "
            "sent for rework. First-pass non-acceptance = actual minus first-pass accepted; "
            "it is not final scrap/rejection.",
        ),
        8: (
            "5. Action Tracker",
            "The tracker includes actions raised in the selected period, unresolved actions "
            "carried into it, and actions closed during it. Production line / product / unit "
            "filters do not filter actions; the project filter does.",
        ),
        9: (
            "6. Monthly review",
            "A saved monthly management review is included only when the export covers a complete "
            "calendar month. Prepared By is the person who generated the export.",
        ),
        10: (
            "7. Data quality",
            "Use consistent units, avoid duplicate entries and record production dates "
            "consistently. The summary keeps each unit of measure separate; do not add pcs "
            "and kg together.",
        ),
        11: (
            "8. Excel compatibility",
            "Formula cells recalculate when opened in Excel. If using LibreOffice, confirm "
            "formulas recalculate on opening. Targets remain illustrative until approved by "
            "management.",
        ),
    }
    for row, (heading, detail) in instructions.items():
        guide.cell(row, 1, heading)
        guide.cell(row, 2, detail)
        guide.cell(row, 2).alignment = Alignment(vertical="top", wrap_text=True)
        guide.row_dimensions[row].height = 62


def _filter_description(
    *,
    production_line: str | None,
    product_model: str | None,
    project_id: UUID | None,
    project_name: str | None,
    unit_of_measure: str | None,
) -> str:
    active = []
    if production_line:
        active.append(f"Line: {production_line.strip()}")
    if product_model:
        active.append(f"Product: {product_model.strip()}")
    if project_id:
        active.append(f"Project: {project_name or project_id}")
    if unit_of_measure:
        active.append(f"Unit: {unit_of_measure.strip().lower()}")
    if active:
        return " | ".join(active)
    return "No additional filters (all lines, products, projects and units)."


def build_production_excel_export(
    db: Session,
    *,
    actor: User,
    date_from: date,
    date_to: date,
    production_line: str | None = None,
    product_model: str | None = None,
    project_id=None,
    unit_of_measure: str | None = None,
) -> tuple[bytes, str]:
    if not TEMPLATE_PATH.is_file():
        raise FileNotFoundError(f"Production report template not found: {TEMPLATE_PATH}")

    report = get_production_report(
        db,
        date_from=date_from,
        date_to=date_to,
        production_line=production_line,
        product_model=product_model,
        project_id=project_id,
        unit_of_measure=unit_of_measure,
    )
    entry_statement = (
        select(ProductionEntry)
        .options(selectinload(ProductionEntry.project))
        .where(
            *_entry_filters(
                date_from=date_from,
                date_to=date_to,
                production_line=production_line,
                product_model=product_model,
                project_id=project_id,
                unit_of_measure=unit_of_measure,
            )
        )
        .order_by(
            ProductionEntry.production_date.asc(),
            ProductionEntry.production_line.asc(),
            ProductionEntry.product_model.asc(),
            ProductionEntry.created_at.asc(),
        )
    )
    entries = list(db.scalars(entry_statement).all())
    actions = _get_actions(
        db, date_from=date_from, date_to=date_to, project_id=project_id
    )
    review = _get_monthly_review(db, date_from=date_from, date_to=date_to)
    project_name = (
        db.scalar(select(Project.name).where(Project.id == project_id))
        if project_id
        else None
    )

    workbook = load_workbook(TEMPLATE_PATH)
    log_last_row = _write_production_log(workbook["Production Log"], entries)
    _write_action_tracker(workbook["Action Tracker"], actions)
    units = [metric.unit_of_measure for metric in report.totals_by_unit]
    _write_management_summary(
        workbook["Management Summary"],
        date_from=date_from,
        date_to=date_to,
        actor=actor,
        review=review,
        units=units,
        log_last_row=log_last_row,
        action_summary=report.actions,
        filter_summary=_filter_description(
            production_line=production_line,
            product_model=product_model,
            project_id=project_id,
            project_name=project_name,
            unit_of_measure=unit_of_measure,
        ),
    )
    _update_reference_sheets(workbook)

    workbook.properties.creator = "JES Electronics Systems Pvt Ltd"
    workbook.properties.lastModifiedBy = actor.name
    workbook.properties.title = "MIS Production Management Report"
    workbook.properties.subject = (
        f"Production reporting from {date_from.isoformat()} to {date_to.isoformat()}"
    )
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.calculation.calcMode = "auto"
    workbook.active = 0

    output = BytesIO()
    workbook.save(output)
    filename = (
        f"MIS_Production_Report_{date_from.isoformat()}_to_{date_to.isoformat()}.xlsx"
    )
    return output.getvalue(), filename
