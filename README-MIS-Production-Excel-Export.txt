MIS PRODUCTION EXCEL EXPORT
===========================

This patch adds an authenticated Excel export to Reports > Production. It uses the
uploaded JESES Monthly Production MIS template and preserves its five worksheets:

1. Management Summary
2. Production Log
3. Action Tracker
4. KPI Definitions
5. Instructions

The workbook is populated from the same inclusive date range and filters currently
applied on the Production Analytics page.

IMPORTANT REPORTING SEMANTICS
-----------------------------
- Production Line, Unit of Measure and Project are added to the Production Log.
- Quantities are summarized separately for each unit. kg and pcs are never combined.
- Accepted Quantity means accepted at first inspection.
- Rework Quantity means the quantity sent for rework.
- Actual minus first-pass accepted is labelled First-pass non-acceptance, not final
  rejection or scrap. The current MIS model does not store post-rework disposition,
  so final scrap/rejection is not calculated.
- The Action Tracker includes actions created in the selected period, unresolved
  actions carried into the period, and actions closed during the period. Project filter
  applies to actions; line/model/unit filters apply to production rows only.
- A saved management review is included only when the export covers a complete calendar
  month. Prepared By is the user requesting the export.

APPLY
-----
Extract this ZIP into the repository root with the backend/frontend folders merged.

Add this dependency to the existing backend/requirements.txt (append it; do not replace
the existing dependency list):

  openpyxl==3.1.5

Then install it from backend/:

  .\.venv\Scripts\Activate.ps1
  pip install openpyxl==3.1.5

No database migration is required.

VALIDATE BACKEND
----------------
From backend/ (keep TEST_DATABASE_URL pointed at the disposable MIS_test database):

  ruff check app tests scripts
  python -m compileall -q app scripts tests
  pytest -q tests/test_production_excel_export.py

VALIDATE FRONTEND
-----------------
From frontend/:

  npm run lint
  npm run typecheck
  npm run build

RUN
---
Restart the backend and frontend. Open Reports > Production, set the reporting period
and any filters, then click Export to Excel. The downloaded filename includes the date
range. The export endpoint is:

  GET /api/v1/production/reports/export.xlsx

Query parameters match the Production Reports summary endpoint:
  date_from, date_to, production_line, product_model, project_id, unit_of_measure

SAFETY
------
The export is read-only and creates no database records. It includes existing production
and action data only. The original template is stored at:
  backend/app/templates/JESES_Monthly_Production_MIS_Template.xlsx
