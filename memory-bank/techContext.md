# Technical Context

Derived from reading the code on branch `milestone-4` (created from `feature/milestone5-inventory-backoffice`).
Where the briefing and the code disagree, the code is described and the discrepancy is noted.

## Monorepo layout
| Path | What it is |
|---|---|
| `services/api` | The real backend (FastAPI). |
| `services/admin-api` | Stub: FastAPI app with only `GET /health` (title "LEONARD Admin API"). Not in docker-compose. |
| `uis/talent-pipeline-tracker` | Next.js 16.3.2, React 19.2.8, TypeScript, Tailwind 4, ESLint, Playwright. Separate graded project (has its own `AGENTS.md`). |
| `uis/backoffice` | Vanilla JS + static HTML, bundled with esbuild into `public/`. Playwright tests. |
| `uis/website` | Does not exist yet (documented in `uis/README.md`; created in Milestone 4). |
| `components/milestone2` | TypeScript business logic: types, data, filters, sorting, search, aggregations, validations (`src/index.ts` re-exports). Built with `tsc` into `dist/`. |
| `packages/incident_analysis` | Python CSV validator/analyzer (`analyze_csv`, `results_csv`, `RULES`, `AnalysisError`) with tests. |
| `packages/shared` | `@repo/shared-types`: TS types, auth helpers, `incidents.py`, Jest tests. |
| `infra/`, `docs/` | `infra/` holds only READMEs; containerization is not finished. |
| root | `index.html`, `application.html`, `project-shell.html`, `validation.js` (Milestone 1 static site), `docker-compose.yml`, `pyproject.toml`. |

## Backend — `services/api`
- The application is `services/api/app/main.py`. `services/api/main.py` is only a re-export shim (`from services.api.app.main import app`), not a second app.
- `app/main.py` includes these routers: `public`, `auth`, `users`, `profiles` (all from `auth.py`), `suppliers`, `incidents`, `inventory` (from `routers/`). It also registers two global exception handlers (`RequestValidationError` and `Exception`), an upload-limit middleware, and direct routes `GET /health`, `POST /api/incidents/analyze`, `GET /api/incidents/results/export`, `GET /`.
- Route prefixes are inconsistent: `/api/incidents`, `/suppliers`, `/inventory`.
- Auth (`auth.py`, ~490 lines): JWT with python-jose, passlib/bcrypt, password recovery. Config from `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `PASSWORD_RESET_EXPIRE_MINUTES`, `AUTH_DB_PATH`.
- Pydantic models for suppliers/incidents in `services/api/models.py`; SQLModel inventory tables in `app/models.py`; schemas in `app/schemas.py`; Supabase seeding in `seed.py`.
- Dependencies (`requirements.txt`): fastapi, uvicorn, python-multipart, httpx, tinydb, pydantic[email], python-jose, passlib[bcrypt], bcrypt, python-dotenv, sqlmodel, psycopg[binary].
- **No CORS middleware exists anywhere in `services/` source** (only inside `.venv` packages). Cross-origin browser access is not enabled by the API itself; this is a known gap, not changed in this milestone.

## Persistence — two models (known constraint, do not fix)
This split is the history of the project, not a defect. Suppliers were specified as FastAPI + TinyDB + Pydantic; inventory was later specified as Supabase + SQLModel.
- **TinyDB (JSON files):** suppliers and incidents share `data/suppliers.json` (`SUPPLIERS_DB_PATH`, via `services/api/database.py`, guarded by a process-wide lock); auth users/profiles are in `data/auth.json` (`AUTH_DB_PATH`).
- **Supabase Postgres + SQLModel:** inventory tables `ingredients`, `ingredient_entries`, `ingredient_exits`. Configured in `services/api/app/database.py` from `SUPABASE_DATABASE_URL` or the `SUPABASE_DB_*` variables (driver `postgresql+psycopg`; `postgres://` / `postgresql://` are rewritten).
- Costs: two persistence models inside one API; no shared transactions across them; two different testing setups; TinyDB is single-process and file-based.
- Rule: do not refactor the database layer in Milestone 4.

## Frontends
- **backoffice:** sources `src/app.js`, `auth.js`, `suppliers.js`, `incidents.js`, `inventory.js`, `inventory-api.js`. `npm run build` runs esbuild on four entry points (`app`, `suppliers`, `incidents`, `inventory`) to `public/` (ESM, minified, fonts via file loader). Pages: `public/index.html`, `incidents/`, `inventory/`, `suppliers/`. No `dev` script. Tests: Playwright (`tests/incidents.spec.js`, `tests/suppliers.spec.js`).
- **talent-pipeline-tracker:** App Router (`login`, `register`, `account`, `forgot-password`, `reset-password`, `candidates`), `components/`, `hooks/`, `lib/`, `services/` (`authApi.ts`, `trackerApi.ts`, `session.ts`), `types/`.
- **milestone2:** only `typescript` as a dependency; scripts `typecheck`, `build`, `dev` (tsc watch), `serve`.

## Tests
- Root `pyproject.toml` (`brasaland-quality-checks`, Python >=3.11, uv): pytest `testpaths = ["services/api/tests/unit"]`, `pythonpath = [".", "packages"]`, coverage on `services.api.auth` with `fail_under = 70`.
- `services/api/tests/` also contains `test_api.py`, `test_inventory.py`, `test_password_reset.py`, `test_suppliers.py`, which are outside the configured `testpaths`.
- `packages/incident_analysis/test_analysis.py`; `packages/shared` runs Jest (`npm test` at root delegates to it).
- Playwright for backoffice and tracker.

## Containers
`docker-compose.yml` defines `ui` (ports 3000/3001, `uis/Dockerfile`, `uis/start.sh`, `AUTH_API_URL` and `NEXT_PUBLIC_INVENTORY_API_URL` pointing to `http://backend:8012`) and `backend` (port 8012, `env_file: .env`, mounts `services`, `packages`, `shared`). Containerization is not complete or documented; see `progress.md`.

## Constraints
- `.env` is never committed; no secrets in tracked files.
- Do not move or rename `services/`, `packages/`, `components/`.
- Keep `uis/talent-pipeline-tracker` unchanged.
- Milestone 2 business logic lives only in `components/milestone2/src`; frontends import it, never copy it.

## Discrepancies briefing vs code
- The briefing says the incident dashboard will be "real-time"; the backoffice has no polling, websockets or SSE (checked `uis/backoffice/src`), only request/response REST calls.
- `uis/README.md` documents `uis/website`, which does not exist yet.
