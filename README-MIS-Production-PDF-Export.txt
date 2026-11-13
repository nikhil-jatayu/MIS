MIS PRODUCTION PDF MANAGEMENT REPORT
====================================

WHAT THIS PATCH ADDS
--------------------
- An authenticated PDF export endpoint:
    GET /api/v1/production/reports/export.pdf
- An "Export management PDF" button on Reports > Production.
- PDF output uses the same inclusive date range and optional filters as the
  Production Reports page and Excel export.
- A management-ready landscape PDF with:
    1. Executive summary, report metadata, active filters, unit-separated KPI tables.
    2. Planned-versus-actual trend charts, one chart per unit of measure.
    3. Production-line and product/model breakdowns.
    4. Corrective action tracker with owners, deadlines, status and closure notes.
    5. KPI definitions, data interpretation and filter/action scope notes.
- JES Electronics Systems Pvt Ltd attribution in the PDF header/footer and MIS identity.

REPORTING SEMANTICS
-------------------
- Quantities are never combined across units such as kg and pcs.
- Accepted quantity means accepted at first inspection.
- Rework quantity means units sent for rework.
- First-pass non-acceptance = actual quantity minus accepted quantity at first
  inspection. It is not final scrap or rejection.
- Final scrap/rejection is not calculated because the current production record
  does not store post-rework disposition.
- Actions include those raised in the reporting period, unresolved actions carried
  into the period, and actions closed during the period.
- Project filter applies to production and action rows. Production line, product/model
  and unit filters apply to production metrics only.
- Current open/overdue action counts reflect status at report generation, not
  historical status at the end of the selected reporting period.
- Trends remain grouped by unit; daily granularity is used for ranges up to 62 days,
  and monthly granularity for longer ranges.

DEPENDENCY
----------
Append the following pinned dependency to the existing backend/requirements.txt.
Do not replace the existing requirements file or remove the openpyxl dependency
used by the Excel export. If ReportLab is already listed, do not add a duplicate.

PowerShell, from the repository root:

    $requirements = ".\backend\requirements.txt"
    if (-not (Select-String -Path $requirements -Pattern '^reportlab==5\.1\.0$' -Quiet)) {
        Add-Content -Path $requirements -Value 'reportlab==5.1.0'
    }

Install from backend/ with the virtual environment activated:

    cd backend
    .\.venv\Scripts\Activate.ps1
    pip install reportlab==5.1.0

ReportLab 5.1.0 is available as a pure-Python wheel and supports Python 3.9 through
3.14. It is used only by the server-side PDF export service.

APPLY
-----
Stop the backend and frontend development servers first. Extract the ZIP into the
repository root, merging the backend and frontend folders. Install ReportLab before
restarting the backend because the PDF service is imported by the reports router.
This patch updates the existing production reports route and report page, and adds
one service and one integration test. It does not change the database schema.

VALIDATE BACKEND
----------------
Keep TEST_DATABASE_URL pointed at the disposable MIS_test database. The test suite
can recreate the configured test database; never point it at MIS. From backend/:

    ruff check app tests scripts
    python -m compileall -q app scripts tests
    pytest -q tests/test_production_pdf_export.py

VALIDATE FRONTEND
-----------------
From frontend/:

    npm run lint
    npm run typecheck
    npm run build

RUN
---
Restart the backend and frontend. Open Reports > Production. Select a date range and
any desired filters, then select "Export management PDF". The PDF download includes
the selected date range in its filename.

No migration is required. The endpoint is read-only and creates no database records.
