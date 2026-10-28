# JES Electronics Systems Pvt Ltd — MIS

Management Information System for the R&D and production pipeline: projects,
inventory and BOM allocation, purchase requests, progress, production/testing,
attachments, Time Counter alerts, and a complete audit trail.

- **Backend:** FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, PostgreSQL, APScheduler
- **Frontend:** Next.js 16 (App Router), TypeScript, Tailwind CSS 4, TanStack Query
- **Auth:** JWT access token in an HTTP-only cookie (Bearer fallback), bcrypt hashing
- **Roles:** `SUPER_ADMIN`, `ADMIN`, `USER`, enforced on the API and in the UI

## Repository layout

```text
.
├── backend/
│   ├── app/
│   │   ├── api/routes/      # HTTP endpoints
│   │   ├── core/            # config, security, errors, cookies, dependencies
│   │   ├── db/              # engine, sessions, declarative base
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic request/response contracts
│   │   ├── services/        # business rules and workflows
│   │   ├── main.py          # FastAPI app and lifespan hooks
│   │   └── scheduler.py     # APScheduler Time Counter job
│   ├── alembic/             # migrations
│   ├── scripts/seed.py      # idempotent seed command
│   ├── tests/               # API test suite and Playwright fixtures
│   └── var/uploads/         # local attachment storage (runtime)
├── frontend/
│   ├── src/app/             # App Router pages (public and protected)
│   ├── src/components/      # shell, UI primitives, badges
│   ├── src/lib/             # API client, auth context, types, helpers
│   ├── src/proxy.ts         # optimistic cookie route guard
│   └── tests/e2e/           # Playwright end-to-end tests
├── .env.example
└── claude.md                # original product specification
```

## Prerequisites

- Python **3.14** (the backend targets `py314`)
- PostgreSQL **15+** with a database for the app and one for tests
- Node.js **20.9+** (tested with Node 24) and npm

## Quick start

### 1. Environment

Copy `.env.example` to `.env` in the repository root and set at least:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/MIS
TEST_DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/MIS_test
JWT_SECRET_KEY=<a long random value>
CORS_ORIGINS=http://localhost:3000
```

Generate a JWT secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

The test suite drops and recreates the database named in `TEST_DATABASE_URL`, so
never point it at a real database. The PostgreSQL role needs `CREATEDB` for that
to work, or you can create `MIS_test` in advance.

### 2. Backend

```bash
cd backend
py -3.14 -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements-dev.txt
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at `http://localhost:8000`, interactive docs at
`http://localhost:8000/docs`, and the health check at `/health`.

`SEED_ON_STARTUP=true` also runs the idempotent seed during application startup.
The standalone `scripts/seed.py` command is the explicit option for deployments.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

Use the same host for the frontend and API (`localhost` in both places). The
access token is an HTTP-only cookie, so `NEXT_PUBLIC_API_URL=http://localhost:8000`
must not be mixed with `http://127.0.0.1:3000`, otherwise the browser will not
send the cookie to the API.

### 4. Default accounts

| Office People ID | Temporary password | Role |
| --- | --- | --- |
| `ashmant@jatayues.com` | `ashmant@123` | Super Admin |
| `ratna@jatayues.com` | `ratna@123` | Super Admin |

Both accounts have `must_change_password=true`; the first sign-in redirects to
the password change screen. The seed is idempotent: it creates only missing
accounts, settings rows, and never resets an existing password.

## Roles and permissions

| Capability | Super Admin | Admin | User |
| --- | :-: | :-: | :-: |
| View all projects and dashboard | ✓ | ✓ | ✓ |
| Create projects, set deadlines, assign people | ✓ | ✓ | — |
| Manage inventory | ✓ | ✓ | — |
| Raise purchase requests | ✓ | ✓ | ✓ (assigned projects) |
| Approve / reject / order / receive requests | ✓ | ✓ | — |
| Log progress | ✓ | ✓ | ✓ (assigned projects) |
| Start production, assign tester, sign off completion | ✓ | ✓ | — |
| Submit test result | ✓ | ✓ | ✓ (assigned tester) |
| Manage users and Time Counter settings | ✓ | — | — |
| View audit trail | ✓ | — | — |

## Main workflows

1. **Order intake** — an Admin creates a project with type, priority, dates,
   BOM, and team. Inventory is checked atomically on save.
2. **Inventory readiness** — a fully available BOM is allocated and the project
   moves to `READY_FOR_PRODUCTION`. Shortages keep it in `PENDING_INVENTORY`
   and expose one-click purchase requests.
3. **Procurement** — purchase requests move through `PENDING → APPROVED or
   REJECTED → ORDERED → DELIVERED`. Ordering pauses the project in
   `AWAITING_DELIVERY` with a delay reason; delivery re-checks and allocates
   stock automatically.
4. **Production and testing** — Admin starts production, assigns a tester, and
   the tester records pass/fail with a note. Admin then completes the project.
5. **Progress** — assigned users append notes and a progress percentage. The
   progress log is append-only.
6. **Time Counter** — a scheduled job evaluates pending projects against the
   configured thresholds and deadline reminder window, creating standard and
   escalated alerts for the right roles. The check can also be triggered from
   the Time Counter screen.
7. **Audit trail** — every state-changing action records actor, action, entity,
   and before/after payloads. There are no update or delete endpoints for audit
   records.

## Configuration

All backend settings come from the root `.env` (see `.env.example`). Important
values:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL SQLAlchemy URL using the `psycopg` driver |
| `TEST_DATABASE_URL` | Disposable database for the backend test suite |
| `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` | Token signing and lifetime |
| `CORS_ORIGINS` | Comma-separated exact frontend origins |
| `COOKIE_NAME`, `COOKIE_SECURE`, `COOKIE_SAMESITE` | Access-token cookie policy |
| `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB`, `ALLOWED_UPLOAD_EXTENSIONS` | Attachments |
| `SEED_ON_STARTUP` | Run the idempotent seed at application startup |
| `SCHEDULER_*` | Time Counter job enablement, interval, and timezone |
| `BCRYPT_ROUNDS` | Password hashing work factor |

Frontend settings live in `frontend/.env.local`:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
```

For HTTPS deployments set `COOKIE_SECURE=true` and restrict `CORS_ORIGINS` to
the real frontend origin. The default login throttle is held in process memory;
run a single API worker or replace it with a shared store before scaling out.

## Tests and quality checks

### Backend

```bash
cd backend
.venv\Scripts\pytest.exe -q          # Windows
# .venv/bin/pytest -q                # macOS/Linux
.venv\Scripts\ruff.exe check app tests scripts
.venv\Scripts\ruff.exe format --check app tests scripts
```

The API suite covers authentication and users, projects and inventory, progress
and testing and attachments, alerts and audit, plus full lifecycle workflow
tests (`tests/test_full_workflow.py`) that cover:

- a fully stocked BOM that is allocated on creation, refuses unnecessary
  purchase requests, and moves through production, testing, and sign-off;
- a partial/empty BOM that raises purchase requests, is approved, ordered with
  a delay reason, received, automatically allocated, retested, and completed;
- Time Counter generation, recipient selection, duplicate suppression, unread
  counts, and read state inside the same workflow;
- rejection/replacement requests, BOM locking, role restrictions, and audit
  entries for the purchase, inventory, and project transitions.

The suite recreates `MIS_test` and runs migrations before each session. Tests
are not safe to run in parallel because they share that database.

### Frontend

```bash
cd frontend
npm run lint
npm run typecheck
npm run build
```

### End-to-end

With the backend on `:8000` and the frontend on `:3000` already running:

```bash
cd frontend
npm run test:e2e
```

Set `PLAYWRIGHT_API_URL` when the API is not reachable at
`http://localhost:8000`; the browser cookie is shared with the frontend origin.

Playwright creates three temporary accounts (`e2e.superadmin@jatayues.com`,
`e2e.member@jatayues.com`, and `e2e.forced@jatayues.com`), exercises sign-in,
every management section, project creation, the forced password change, and the
role gate. It also drives a complete shortage workflow through the UI: raise a
purchase request from the project page, approve it, mark it ordered with a delay
reason, receive it, verify the project returns to ready, trigger the Time
Counter, and assert the deadline alert. Cleanup removes those accounts, any
`E2E ` projects, and `E2E-` inventory items. The fixture refuses to run
when `ENVIRONMENT=production`.

## Operational notes

- Attachments are stored under `backend/var/uploads` by default; back this
  directory up with the database.
- The scheduler uses `SCHEDULER_TIMEZONE` (default `Asia/Kolkata`) and runs daily
  by default. Set `SCHEDULER_RUN_ON_STARTUP=true` to evaluate once at boot.
- Audit and progress records are append-only by design.
- Local development uses `COOKIE_SECURE=false`. Production deployments must use
  HTTPS and a secure cookie.
- Version pins are in `backend/requirements.txt` and `frontend/package-lock.json`.

## Out of scope for v1

Email/SMS delivery, websockets, exports, SSO, mobile apps, cloud deployment
manifests, Docker images, and advanced charting.

---

Made and managed by JES Electronics Systems Pvt Ltd
