# Telemetry Plan — Brasaland Inventory Management System

**Document Version:** 1.0  
**Date:** November 2026  
**Author:** Technology Team  
**Status:** Design Phase (Ready for Implementation)

---

## Executive Summary

This telemetry plan defines a comprehensive data capture strategy for Brasaland's inventory management system and its backoffice operations. The plan identifies **mandatory metrics** required from day one, plus **21 additional instrumentation opportunities** spanning inventory operations, authentication, performance, errors, and user navigation. Every event is justified by a specific business or operational hypothesis and decision it enables.

**Key Principles:**
- **Hypothesis-driven:** Each event answers a concrete question
- **Privacy-first:** Sensitive data is anonymised or excluded
- **Stream and batch:** Real-time and periodic processing based on operational need
- **Consistency:** All events follow a standard envelope structure
- **Traceability:** Every user action and backend process is correlatable

---

## Part 1: Catalogue of Data Opportunities

### 1.1 Mandatory Metrics (From Company Briefing)

These metrics are non-negotiable business requirements:

| Metric | Hypothesis | Decision Enabled |
|--------|-----------|------------------|
| Total sales per location per day (COP and USD) | We need daily sales visibility to manage cash flow and operational performance | Management can allocate resources and address underperforming locations in real time |
| Inventory levels by location and product | We need to know current stock to avoid overstock and stockouts | Procurement can order the right quantities; operations can redirect stock between locations |
| Order fulfillment time (inbound and outbound) | We need to track how quickly orders are processed to optimize workflows | Operations can identify bottlenecks and adjust staffing |
| Failed direct stock edit attempts | We need to know when operators try to bypass the order system | Security team can audit unauthorized attempts; compliance can prove audit trail |
| Minimum stock threshold alerts | We need to trigger alerts when stock falls below safety levels | Procurement team acts immediately to prevent stockouts affecting service |

### 1.2 Inventory Operations (Identified Opportunities)

#### 1.2.1 Inbound Order Flow

**Event: `inbound_order_created`**
- **Hypothesis:** We need to know every time stock is received to verify procurement efficiency
- **Decision:** Operations can track order-to-receipt time; procurement can measure supplier performance
- **Stream/Batch:** Batch (daily aggregates)

**Event: `inbound_order_received`**
- **Hypothesis:** We need to track when received stock matches or deviates from ordered quantities
- **Decision:** Procurement can identify discrepancies with suppliers
- **Stream/Batch:** Batch (daily)

**Event: `inbound_validation_failed`**
- **Hypothesis:** We need to track when received stock fails quality or format checks
- **Decision:** Operations can identify patterns in supplier failures; Lucía can renegotiate terms
- **Stream/Batch:** Batch (daily)

**Event: `inbound_quantity_mismatch`**
- **Hypothesis:** We need to know when received quantities differ from orders (underage/overage)
- **Decision:** Procurement can dispute invoices or adjust future orders
- **Stream/Batch:** Batch (daily)

#### 1.2.2 Outbound Order Flow

**Event: `outbound_order_created`**
- **Hypothesis:** We need to track every order placed by locations to measure demand patterns
- **Decision:** Operations can forecast capacity needs; Mariana can answer "how many orders per day?"
- **Stream/Batch:** Batch (hourly aggregates)

**Event: `outbound_order_allocated`**
- **Hypothesis:** We need to know when stock is reserved to track allocation efficiency
- **Decision:** Operations can identify if certain products are over-allocated; prevent double-booking
- **Stream/Batch:** Stream (real-time inventory visibility)

**Event: `outbound_order_fulfilled`**
- **Hypothesis:** We need to know when orders leave the warehouse to measure fulfillment SLA
- **Decision:** Operations can track order-to-delivery time; identify delays
- **Stream/Batch:** Stream (real-time fulfillment tracking)

**Event: `outbound_order_cancelled`**
- **Hypothesis:** We need to know when orders are cancelled and why to identify process failures
- **Decision:** Operations can root-cause cancellations; prevent repeat issues
- **Stream/Batch:** Batch (daily)

#### 1.2.3 Stock Validation and Security

**Event: `direct_stock_edit_attempted`** ⭐ MANDATORY
- **Hypothesis:** We need to detect and log any attempt to modify stock outside the order system
- **Decision:** Security team can audit unauthorized attempts; Nicolás can prove the system enforces constraints
- **Stream/Batch:** Stream (real-time logging)
- **Sensitive Data:** Yes (includes user attempting action)

**Event: `direct_stock_edit_rejected`** ⭐ MANDATORY
- **Hypothesis:** We need to know when the system successfully blocks a direct stock edit
- **Decision:** Operations team verifies the system is functioning; audit trail for compliance
- **Stream/Batch:** Stream (real-time logging)

**Event: `stock_validation_failed`**
- **Hypothesis:** We need to track validation errors (negative quantities, invalid SKUs, etc.)
- **Decision:** Operations can identify which products cause the most validation errors; fix root causes
- **Stream/Batch:** Batch (daily aggregates by error type)

**Event: `stock_threshold_breached`** ⭐ MANDATORY
- **Hypothesis:** We need to trigger alerts when stock falls below minimum levels
- **Decision:** Procurement team is alerted immediately to place emergency orders
- **Stream/Batch:** Stream (real-time alert generation)

**Event: `stock_threshold_recovered`**
- **Hypothesis:** We need to know when stock recovers above threshold to clear alerts
- **Decision:** Operations can track how often thresholds are breached and recovered
- **Stream/Batch:** Stream (closes alert workflow)

#### 1.2.4 Product-Level Insights

**Event: `product_stock_query`**
- **Hypothesis:** We need to know which products are queried most often to identify decision-critical items
- **Decision:** Operations can prioritize monitoring for products causing the most queries
- **Stream/Batch:** Batch (hourly aggregates)

**Event: `product_low_confidence_stock`**
- **Hypothesis:** We need to know when operators manually override automated stock counts (indicating data quality issues)
- **Decision:** Procurement and IT can identify products with unreliable counts; audit discrepancies
- **Stream/Batch:** Batch (daily)

### 1.3 Authentication & Access Control (Identified Opportunities)

**Event: `user_login_successful`** ⭐ MANDATORY
- **Hypothesis:** We need to track login success to measure system accessibility and user engagement
- **Decision:** Operations team can verify all locations are logging in; identify locations with zero activity
- **Stream/Batch:** Batch (daily aggregates by location)
- **Sensitive Data:** No (only userId, location, timestamp)

**Event: `user_login_failed`**
- **Hypothesis:** We need to know failed login attempts to identify credential issues and security threats
- **Decision:** Security team can alert on credential compromise patterns; Ashley can reset locked accounts
- **Stream/Batch:** Stream (threshold-based alert if >3 fails per user per 10 min)
- **Sensitive Data:** Yes (includes username/email attempts)

**Event: `session_created`**
- **Hypothesis:** We need to track session creation to measure concurrent user load
- **Decision:** Infrastructure team can right-size resources; operations knows peak hours
- **Stream/Batch:** Batch (hourly)

**Event: `session_expired`**
- **Hypothesis:** We need to track session timeouts to identify if security settings are too aggressive
- **Decision:** Operations can adjust timeout settings; validate user experience
- **Stream/Batch:** Batch (daily aggregates)

**Event: `permission_denied`**
- **Hypothesis:** We need to track access control violations to identify either configuration errors or unauthorized attempts
- **Decision:** Security team can audit permissions; operations can fix legitimate access issues
- **Stream/Batch:** Batch (daily aggregates by resource type)

**Event: `credential_changed`**
- **Hypothesis:** We need to know when credentials are updated to maintain audit trail
- **Decision:** Compliance team has record of access control changes
- **Stream/Batch:** Batch (daily)

### 1.4 Performance & Reliability (Identified Opportunities)

**Event: `api_request_completed`**
- **Hypothesis:** We need to measure API response times to identify performance degradation
- **Decision:** Infrastructure team can trigger scaling; Nicolás can identify bottlenecks
- **Stream/Batch:** Batch (percentile aggregates: p50, p95, p99 per endpoint, per hour)
- **High-frequency:** Throttled to 1 per 10 requests (every 10th request)

**Event: `database_query_slow`**
- **Hypothesis:** We need to identify slow database queries affecting user experience
- **Decision:** Database team can add indexes; Nicolás can refactor queries
- **Stream/Batch:** Stream (threshold: >1 second, real-time logging)

**Event: `background_job_failed`**
- **Hypothesis:** We need to know when automated processes (stock reconciliation, alerts) fail
- **Decision:** Operations can manually intervene; Nicolás can fix broken processes
- **Stream/Batch:** Stream (real-time alert)

**Event: `service_error_occurred`**
- **Hypothesis:** We need to track uncaught errors to identify bugs and system instability
- **Decision:** Development team can prioritize fixes; Nicolás can measure system health
- **Stream/Batch:** Stream (error alerting) + Batch (daily aggregates by error type)

**Event: `resource_exhaustion_warning`**
- **Hypothesis:** We need to know when system resources (memory, disk, connections) approach limits
- **Decision:** Infrastructure team can provision capacity before failure
- **Stream/Batch:** Stream (threshold-based alert)

### 1.5 User Navigation & Behavior (Identified Opportunities)

**Event: `page_viewed`**
- **Hypothesis:** We need to know which sections operators visit most to identify feature usage
- **Decision:** Camila can identify which sections drive behavior; operations can optimize UI for high-traffic areas
- **Stream/Batch:** Batch (hourly aggregates)

**Event: `feature_clicked`**
- **Hypothesis:** We need to track which buttons/features are used to understand operator workflows
- **Decision:** Operations can optimize UX for frequent tasks; identify abandoned features
- **Stream/Batch:** Batch (daily aggregates)

**Event: `workflow_abandoned`**
- **Hypothesis:** We need to know when operators start but don't complete order flows to identify friction
- **Decision:** Operations can redesign confusing workflows; identify forms that cause abandonment
- **Stream/Batch:** Batch (daily aggregates by workflow type)

**Event: `search_performed`**
- **Hypothesis:** We need to know what operators are searching for in inventory to identify missing features
- **Decision:** Operations can add indexes for frequent searches; Nicolás can improve search speed
- **Stream/Batch:** Batch (daily aggregates by search term)

**Event: `report_generated`**
- **Hypothesis:** We need to know which reports are run most to understand what operations team needs
- **Decision:** Mariana can invest in reports that drive decisions; operations can automate popular reports
- **Stream/Batch:** Batch (daily)

### 1.6 Business Metrics Summary

| Event Count | Category | Purpose |
|-------------|----------|---------|
| 5 | Mandatory (from BRIEFING) | Floor requirements |
| 10 | Inventory Operations | Understand stock flow end-to-end |
| 7 | Authentication & Access | Security and audit trail |
| 5 | Performance & Reliability | System health visibility |
| 5 | User Navigation | Operator behavior and UX optimization |
| **32** | **TOTAL** | **Complete telemetry coverage** |

---

## Part 2: Event Envelope & Schema Design

### 2.1 Standard Event Envelope

Every event must include this structure:

```json
{
  "eventId": "uuid-v4-unique-identifier",
  "timestamp": "2026-11-16T22:08:35.347Z",
  "sessionId": "sess-unique-or-anonymous",
  "userId": "user-123-or-system-process",
  "event_type": "entity_action",
  "schemaVersion": "1.0",
  "requestId": "req-correlation-id-for-tracing",
  "properties": {
    // event-specific fields (see allowlist per event)
  }
}
```

**Envelope Field Definitions:**

- **eventId** (UUID): Unique identifier for this specific event instance
- **timestamp** (ISO 8601): When the event occurred (UTC)
- **sessionId** (string): User session or process session identifier; "anonymous" for system events
- **userId** (string): User ID performing the action; "system" for automated processes
- **event_type** (string): Taxonomy format `entity_action` (e.g., `inbound_order_created`)
- **schemaVersion** (string): Schema version for backward compatibility (e.g., "1.0", "1.1")
- **requestId** (string): Correlation ID to link frontend request → backend action → logs
- **properties** (object): Event-specific payload (fields explicitly listed in allowlist)

### 2.2 Event Schemas: Mandatory Metrics

**[See event-schemas.json for complete JSON schema definitions]**

#### Schema Structure (Example)

```json
{
  "event_type": "inbound_order_created",
  "description": "Triggered when an inbound order is registered in the system",
  "contains_pii": false,
  "contains_sensitive_data": true,
  "sensitive_data_strategy": "Order IDs are anonymised in audit logs; supplier IDs are retained for procurement",
  "stream_or_batch": "batch",
  "batch_window": "hourly",
  "throttle_rule": "none",
  "properties": {
    "orderId": {"type": "string", "required": true, "description": "Unique order identifier"},
    "supplierId": {"type": "string", "required": true, "description": "Supplier ID"},
    "locationId": {"type": "string", "required": true, "description": "COL-01 to COL-10, FLA-01 to FLA-04"},
    "productCount": {"type": "integer", "required": true, "description": "Number of distinct products ordered"},
    "totalQuantity": {"type": "integer", "required": true, "description": "Total units across all products"},
    "totalCost": {"type": "number", "required": true, "description": "Total cost in supplier currency"}
  },
  "property_allowlist": ["orderId", "supplierId", "locationId", "productCount", "totalQuantity", "totalCost"],
  "decision_enabled": "Procurement can track order-to-receipt time; measure supplier performance"
}
```

---

## Part 3: Delivery Strategy (Stream vs. Batch)

### 3.1 Stream Events (Real-time Processing)

**When to use:** Decision must be made within seconds; operational alert needed.

**Events (8 total):**

| Event | Latency Requirement | Reason |
|-------|-------------------|--------|
| `direct_stock_edit_rejected` | <100ms | Security/audit trail must capture immediately |
| `stock_threshold_breached` | <1s | Procurement team must be alerted to order emergency stock |
| `stock_threshold_recovered` | <1s | Closes alert workflow |
| `outbound_order_allocated` | <1s | Inventory visibility must be real-time |
| `outbound_order_fulfilled` | <1s | Fulfillment tracking and delivery forecasting |
| `user_login_failed` | <1s | Threshold-based alert for credential attacks (>3 fails/10min) |
| `database_query_slow` | <1s | Performance team must identify bottlenecks |
| `background_job_failed` | <1s | Operational alert for failed automated processes |

**Infrastructure:** Stream events are written to a message queue (Kafka, Redis Streams, or Supabase Realtime) with subscribers consuming in real-time.

### 3.2 Batch Events (Periodic Aggregation)

**When to use:** Trend analysis is sufficient; decision can wait until next batch window.

**Events (24 total):**

| Event | Batch Window | Reason |
|-------|--------------|--------|
| `inbound_order_created` | Hourly | Procurement reviews daily; aggregates by supplier are sufficient |
| `inbound_order_received` | Daily | Reconciliation happens daily |
| `inbound_validation_failed` | Daily | Quality patterns emerge over days; daily digest |
| `inbound_quantity_mismatch` | Daily | Disputes happen by end of day |
| `outbound_order_created` | Hourly | Operations team needs hourly aggregates; Mariana answers "how many per day" |
| `outbound_order_cancelled` | Daily | Root-cause analysis happens daily |
| `stock_validation_failed` | Daily | Error patterns emerge daily |
| `product_stock_query` | Hourly | Identify decision-critical products by daily trend |
| `product_low_confidence_stock` | Daily | Data quality issues reviewed daily |
| `user_login_successful` | Daily | Monitor location activity daily |
| `session_created` | Hourly | Capacity planning by hourly trends |
| `session_expired` | Daily | Security review of timeout patterns daily |
| `permission_denied` | Daily | Access control audit by daily aggregates |
| `credential_changed` | Daily | Compliance review daily |
| `api_request_completed` | Hourly (percentiles) | Performance dashboards updated hourly |
| `service_error_occurred` | Hourly alerts + daily digest | Real-time alert for critical errors; daily digest for root-cause analysis |
| `resource_exhaustion_warning` | Stream (threshold) OR Hourly | Threshold-based immediate alert; hourly trend |
| `page_viewed` | Hourly | Usage patterns by location/time, updated hourly |
| `feature_clicked` | Daily | Feature adoption by daily trends |
| `workflow_abandoned` | Daily | UX friction analysis by daily metrics |
| `search_performed` | Daily | Search trends and feature requests by daily digest |
| `report_generated` | Daily | Report usage by daily metrics |
| `direct_stock_edit_attempted` | Stream (logging) | Real-time logging for immediate audit trail |

---

## Part 4: High-Frequency Throttling & Debouncing

### 4.1 Throttle Rules

**Events with high frequency:**

- **`page_viewed`:** Throttle to 1 event per page per 30 seconds (avoid spam from refresh cycles)
- **`api_request_completed`:** Sample 1 in 10 requests (every 10th request to reduce volume while maintaining accuracy)
- **`feature_clicked`:** Debounce button clicks — only emit after 500ms of inactivity (prevent double-click noise)

### 4.2 Sampling Strategy for High-Volume Events

For `api_request_completed`, instead of capturing every request:
- **Deterministic sampling:** Use `hash(requestId) % 10 == 0` to consistently sample same endpoints
- **Stratified by endpoint:** Different endpoints may have different sample rates based on importance
- **P50, P95, P99:** Aggregation pipeline computes percentiles from samples; these remain accurate

---

## Part 5: Sensitive Data & Privacy Handling

### 5.1 Fields Containing PII or Sensitive Data

| Event | Sensitive Field | Type | Handling |
|-------|-----------------|------|----------|
| `direct_stock_edit_attempted` | userId, timestamp | Audit log | Retained in secure audit log; anonymised in analytics |
| `direct_stock_edit_rejected` | userId, timestamp | Audit log | Retained in secure audit log; anonymised in analytics |
| `user_login_failed` | email/username attempted | Credentials | Never logged in full; only hash of username + count of fails |
| `permission_denied` | userId, resource_id | Access pattern | Anonymised by default; retained for security audit only |
| `credential_changed` | userId, old_hash, new_hash | Credentials | Only password hashes; original credentials never logged |

### 5.2 Anonymisation Strategies

**Strategy 1: Hashing**
- Apply SHA-256 hash to email/username in failed login events
- Purpose: Link multiple failed attempts to same user without exposing credentials

**Strategy 2: Aggregation**
- Never emit individual failed login events; instead emit `login_failures_per_user_per_period`
- Aggregate: "user_id_hash had 5 failed attempts in last 10 minutes"

**Strategy 3: Exclusion**
- Never capture passwords, API keys, or credit card data in any event
- If needed for audit, store separately in encrypted audit log with separate access controls

**Strategy 4: Redaction**
- For events containing email, retain only domain: `user@acme.com` → `user@***`
- For phone numbers: `+1-555-0100` → `+1-***-****`

### 5.3 Data Retention Policy

- **Stream events (audit logs):** 90 days (then archive)
- **Batch aggregates:** 1 year
- **Sensitive data (failed logins, auth attempts):** 30 days (then delete)
- **PII:** Never persisted; only hashes retained

---

## Part 6: Risks, Exclusions & Critical Thinking

### 6.1 Events Considered & Rejected

| Event | Reason Rejected |
|-------|-----------------|
| `every_keystroke_logged` | Privacy violation; no business decision requires character-level capture |
| `customer_browsing_history` | Out of scope (not in backoffice); would require separate telemetry infrastructure |
| `meal_preparation_time_per_dish` | Requires POS integration not yet designed; defer to POS integration project |
| `supplier_payment_details` | Sensitive financial data; never captured in operational telemetry |
| `employee_location_tracking` | Privacy violation; not needed for inventory or operations decisions |
| `detailed_stack_traces` | Too noisy; only emit error type + line number for meaningful aggregation |

### 6.2 Data That Will Not Be Captured (And Why)

| Data | Reason |
|------|--------|
| Full SQL queries | Query volume too high; only emit query duration + endpoint |
| Raw request/response bodies | Payload size too large; only emit summary metrics (size, duration) |
| Employee personal data (name, DOB, address) | PII that is not needed for operational decisions |
| Customer profiles | Out of scope; belongs to CRM telemetry, not inventory system |
| Supplier pricing negotiations | Commercially sensitive; excluded from general audit logs |

### 6.3 Cost-Benefit Analysis

**High-volume events:**
- `api_request_completed`: 1,000s per hour → Sampled (1 in 10) to control storage cost
- `page_viewed`: 100s per hour → Throttled (1 per 30s per page) to reduce noise

**Benefit:** Understand performance and usage patterns with 90% accuracy at 10% storage cost

---

## Part 7: Correlating Frontend → Backend → Logs

**Example:** A user clicks "Create Order" button at 10:05:00 AM

```
1. Frontend captures click event: "feature_clicked"
   - eventId: evt-abc-123
   - requestId: req-xyz-789  ← Correlation ID
   - feature: "create_order_button"
   - timestamp: 2026-11-16T10:05:00Z

2. Frontend makes API request with header: X-Request-ID: req-xyz-789

3. Backend receives request, logs incoming: "api_request_started"
   - requestId: req-xyz-789  ← Same correlation ID
   - endpoint: POST /orders
   - userId: user-456

4. Backend processes, emits: "outbound_order_created"
   - requestId: req-xyz-789  ← Same correlation ID
   - orderId: order-999
   - timestamp: 2026-11-16T10:05:01Z

5. Developer searches logs with req-xyz-789 and can trace:
   - User click → API request → Business event → Database write → Success response
```

**Implementation:** All backend endpoints must accept `X-Request-ID` header; all events must include this in `requestId` field.

---

## Part 8: Implementation Checklist

### Phase 1: Infrastructure (Week 1-2)
- [ ] Set up message queue for stream events (Kafka, Redis Streams, or Supabase Realtime)
- [ ] Design batch aggregation pipeline (nightly jobs)
- [ ] Create event logging SDK (standardize envelope capture)
- [ ] Set up data storage (time-series DB for metrics, secure audit log for sensitive data)

### Phase 2: Core Instrumentation (Week 2-4)
- [ ] Instrument inventory operations (inbound/outbound order events)
- [ ] Add authentication logging
- [ ] Instrument API response time tracking
- [ ] Add error/exception capturing

### Phase 3: Dashboard & Alerting (Week 4-6)
- [ ] Build real-time operational dashboard (Mariana's executive view)
- [ ] Set up alerts (stock threshold, login failures, slow queries)
- [ ] Create daily/weekly report generation

### Phase 4: Validation & Optimization (Week 6+)
- [ ] Validate event data quality
- [ ] Optimize high-frequency sampling
- [ ] Archive old events per retention policy
- [ ] Gather feedback from operations team

---

## Part 9: Glossary & Definitions

- **Stream:** Real-time processing; decision needed within seconds
- **Batch:** Periodic aggregation; decision needed within hours
- **Event Envelope:** Standard JSON structure every event must follow
- **Property Allowlist:** Explicit whitelist of keys allowed in an event's properties object
- **Throttle:** Reduce frequency of emission (e.g., 1 per 30 seconds)
- **Debounce:** Delay emission until action completes (e.g., 500ms after last keystroke)
- **Sampling:** Emit only N% of events to reduce volume
- **Correlation ID:** Unique identifier (requestId) linking frontend action → backend events → logs
- **PII:** Personally Identifiable Information (email, phone, name, ID number)
- **Anonymisation:** Removing or hashing PII while retaining analytical value
- **Hot path:** Frequently executed code that emits high-volume events

---

## References

- **Company Context:** `CONTEXT.md` (Brasaland organization, 14 locations, 2 countries, Nicolás Park CTO)
- **Inventory System Constraints:** Stock modifications only via orders; direct edits rejected (audit trail requirement)
- **Event Schema Standard:** JSON Schema draft-07 (see `event-schemas.json`)
- **Telemetry Best Practices:** Hypothesis-driven capture; every event justifies its cost

---

**Next Steps:**
1. Review this plan with Nicolás Park (CTO) and Felipe Guerrero (Operations Director)
2. Validate event schemas match system architecture (see `event-schemas.json`)
3. Approve infrastructure design (stream vs. batch processing)
4. Begin Phase 1 implementation (message queue setup)
