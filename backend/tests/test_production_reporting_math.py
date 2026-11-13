from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.production import ProductionEntryCreate
from app.services.production_reporting_service import calculate_quality_metrics


def test_quality_metrics_keep_rework_separate_from_first_pass_non_acceptance():
    metrics = calculate_quality_metrics(
        actual_quantity=Decimal("90"),
        accepted_first_pass_quantity=Decimal("87"),
        rework_sent_quantity=Decimal("2"),
    )

    assert metrics["first_pass_non_acceptance_quantity"] == Decimal("3")
    assert metrics["first_pass_yield_percent"] == pytest.approx(96.6666666667)
    assert metrics["rework_rate_percent"] == pytest.approx(2.2222222222)
    assert metrics["first_pass_non_acceptance_rate_percent"] == pytest.approx(3.3333333333)
    assert "scrap_quantity" not in metrics


def test_quality_rates_are_none_when_actual_quantity_is_zero():
    metrics = calculate_quality_metrics(
        actual_quantity=Decimal("0"),
        accepted_first_pass_quantity=Decimal("0"),
        rework_sent_quantity=Decimal("0"),
    )

    assert metrics["first_pass_yield_percent"] is None
    assert metrics["rework_rate_percent"] is None
    assert metrics["first_pass_non_acceptance_rate_percent"] is None


def test_entry_schema_rejects_overlapping_first_pass_acceptance_and_rework():
    payload = {
        "production_date": "2026-11-02",
        "production_line": "Line A",
        "product_model": "Model X",
        "process_stage": "Assembly",
        "unit_of_measure": "pcs",
        "planned_quantity": 100,
        "actual_quantity": 90,
        "accepted_quantity": 89,
        "rework_quantity": 2,
    }
    with pytest.raises(ValidationError):
        ProductionEntryCreate.model_validate(payload)
