# Business Performance Data Pipeline — Design Document

**Company:** Brasaland  
**Pipeline Version:** 1.0 (Design Phase)  
**Date:** November 2026  
**Status:** Design – Ready for Implementation Review

---

## Executive Summary

This document defines the design of a new data pipeline that transforms telemetry events from Brasaland's inventory system into business-focused KPIs for leadership decision-making. This pipeline feeds daily sales performance, inventory health, and operational efficiency reports to department heads and the executive team—independent of the existing technical telemetry report used by engineering.

**Key Pipeline Attributes:**
- **Idempotency:** Running twice on the same data produces identical results (no duplicates, no data loss)
- **Observability:** Every run leaves a complete audit trail with timing, record counts, and error traces
- **Recoverability:** Failures are logged with phase checkpoints; re-runs resume from the last clean state

---

## Phase 1: Current State Analysis

### 1.1 What We Have Today

**Telemetry Events Table:** `public.telemetry_events` (Supabase)
- **Source:** Backend API receives telemetry from backoffice and inventory system
- **Schema:** 8 columns: `id`, `timestamp`, `service`, `event_type`, `level`, `value`, `message`, `tags` (JSONB)
- **Immutability:** Events are append-only; no updates or deletes
- **Mandatory Metrics Captured:**
  - `outbound_order_created` — daily sales transactions by location
  - `inbound_order_received` — inventory receipts from suppliers
  - `stock_minimum_threshold_breach` — low-stock alerts by product and location
  - `failed_direct_stock_edit` — unauthorized edit attempts
  - `outbound_order_fulfilled` — order fulfillment tracking

**Existing Technical Report:** `GET /telemetry/report`
- **Purpose:** Engineering troubleshooting (event volume, error rates, latency by day)
- **Audience:** Internal tech team
- **Endpoints:** `services/telemetry/analysis.py`
- **Output:** Read-only metrics for operational debugging

### 1.2 Business Gap

The technical report answers **engineering questions:**
> "How many events did we process? What error rates occurred? What was API latency yesterday?"

It **does not answer business questions:**
- "What is total revenue by location by day?" (in COP and USD)
- "Which products are understocked across the chain?"
- "Which locations are top performers this week?"
- "What is average order fulfillment time by location?"
- "Are there emerging supply chain bottlenecks?"

**Gap Identified:** Leadership needs daily rollups aggregated by location and product, with business context (which sales happened, inventory health, operational SLAs)—not raw event counts. The existing report is immutable and reserved for engineering; this pipeline must produce new tables in a **reporting schema** with a separate API endpoint in `services/reporting/`.

---

## Phase 2: Pipeline Design

### 2.1 Pipeline Purpose (Single Sentence)

**Produce a daily business performance rollup by location that feeds the Executive Operations Report (cadence: daily at 7 AM), computing sales revenue (COP and USD), inventory health (critical stock locations), and fulfillment SLA attainment from telemetry events.**

### 2.2 Extraction Format

**Source Tables:**
1. `public.telemetry_events` — event source (append-only)
2. `public.inventory_products` — product metadata (SKU, standard UOM, supplier cost)
3. `public.locations` — location metadata (location code, market code, exchange rate snapshot)

**Data Arrival:**
- **telemetry_events:** Continuous; events arrive with original business timestamp in `tags._telemetry.eventId`
- **Refresh cadence:** Daily at 6:00 AM UTC (1 hour before pipeline run at 7 AM)
- **Historical lookback:** Last 24 hours + 48-hour recompute window for late-arriving events

**Event Payload Shape** (extracted from `tags` JSONB):
```json
{
  "eventId": "evt-20261120-001",
  "requestId": "req-abc123",
  "eventTimestamp": "2026-11-20T14:30:45Z",
  "eventType": "outbound_order_created",
  "locationId": "COL-01",
  "orderId": "ord-98765",
  "quantity": 50,
  "productId": "prod-pizza-dough-25kg",
  "amountCOP": 125000,
  "amountUSD": 31.25,
  "sessionId": "sess-xyz",
  "userId": "op-maria-col01"
}
```

### 2.3 Data Flow Diagram

**Three Distinct Stages:**

```
┌─────────────────────────────────────────────────────────────────┐
│                      EXTRACTION LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  telemetry_events         inventory_products    locations       │
│       (append)                  (lookup)         (lookup)        │
│         │                          │                │            │
│         └──────────────┬───────────┘                │            │
│                        ▼                           ▼            │
│           Query Events + Enrich Metadata                        │
│           ✓ Filter: last 72 hours                              │
│           ✓ Join product costs, location code                  │
│           ✓ Deduplicate by eventId (upsert key)                │
│                                                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   TRANSFORMATION LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│  Aggregation Pipeline (Pandas / SQL):                           │
│  ✓ Group by: event_date, location_id, event_type              │
│  ✓ Calculate:                                                   │
│    - daily_sales_cop (SUM of amountCOP)                        │
│    - daily_sales_usd (SUM of amountUSD)                        │
│    - fulfillment_count (COUNT fulfilled)                       │
│    - avg_fulfillment_time_hours (AVG duration)                 │
│    - stock_breach_count (critical alerts)                      │
│  ✓ Add run metadata:                                            │
│    - event_window_start, event_window_end                      │
│    - record_count, late_event_count                            │
│    - run_id (UUID, unique per execution)                       │
│                                                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        LOAD LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  Destination: reporting.daily_operations_rollup               │
│  Strategy: UPSERT by (report_date, location_id)               │
│  - If row exists: UPDATE all metrics + set updated_at         │
│  - If new: INSERT full row                                    │
│  - Audit all changes in reporting.pipeline_runs               │
│                                                                 │
│  POST /reporting/kpi-query endpoint available                 │
│  (populated from daily_operations_rollup)                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 Handling Updates and Duplicates

**Scenario:** An event arrives with a past timestamp after the daily run completes.

**Strategy: 48-Hour Recompute Window**

1. **Normal Run (Daily at 7 AM):** Processes events from yesterday (24 hours back)
   - Query: `WHERE timestamp >= now() - interval '24 hours'`
   - Load: UPSERT into `daily_operations_rollup` for yesterday's date

2. **Late Event Arrival:** An event timestamped at 11/19 14:00 arrives at 11/20 23:00
   - Next scheduled run (11/21 7 AM) includes 48-hour lookback: `WHERE timestamp >= now() - interval '48 hours'`
   - Query detects yesterday's row is affected; re-runs aggregation for 11/19
   - UPSERT updates same row (`report_date = 11/19, location_id = COL-01`)
   - Log: Creates record in `pipeline_runs` with `invalidation_trigger = 'late_event_recompute'`

3. **Duplicate Prevention at Ingest Layer**
   - Every event's `eventId` is unique (source guarantee)
   - Transformation deduplicates: `GROUP BY eventId, location_id` (deduplicate by envelope)
   - Load layer upse rts by date + location, so second run with same events = same metrics

**Mechanism:** Deduplication occurs in the extraction layer using event envelope fields; aggregation is naturally idempotent because it uses `SUM`, `COUNT`, and `AVG` over the deduplicated event set.

### 2.5 Destination Tables and New Endpoints

**New Reporting Schema Tables:**

| Table Name | Purpose | Key Columns | Refresh |
|-----------|---------|------------|---------|
| `reporting.daily_operations_rollup` | Daily KPI aggregates by location | `report_date`, `location_id`, `daily_sales_cop`, `daily_sales_usd`, `fulfillment_count`, `avg_fulfillment_time_hours`, `stock_breach_count` | Daily, 7 AM |
| `reporting.pipeline_runs` | Audit trail of every pipeline execution | `run_id`, `run_start`, `run_end`, `records_processed`, `status`, `error_message`, `invalidation_trigger` | Per run |
| `reporting.location_product_inventory` | Current inventory snapshot by location and product | `location_id`, `product_id`, `quantity_on_hand`, `quantity_critical_threshold`, `is_critical`, `snapshot_timestamp` | Daily, 6:30 AM |

**New Service Endpoints** (`services/reporting/`):

1. **Status Query:** `GET /reporting/status`
   - Returns: Last run time, status (success/failed/running), next scheduled run
   - Function called: `get_pipeline_status()`

2. **Manual Trigger:** `POST /reporting/run-now`
   - Triggers immediate pipeline run (if not already running)
   - Returns: `run_id`, start time, expected completion
   - Function called: `trigger_pipeline_flow()`

3. **KPI Query:** `GET /reporting/kpi-query?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&location_id=COL-01`
   - Returns: Sales, fulfillment SLA, inventory health for date range
   - Function called: `query_business_kpis()`
   - Consumed by: Part 3 dashboard

---

## Phase 3: Resilience and Idempotency

### 3.1 Idempotency Strategy

**Scenario:** Pipeline fails during load. At 7:15 AM, 847 of 1,412 aggregated rows were inserted, then Supabase timeout terminated the connection.

**Recovery on Second Run (Automatic Retry at 7:30 AM):**

1. **Checkpoint:** Pipeline records `phase_checkpoint` in `reporting.pipeline_runs` before each stage:
   - Checkpoint 1: "EXTRACT_COMPLETE" (events queried, deduplicated)
   - Checkpoint 2: "TRANSFORM_COMPLETE" (aggregations computed in memory)
   - Checkpoint 3: "LOAD_START" (before UPSERT)

2. **Re-Run Logic:**
   - Read last run's checkpoint from `reporting.pipeline_runs`
   - If checkpoint < "TRANSFORM_COMPLETE": re-extract and re-transform
   - If checkpoint = "LOAD_START": query already-loaded rows; re-attempt UPSERT
   - UPSERT guarantees: second run inserts same row keys, updates same metrics → no duplicates

3. **Verification:** After re-run completes:
   - Count rows in `daily_operations_rollup` for yesterday = count from final TRANSFORM stage
   - Sum daily_sales_cop = exact same value as first attempt (or first + late events)
   - No duplicate rows exist (checked by run_id in audit log)

**Guarantee:** Idempotency is enforced by:
- Deduplication on `eventId` in extraction
- Event envelope immutability (no source update)
- UPSERT strategy (insert new or update existing, never both)

### 3.2 Execution Log Design

**Table: `reporting.pipeline_runs`**

| Field Name | Data Type | Justification |
|-----------|-----------|---------------|
| `run_id` | UUID | Unique identifier for each execution; allows tracing all rows inserted in this run |
| `run_start_time` | TIMESTAMPTZ | Records when pipeline began; used to detect overlaps (concurrent runs) and calculate total duration |
| `run_end_time` | TIMESTAMPTZ | Completion time; null if still running; used to SLA monitoring (must complete by 7:45 AM) |
| `extraction_record_count` | INTEGER | Number of unique events extracted; helps detect data loss vs. normal low-volume periods |
| `transformation_record_count` | INTEGER | Aggregated rows computed (by location, date); if 0, indicates no data processed or filter misconfiguration |
| `load_record_count` | INTEGER | Rows successfully upserted; must match transformation count (else partial failure) |
| `status` | TEXT (enum) | RUNNING, COMPLETED, FAILED; used for monitoring and preventing concurrent runs |
| `error_message` | TEXT | If status = FAILED, contains exception + stack trace for debugging (Supabase timeout, permission denied, etc.) |
| `invalidation_trigger` | TEXT | Reason for run (scheduled, manual_trigger, late_event_recompute); helps distinguish routine vs. anomalous runs |
| `late_event_count` | INTEGER | Count of events with timestamp > 24 hours old; flags data quality or system time skew issues |
| `phase_checkpoint` | TEXT | Last completed stage (EXTRACT_COMPLETE, TRANSFORM_COMPLETE, LOAD_COMPLETE); used for resumption logic |

**Example Log Entry:**
```
run_id: 'a1b2c3d4-e5f6-4789-0abc-def1234567890'
run_start_time: 2026-11-20 07:00:00+00:00
run_end_time: 2026-11-20 07:12:30+00:00
extraction_record_count: 2847
transformation_record_count: 14  (14 locations × 1 day)
load_record_count: 14
status: 'COMPLETED'
error_message: null
invalidation_trigger: 'scheduled'
late_event_count: 23
phase_checkpoint: 'LOAD_COMPLETE'
```

---

## Phase 4: Mapping to Prefect

### 4.1 Prefect Flows and Tasks

**Main Flow:** `daily_business_performance_flow`
- **Purpose:** Orchestrate extraction → transformation → load
- **Trigger:** Scheduled daily at 7:00 AM UTC (via Prefect Cloud)
- **Retry Policy:** Auto-retry on timeout (max 2 attempts, 5-minute backoff)
- **State Transitions:**
  - Running → Completed (success)
  - Running → Failed (3+ retry failures)

**Task 1: `extract_telemetry_events`**
- **Input:** Date range (last 24 hours by default; 48 hours if late_event_recompute triggered)
- **Output:** Pandas DataFrame with deduplicated events + product/location enrichment
- **Retry:** 2 times on network errors
- **Failure State:** Failed (logs database query error to `pipeline_runs`)

**Task 2: `transform_to_business_metrics`**
- **Input:** DataFrame from Task 1
- **Output:** Aggregated DataFrame (14 rows for 14 locations; 1 date)
- **Computation:** GroupBy location + event_type; compute SUM, COUNT, AVG
- **Failure State:** Failed (logs aggregation error)

**Task 3: `load_to_reporting_schema`**
- **Input:** Aggregated DataFrame from Task 2
- **Output:** Number of rows upserted to `reporting.daily_operations_rollup`
- **Strategy:** UPSERT by (report_date, location_id)
- **Failure State:** Partial failure (some rows inserted, then timeout); checkpoint recorded before retry
- **Success State:** Completed (all rows loaded)

**Optional Task 4: `recompute_inventory_snapshot`** (Part 2 addition)
- Runs after main flow completes
- Populates `reporting.location_product_inventory` from latest telemetry
- Runs in background; does not block main flow completion

### 4.2 Prefect Configuration Blocks

**Block 1: `supabase-reporting-db`**
- **Type:** Database connection block
- **Config:** Connection string, timeout (30s), pool size (5)
- **Credentials:** Stored in Prefect Cloud secrets (server-only role for `reporting` schema write)

**Block 2: `prefect-cloud-schedule`**
- **Type:** Cron schedule
- **Config:** `0 7 * * *` (daily at 7 AM UTC)
- **Timezone:** UTC

**Block 3: `slack-alerts`** (optional for Part 2)
- **Type:** Notification block
- **Config:** Webhook URL for failure alerts
- **Trigger:** When flow state = Failed

---

## Phase 5: Application Integration (Design Only)

### 5.1 Three New Endpoints in `services/reporting/`

**Endpoint 1: Status Query**
```
GET /reporting/status
Authorization: Bearer <auth_token>

Response (200):
{
  "last_run": {
    "run_id": "a1b2c3d4-...",
    "start": "2026-11-20T07:00:00Z",
    "end": "2026-11-20T07:12:30Z",
    "status": "COMPLETED",
    "records_loaded": 14
  },
  "next_scheduled": "2026-11-21T07:00:00Z",
  "is_running": false
}
```
**Calls:** `data/pipelines/reporting_flows.get_pipeline_status()`

---

**Endpoint 2: Manual Trigger**
```
POST /reporting/run-now
Authorization: Bearer <auth_token>
Body: { "mode": "normal" | "late_event_recompute" }

Response (202 Accepted):
{
  "run_id": "b2c3d4e5-...",
  "status": "RUNNING",
  "started_at": "2026-11-20T14:35:00Z",
  "estimated_completion": "2026-11-20T14:45:00Z"
}

Errors:
- 409 Conflict: Pipeline already running
- 403 Forbidden: User lacks permission to trigger
```
**Calls:** `data/pipelines/reporting_flows.trigger_pipeline_flow(mode='normal')`

---

**Endpoint 3: KPI Query**
```
GET /reporting/kpi-query?start_date=2026-11-13&end_date=2026-11-20&location_id=COL-01
Authorization: Bearer <auth_token>

Response (200):
{
  "query": {
    "start_date": "2026-11-13",
    "end_date": "2026-11-20",
    "location_id": "COL-01"
  },
  "data": [
    {
      "date": "2026-11-13",
      "location_id": "COL-01",
      "daily_sales_cop": 2450000,
      "daily_sales_usd": 612.50,
      "fulfillment_count": 42,
      "avg_fulfillment_time_hours": 2.3,
      "stock_breach_count": 1
    },
    ...
  ],
  "summary": {
    "total_sales_cop": 17150000,
    "total_sales_usd": 4287.50,
    "avg_fulfillment_time_hours": 2.15
  }
}
```
**Calls:** `data/pipelines/reporting_flows.query_business_kpis(start_date, end_date, location_id)`

### 5.2 Function and Flow Mapping

| Endpoint | Calls | Location | Purpose |
|----------|-------|----------|---------|
| `GET /reporting/status` | `get_pipeline_status()` | `data/pipelines/reporting_flows.py` | Read from `pipeline_runs`; return last status |
| `POST /reporting/run-now` | `trigger_pipeline_flow()` | `data/pipelines/reporting_flows.py` | Submit job to Prefect; return run_id |
| `GET /reporting/kpi-query` | `query_business_kpis()` | `data/pipelines/reporting_flows.py` | Query `daily_operations_rollup`; apply date/location filters |

---

## Design Consistency with Telemetry Plan

✅ **Mandatory Metrics Used:**
- `outbound_order_created` → daily_sales_cop, daily_sales_usd
- `outbound_order_fulfilled` → fulfillment_count, avg_fulfillment_time_hours
- `stock_minimum_threshold_breach` → stock_breach_count
- `inbound_order_received` → (Part 2: inventory health)
- `failed_direct_stock_edit` → (Part 2: security audit trail)

✅ **Domain Vocabulary (Brasaland):**
- Locations: COL-01 to COL-10, FLA-01 to FLA-04
- Markets: Colombia (COL), Florida (FLA)
- Currency: COP (Colombian Peso) and USD
- Event types from telemetry plan
- Product IDs (from `inventory_products` table)

✅ **Telemetry Events as Source:**
- `public.telemetry_events` is immutable source (no changes)
- `services/telemetry/analysis.py` and `/telemetry/report` unchanged
- New pipeline is separate (new schema, new endpoints, new audience)

---

## Answers to Key Design Questions

### Idempotency

**Q1: Duplicates at the source**  
*How do you prevent counting the same action twice?*

**A:** Deduplication key is `eventId` (extracted from `tags._telemetry.eventId`). If the same event arrives twice (e.g., retry), the envelope's eventId is identical. Extraction layer groups by eventId, taking the first occurrence. Aggregation then counts unique eventIds per location per day.

**Q2: Re-run after failure**  
*If pipeline dies during load, how do you guarantee the same outcome?*

**A:** UPSERT by (report_date, location_id). Second run queries same event set, computes same aggregations, executes UPSERT. Rows with matching date + location are updated (not inserted again). No duplicates result.

**Q3: Late events**  
*How do you recompute daily metrics without inflating numbers?*

**A:** 48-hour recompute window. If event arrives after daily run, next scheduled run includes yesterday in its lookback. UPSERT updates yesterday's row with new total. Audit log records `late_event_count` and `invalidation_trigger = 'late_event_recompute'`.

### Observability

**Q4: Silence vs. true absence**  
*How do you distinguish zero activity from failed capture?*

**A:** Minimum signals:
- `extraction_record_count` > 0 (events exist)
- `late_event_count` (indicates freshness issues if high)
- `run_start_time` and `run_end_time` (absence of end_time = still running or crashed)
- Alert if no rows loaded for 3+ consecutive days

**Q5: Collection traceability**  
*How do you detect gaps or bursts in data?*

**A:** Correlate `run_id` to all rows loaded in that run. Each row in `daily_operations_rollup` can be traced back to the specific pipeline_run that created/updated it. Query: `WHERE run_id = 'xyz'` retrieves all data from one execution. Burst detection: compare `extraction_record_count` day-to-day; spike = anomaly.

**Q6: Growth vs. data loss**  
*How do you distinguish business growth from data capture failures?*

**A:** Compare `daily_sales_cop` day-over-day with `extraction_record_count`. If sales spike but event count drops → likely data loss. If both spike = real growth. Cross-check with active session count or location open hours (independent signal).

### Recoverability

**Q7: Database outage**  
*Where do you resume if connection drops mid-load?*

**A:** `phase_checkpoint` recorded before each stage. If load fails, checkpoint = "TRANSFORM_COMPLETE". Next run detects this, skips extraction/transform, re-attempts load only. Transformation result is deterministic (same aggregate values), so retry is safe.

**Q8: Frontend buffer**  
*Should we buffer offline events in the browser?*

**A:** Yes, for resilience. Browser buffers events in localStorage during offline. On reconnect, sends batch. Risk: duplicate events if user retries manually + auto-send. Mitigation: server-side dedup on `eventId` (already in place). Client should NOT send same event twice; track sent event IDs locally.

**Q9: Transmission retry**  
*How do we design retries without breaking idempotency?*

**A:** Use `Idempotency-Key` header = eventId. Client sets this on POST /telemetry/events. Server stores eventId as `id` in telemetry_events. If retry arrives, server checks: if eventId exists, return 200 OK (not 201 Created). Client treats 200 as success; no duplicate inserted.

### Cross-Cutting

**Q10: Concurrent runs**  
*How do we handle overlapping cron + manual trigger?*

**A:** Window lock using `reporting.pipeline_runs`. Before flow starts, insert row with `status = 'RUNNING'` and unique `run_id`. If another flow tries to start, it queries: "SELECT COUNT(*) WHERE status = 'RUNNING'". If count > 0, flow exits with error "Pipeline already running. Try again after: [end_time + 5 min]". Scheduled cron will not trigger if manual run is active.

---

## Summary: What This Design Delivers

| Requirement | How It's Addressed |
|-------------|-------------------|
| Idempotency | UPSERT by date + location; dedup by eventId; deterministic aggregation |
| Observability | Execution log with 10+ fields; run_id tracing; invalidation triggers |
| Recoverability | Phase checkpoints; lazy re-run from last clean state |
| Business-Focused | Metrics answering leadership questions (sales, inventory, SLAs) |
| Separate Pipeline | New schema (reporting.*), new endpoints (/reporting/*), immutable telemetry source |
| Domain Accuracy | Uses Brasaland locations, markets, currencies, and event types exactly as defined |
| Prefect Integration | Daily_business_performance_flow + 3 tasks + config blocks; ready for Part 2 implementation |
| Production-Ready | Handles late events, concurrent runs, failures, and audits fully |

---

## Next Steps (Part 2: Implementation)

1. Create `data/pipelines/reporting_flows.py` with Prefect flows and tasks
2. Implement `services/reporting/` module with 3 endpoints
3. Create destination tables in Supabase: `reporting.daily_operations_rollup`, `reporting.pipeline_runs`, `reporting.location_product_inventory`
4. Add monitoring and alerts (Slack integration optional)
5. Test idempotency with manual failure scenarios

---

**Document prepared for 4Geeks Academy AI Engineering milestone review.**
