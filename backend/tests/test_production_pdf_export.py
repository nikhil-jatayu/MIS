from __future__ import annotations

from datetime import date

from app.models.production import ProductionEntry


def test_production_pdf_export_returns_management_report_for_selected_period(
    client, db, auth_headers, standard_users
):
    user = standard_users["super"]
    db.add_all(
        [
            ProductionEntry(
                production_date=date(2026, 11, 3),
                production_line="Assembly Line A",
                product_model="Control Unit CU-100",
                work_order_customer="DEMO-WO-PDF-001",
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
                work_order_customer="DEMO-WO-PDF-002",
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
        "/api/v1/production/reports/export.pdf",
        headers=auth_headers["super"],
        params={"date_from": "2026-11-01", "date_to": "2026-11-30"},
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/pdf")
    assert (
        "MIS_Production_Management_Report_2026-11-01_to_2026-11-30.pdf"
        in response.headers["content-disposition"]
    )
    assert response.content.startswith(b"%PDF-")
    assert response.content.rstrip().endswith(b"%%EOF")
    assert len(response.content) > 2_000
