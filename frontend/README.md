# JES MIS frontend

Next.js 16 App Router frontend for the JES Electronics Systems Pvt Ltd MIS.
See the repository [README](../README.md) for the full setup, architecture, and
role matrix.

## Local setup

```bash
npm install
cp .env.example .env.local
npm run dev
```

The app runs at `http://localhost:3000` and expects the API at the URL in
`NEXT_PUBLIC_API_URL` (default `http://localhost:8000`). Keep both on the same
host (`localhost`) so the HTTP-only access-token cookie is sent to the API.

## Commands

```bash
npm run dev        # development server
npm run build      # production build
npm start          # serve the production build
npm run lint       # ESLint with zero warnings
npm run typecheck  # TypeScript without emitting
npm run test:e2e   # Playwright (requires a running backend and frontend)
```

End-to-end tests use temporary `e2e.*@jatayues.com` accounts created by
`backend/tests/e2e_fixture.py`; the fixture removes them and any `E2E ` projects
when the suite finishes. It refuses to run when `ENVIRONMENT=production`.

## Project structure

- `src/app/(app)/` — authenticated pages (dashboard, projects, inventory,
  purchases, alerts, users, Time Counter, audit)
- `src/app/login/`, `src/app/change-password/` — public auth flow
- `src/components/` — app shell, UI primitives, status badges
- `src/lib/` — typed API client, auth context, shared types and helpers
- `src/proxy.ts` — optimistic cookie guard for protected routes
