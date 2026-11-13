MIS OPERATIONS REPORTING — PROJECTS, INVENTORY AND PURCHASES
============================================================

BRANCH
------
Apply on: feature/mis-reporting-and-analytics
Apply from the repository root in VS Code PowerShell.

WHAT THIS ADDS
--------------
- An authenticated API endpoint:
    GET /api/v1/operations/reports/summary
- A new sidebar entry and page:
    Reports > Operations reports
    http://localhost:3000/reports/operations
- Three report sections: Projects, Inventory, Purchase Requests.
- Shared date range, project selector, project status/type/priority filters,
  and purchase status filter.
- Project status/priority breakdowns, current progress, overdue count, progress
  updates, and a project-creation trend.
- Current inventory snapshot by SKU, with active-project BOM required, allocated,
  and shortage quantities.
- Purchase status counts, request details, quantities grouped per SKU, and average
  approval/delivery durations where timestamps exist.
- API tests covering summary data, filters, user purchase visibility, and date validation.

IMPORTANT DATA DEFINITIONS / LIMITATIONS
---------------------------------------
1. Projects are selected by created_at inside the inclusive date range. Status,
   priority, progress and overdue values are current values, not historical snapshots.
   A historical status/progress ledger is not present in the existing Project model.
2. The overdue count is current as of the report run date, among projects created in
   the selected range, whose end_date has passed and whose current status is not COMPLETED.
3. Inventory is a current stock snapshot. The existing model has no inventory movement
   ledger, so the date range cannot reconstruct historical stock balances.
4. Active-project BOM demand uses active project statuses only. Quantities are displayed
   per SKU. Do not sum quantities across different SKUs because the InventoryItem model
   does not store a unit of measure.
5. Purchase requests are selected by created_at. Their status is the current status;
   historical state transitions are not reconstructed. Average approval/delivery times
   use the selected request cohort that has the corresponding timestamp.
6. The PurchaseRequest model has no unit-price or amount field, so financial spend/value
   cannot be calculated. Requested quantities are grouped by SKU and never combined across
   different items.
7. Purchase request visibility follows the existing API rule: regular USER accounts see
   only requests they raised or requests belonging to projects where they are members.
8. Project and inventory reporting follow the existing app's authenticated read visibility.
9. Project detail rows are capped at 250; purchase detail and per-SKU breakdown rows are
   capped at the latest 500 requests. Summary counts and status breakdowns use the full
   matching cohort.
10. No database migration is required.

APPLY
-----
1. Stop backend and frontend development servers.
2. Extract MIS-Operations-Reporting-Patch.zip into the repository root.
3. Run:

   python tools/apply_operations_reporting_patch.py

The script verifies the expected branch and integration anchors before changing files.
It backs up the two existing integration files into a temporary folder, then copies the
new route, service, schema, test and frontend files. It does not stage or commit anything.

VALIDATE BACKEND
----------------
From backend/ with .venv active:

   ruff check app tests scripts
   python -m compileall -q app scripts tests

Verify TEST_DATABASE_URL points to the disposable MIS_test database before running tests.
The test fixture drops and recreates the configured test database.

   pytest -q tests/test_operations_reporting.py
   pytest -q

VALIDATE FRONTEND
-----------------
From frontend/:

   npm run lint
   npm run typecheck
   npm run build

MANUAL TESTS
------------
- Open /reports/operations.
- Check the Projects, Inventory and Purchases tabs.
- Test a 7-day and a 30-day period.
- Filter by a project, project status, type, priority and purchase status.
- Verify normal USER access only displays purchase requests raised by that user or
  belonging to their projects.
- Compare inventory available quantities against the Inventory page, and BOM shortage
  figures against the relevant project details.

No commit or push is performed by the patch script.
