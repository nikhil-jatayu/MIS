from __future__ import annotations

import math
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from io import BytesIO
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.production import ProductionAction, ProductionMonthlyReview
from app.models.project import Project
from app.models.user import User
from app.schemas.production_reporting import (
    ProductionReportDimensionMetric,
    ProductionReportMetric,
    ProductionReportRead,
    ProductionReportTrendPoint,
)
from app.services.production_reporting_service import get_production_report

REPORT_TIMEZONE = ZoneInfo("Asia/Kolkata")
OPEN_STATUSES = ("OPEN", "IN_PROGRESS", "ON_HOLD")
PAGE_SIZE = landscape(A4)

NAVY = colors.HexColor("#15324B")
TEAL = colors.HexColor("#0F5968")
TEAL_LIGHT = colors.HexColor("#E7F3F3")
BLUE = colors.HexColor("#6B9DB8")
BLUE_LIGHT = colors.HexColor("#EAF1F6")
INK = colors.HexColor("#233746")
MUTED = colors.HexColor("#657786")
GRID = colors.HexColor("#D9E2E8")
PALE = colors.HexColor("#F4F7F9")
WHITE = colors.white
RED = colors.HexColor("#A93434")
RED_LIGHT = colors.HexColor("#FCECEC")
AMBER = colors.HexColor("#946200")
AMBER_LIGHT = colors.HexColor("#FFF5D9")
GREEN = colors.HexColor("#26734D")
GREEN_LIGHT = colors.HexColor("#EAF5EF")


@dataclass(frozen=True)
class ActionPdfRow:
    action_number: str
    date_raised: date
    issue_observation: str
    corrective_action: str
    responsible_name: str
    deadline: date
    status: str
    closed_date: date | None
    closure_text: str


class UnitTrendChart(Flowable):
    """Small vector chart; each instance represents exactly one unit of measure."""

    def __init__(
        self,
        *,
        unit: str,
        points: list[ProductionReportTrendPoint],
        width: float,
        height: float = 132,
    ) -> None:
        super().__init__()
        self.unit = unit
        self.points = points
        self.width = width
        self.height = height

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        self.width = min(self.width, avail_width)
        return self.width, self.height

    def draw(self) -> None:
        canvas = self.canv
        canvas.saveState()
        canvas.setFillColor(INK)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(0, self.height - 11, f"Production trend - {self.unit}")

        legend_y = self.height - 10
        legend_x = max(175, self.width - 170)
        canvas.setFillColor(BLUE)
        canvas.rect(legend_x, legend_y - 2, 7, 7, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(legend_x + 11, legend_y - 1, "Planned")
        canvas.setFillColor(TEAL)
        canvas.rect(legend_x + 65, legend_y - 2, 7, 7, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.drawString(legend_x + 76, legend_y - 1, "Actual")

        plot_left = 43
        plot_right = self.width - 10
        plot_bottom = 23
        plot_top = self.height - 31
        plot_width = max(1, plot_right - plot_left)
        plot_height = max(1, plot_top - plot_bottom)
        max_value = max(
            [
                max(point.planned_quantity, point.actual_quantity)
                for point in self.points
            ]
            or [1.0]
        )
        axis_max = max(1.0, max_value * 1.12)

        canvas.setStrokeColor(GRID)
        canvas.setLineWidth(0.45)
        canvas.setFont("Helvetica", 6.5)
        for tick in range(5):
            value = axis_max * tick / 4
            y = plot_bottom + plot_height * tick / 4
            canvas.line(plot_left, y, plot_right, y)
            canvas.setFillColor(MUTED)
            canvas.drawRightString(plot_left - 6, y - 2, _format_number(value))

        if not self.points:
            canvas.setFillColor(MUTED)
            canvas.setFont("Helvetica-Oblique", 8)
            canvas.drawCentredString(
                self.width / 2,
                plot_bottom + plot_height / 2,
                "No trend data for this unit in the selected period.",
            )
            canvas.restoreState()
            return

        slot = plot_width / len(self.points)
        bar_width = max(2.0, min(8.0, slot * 0.27))
        label_step = max(1, math.ceil(len(self.points) / 12))

        for index, point in enumerate(self.points):
            center = plot_left + slot * (index + 0.5)
            planned_height = plot_height * point.planned_quantity / axis_max
            actual_height = plot_height * point.actual_quantity / axis_max

            canvas.setFillColor(BLUE)
            canvas.rect(
                center - bar_width - 1,
                plot_bottom,
                bar_width,
                max(0.6, planned_height),
                fill=1,
                stroke=0,
            )
            canvas.setFillColor(TEAL)
            canvas.rect(
                center + 1,
                plot_bottom,
                bar_width,
                max(0.6, actual_height),
                fill=1,
                stroke=0,
            )

            if index % label_step == 0 or index == len(self.points) - 1:
                label = _period_label(point.period)
                canvas.saveState()
                canvas.translate(center, plot_bottom - 7)
                canvas.rotate(32)
                canvas.setFillColor(MUTED)
                canvas.setFont("Helvetica", 6)
                canvas.drawRightString(0, 0, label)
                canvas.restoreState()

        canvas.setStrokeColor(TEAL)
        canvas.line(plot_left, plot_bottom, plot_left, plot_top)
        canvas.line(plot_left, plot_bottom, plot_right, plot_bottom)
        canvas.restoreState()


def _safe_text(value: object | None) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u00a0": " ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text.encode("cp1252", errors="replace").decode("cp1252")


def _paragraph(
    value: object | None,
    style: ParagraphStyle,
    *,
    allow_markup: bool = False,
) -> Paragraph:
    text = _safe_text(value)
    if not allow_markup:
        text = escape(text).replace("\n", "<br/>")
    return Paragraph(text or "-", style)


def _format_number(value: float | int | None, decimals: int = 2) -> str:
    if value is None:
        return "-"
    rendered = f"{float(value):,.{decimals}f}"
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _format_percent(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}%"


def _format_date(value: date | None) -> str:
    return "-" if value is None else value.strftime("%d %b %Y")


def _period_label(value: str) -> str:
    try:
        if len(value) == 7:
            return datetime.strptime(value, "%Y-%m").strftime("%b %y")
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d %b")
    except ValueError:
        return value


def _filter_description(
    *,
    production_line: str | None,
    product_model: str | None,
    project_name: str | None,
    project_id: object | None,
    unit_of_measure: str | None,
) -> str:
    applied: list[str] = []
    if production_line:
        applied.append(f"Production line: {production_line.strip()}")
    if product_model:
        applied.append(f"Product/model: {product_model.strip()}")
    if project_id:
        applied.append(f"Project: {project_name or project_id}")
    if unit_of_measure:
        applied.append(f"Unit: {unit_of_measure.strip().lower()}")
    return (
        " | ".join(applied)
        if applied
        else "No additional filters - all lines, products, projects and units."
    )


def _get_actions(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    project_id,
) -> list[ProductionAction]:
    start_at = datetime.combine(date_from, time.min, tzinfo=REPORT_TIMEZONE)
    end_exclusive = datetime.combine(
        date_to + timedelta(days=1), time.min, tzinfo=REPORT_TIMEZONE
    )
    clauses = [ProductionAction.date_raised <= date_to]
    if project_id:
        clauses.append(ProductionAction.project_id == project_id)
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
        .where(*clauses, period_or_active)
        .order_by(ProductionAction.deadline.asc(), ProductionAction.date_raised.desc())
    )
    return list(db.scalars(statement).all())


def _action_rows(actions: Iterable[ProductionAction]) -> list[ActionPdfRow]:
    result: list[ActionPdfRow] = []
    for action in actions:
        closed_date = None
        if action.closed_at:
            closed_date = (
                action.closed_at.astimezone(REPORT_TIMEZONE).date()
                if action.closed_at.tzinfo
                else action.closed_at.date()
            )
        closure_text = action.closure_evidence or action.remarks or "-"
        if action.closed_by:
            closure_text = f"{action.closed_by.name}: {closure_text}"
        result.append(
            ActionPdfRow(
                action_number=action.action_number,
                date_raised=action.date_raised,
                issue_observation=action.issue_observation,
                corrective_action=action.corrective_action,
                responsible_name=(
                    action.responsible_user.name if action.responsible_user else "Unassigned"
                ),
                deadline=action.deadline,
                status=action.status,
                closed_date=closed_date,
                closure_text=closure_text,
            )
        )
    return result


def _get_monthly_management_note(
    db: Session, *, date_from: date, date_to: date
) -> str | None:
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
    review = db.scalar(
        select(ProductionMonthlyReview).where(
            ProductionMonthlyReview.year == date_from.year,
            ProductionMonthlyReview.month == date_from.month,
        )
    )
    return review.management_summary if review else None


def _make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=29,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=3,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=TEAL,
            spaceAfter=3,
        ),
        "company": ParagraphStyle(
            "CompanyCredit",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=MUTED,
            spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=NAVY,
            spaceBefore=6,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "subsection": ParagraphStyle(
            "SubsectionHeading",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=TEAL,
            spaceBefore=6,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "BodySmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=INK,
            spaceAfter=3,
        ),
        "muted": ParagraphStyle(
            "MutedSmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.2,
            leading=9.5,
            textColor=MUTED,
            spaceAfter=3,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.8,
            leading=8.2,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=INK,
        ),
        "table_cell_center": ParagraphStyle(
            "TableCellCenter",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=INK,
            alignment=TA_CENTER,
        ),
        "card_label": ParagraphStyle(
            "CardLabel",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "card_value": ParagraphStyle(
            "CardValue",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=21,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
        "note": ParagraphStyle(
            "NoteBox",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=INK,
        ),
    }


def _table_style(*, header_rows: int = 1, compact: bool = False) -> TableStyle:
    padding = 3 if compact else 4
    commands = [
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]
    if header_rows < 2:
        commands.append(("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [WHITE, PALE]))
    return TableStyle(commands)


def _header_row(labels: list[str], styles: dict[str, ParagraphStyle]) -> list[Paragraph]:
    return [_paragraph(label, styles["table_header"]) for label in labels]


def _summary_table(
    rows: list[ProductionReportMetric],
    styles: dict[str, ParagraphStyle],
    *,
    available_width: float,
    mode: str,
) -> Table:
    if mode == "output":
        labels = [
            "Unit",
            "Entries",
            "Planned qty",
            "Actual qty",
            "Plan achievement",
            "Production hrs",
            "Downtime hrs",
            "Downtime %",
        ]
        data = [_header_row(labels, styles)]
        for metric in rows:
            data.append(
                [
                    _paragraph(metric.unit_of_measure, styles["table_cell_center"]),
                    _paragraph(str(metric.entries_count), styles["table_cell_center"]),
                    _paragraph(
                        _format_number(metric.planned_quantity), styles["table_cell_center"]
                    ),
                    _paragraph(_format_number(metric.actual_quantity), styles["table_cell_center"]),
                    _paragraph(
                        _format_percent(metric.plan_achievement_percent),
                        styles["table_cell_center"],
                    ),
                    _paragraph(
                        _format_number(metric.production_hours), styles["table_cell_center"]
                    ),
                    _paragraph(_format_number(metric.downtime_hours), styles["table_cell_center"]),
                    _paragraph(
                        _format_percent(metric.downtime_percent), styles["table_cell_center"]
                    ),
                ]
            )
        widths = [0.07, 0.08, 0.13, 0.13, 0.16, 0.14, 0.14, 0.15]
    else:
        labels = [
            "Unit",
            "Accepted (first pass)",
            "First-pass non-acceptance",
            "First-pass yield",
            "Non-acceptance rate",
            "Rework sent",
            "Rework rate",
        ]
        data = [_header_row(labels, styles)]
        for metric in rows:
            data.append(
                [
                    _paragraph(metric.unit_of_measure, styles["table_cell_center"]),
                    _paragraph(
                        _format_number(metric.accepted_first_pass_quantity),
                        styles["table_cell_center"],
                    ),
                    _paragraph(
                        _format_number(metric.first_pass_non_acceptance_quantity),
                        styles["table_cell_center"],
                    ),
                    _paragraph(
                        _format_percent(metric.first_pass_yield_percent),
                        styles["table_cell_center"],
                    ),
                    _paragraph(
                        _format_percent(metric.first_pass_non_acceptance_rate_percent),
                        styles["table_cell_center"],
                    ),
                    _paragraph(
                        _format_number(metric.rework_sent_quantity),
                        styles["table_cell_center"],
                    ),
                    _paragraph(
                        _format_percent(metric.rework_rate_percent),
                        styles["table_cell_center"],
                    ),
                ]
            )
        widths = [0.08, 0.16, 0.19, 0.14, 0.14, 0.14, 0.15]
    table = Table(
        data,
        colWidths=[available_width * weight for weight in widths],
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(_table_style(compact=True))
    return table


def _metric_dimension_table(
    title: str,
    rows: list[ProductionReportDimensionMetric],
    styles: dict[str, ParagraphStyle],
    available_width: float,
) -> list[object]:
    story: list[object] = [Paragraph(escape(title), styles["subsection"])]
    if not rows:
        story.append(
            _paragraph("No records in this breakdown for the selected filters.", styles["muted"])
        )
        return story

    labels = [
        "Line / product",
        "Unit",
        "Entries",
        "Planned",
        "Actual",
        "Plan ach. %",
        "FPY %",
        "Rework %",
        "Downtime %",
    ]
    data = [_header_row(labels, styles)]
    for row in rows:
        data.append(
            [
                _paragraph(row.dimension_value, styles["table_cell"]),
                _paragraph(row.unit_of_measure, styles["table_cell_center"]),
                _paragraph(str(row.entries_count), styles["table_cell_center"]),
                _paragraph(_format_number(row.planned_quantity), styles["table_cell_center"]),
                _paragraph(_format_number(row.actual_quantity), styles["table_cell_center"]),
                _paragraph(
                    _format_percent(row.plan_achievement_percent), styles["table_cell_center"]
                ),
                _paragraph(
                    _format_percent(row.first_pass_yield_percent), styles["table_cell_center"]
                ),
                _paragraph(_format_percent(row.rework_rate_percent), styles["table_cell_center"]),
                _paragraph(_format_percent(row.downtime_percent), styles["table_cell_center"]),
            ]
        )
    weights = [0.22, 0.08, 0.08, 0.11, 0.11, 0.11, 0.10, 0.10, 0.09]
    table = LongTable(
        data,
        colWidths=[available_width * weight for weight in weights],
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(_table_style(compact=True))
    story.append(table)
    story.append(Spacer(1, 5))
    return story


def _action_table(
    actions: list[ActionPdfRow],
    styles: dict[str, ParagraphStyle],
    available_width: float,
) -> LongTable | None:
    if not actions:
        return None
    data = [
        _header_row(
            [
                "Action",
                "Raised",
                "Issue and corrective action",
                "Responsible",
                "Deadline",
                "Status",
                "Closed",
                "Closure evidence / note",
            ],
            styles,
        )
    ]
    status_colors = {
        "OPEN": RED,
        "IN_PROGRESS": BLUE,
        "ON_HOLD": AMBER,
        "CLOSED": GREEN,
    }
    for item in actions:
        status = item.status.upper()
        status_color = status_colors.get(status, INK)
        action_detail = (
            f"<b>Issue:</b> {escape(_safe_text(item.issue_observation))}<br/>"
            f"<b>Corrective action:</b> {escape(_safe_text(item.corrective_action))}"
        )
        closure = item.closure_text
        if item.closed_date:
            closure = f"Closed {_format_date(item.closed_date)}<br/>{closure}"
        data.append(
            [
                _paragraph(item.action_number, styles["table_cell_center"]),
                _paragraph(_format_date(item.date_raised), styles["table_cell_center"]),
                _paragraph(action_detail, styles["table_cell"], allow_markup=True),
                _paragraph(item.responsible_name, styles["table_cell"]),
                _paragraph(_format_date(item.deadline), styles["table_cell_center"]),
                Paragraph(
                    (
                        f'<font color="{status_color.hexval()}"><b>'
                        f'{escape(_safe_text(status.replace("_", " ")))}</b></font>'
                    ),
                    styles["table_cell_center"],
                ),
                _paragraph(_format_date(item.closed_date), styles["table_cell_center"]),
                _paragraph(closure, styles["table_cell"]),
            ]
        )
    weights = [0.075, 0.08, 0.29, 0.105, 0.085, 0.095, 0.08, 0.19]
    table = LongTable(
        data,
        colWidths=[available_width * weight for weight in weights],
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(_table_style(compact=True))
    return table


def _card_table(
    cards: list[tuple[str, str]],
    styles: dict[str, ParagraphStyle],
    available_width: float,
) -> Table:
    data = [[_paragraph(label, styles["card_label"]) for label, _ in cards]]
    data.append([_paragraph(value, styles["card_value"]) for _, value in cards])
    table = Table(
        data,
        colWidths=[available_width / len(cards)] * len(cards),
        rowHeights=[19, 31],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.6, GRID),
                ("INNERGRID", (0, 0), (-1, -1), 0.45, GRID),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _management_highlights(
    report: ProductionReportRead,
    styles: dict[str, ParagraphStyle],
    management_note: str | None,
) -> list[object]:
    story: list[object] = [Paragraph("Management highlights", styles["section"])]
    if not report.totals_by_unit:
        story.append(
            _paragraph(
                "No production records matched the selected reporting period and filters. "
                "Review the date range and filters before drawing operational conclusions.",
                styles["body"],
            )
        )
    else:
        for metric in report.totals_by_unit:
            summary = (
                f"<b>{escape(_safe_text(metric.unit_of_measure))}:</b> "
                f"{_format_number(metric.actual_quantity)} actual against "
                f"{_format_number(metric.planned_quantity)} planned "
                f"({_format_percent(metric.plan_achievement_percent)} plan achievement); "
                f"first-pass yield {_format_percent(metric.first_pass_yield_percent)}, "
                f"rework rate {_format_percent(metric.rework_rate_percent)}, "
                f"downtime {_format_percent(metric.downtime_percent)}."
            )
            story.append(Paragraph(summary, styles["body"]))
    if report.actions.current_overdue_actions:
        story.append(
            _paragraph(
                f"Management attention: {report.actions.current_overdue_actions} production "
                "action(s) are currently overdue.",
                styles["body"],
            )
        )
    if report.inconsistent_quality_record_count:
        story.append(
            _paragraph(
                f"Data quality: {report.inconsistent_quality_record_count} production record(s) "
                "have accepted plus rework quantities greater than actual output. "
                "Review these records.",
                styles["body"],
            )
        )
    if management_note:
        story.extend(
            [
                Paragraph("Saved monthly management review", styles["subsection"]),
                _paragraph(management_note, styles["body"]),
            ]
        )
    return story


def _draw_page(canvas: Canvas, document) -> None:
    canvas.saveState()
    page_width, page_height = PAGE_SIZE
    canvas.setFillColor(NAVY)
    canvas.rect(0, page_height - 13 * mm, page_width, 13 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(14 * mm, page_height - 8.2 * mm, "MIS  |  PRODUCTION MANAGEMENT REPORT")
    canvas.setFont("Helvetica", 7.2)
    canvas.drawRightString(
        page_width - 14 * mm,
        page_height - 8.2 * mm,
        "JES ELECTRONIC SYSTEMS PVT LTD",
    )
    canvas.setStrokeColor(GRID)
    canvas.setLineWidth(0.5)
    canvas.line(14 * mm, 12 * mm, page_width - 14 * mm, 12 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 6.8)
    canvas.drawString(
        14 * mm,
        7.5 * mm,
        "JES Electronic Systems Pvt Ltd | Internal management report",
    )
    canvas.drawRightString(page_width - 14 * mm, 7.5 * mm, f"Page {document.page}")
    canvas.restoreState()


def render_production_pdf(
    report: ProductionReportRead,
    *,
    actor_name: str,
    generated_at: datetime,
    filter_summary: str,
    actions: list[ActionPdfRow],
    management_note: str | None = None,
) -> bytes:
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=PAGE_SIZE,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="MIS Production Management Report",
        author="JES Electronic Systems Pvt Ltd",
        subject=(
            f"Production report from {report.date_from.isoformat()} "
            f"to {report.date_to.isoformat()}"
        ),
    )
    styles = _make_styles()
    story: list[object] = []
    available_width = PAGE_SIZE[0] - 28 * mm

    # Page 1: executive summary and unit-separated KPI tables.
    story.extend(
        [
            Spacer(1, 3 * mm),
            Paragraph("Production Management Report", styles["title"]),
            Paragraph("Management Information System", styles["subtitle"]),
            Paragraph(
                "Designed, developed and managed by JES Electronic Systems Pvt Ltd",
                styles["company"],
            ),
        ]
    )
    metadata = [
        [
            _paragraph("REPORTING PERIOD", styles["table_header"]),
            _paragraph("PREPARED BY", styles["table_header"]),
            _paragraph("GENERATED", styles["table_header"]),
            _paragraph("TREND", styles["table_header"]),
        ],
        [
            _paragraph(
                f"{_format_date(report.date_from)} to {_format_date(report.date_to)} (inclusive)",
                styles["table_cell_center"],
            ),
            _paragraph(actor_name, styles["table_cell_center"]),
            _paragraph(
                generated_at.strftime("%d %b %Y, %I:%M %p IST"),
                styles["table_cell_center"],
            ),
            _paragraph(
                "Daily" if report.granularity == "day" else "Monthly",
                styles["table_cell_center"],
            ),
        ],
    ]
    meta_table = Table(
        metadata,
        colWidths=[available_width * factor for factor in (0.34, 0.20, 0.26, 0.20)],
        rowHeights=[17, 25],
        hAlign="LEFT",
    )
    meta_table.setStyle(_table_style(compact=True))
    story.extend([meta_table, Spacer(1, 5)])

    filter_table = Table(
        [[_paragraph("APPLIED FILTERS", styles["table_header"])],
         [_paragraph(filter_summary, styles["note"]) ]],
        colWidths=[available_width],
        hAlign="LEFT",
    )
    filter_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TEAL),
                ("BACKGROUND", (0, 1), (-1, -1), TEAL_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, GRID),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend([filter_table, Spacer(1, 7)])

    record_count = sum(metric.entries_count for metric in report.totals_by_unit)
    cards = [
        ("PRODUCTION ENTRIES", f"{record_count:,}"),
        ("UNIT GROUPS", str(len(report.totals_by_unit))),
        ("CURRENTLY OPEN ACTIONS", str(report.actions.current_open_actions)),
        ("CURRENTLY OVERDUE", str(report.actions.current_overdue_actions)),
    ]
    story.extend([_card_table(cards, styles, available_width), Spacer(1, 6)])

    story.append(Paragraph("Production output by unit", styles["section"]))
    if report.totals_by_unit:
        story.append(
            _summary_table(
                report.totals_by_unit,
                styles,
                available_width=available_width,
                mode="output",
            )
        )
        story.append(Spacer(1, 5))
        story.append(
            _summary_table(
                report.totals_by_unit,
                styles,
                available_width=available_width,
                mode="quality",
            )
        )
    else:
        story.append(
            _paragraph("No production records match the selected filters.", styles["body"])
        )
    story.extend(_management_highlights(report, styles, management_note))
    story.append(
        _paragraph(
            "Important: quantities are reported separately by unit of measure. Values such as "
            "kg and pcs are not combined. First-pass non-acceptance is not the same as final "
            "scrap or rejection.",
            styles["muted"],
        )
    )

    # Page 2: unit-specific trends. Every chart is kept separate by unit.
    story.extend([PageBreak(), Paragraph("Production trends", styles["title"])])
    story.append(
        _paragraph(
            f"{report.granularity.title()} trend for the selected period. Planned and actual "
            "quantities are compared only within the same unit of measure.",
            styles["muted"],
        )
    )
    if not report.totals_by_unit:
        story.append(
            _paragraph("No production trend is available for this selection.", styles["body"])
        )
    else:
        for metric in report.totals_by_unit:
            unit_points = [
                point for point in report.trend if point.unit_of_measure == metric.unit_of_measure
            ]
            story.append(
                KeepTogether(
                    [
                        UnitTrendChart(
                            unit=metric.unit_of_measure,
                            points=unit_points,
                            width=available_width,
                        ),
                        Spacer(1, 7),
                    ]
                )
            )

    # Page 3: line and model breakdowns.
    story.extend(
        [
            PageBreak(),
            Paragraph("Production line and product analysis", styles["title"]),
            _paragraph(
                "Each row is grouped by both dimension and unit. Compare like-for-like units; "
                "do not compare raw quantities across kg, pcs or other measures.",
                styles["muted"],
            ),
        ]
    )
    story.extend(
        _metric_dimension_table(
            "Production-line performance",
            report.by_line,
            styles,
            available_width,
        )
    )
    story.extend(
        _metric_dimension_table(
            "Product / model performance",
            report.by_product,
            styles,
            available_width,
        )
    )

    # Page 4+: action tracker. LongTable repeats the header on additional pages.
    story.extend(
        [
            PageBreak(),
            Paragraph("Corrective action tracker", styles["title"]),
            _paragraph(
                "The table includes actions raised in the selected period, unresolved actions "
                "carried into the period, and actions closed during the period.",
                styles["muted"],
            ),
        ]
    )
    action_cards = [
        ("CREATED IN PERIOD", str(report.actions.actions_created_in_period)),
        ("CURRENTLY OPEN", str(report.actions.current_open_actions)),
        ("CURRENTLY OVERDUE", str(report.actions.current_overdue_actions)),
        ("CLOSED IN PERIOD", str(report.actions.closed_actions_in_period)),
    ]
    story.extend([_card_table(action_cards, styles, available_width), Spacer(1, 7)])
    action_table = _action_table(actions, styles, available_width)
    if action_table is None:
        story.append(
            _paragraph("No corrective actions are in scope for this selection.", styles["body"])
        )
    else:
        story.append(action_table)
    story.extend(
        [
            Spacer(1, 6),
            _paragraph(report.actions.scope_note, styles["muted"]),
        ]
    )

    # Definitions and scope notes are kept on a dedicated final section.
    story.extend(
        [
            PageBreak(),
            Paragraph("KPI definitions and reporting notes", styles["title"]),
        ]
    )
    definitions = [
        ["Plan achievement", "Actual quantity / planned quantity x 100"],
        ["First-pass yield (FPY)", "Accepted quantity at first inspection / actual quantity x 100"],
        [
            "First-pass non-acceptance rate",
            "(Actual quantity - first-pass accepted quantity) / actual quantity x 100",
        ],
        [
            "First-pass non-acceptance quantity",
            "Actual quantity - accepted quantity at first inspection. This can include rework "
            "and other pending dispositions.",
        ],
        ["Rework rate", "Quantity sent for rework / actual quantity x 100"],
        ["Downtime percentage", "Downtime hours / (production hours + downtime hours) x 100"],
        [
            "Final scrap / rejection",
            "Not calculated. The current MIS production record does not capture "
            "post-rework disposition.",
        ],
    ]
    definition_data = [
        [
            _paragraph("KPI", styles["table_header"]),
            _paragraph("Definition", styles["table_header"]),
        ]
    ]
    definition_data.extend(
        [
            _paragraph(name, styles["table_cell"]),
            _paragraph(definition, styles["table_cell"]),
        ]
        for name, definition in definitions
    )
    definition_table = Table(
        definition_data,
        colWidths=[available_width * 0.25, available_width * 0.75],
        repeatRows=1,
        hAlign="LEFT",
    )
    definition_table.setStyle(_table_style(compact=False))
    story.append(definition_table)
    story.extend(
        [
            Spacer(1, 8),
            Paragraph("Filter and action scope", styles["section"]),
            _paragraph(
                "Date range is inclusive. Production-line, product/model, project and unit "
                "filters apply to production metrics. The optional project filter also applies "
                "to actions; line, product/model and unit filters do not filter actions.",
                styles["body"],
            ),
            _paragraph(
                "Open and overdue action counts reflect current status at report generation, "
                "not the historical status at the end of the reporting period. Closed-in-period "
                "counts use the closure timestamp within the selected dates.",
                styles["body"],
            ),
            _paragraph(
                "Trend granularity is daily for ranges of 62 days or fewer and monthly for "
                "longer ranges. Targets shown in the original management workbook are "
                "illustrative unless formally approved by management.",
                styles["body"],
            ),
            Paragraph("Quality definition", styles["section"]),
            _paragraph(report.quality_definition, styles["body"]),
        ]
    )

    document.build(story, onFirstPage=_draw_page, onLaterPages=_draw_page)
    return output.getvalue()


def build_production_pdf_export(
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
    report = get_production_report(
        db,
        date_from=date_from,
        date_to=date_to,
        production_line=production_line,
        product_model=product_model,
        project_id=project_id,
        unit_of_measure=unit_of_measure,
    )
    actions = _action_rows(
        _get_actions(
            db,
            date_from=date_from,
            date_to=date_to,
            project_id=project_id,
        )
    )
    project_name = (
        db.scalar(select(Project.name).where(Project.id == project_id))
        if project_id
        else None
    )
    management_note = _get_monthly_management_note(
        db,
        date_from=date_from,
        date_to=date_to,
    )
    filters = _filter_description(
        production_line=production_line,
        product_model=product_model,
        project_name=project_name,
        project_id=project_id,
        unit_of_measure=unit_of_measure,
    )
    generated_at = datetime.now(REPORT_TIMEZONE)
    content = render_production_pdf(
        report,
        actor_name=actor.name,
        generated_at=generated_at,
        filter_summary=filters,
        actions=actions,
        management_note=management_note,
    )
    filename = (
        f"MIS_Production_Management_Report_{date_from.isoformat()}_to_{date_to.isoformat()}.pdf"
    )
    return content, filename
