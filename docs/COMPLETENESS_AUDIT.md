# Brasaland Monorepo Completeness Audit

Audit date: 2026-11-05
Audited checkout: branch `milestone-4`, HEAD `3c633ba`
Method: inspect source and Git history; run checks that did not install dependencies. No application or data files were changed.

## Summary

| # | Project | Status | Evidence |
|---|---|---|---|
| 1 | Milestone 1 - web fundamentals | PARTIAL | Semantic landing page, Restaurant JSON-LD, Tailwind responsive classes, CTA, and per-field validation exist. Application location values conflict with the company location contract. ([index.html](../index.html#L14), [application.html](../application.html#L125), [validation.js](../validation.js#L220)) |
| 2 | Milestone 2 - TypeScript business logic | PARTIAL | Brasaland interfaces and typed filters, searches, sorting, aggregation, and validation exist. The location portfolio conflicts with the canonical company IDs; typecheck could not run because `tsc` is absent. ([types.ts](../components/milestone2/src/types.ts#L34), [search.ts](../components/milestone2/src/search.ts#L3), [validations.ts](../components/milestone2/src/validations.ts#L23)) |
| 3 | Milestone 3 | UNVERIFIED | `MILESTONE3.md` identifies the Next.js Talent Pipeline Tracker; a static-shell version is also in `components/milestone3`. Tracker lint passes, but the browser/runtime suite was not run. ([MILESTONE3.md](../MILESTONE3.md), [components/milestone3/index.html](../components/milestone3/index.html)) |
| 4 | Talent pipeline tracker | PARTIAL | Live candidate list, filtering/search, detail/edit/register, PATCH status/stage, and note read/add/delete calls exist. Note update is absent; candidate status/stage types are widened with `string`. ([trackerApi.ts](../uis/talent-pipeline-tracker/src/services/trackerApi.ts#L29), [tracker.ts](../uis/talent-pipeline-tracker/src/types/tracker.ts#L18)) |
| 5 | Milestone 4 - AI-driven engineering | PARTIAL | `memory-bank/` has business and technical context. Root `AGENTS.md`, scoped rules, an authored skill, the website pages, and the M2-connected backoffice deliverable are absent. ([memory-bank/projectbrief.md](../memory-bank/projectbrief.md), [memory-bank/techContext.md](../memory-bank/techContext.md)) |
| 6 | Backend architecture proposal | PARTIAL | A complete `docs/ARCHITECTURE_PROPOSAL.md` exists on `origin/BACKEND-PROPOSAL` at `5722c0d`, but is not present at this checkout's HEAD. |
| 7 | Supplier directory | PARTIAL | Pydantic validation, idempotent seed, all required API routes, and the API-backed directory UI exist. The status PATCH does not refresh `updated_at`. ([models.py](../services/api/models.py#L9), [seed.py](../services/api/seed.py#L28), [suppliers.py](../services/api/routers/suppliers.py#L58)) |
| 8 | Authentication | COMPLETE | JWT login, protected routes, `/auth/me`, roles/users, frontend guard, and forgot/reset/change flows are wired. Current auth suite: 85 passed; `auth.py` coverage 91.35%. ([auth.py](../services/api/auth.py#L233), [AuthBoundary.tsx](../uis/talent-pipeline-tracker/src/components/auth/AuthBoundary.tsx), [authApi.ts](../uis/talent-pipeline-tracker/src/services/authApi.ts)) |
| 9 | Milestone 5 - ORM and inventory UI | UNVERIFIED | SQLModel tables, environment-based database setup, inventory routes, and backoffice views exist. Runtime could not be established: the import-only API check fails in this environment because SQLAlchemy is missing. ([models.py](../services/api/app/models.py#L16), [database.py](../services/api/app/database.py#L15), [inventory.py](../services/api/routers/inventory.py#L78)) |
| 10 | Bullet-proof app testing | COMPLETE | `TESTING.md` documents test cases and commands. The configured auth unit suite passed 85 tests with 91.35% `auth.py` coverage; shared session tests passed 28/28 at 100%. ([TESTING.md](../TESTING.md#L1), [pyproject.toml](../pyproject.toml#L12)) |
| 11 | Error handling | COMPLETE | Tracker/backoffice async views have loading, error, and empty/success states; FastAPI registers validation and generic exception handlers; scripts return exit codes through `SystemExit(main())`. ([main.py](../services/api/app/main.py#L92), [useApiData.ts](../uis/talent-pipeline-tracker/src/hooks/useApiData.ts), [analyze.py](../scripts/analyze.py#L44)) |
| 12 | Incident file analyzer | COMPLETE | CLI, API analyze/export, and backoffice upload use the same `packages/incident_analysis` functions. Analyzer tests passed 10/10. ([__init__.py](../packages/incident_analysis/__init__.py#L18), [main.py](../services/api/app/main.py#L122), [app.js](../uis/backoffice/src/app.js)) |
| 13 | Centralized incident manager | PARTIAL | Incident model, idempotent seed, list/create/read/status/summary APIs, and consuming backoffice panels exist. There is no incident DELETE route, so the requested CRUD set is incomplete. ([incidents.py](../services/api/routers/incidents.py#L43), [seed_incidents.py](../scripts/seed_incidents.py#L19), [incidents.js](../uis/backoffice/src/incidents.js)) |
| 14 | Containerization | PARTIAL | Compose, both Dockerfiles and `.dockerignore` files, source mounts, Uvicorn reload, named network, and backend `env_file` are present. Images built in the prior Compose validation, but runtime API access failed on Supabase DNS and was not verified here. ([docker-compose.yml](../docker-compose.yml#L1), [uis/Dockerfile](../uis/Dockerfile), [services/Dockerfile](../services/Dockerfile)) |

No whole project is classified MISSING; several required subdeliverables are absent as detailed below. COMPLETE denotes code/test evidence, not a claim that every deployed environment was exercised.

## Partial And Missing Deliverables

### 1. Milestone 1

The form is Brasaland-oriented rather than a generic contact form: it asks for department, market, location, challenge, target date, current process, and expected outcome. `validation.js` maps every form field through `validateField` and `validateForm`. However, `application.html` offers `CO-MED-01` through `CO-MED-08` and `US-MIA-01` through `US-MIA-06`; the canonical incident/location contract is `COL-01` through `COL-10` and `FLA-01` through `FLA-04` in [Context-company.md](../Context-company.md#L19), also used by [inventory models](../services/api/app/models.py#L8). The exact request schema is not specified in `CONTEXT.md`, so its field-for-field match cannot be proven from that file alone. The submit handler displays a local success message and resets the form; it does not persist or POST the application.

### 2. Milestone 2

The code has Brasaland entities, separated utility modules, pure filters and copy-sorting, linear and binary searches, business validation, and empty-array handling in `calculateSalesSummary`. There are no `any` annotations in the module. Its location assumptions are `CO-MED-01..08` and `US-MIA-01..06`; `validateLocationPortfolio` enforces 8/6, conflicting with `Context-company.md` and the API's 10/4 `COL`/`FLA` IDs. The package defines `npm run typecheck`, but `npm --prefix components/milestone2 run typecheck` returned `sh: 1: tsc: not found`; type correctness is therefore unverified in this no-install audit.

### 3. Milestone 3

`MILESTONE3.md` names `uis/talent-pipeline-tracker` and gives its dev/lint/build commands. `project-shell.html` embeds `components/milestone3/index.html`, a static candidate tracker that fetches the external 4Geeks tracker API. The Next.js tracker lint passed, but neither a live browser session nor its Playwright suite was run. The browser test config starts an API with `uv run`; this audit did not permit a command that might sync/install project dependencies.

### 4. Talent Pipeline Tracker

Candidate list/filter/search, detail, register and edit flows are wired through `trackerApi.ts`; status and stage use `patchCandidate` with `PATCH`. Forms validate required fields and display request feedback. `getCandidateNotes`, `addCandidateNote`, and `deleteCandidateNote` provide read/create/delete, but no note update function or endpoint call exists. `CandidateRecord.status`, `CandidateRecord.stage`, and patch inputs use `CandidateStatus | string` / `CandidateStage | string`, weakening the declared unions. The list/detail/edit routes have loading/error handling and the list has an empty state; `CandidateDetailClient.refreshNotes` has no separate loading state.

### 5. Milestone 4

`memory-bank/projectbrief.md` and `techContext.md` are present. The following Milestone 4 artifacts are not tracked at HEAD: root `AGENTS.md`, `.agents/rules/` with an explicitly scoped rule, and an authored `.agents/skills/<name>/SKILL.md`. The only tracked `.agents/skills/` content is the vendored Supabase material, excluded by the brief's rule.

`uis/website` has package/config files and typed content data, but its `src/app` contains only `globals.css`; there is no `layout.tsx` or `page.tsx` to render the Milestone 1 site or form. `uis/backoffice` is the existing static incident/supplier/inventory UI; no file imports `components/milestone2` or renders its output as the required M2 backoffice. The website typecheck passed, but that does not establish a rendered page.

### 6. Backend Architecture Proposal

The proposal on `origin/BACKEND-PROPOSAL` commit `5722c0d` contains a justified modular-monolith pattern, folder/module layout, router organization, technical decisions, frontend/backend separation, CORS/env guidance, seven risks, and three official FastAPI documentation references. It is not in the current `milestone-4` tree. For this checkout to contain the deliverable, `docs/ARCHITECTURE_PROPOSAL.md` must be present at HEAD.

### 7. Supplier Directory

`SupplierCreate` has country/currency and category validation, `Rate` requires a positive finite strict float, and `Status` is `active | suspended`. `seed_database` inserts only missing name/country pairs. The API has POST, filtered GET list, GET by ID, PATCH rate, PATCH status, and DELETE; the UI loads the API list, filters without reload, registers suppliers, edits rates/status, and labels Active/Suspended. `update_status` changes only `status`, unlike `update_rate`, which also stamps `updated_at`; status changes therefore leave the timestamp stale.

### 9. Milestone 5 Runtime

The implementation exists: `Ingredient`, `IngredientEntry`, and `IngredientExit` SQLModel tables; `get_inventory_database_url` reads `SUPABASE_DATABASE_URL` / `SUPABASE_DB_*`; inventory routes cover products, inbound/outbound orders and history; the backoffice provides product, receive, consumption and history views. Runtime is unverified. The import-only check of `services.api.app.main:app` failed with `ModuleNotFoundError: No module named 'sqlalchemy'`; no dependencies were installed.

### 13. Centralized Incident Manager

The seed skips duplicate `source_incident_id` values; the router implements create, list/filter, read by ID, status PATCH, and summary; the backoffice calls list/create/summary/status and renders list, filters, and summary panels. There is no `DELETE` route in `services/api/routers/incidents.py`, so it is not full CRUD. `scripts/seed_incidents.py` is the seed file that must be present for that part to count; it is present.

### 14. Containerization

The required files and connections are present: Compose builds from `./uis` and `./services`, mounts source, maps UI ports 3000/3001 and API 8012, targets `backend:8012`, and uses a named network. The backend has root `.env` as `env_file`; `services/Dockerfile` enables Uvicorn `--reload`; both `.dockerignore` files exist and no credential literals were found in the Docker files. Image build and `docker compose config --quiet` passed in the prior validation. Runtime did not: the earlier stack could not resolve the configured Supabase pooler from the Compose network, so UI-to-API behavior and reload were not verified.

## Cross-Cutting Findings

### Secrets And Git History

- Working tree: root `.env` contains a credential-like assignment; its value was not printed. `uis/talent-pipeline-tracker/.env.local` also exists. Both paths are ignored. The tracked `.env.example` has no matching long credential assignment.
- History: no commits contain `.env` or `uis/talent-pipeline-tracker/.env.local`. `.env.example` is present in history, including `c8052b9`; the template scan found no populated credential-like assignment. A history scan for private-key PEM blocks and common AWS/GitHub/OpenAI token shapes found no matching blobs.
- A tracked `services/admin-api/.venv/.../certifi/cacert.pem` is a public CA bundle, not a private key. It is included in the committed virtualenv listed below.

### Committed Generated Artifacts

- `services/admin-api/.venv/`: 1,723 tracked files, first present in the milestone baseline history (including `287d3d8`). This includes vendored dependencies and the public CA bundle above.
- `components/milestone2/dist/`: 9 tracked compiled JavaScript files.
- Tracked `node_modules`: 0. The broad generated-artifact scan also matched 16 `pip` build files inside the tracked virtualenv; they are already counted in its 1,723 files.

### Hardcoded Hosts

Runtime source literals include [services/api/auth.py](../services/api/auth.py#L359), whose password-reset URL defaults to `http://localhost:3001`; [next.config.ts](../uis/talent-pipeline-tracker/next.config.ts#L8), whose API fallback is `http://127.0.0.1:8012`; and [page.tsx](../uis/talent-pipeline-tracker/src/app/page.tsx#L50), which links to `http://localhost:3000/project-shell.html`. [start.sh](../uis/start.sh#L6) binds Next to `0.0.0.0` intentionally. Playwright configs also hardcode loopback test hosts: [tracker config](../uis/talent-pipeline-tracker/playwright.config.ts#L15) and [backoffice config](../uis/backoffice/playwright.config.js#L10).

### CORS

No `CORSMiddleware` is configured in the real API. `services/api/app/main.py` registers only `UploadLimitMiddleware` at `app.add_middleware`; the proposal branch discusses CORS, but the running API does not implement it.

### API Entry Point And Boot

The real app is `services.api.app.main:app` in [services/api/app/main.py](../services/api/app/main.py#L76), which includes `public_router`, `auth_router`, `users_router`, `profiles_router`, `suppliers_router`, `incidents_router`, and `inventory_router` at lines 83-89. [services/api/main.py](../services/api/main.py#L1) is only a re-export shim. API import/runtime is UNVERIFIED here: the no-install import check stopped at the missing SQLAlchemy module, and the lifespan would create SQLModel tables and seed TinyDB, so it was not started during this read-only audit.

### Tests And Checks

| Command | Result |
|---|---|
| `.venv/bin/python -m pytest --cov=services.api.auth --cov-report=term-missing -q` | 85 passed; `services/api/auth.py` coverage 91.35%. |
| `PYTHONPATH=packages .venv/bin/python -m unittest discover -s packages/incident_analysis -p 'test_*.py'` | 10 passed. |
| `npm --prefix packages/shared test -- --coverage` | 28 passed; 100% statements, branches, functions and lines. |
| `npm --prefix uis/talent-pipeline-tracker run lint` | Passed. |
| `npm --prefix uis/website run typecheck` | Passed; this is only the scaffold, with no route page. |
| `npm --prefix components/milestone2 run typecheck` | Could not run: `tsc: not found`; no install performed. |
| Tracker/backoffice Playwright suites | UNVERIFIED; not run in this audit. Their configs start API/frontend services; tracker uses `uv run`, and backoffice API startup can mutate local data / connect to Supabase. |

The configured root pytest `testpaths` contains only `services/api/tests/unit`. The separate `services/api/tests/test_api.py`, `test_inventory.py`, `test_suppliers.py`, and `test_password_reset.py` suites exist but were not run by the default command. Backoffice Playwright files are `tests/incidents.spec.js` and `tests/suppliers.spec.js`; there is no inventory UI Playwright suite in that directory.

## Remaining Work In Dependency Order

1. Bring the Milestone 1 form and Milestone 2 location/domain IDs into one contract with `Context-company.md` and the API models; obtain a runnable Milestone 2 typecheck environment.
2. Complete the missing Milestone 4 deliverables: root `AGENTS.md`, scoped `.agents/rules/` rule, an authored `.agents/skills/<name>/SKILL.md`, rendered `uis/website/src/app` pages/components, and a backoffice view importing Milestone 2 output.
3. Make the architecture proposal available on the delivered branch; the complete draft is currently only on `origin/BACKEND-PROPOSAL`.
4. Complete candidate-note CRUD/type guarantees in the tracker; update supplier `updated_at` on status changes; add the missing incident DELETE operation required for CRUD.
5. Verify the API with its required SQLAlchemy dependencies and reachable Supabase database, then exercise the tracker/backoffice browser suites and live reload without installing during this audit.
6. Re-run the Compose runtime check after the API can reach its configured database; the images/config alone do not establish a working stack.