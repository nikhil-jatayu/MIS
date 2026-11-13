from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.errors import UnprocessableError


def validate_report_date_range(date_from: date, date_to: date) -> None:
    """Validate inclusive report dates consistently across MIS report services."""
    if date_from > date_to:
        raise UnprocessableError(
            "The report start date must be on or before the end date",
            code="INVALID_REPORT_DATE_RANGE",
        )


def safe_percent(numerator: Decimal, denominator: Decimal) -> float | None:
    """Return a percentage, or None when its denominator is zero."""
    if denominator == 0:
        return None
    return float((numerator / denominator) * Decimal("100"))
