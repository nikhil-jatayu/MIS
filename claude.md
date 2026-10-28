# ROLE

You are a senior full-stack engineer. Build v1 of an R&D and Production Management Information System (MIS) for JES Electronics Systems Pvt Ltd. Keep it simple, clean and maintainable. No features beyond this spec. State assumptions briefly; ask me only if something blocks you.

# STACK

- Backend: FastAPI, SQLAlchemy , Alembic, Pydantic v2, PostgreSQL (DATABASE_URL already in .env; the database already exists).
- Frontend: Next.js (App Router, TypeScript), Tailwind CSS.
- Auth: JWT (access token), bcrypt password hashing, role-based route guards on backend and frontend.
- Background jobs: APScheduler inside the FastAPI app.
- Pin dependency versions. Config via .env only; provide .env.example.

# ROLES

- SUPER_ADMIN: full config, global inventory, user management, sets Time Counter thresholds; receives top-level escalated alerts.
- ADMIN: creates projects, sets deadlines, assigns Users, approves purchase order requests; receives escalation alerts.
- USER: views assigned projects, logs progress, requests unavailable inventory; receives standard deadline alerts.

# SEED DATA (on first startup / seed script, idempotent)

- Super Admins: ashmant@jatayues.com (password ashmant@123) and ratna@jatayues.com (password ratna@123).
- Hash passwords. Set `must_change_password=true` so the first login forces a new password.
- Other users are created later by the Super Admin through the UI (name, email/Office ID, role, temporary password).

# AUTH AND LAYOUT

- Login with Office People ID (use email as the ID unless an Office ID field is added) + password. After login, redirect to the role-specific dashboard.
- Header: company name "JES Electronics Systems Pvt Ltd", logo placeholder (single file to replace), navigation.
- Persistent footer on every page: "Made and managed by JES Electronics Systems Pvt Ltd".

# DATA MODEL (v1)

- users: id, name, email, role, password_hash, is_active, must_change_password
- projects: id, name, description, type (R&D|PRODUCTION), status, priority (LOW|MEDIUM|HIGH|CRITICAL), start_date, end_date, created_by, status_changed_at
- project_members: project_id, user_id, role_in_project (DEVELOPER|PRODUCER|TESTER)
- inventory_items: id, name, sku, quantity_available
- project_bom: project_id, item_id, quantity_required, quantity_allocated
- purchase_requests: id, project_id, item_id, quantity, requested_by, status (PENDING|APPROVED|REJECTED|ORDERED|DELIVERED), reason, approved_by
- progress_logs: id, project_id, user_id, note, progress_percent, created_at (append-only)
- attachments: id, project_id, filename, stored_path, uploaded_by (local disk storage, configurable folder)
- alerts: id, user_id, project_id, type (STANDARD|ESCALATED), message, is_read, created_at
- audit_logs: id, actor_id, action, entity, entity_id, before, after, created_at (append-only: no update/delete endpoints)
- settings: key/value (time counter thresholds)

# PROJECT STATUS FLOW

PENDING_INVENTORY  READY_FOR_PRODUCTION  IN_PRODUCTION  IN_TESTING  COMPLETED. Also AWAITING_DELIVERY (production paused, with a delay reason).

# FEATURES

1. Project dashboard: list/cards of all projects with type, status, priority, assigned personnel, start/end dates, progress %, and inventory checklist. Filter and sort by type, status, priority, deadline. Users see all projects but only perform actions in the assigned project; Admins and Super Admins see all.
2. Order intake (Admin): create project with type R&D or Production, BOM, deadline, priority, and assigned people.
3. Inventory check on project creation: compare BOM against inventory.
   - All available: allocate items, status = READY_FOR_PRODUCTION.
   - Partial/unavailable: flag shortages; one-click "Create Purchase Request" per shortage (User or Admin).
   - Admin approves/rejects requests. When status is ORDERED, project goes AWAITING_DELIVERY and records the delay reason. On DELIVERED, re-check and allocate automatically.
4. Progress logging: assigned Users append notes and progress %. History is read-only.
5. Production and testing: Admin moves project to IN_PRODUCTION when ready, then assigns a Tester (QA). The Tester marks pass/fail with a note, then Admin signs off COMPLETED.
6. Smart alerts (Time Counter):
   - Super Admin configures `safe_threshold_days` and `escalation_threshold_days`, and a deadline-reminder window, in the UI.
   - Scheduler runs daily (interval configurable). For each active project, pending days = days since last status change or progress log.
   - Within the safe threshold or the approaching-deadline window: STANDARD alert to assigned Users only.
   - Beyond the escalation threshold: ESCALATED alert to Admins; severely delayed (configurable multiplier) also to Super Admins. Bypass Users.
   - De-duplicate: at most one alert per project per type per day.
   - In-app notification bell with unread count. No email/SMS in v1.
7. Attachments: upload and download files per project (size and type limits in config).
8. Audit trail: automatically log every create/update, inventory change, status change and deadline change. Super Admin read-only viewer with filters.
9. Super Admin pages: user management (create, deactivate, change role, reset password), inventory CRUD, threshold settings.

# NON-FUNCTIONAL

- Backend structure: app/{api,models,schemas,services,core}. Business logic in services, not in route handlers.
- Consistent error responses, input validation, pagination on list endpoints, CORS from config.
- Authorization enforced server-side on every endpoint.
- Alembic migrations for the schema; seed script separate.
- README: setup, env vars, run migrations/seed, start backend and frontend, default Super Admin login note.

# OUT OF SCOPE (v1)

Email/SMS, real-time websockets, reporting/exports, SSO, mobile app, Docker/cloud deployment, advanced charts.

# DELIVERY ORDER (stop after each section, show results, wait for my approval)

1. Project skeleton, DB models, migrations, seed, auth + role guards, layout (header/footer), login and role dashboards.
2. Users, inventory, projects, BOM and the inventory-check/purchase-request workflow.
3. Progress logs, production/testing flow, attachments.
4. Time Counter, alerts, notification bell, audit trail and viewer.
   After each section, run tests covering that whole section (API tests with pytest; a few key frontend flows) and report pass/fail. Do not test each module separately.
