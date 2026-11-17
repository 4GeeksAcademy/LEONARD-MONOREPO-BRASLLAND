# Caching & Performance Report

## 1. Frontend decisions (`uis/talent-pipeline-tracker`)

### Lazy-loaded components (`next/dynamic`)
| Component | Where | Why lazy |
|---|---|---|
| `CandidateForm` (~210 lines, heaviest component) | `candidates/new`, `candidates/[id]/edit` | Only needed on the form routes; the list/detail pages never pay for it. Fallback: "Loading form...". |
| `CandidateNotesPanel` (extracted from `CandidateDetailClient`) | candidate detail page | Notes sit below the fold; the profile data renders first, notes hydrate after. Fallback: "Loading notes...". |

The caller keeps ownership of the shared state (`notes`) and passes `onNotesChange`/`onFeedback`, so behaviour is unchanged. I did not measure bundle sizes; the gain is estimated as a smaller initial JS chunk on the detail/form routes.

### `useMemo`
`app/page.tsx` computes `pipelineSummary` (candidates per stage + average experience) with `useMemo(..., [response?.data])`. It is declared before the early returns (rules of hooks). Honest caveat: it is one O(n) pass over at most 100 rows, so the benefit is small; it avoids recomputation on re-renders caused by filter input or unrelated state, not on data changes. `CandidateForm` already memoised its `initialState`.

## 2. Backend decisions (`services/api`)

Cache: `cache.py` `TTLCache` – in-process, thread-safe, monotonic clock, LRU cap, hit/miss counters.
A timing middleware (`api.timing` logger) logs `METHOD path -> status | ms` for every request.

| Endpoint | Cost (measured, large data) | Frequency | TTL | Key | Invalidation |
|---|---|---|---|---|---|
| `GET /api/incidents/summary` | ~165 ms median (20k incidents, repeated Counter scan) | every dashboard load | 30 s | single global key | cleared on incident create and status update |
| `GET /inventory/products` | ~25 ms median warm, ~220 ms cold (SUM over 150k movements + join) | every stock screen | 15 s | `location_id` | cleared on product create, inbound order, outbound order |

No private data is cached: both payloads are shared aggregates (counts, stock per location) with no user fields, so a shared key is safe.

### Measurements (SQLite, 20,100 incidents, 420 ingredients, 150,500 movements; 30 requests each)
Seeded with `scripts/seed_load_data.py` (before seeding: 100 incidents, 20 ingredients, 500 movements; after: 20,100 / 420 / 150,500).

| Endpoint | No cache (median) | Cached (median) | Cached (first/miss) |
|---|---|---|---|
| `/api/incidents/summary` | 163.6 ms | 4.4 ms | 191.5 ms |
| `/inventory/products?location_id=COL-01` | 25.1 ms | 4.9 ms | 37.0 ms |
| `/inventory/orders` (not cached) | 297.6 ms | 291.3 ms | – |
| `/suppliers` (not cached) | 5.2 ms | 5.8 ms | – |
| `/auth/me` (not cached) | 5.3 ms | 4.8 ms | – |

Numbers come from an in-process `TestClient` on one machine, so absolute values are indicative; the ratio is the point. Production uses Postgres, where the aggregate query will differ.

Invalidation verified: summary total 20,100 → create incident → next read 20,101 (no waiting for TTL).

## 3. Tradeoffs
- **Freshness vs speed:** dashboard counters can lag up to 30 s only for out-of-band changes; API writes invalidate immediately. Stock is the riskier one, hence the shorter 15 s TTL and invalidation on every movement.
- **In-process cache:** each worker has its own copy. With several workers a write invalidates only its own worker; others serve stale data until TTL expires. A shared store (Redis) would fix this. Acceptable now at a worst-case staleness of 15–30 s.
- **Coarse invalidation:** `clear()` drops all keys instead of targeted ones – simpler and safe, at the cost of extra misses after writes.
- **Thundering herd:** concurrent misses may compute the value more than once; fine at this scale.
- **Left unoptimised on purpose:** `build_summary` still uses a repeated `Counter` scan; a single-pass count would cut the miss cost and is a good follow-up.

## 4. Not cached, and why
- `/inventory/orders`: contains `user_uuid`, changes with every movement, needs a full union sort; low hit rate and a privacy risk under a shared key (still ~290 ms – candidate for pagination/indexing instead).
- `GET /suppliers`: 15 rows, ~5 ms; caching adds complexity for no gain.
- `GET /inventory/products/{id}`: single item, write-sensitive.
- `/auth/me`, `/profiles/me`, auth/login/password endpoints: per-user or sensitive; cheap.
- `/api/incidents/results/export`: already has a per-user session cache; `/api/incidents/analyze` is a POST.

## 5. Testing
Backend tests (SQLite/no remote DB): 92 pass / 18 fail on both `main` and this branch (failures are pre-existing, unrelated to caching). `tsc --noEmit` passes.
