from __future__ import annotations

from datetime import date
from io import BytesIO

from openpyxl import load_workbook

from app.models.production import ProductionEntry


def test_production_excel_export_preserves_five_sheets_and_unit_separation(
    client, db, auth_headers, standard_users
):
    user = standard_users["super"]
    db.add_all(
        [
            ProductionEntry(
                production_date=date(2026, 11, 3),
                production_line="Assembly Line A",
                product_model="Control Unit CU-100",
                work_order_customer="DEMO-WO-001",
                process_stage="Assembly",
                unit_of_measure="pcs",
                planned_quantity=100,
                actual_quantity=95,
                accepted_quantity=92,
                rework_quantity=2,
                production_hours=7,
                downtime_hours=1,
                created_by=user.id,
            ),
            ProductionEntry(
                production_date=date(2026, 11, 3),
                production_line="Finishing Line",
                product_model="Protective Coating PC-450",
                work_order_customer="DEMO-WO-002",
                process_stage="Finishing",
                unit_of_measure="kg",
                planned_quantity=50,
                actual_quantity=48,
                accepted_quantity=46,
                rework_quantity=1,
                production_hours=6,
                downtime_hours=2,
                created_by=user.id,
            ),
        ]
    )
    db.commit()

    response = client.get(
        "/api/v1/production/reports/export.xlsx",
        headers=auth_headers["super"],
        params={"date_from": "2026-11-01", "date_to": "2026-11-30"},
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "MIS_Production_Report_2026-11-01_to_2026-11-30.xlsx" in response.headers[
        "content-disposition"
    ]

    workbook = load_workbook(BytesIO(response.content), data_only=False)
    assert workbook.sheetnames == [
        "Management Summary",
        "Production Log",
        "Action Tracker",
        "KPI Definitions",
        "Instructions",
    ]
    log = workbook["Production Log"]
    assert log["R4"].value == "Production Line"
    assert log["S4"].value == "Unit of Measure"
    assert log["I4"].value == "First-pass Non-acceptance Qty"
    assert log["I5"].value.startswith("=IF(")
    assert log["U5"].value.startswith("=IFERROR(")
    assert {log[f"S{row}"].value for row in (5, 6)} == {"pcs", "kg"}

    summary = workbook["Management Summary"]
    assert summary["B9"].value in {"kg", "pcs"}
    assert summary["C9"].value in {"kg", "pcs"}
    assert summary["B15"].value.startswith("=IFERROR(")
    assert "first-pass" in workbook["KPI Definitions"]["A7"].value.lower()
    assert "final" in workbook["KPI Definitions"]["E7"].value.lower()
