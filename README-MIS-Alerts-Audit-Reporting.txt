MIS ALERTS & AUDIT REPORTING
============================

BRANCH
------
Apply on: feature/mis-reporting-and-analytics
Run the integration script from the MIS repository root.

WHAT THIS ADDS
--------------
- New report page: /reports/alerts-audit
- Alerts report API: GET /api/v1/reports/alerts-audit/alerts
- Audit report API: GET /api/v1/reports/alerts-audit/audit
- Alerts report: total/read/unread, standard/escalated, project distribution,
  alert trend, and recent alert details.
- Audit report: event totals, distinct actors/entity references, action/entity
  breakdowns, actor activity, event trend, and recent event metadata.
- Alerts filters: date range, project, alert type, and read state.
- Audit filters: date range, actor, action, and entity.

ACCESS CONTROL AND DATA DEFINITIONS
-----------------------------------
1. Alerts reporting is strictly scoped to the authenticated user's own alerts. Aggregate
   counts and project breakdowns use the same recipient scope; no other user's alert
   records are exposed.
2. The Alerts date range applies to Alert.alert_date, which is the alert's business date.
   Read/unread is current state, not a historical read-state snapshot. Trend buckets use
   alert creation timestamps.
3. Audit report endpoints are Super Admin only, matching the existing Audit Trail route.
4. Audit report rows deliberately include audit metadata only. They do not return before/after
   JSON payloads. Use the existing Audit Trail page for authorized record-level inspection.
5. Both reports accept inclusive date ranges up to 366 days. Daily trend is used for ranges
   up to 63 calendar days; longer ranges use monthly buckets.
6. Full matching counts and breakdowns are calculated from the complete result cohort.
   Detailed rows are capped to the latest 250 alerts and 300 audit events, respectively;
   the API scope note reports when a cap is applied.
7. No schema or database migration is required. No new dependency is required.

APPLY
-----
1. Stop backend and frontend development servers.
2. Extract MIS-Alerts-Audit-Reporting-Patch.zip into the repository root.
3. From the repository root run:

   python tools/apply_alerts_audit_reporting_patch.py

The script checks the current branch and exact integration anchors before editing. It backs
up backend/app/api/router.py and frontend/src/components/app-shell.tsx into a temporary folder.
It then copies the new backend and frontend files and adds the route and sidebar entry.
It does not stage, commit or push anything.

VALIDATE BACKEND
----------------
From backend/ with .venv active:

   ruff check app tests scripts
   python -m compileall -q app scripts tests

Verify TEST_DATABASE_URL is set to the disposable MIS_test database before running tests.
The test fixture drops and recreates the configured test database.

   pytest -q tests/test_alerts_audit_reporting.py
   pytest -q

VALIDATE FRONTEND
-----------------
From frontend/:

   npm run lint
   npm run typecheck
   npm run build

MANUAL TESTS
------------
- Open /reports/alerts-audit as a regular USER and confirm only the Alerts tab appears.
- Confirm a regular USER sees only their own alerts in the report.
- Sign in as Super Admin and confirm both Alerts and Audit tabs appear.
- Check date range, project, alert type and read-state filters on Alerts.
- Check date range, actor, action and entity filters on Audit.
- Confirm a non-Super Admin receives HTTP 403 from the audit report endpoint.
- Confirm report notes explain recipient scope, current read state and audit payload omission.

No commit or push is performed by this patch.
