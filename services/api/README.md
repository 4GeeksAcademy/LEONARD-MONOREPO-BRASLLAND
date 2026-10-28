# Brasaland Incident API

FastAPI service for internal incident analysis. It imports the exact same
streaming analyzer as `scripts/analyze.py` and serves the backoffice at the
same origin. No AI service is used.

## Run

From the repository root:

```bash
uv sync --project services/api --locked
uv run --project services/api python -c 'import secrets; from dotenv import set_key; set_key(".env", "JWT_SECRET_KEY", secrets.token_urlsafe(48)); set_key(".env", "ACCESS_TOKEN_EXPIRE_MINUTES", "30")'
npm --prefix uis/backoffice ci
npm --prefix uis/backoffice run build
uv run --project services/api uvicorn services.api.app.main:app --host 0.0.0.0 --port 8012
```

Generate the secret once, not on every startup: changing it invalidates existing
tokens. The root `.env` is ignored by Git. Keep the secret random, at least
32 bytes, and shared between deployments that verify the same tokens. Environment
variables override `.env`; expiry must be a positive number of minutes.
`bcrypt==4.0.1` is pinned for compatibility with `passlib[bcrypt]`.

Password recovery uses Resend. Add these settings to the root `.env` (never put
the API key in source control):

```bash
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL="Brasaland <onboarding@resend.dev>"
FRONTEND_BASE_URL=http://localhost:3001
PASSWORD_RESET_EXPIRE_MINUTES=30
```

Use a sender permitted by your Resend account in `RESEND_FROM_EMAIL`. Reset
links point to `/reset-password` on `FRONTEND_BASE_URL`; expiry must be between
15 and 60 minutes. A reset token is stored only as a SHA-256 hash in the
`password_reset_tokens` TinyDB table and is removed after use, expiry, or a
subsequent password change. If Resend is unavailable, the public request still
returns the same generic response and the failure is logged.

API documentation is available at `http://localhost:8012/docs`. Build the
backoffice before starting the server, then start the existing Next.js frontend:

```bash
npm --prefix uis/talent-pipeline-tracker ci
npm --prefix uis/talent-pipeline-tracker run dev -- --port 3001
```

Register or log in at `http://localhost:3001/login` and open the backoffice at
`http://localhost:3001/backoffice/`. Next.js proxies static assets and protected
API calls onto the same origin as its stored JWT; do not open the internal UI
directly on the API port. If the API port changes, set `AUTH_API_URL` in the
Next.js environment. See [frontend authentication](../../uis/talent-pipeline-tracker/README.md).

## Inventory Database

Set `SUPABASE_DATABASE_URL` or the `SUPABASE_DB_HOST`, `SUPABASE_DB_PORT`,
`SUPABASE_DB_NAME`, `SUPABASE_DB_USER`, and `SUPABASE_DB_PASSWORD` values in the
ignored repository-root `.env` file. Use the Supabase transaction pooler on port
6543; do not commit the password. The service uses SQLModel only for ingredient
and order data; TinyDB continues to handle authentication and users. Inventory
endpoints return `503` until all connection settings are configured. Schema
creation via `SQLModel.metadata.create_all` is for this learning environment only.
Product reads require a Brasaland `location_id` (`COL-01` through `COL-10` or
`FLA-01` through `FLA-04`); `current_stock` is calculated only for that location.

## Endpoints

| Endpoint | Contract |
| --- | --- |
| `POST /api/incidents` | Creates a validated incident with title, description, category, status, origin, and branch. |
| `GET /api/incidents` | Lists incidents; optional `status`, `origin`, `branch`, and `category` filters. |
| `GET /api/incidents/{id}` | Returns one incident or `404`. |
| `PATCH /api/incidents/{id}/status` | Applies a lifecycle-valid status transition. |
| `GET /api/incidents/summary` | Returns totals by status, category, origin, and branch. |
| `GET /inventory/products?location_id=COL-01` | Lists ingredients with stock at the selected location. |
| `POST /inventory/products` | Creates an ingredient with zero stock. |
| `GET /inventory/products/{id}?location_id=COL-01` | Returns one ingredient with stock at the selected location. |
| `POST /inventory/orders/inbound` | Records a location-scoped stock addition attributed to the authenticated user. |
| `POST /inventory/orders/outbound` | Records a location-scoped stock removal if sufficient stock exists. |
| `GET /inventory/orders` | Lists inbound and outbound orders with ingredient data and user UUID. |
| `POST /api/incidents/analyze` | Multipart field `file`, a UTF-8 `.csv`; returns aggregate JSON plus validation-rule labels. |
| `GET /api/incidents/results/export` | Downloads the authenticated user's last successful analysis as `results.csv`. |
| `GET /health` | Service availability (protected). |

Example upload after setting `TOKEN` to the access token returned by login:

```bash
curl -H "Authorization: Bearer $TOKEN" -F 'file=@scripts/incidents-brasaland-demo.csv' http://localhost:8012/api/incidents/analyze
curl -H "Authorization: Bearer $TOKEN" http://localhost:8012/api/incidents/results/export -o results.csv
```

| Status | Meaning |
| --- | --- |
| `400` | Empty/header-only file, invalid UTF-8, wrong CSV headers, or corrupt quoting. |
| `401` | Missing, malformed, expired, or invalid token; inactive or deleted user. |
| `403` | Authenticated caller lacks ownership or administrator permission. |
| `404` | No successful analysis for this user, result expired, or cache entry evicted. |
| `413` | Multipart upload exceeds 256 MiB, including multipart overhead. |
| `415` | File does not have a `.csv` extension. |
| `422` | Missing multipart file. |

Files with invalid records still return `200`: invalid rows are counted and
excluded, including files where every row is invalid. No-score averages are
`null`. Failed requests do not overwrite the last successful analysis.

## Authentication and Ownership

| Endpoint | Access |
| --- | --- |
| `POST /users` | Public registration; email/password and optional name/phone/address. Role defaults to `user`; privileged registration is rejected. |
| `POST /auth/login` | Public; JSON email/password or OAuth2 form username/password (username is the email). Returns a bearer JWT. |
| `POST /auth/forgot-password` | Public; accepts `{ "email": "..." }`, queues a Resend email when the address exists, and always returns the same `200` message. |
| `POST /auth/reset-password` | Public; accepts `{ "token": "...", "new_password": "..." }`; expired, invalid, or used tokens return `400`. |
| `POST /auth/change-password` | Authenticated; accepts `{ "current_password": "...", "new_password": "..." }`; a wrong current password returns `400`. |
| `GET /auth/me` | Authenticated identity with linked profile. |
| `GET /users` | Admin only; password hashes are never returned. |
| `GET /users/{id}` | Owner or admin. |
| `PUT /users/{id}` | Owner or admin; only admins may change role or is_active. Email/password updates are supported. |
| `DELETE /users/{id}` | Owner or admin; also removes the linked profile. |
| `GET /profiles/me` | Authenticated user's profile only. |
| `PUT /profiles/me` | Updates only the caller's name/phone/address; omitted fields remain unchanged. |

The application-level dependency protects **every API route** by default, with
only registration, login, forgot-password, and reset-password exempted. This
includes supplier, incident management, incident analysis, `/health`, and `/`.
Interactive docs, OpenAPI, and static
backoffice assets remain public; static assets do not grant access to API data.
AUTH-02 integrates bearer-token login, registration, profile editing, logout,
and protected views into the existing Next.js app and proxied backoffice.

Users, profiles, and hashed password-reset tokens live in named TinyDB tables in `data/auth.json`
(override with `AUTH_DB_PATH`). User IDs are stable UUID strings; JWTs carry both
`sub` and `user_id`, plus `iat` and `exp`. Other modules must reference this ID
as `user_id`, not create SQL user/profile tables, including after Supabase is
introduced. Passwords use passlib bcrypt, with an 8-character minimum and a
72-byte UTF-8 maximum to avoid bcrypt truncation. Tokens are stateless; no
authentication cookies or server-side login sessions are used. Account deletion
or deactivation invalidates access immediately because each request reads the user.
Password changes do not revoke already issued access tokens; they expire normally.

There is no public admin bootstrap endpoint. To promote the first account, an
operator with local database access can run the following from the repository
root, replacing `REGISTERED_USER_ID` with the ID returned by registration.
Stop the API while performing this local maintenance:

```bash
uv run --project services/api python -c 'from dotenv import load_dotenv; load_dotenv(); from tinydb import Query; from services.api.auth import open_auth_database; db = open_auth_database(); db.table("users").update({"role": "admin"}, Query().id == "REGISTERED_USER_ID"); db.close()'
```

### Manual Verification

1. Open `/docs`, register through `POST /users`, then login with email/password.
2. Use **Authorize**, entering the email in the username field and the password.
	Swagger obtains the JWT through the OAuth2 form login; JSON login returns the
	same token type for other clients.
3. Call `/auth/me`, `/profiles/me`, and `/suppliers` with authorization.
4. Log out in Swagger and confirm protected calls return `401`.
5. Authorize as a second user and confirm accessing/updating/deleting the first
	account returns `403`; profile updates can only target `/profiles/me`.
6. Send a malformed bearer token and verify `401`. For expiry, temporarily set
	`ACCESS_TOKEN_EXPIRE_MINUTES=1`, restart, login, then call a protected endpoint
	after expiry. Restore the desired window afterward.

Focused disposable-database HTTP verification covers registration, JSON/form
login, JWT claims/expiry, protected route families, ownership denials, profile
updates, admin permissions, activation, password changes, user deletion, linked
profile cleanup, and cross-user incident-cache isolation. Password-reset tests
mock Resend and verify the generic response, email link, hashed token storage,
expiry, single-use behavior, and password updates.

## Data Handling and Deployment

Historical incidents can be loaded with `uv run --project services/api python
scripts/seed_incidents.py [path/to/incidents.csv]`. The default source is
`data/raw/incidents-brasaland.csv` when present, otherwise the bundled demo CSV.
The seeder and API use the same TinyDB file; override it with
`SUPPLIERS_DB_PATH`. Repeated runs skip previously imported CSV IDs.

Only aggregate summaries are retained, keyed by the authenticated user's ID.
Results expire after one hour; the cache holds at most 128 users,
evicting the oldest entries when full. The cache is process-local: restarting
the service loses summaries. Use **one worker** for this implementation; a
shared, authenticated result store and concurrency-safe identity database are
required before using multiple workers. TinyDB writes are serialized within
this process; TinyDB is not suitable for concurrent multi-process writers.

Uploaded files are streamed from FastAPI's spooled temporary upload, not stored
in the repository. Temporary files are closed by the request lifecycle. Raw
records and customer identifiers are never included in summaries or exports.
Fonts, icons, and the decorative food photograph are served locally.

This course implementation provides JWT authentication, not company SSO.
Keep the Codespaces port private and deploy only with HTTPS, login/upload/rate limits,
encrypted temporary storage, and appropriate retention controls before using
sensitive production data. Avoid request-body logging at the gateway.

## Tests

```bash
uv run --project services/api python -m unittest discover -s services/api/tests -p 'test_*.py' -v
```

The existing pre-auth tests require a future update to register users and send
bearer tokens; their public-route and browser-cookie assumptions no longer apply.
They previously verified the context benchmark, download contract, browser isolation,
expiration, last successful result, UTF-8/input failures, missing files, and
upload limits for both Content-Length and streamed requests.