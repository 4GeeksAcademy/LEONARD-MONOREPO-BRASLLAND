# Talent Pipeline Tracker (Milestone 3)

Internal Brasaland People and Culture tracker built with Next.js App Router + TypeScript.

## Environment Variables

Optional variables in `.env.local`:

```bash
NEXT_PUBLIC_API_URL=https://playground.4geeks.com/tracker/api/v1
AUTH_API_URL=http://127.0.0.1:8012
```

`NEXT_PUBLIC_API_URL` is the existing course candidate service, not the local
account API. Only configure trusted API origins: protected requests send the
bearer token to this URL. `AUTH_API_URL` is server-only and defaults to the local
FastAPI service. Next.js proxies account requests under `/api/backend`, and
serves the incident and supplier backoffice under `/backoffice/`, keeping all
internal applications on one browser origin without CORS or authentication cookies.

## Run Locally

```bash
uv sync --project services/api --locked
npm --prefix uis/backoffice ci
npm --prefix uis/backoffice run build
npm --prefix uis/talent-pipeline-tracker ci
```

Configure the API's `JWT_SECRET_KEY` once as described in
[the API README](../../services/api/README.md), then run these in separate terminals:

```bash
uv run --project services/api uvicorn services.api.app.main:app --host 0.0.0.0 --port 8012
npm --prefix uis/talent-pipeline-tracker run dev -- --port 3001
```

Open `http://localhost:3001/login` and register an account. Open the backoffice
through `http://localhost:3001/backoffice/`, not directly on the API port;
`localStorage` is scoped to the browser origin. Use the same hostname consistently.

## Shell Integration

To display this milestone inside `project-shell.html`, run it on port 3001:

```bash
npm run dev -- --port 3001
```

Then open `project-shell.html` from the repo root.

## Delivered Features

- Candidate list with status filter, stage filter, and search via query params.
- Candidate detail view with status and stage updates using `PATCH /records/:id`.
- Notes management (list/add/delete).
- Candidate creation (`POST /records`) and edition (`PUT /records/:id`).
- Loading, success, and error states across async actions.
- Typed API contracts under `src/types` and API service functions under `src/services`.

## AUTH-02

Public auth views: `/login`, `/register`, `/forgot-password`, and
`/reset-password`. Registration calls `POST /users`
with optional name/phone/address, then logs in with the same credentials.
Both flows store the JWT in `localStorage` under `brasaland.access_token`.
Forms remain disabled until hydration and use a POST fallback so credentials
cannot accidentally become URL query parameters.

Password recovery requests a Resend email through `POST /auth/forgot-password`;
the API always returns the same confirmation for registered and unregistered
addresses. Reset links open `/reset-password?token=...` and redirect to login
after success. Authenticated users can change their password at
`/account/change-password`. Configure `RESEND_API_KEY`, `RESEND_FROM_EMAIL`,
`FRONTEND_BASE_URL`, and `PASSWORD_RESET_EXPIRE_MINUTES` in the API's root `.env`
as documented in [the API README](../../services/api/README.md).

Protected views:

- `/`: candidate list, search, and filters.
- `/candidates/new`: candidate creation.
- `/candidates/[id]`: candidate details, updates, and notes.
- `/candidates/[id]/edit`: candidate editing.
- `/account/profile`: email and linked profile from `GET /auth/me`; name,
  phone, and address editing through `PUT /profiles/me`.
- `/account/change-password`: authenticated password update with current-password
    verification and matching new-password confirmation.
- `/backoffice/`: incident upload, analysis, and CSV export.
- `/backoffice/incidents/`: incident registration, lifecycle management, and summary metrics.
- `/backoffice/suppliers/`: supplier directory and management.

The client layout validates stored tokens through `GET /auth/me` before mounting
protected content. Candidate fetching runs in client effects, never server
components. The legacy backoffice validates the same session before revealing
its UI. All protected calls read the current token and attach `Authorization:
Bearer <token>` through the shared helper in `packages/shared/auth/session.ts`.
Missing/invalid tokens and protected `401` responses clear storage and redirect
to `/login`; logout does the same. Transient network errors allow a retry without
deleting a valid token. No Next.js middleware or cookie check is used.

Milestone 1 remains entirely public and unchanged. Its HTML files are not wrapped
in the Next.js session guard. Client guards are a UX mechanism; API authorization
is still the security boundary. Use HTTPS and prevent XSS in production since
the required `localStorage` token is accessible to scripts.

## Verification

```bash
npm --prefix uis/talent-pipeline-tracker run lint
npm --prefix uis/talent-pipeline-tracker run build
npm --prefix uis/talent-pipeline-tracker exec -- playwright install chromium
npm --prefix uis/talent-pipeline-tracker test
```

Build the backoffice first. Browser tests start disposable API/Next.js servers on
ports 8013 and 3011, with temporary auth and supplier databases and a random test
secret. They use the real account and backoffice APIs; external candidate-service
responses are mocked for deterministic checks. Tests cover every protected route,
registration/login errors, linked-profile persistence, bearer headers, upload/export,
logout, protected `401` handling, hydration safety, public-site isolation, and
desktop/mobile screenshots in `test-results/`. Chromium system libraries must
be available through your environment's approved installation process.

The existing pre-auth browser suites in `uis/backoffice` are not the AUTH-02 gate;
they still assume anonymous access. The new suite above exercises authenticated
backoffice flows. Dependency auditing is separate: the current pinned production
chain reports advisories in Next.js, sharp, and source-map-js; upgrade those in
a dedicated dependency/security change before production deployment.
