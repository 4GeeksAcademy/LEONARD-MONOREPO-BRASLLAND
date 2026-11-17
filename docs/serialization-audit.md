# Backend Serialization Audit

Scope: `services/api` (Brasaland Digital API), the mounted telemetry receiver and `services/admin-api`.
Legend: ✅ already serialized · ⚠️ partially serialized (over-exposes, or loose shape) · ❌ not serialized (no `response_model`, raw dict).
"Original" = state before this branch. "Now" = state after (all ✅).

## Findings summary

| Original state | Endpoints |
| --- | --- |
| ❌ | forgot/reset/change-password, supplier DELETE, incident summary, analyze, CSV export, `/health` (x2), telemetry events, `/` |
| ⚠️ | `POST /users`, `GET /users`, `GET /auth/me`, `GET/PUT /profiles/me` |
| ✅ | login, user detail/update/delete, supplier/incident/inventory CRUD (kept, but output schemas decoupled from input schemas) |

Cross-cutting issues fixed:
- **Output schemas inherited from input schemas** (`Supplier(SupplierCreate)`, `Incident(IncidentCreate)`, `IngredientRead(IngredientCreate)`, `IngredientExitRead(IngredientEntryRead)`). Any new writable field would silently become a response field (and vice versa). All output schemas now list every field explicitly.
- **Untyped dict responses** replaced with Pydantic models.
- **Email echoed by unauthenticated auth flows** (`POST /users`) removed.
- **Internal foreign key `user_id` and profile row id** leaked by profile endpoints removed.

## Auth, users, profiles (`services/api/auth.py`)

| Method & route | Purpose | Original | Now | Input schema | Output schema (exact fields) / decision |
| --- | --- | --- | --- | --- | --- |
| `POST /users` | Register | ⚠️ `UserRead` – echoed `email`, `role`, `is_active` | ✅ | `UserCreate` (email, password, name, phone, address; role may only be `user`) | `RegisteredUserRead`: `id`, `created_at`. No email/password. Client already holds the email it submitted and logs in next. |
| `POST /auth/login` | Issue JWT | ✅ `Token` (hand-parsed body for JSON+form support, documented via `openapi_extra`) | ✅ | email + password (JSON or form) | `Token`: `access_token`, `token_type`. No user data. |
| `POST /auth/forgot-password` | Request reset link | ❌ dict | ✅ | `ForgotPasswordRequest` (email) | `MessageRead`: `message` (generic, does not reveal whether account exists). |
| `POST /auth/reset-password` | Consume reset token | ❌ dict | ✅ | `ResetPasswordRequest` (token, new_password) | `MessageRead`: `message`. |
| `POST /auth/change-password` | Change own password | ❌ dict | ✅ | `ChangePasswordRequest` | `MessageRead`: `message`. |
| `GET /auth/me` | Caller profile view | ⚠️ nested full `Profile` (profile `id`, internal `user_id`) | ✅ | – | `CurrentUserRead`: `id`, `email`, `is_active`, `role`, `created_at`, `profile{name, phone, address}`. Email allowed here (profile view). Nested profile flattened to the fields the UI shows; no FK. |
| `GET /users` | Admin user list | ⚠️ `list[UserRead]` over raw DB rows | ✅ | – | `UserListItem`: `id`, `email`, `role`, `is_active` (no `created_at`; list does not need it). |
| `GET /users/{id}` | Owner/admin detail | ✅ `UserRead` | ✅ | – | `UserRead`: `id`, `email`, `is_active`, `role`, `created_at`. `hashed_password` is never a field. |
| `PUT /users/{id}` | Update account | ✅ `UserRead` | ✅ | `UserUpdate` (email, password, role, is_active – role/is_active admin only) | `UserRead` (as above). |
| `DELETE /users/{id}` | Delete account | ✅ 204 no body | ✅ | – | `response_model=None`, empty 204. |
| `GET /profiles/me` | Own profile | ⚠️ `Profile` (profile `id`, `user_id`) | ✅ | – | `ProfileRead`: `name`, `phone`, `address`. |
| `PUT /profiles/me` | Update own profile | ⚠️ `Profile` | ✅ | `ProfileUpdate` (name, phone, address) | `ProfileRead`. |

Auth rule check: no auth response contains a password, hash or token other than the login access token; register/login/forgot/reset/change do not return email. Only `/auth/me` (and admin/owner user reads) return the caller's own email.

## Suppliers (`routers/suppliers.py`)

Consumer: backoffice `suppliers.js` renders every field (name, country, categories, rate, currency, status, contact_email, notes, updated_at), so list and detail share one projection – justified, field list is identical for every consumer.

| Method & route | Purpose | Original | Now | Input | Output |
| --- | --- | --- | --- | --- | --- |
| `POST /suppliers` | Create | ✅ but output inherited `SupplierCreate` | ✅ | `SupplierCreate` | `Supplier`: `id`, `name`, `country`, `categories`, `rate_per_unit`, `currency`, `status`, `contact_email`, `notes`, `updated_at`. `id` comes from the TinyDB doc id. |
| `GET /suppliers` | List (filter country/category) | ✅ (inherited) | ✅ | query | `list[Supplier]` (same fields; all used by UI). |
| `GET /suppliers/{id}` | Detail | ✅ (inherited) | ✅ | – | `Supplier`. |
| `PATCH /suppliers/{id}/rate` | Update rate | ✅ | ✅ | `RateUpdate` (rate_per_unit only) | `Supplier`. |
| `PATCH /suppliers/{id}/status` | Update status | ✅ | ✅ | `StatusUpdate` (status only) | `Supplier`. |
| `DELETE /suppliers/{id}` | Delete | ❌ dict | ✅ | – | `DeleteConfirmation`: `detail`. |

## Incidents (`routers/incidents.py`, `app/main.py`)

Consumer: `incidents.js` renders title, description, category, status, origin, branch, created_at in the list, so list and detail share a projection. The internal `source_incident_id` is stripped by `incident_response` and is not in the schema.

| Method & route | Purpose | Original | Now | Input | Output |
| --- | --- | --- | --- | --- | --- |
| `POST /api/incidents` | Create | ✅ (output inherited `IncidentCreate`) | ✅ | `IncidentCreate` | `Incident`: `id`, `title`, `description`, `category`, `status`, `origin`, `branch`, `created_at`, `updated_at`. |
| `GET /api/incidents` | List (filters) | ✅ (inherited) | ✅ | query | `list[Incident]`. |
| `GET /api/incidents/summary` | Counts dashboard | ❌ dict | ✅ | – | `IncidentSummary`: `total`, `by_status`, `by_category`, `by_origin`, `by_branch` (maps of label→count). |
| `GET /api/incidents/{id}` | Detail | ✅ | ✅ | – | `Incident`. |
| `PATCH /api/incidents/{id}/status` | Transition status | ✅ | ✅ | `IncidentStatusUpdate` (status only) | `Incident`. |
| `POST /api/incidents/analyze` | CSV analysis | ❌ dict | ✅ | multipart CSV file | `AnalysisRead`: `total_records`, `valid_records`, `invalid_records`, `invalid_breakdown`, `categories`, `statuses`, `satisfaction{scored_cases, closed_cases, average, scores}`, `rule_labels`. |
| `GET /api/incidents/results/export` | CSV download | ❌ raw `Response` | ✅ | – | Not JSON: declared `response_class=Response` with `text/csv` content in OpenAPI (`response_model=None`). |

## Inventory (`routers/inventory.py`)

All endpoints already built `Read` schemas by hand (no ORM leakage). Fixed: `IngredientRead` / `IngredientExitRead` inherited from write schemas; now explicit. Relationship decision: orders flatten the ingredient relation to `ingredient_name` + `ingredient_sku` (no nested object) – the UI table only needs those; `ingredient_id` is kept for linking.

| Method & route | Purpose | Original | Now | Input | Output |
| --- | --- | --- | --- | --- | --- |
| `GET /inventory/products` | Products + stock at location | ✅ (inherited) | ✅ | `location_id` query | `list[IngredientRead]`: `id`, `name`, `sku`, `category`, `unit`, `current_stock` (stock is a computed aggregate, not a column). |
| `POST /inventory/products` | Create product | ✅ | ✅ | `IngredientCreate` (name, sku, category, unit) | `IngredientRead`. |
| `GET /inventory/products/{id}` | Product detail | ✅ | ✅ | `location_id` query | `IngredientRead`. |
| `POST /inventory/orders/inbound` | Register entry | ✅ | ✅ | `IngredientEntryCreate` (ingredient_id, location_id, quantity) | `IngredientEntryRead`: `id`, `ingredient_id`, `location_id`, `quantity`, `created_at`, `user_uuid`. |
| `POST /inventory/orders/outbound` | Register exit | ✅ (inherited) | ✅ | `IngredientExitCreate` | `IngredientExitRead`: same fields, now declared explicitly. |
| `GET /inventory/orders` | Unified order list | ✅ | ✅ | `location_id` optional | `list[IngredientOrderRead]`: `id`, `order_type`, `ingredient_id`, `ingredient_name`, `ingredient_sku`, `location_id`, `quantity`, `created_at`, `user_uuid` (all read by `inventory.js`). Server-set fields (`user_uuid`, `created_at`) are not writable. |

## Infrastructure

| Method & route | Purpose | Original | Now | Output |
| --- | --- | --- | --- | --- |
| `GET /health` (api) | Liveness | ❌ dict | ✅ | `HealthRead`: `status`. |
| `GET /health` (admin-api) | Liveness | ❌ dict | ✅ | `HealthRead`: `status`. |
| `POST /telemetry/events` | Frontend telemetry ingest | ❌ dict | ✅ | `TelemetryReceipt`: `received`. Input `TelemetryBatch` (strict, `extra=forbid`, max 100 events). |
| `GET /` | Redirect to `/backoffice/` | ❌ (redirect) | ✅ | Redirect only, `response_model=None`, hidden from OpenAPI. |
| `/backoffice/*` | Static mount | n/a | n/a | Static files, not an API endpoint. |

## Verification

- Existing test suite: identical results before and after (86 pass; the same 13 tests fail in both runs because they require the remote Supabase Postgres, which is not reachable from this environment).
- Smoke test through the ASGI app (register, login, `/auth/me`, `/profiles/me`, forgot-password, `/health`, `/suppliers`, `/api/incidents/summary`, `/api/incidents/analyze`) confirmed the response keys match the schemas above; register returns only `id` and `created_at`; no OpenAPI 200 response lacks a schema.
- Manual `/docs` check should be repeated by the reviewer with real env (`/auth/me`, `/suppliers`, `/api/incidents/summary`).
