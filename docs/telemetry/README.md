# Telemetry Plan & Implementation Guide

## Overview

This directory contains Brasaland's comprehensive telemetry strategy for the inventory management system. The plan identifies **32 distinct events** across **7 categories**, designed to answer both mandatory business questions and emerging operational needs.

**Current Status:** ✅ Design Phase Complete (32 events designed, schemas validated)

---

## 📂 Documentation Structure

### 1. **telemetry-plan.md** (Primary Design Document)
- **9 sections** covering strategy, catalogue, envelope design, delivery strategy, and implementation
- Identifies **32 events**: 3 mandatory (from CONTEXT.md) + 29 identified opportunities
- Hypothesis-driven: each event completes the sentence "We capture X because we need to know Y, which allows us to make decision Z"
- **Stream vs. Batch classification**: 7 stream events (real-time), 24 batch events (periodic aggregation)
- **Privacy/PII strategies**: documents how sensitive data is handled (hashing, aggregation, exclusion, redaction)
- **Implementation checklist**: ready for developer handoff

### 2. **event-schemas.json** (Structured Event Definitions)
- **JSON Schema draft-07** compliant file with all 32 events
- **Event Envelope definition**: the standard structure every event must follow
- **Per-event specifications**:
  - `event_type`: entity_action format (e.g., `inbound_order_created`)
  - `description`: what the event captures
  - `properties`: explicit allowlist of permitted keys (prevents data leakage)
  - `mandatory`: boolean flag indicating BRIEFING requirement
  - `stream_or_batch`: delivery strategy
  - `contains_pii`/`contains_sensitive_data`: privacy flags
  - `sensitive_data_strategy`: how to handle PII/sensitive data
  - `decision_enabled`: concrete business/operational decision the event enables
  - `throttle_rule`: for high-frequency events

### 3. **README.md** (This File)
- Quick-reference guide to the telemetry documentation
- Instructions for developers implementing the events
- Event categories reference
- FAQ and troubleshooting

---

## 🎯 Mandatory Metrics (From CONTEXT.md)

These 3 events are **non-negotiable** and must be instrumented first:

| Event | Category | Hypothesis | Decision |
|-------|----------|-----------|----------|
| `stock_threshold_breached` | inventory_operations | Stock levels fall below minimum | Procurement places emergency orders immediately |
| `direct_stock_edit_rejected` | inventory_operations_security | Operators attempt unauthorized direct edits | Security/compliance confirms constraint enforcement |
| `user_login_successful` | authentication | User authenticates successfully | Operations verifies all locations maintain activity |

---

## 📊 Event Categories (7 Total)

### 1. **Inventory Operations** (8 events)
Core business events tracking stock movements, orders, thresholds, and validations.

- `inbound_order_created` → `inbound_order_received`
- `outbound_order_created` → `outbound_order_allocated` → `outbound_order_fulfilled` or `outbound_order_cancelled`
- `stock_threshold_breached` (mandatory)
- `stock_validation_failed`
- `product_stock_query`

**Decision:** Daily sales per location, inventory levels, order fulfillment time

### 2. **Inventory Operations Security** (1 event)
Audit trail for unauthorized direct stock modification attempts.

- `direct_stock_edit_rejected` (mandatory, stream)

**Decision:** Compliance confirms system enforces non-negotiable business rule

### 3. **Authentication** (3 events)
User login, session, and authentication flow tracking.

- `user_login_successful` (mandatory, batch)
- `session_created`
- `session_expired`

**Decision:** Identity verification, peak usage hours, session timeout tuning

### 4. **Authentication Security** (2 events)
Login failures, permission denials, account security.

- `user_login_failed` (stream, threshold alert on >3 fails per 10 min)
- `permission_denied`

**Decision:** Brute force detection, role-based access control verification

### 5. **Performance** (2 events)
API response times, database query performance.

- `api_request_completed` (sampled 1 in 10)
- `database_query_slow` (threshold alert >1000ms)

**Decision:** Infrastructure capacity planning, bottleneck identification

### 6. **Performance & Reliability** (10 events)
System health, errors, background jobs, caching, external services.

- `service_error_occurred` (critical 5xx errors alert immediately)
- `background_job_failed` (operational alert)
- `api_error_response` (hourly aggregation)
- `cache_invalidated` (hourly aggregation)
- `external_api_call` (sampled 1 in 10)
- `feature_flag_evaluated` (sampled 1 in 50)

**Decision:** System stability monitoring, error prioritization, vendor reliability

### 7. **User Navigation** (6 events)
Which sections operators visit, which workflows they abandon, feature adoption.

- `page_viewed` (throttled 1 per 30s per page)
- `feature_clicked` (debounce 500ms)
- `workflow_abandoned`
- `report_generated`
- `bulk_import_started` / `bulk_import_completed`

**Decision:** UI optimization, feature adoption, workflow redesign

### 8. **Inventory Reconciliation** (2 events)
Physical count vs. system verification.

- `inventory_reconciliation_started`
- `inventory_reconciliation_completed`

**Decision:** Data quality monitoring, accuracy trending, process improvement

### 9. **Supplier Performance** (1 event)
Procurement metric tracking and vendor evaluation.

- `supplier_performance_updated` (weekly aggregation)

**Decision:** Vendor negotiation, supply chain optimization, supplier replacement

---

## 🏗️ Event Envelope Design

Every event **must** follow this standard structure:

```json
{
  "eventId": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-01-30T14:30:00.000Z",
  "sessionId": "session_12345" or "system" (for automated events),
  "userId": "user_67890" or "system" (for automated events),
  "event_type": "inbound_order_created",
  "schemaVersion": "1.0",
  "requestId": "req_abcdef123456",
  "properties": {
    // Event-specific payload (see allowlist)
  }
}
```

### Envelope Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `eventId` | UUID v4 | ✅ | Unique event identifier (prevents deduplication) |
| `timestamp` | ISO 8601 | ✅ | UTC timestamp (enable time-series correlation) |
| `sessionId` | string | ✅ | Session ID or "system" for automated processes |
| `userId` | string | ✅ | User ID or "system" for automated processes |
| `event_type` | string | ✅ | entity_action format (e.g., `inbound_order_created`) |
| `schemaVersion` | string | ✅ | Schema version for backward compatibility (e.g., "1.0") |
| `requestId` | string | ✅ | Correlation ID linking frontend→backend→logs (enables tracing) |
| `properties` | object | ✅ | Event-specific payload (must match allowlist) |

---

## 🚀 Stream vs. Batch Strategy

The plan classifies events based on **business urgency**, not technical preference:

### **Stream Events** (7 total — real-time processing required)
Processed **immediately** when triggered; suitable for:
- Real-time alerts (stock threshold, security breaches)
- System health monitoring (critical errors, slow queries)
- Audit trails (direct stock edit attempts)

**Examples:**
- `stock_threshold_breached` → 1-2 second SLA (enable emergency procurement)
- `direct_stock_edit_rejected` → <100ms SLA (audit compliance)
- `service_error_occurred` (5xx) → <5 second SLA (immediate operational response)

**Implementation:** Publish to message queue (e.g., Kafka, RabbitMQ) with immediate consumer

### **Batch Events** (24 total — periodic aggregation)
Processed in **periodic batches** (hourly/daily); suitable for:
- Trend analysis and reporting
- Aggregated metrics (daily sales, error rates)
- Non-urgent operational data

**Examples:**
- `outbound_order_created` → hourly batch (daily sales per location)
- `api_request_completed` → hourly percentile aggregation (p50/p95/p99)
- `inventory_reconciliation_completed` → daily reporting (accuracy trending)

**Implementation:** Collect to data warehouse; run scheduled batch jobs

---

## 🛡️ Privacy & PII Handling

### Classification Strategy

Each event declares:
- `contains_pii`: boolean (email, username, real names, etc.)
- `contains_sensitive_data`: boolean (passwords, payment info, audit-critical data)
- `sensitive_data_strategy`: how to anonymize/sanitize before emission

### Strategies Used

| Strategy | Example | Use Case |
|----------|---------|----------|
| **Hashing** | SHA-256(username) → `abc123...` | User identification without PII |
| **Aggregation** | count of failed logins (not which user) | Trend analysis without individual data |
| **Exclusion** | Never log passwords, full emails | Never capture at source |
| **Redaction** | Email domain only: `****@example.com` | Business-relevant, anonymized |
| **Secure Audit Log** | Retain raw data in restricted log; anonymized copy to analytics | Compliance + analytics balance |

### Examples from This Plan

| Event | PII/Sensitive? | Strategy | Result |
|-------|---|----------|--------|
| `user_login_failed` | ✅ PII (username) | Hash username | Only `userIdentifierHash` sent to analytics |
| `direct_stock_edit_rejected` | ✅ PII (user ID) | Secure audit log + anonymized analytics copy | Full data in audit log; hashed user in analytics |
| `api_request_completed` | ❌ No | None | Full properties sent to pipeline |
| `stock_threshold_breached` | ❌ No | None | Full properties sent to pipeline |

---

## 📋 Throttling & Debouncing Rules

High-frequency events must be throttled to prevent data explosion while preserving signal:

| Event | Frequency | Throttle Rule | Justification |
|-------|-----------|---------------|---------------|
| `page_viewed` | High (UI framework) | 1 event per page per 30s | User refreshing same page doesn't generate 100 events |
| `feature_clicked` | High (user clicking) | Debounce 500ms | Prevents duplicate events from rapid clicks |
| `api_request_completed` | Very high (every request) | Sample 1 in 10 (hash-based) | Enough for percentile analysis without overwhelming pipeline |
| `api_error_response` | Medium (errors only) | Aggregate by endpoint + status_code hourly | Identify error patterns without noise |
| `external_api_call` | Medium (service calls) | Sample 1 in 10 for high-volume services | Monitor reliability without oversampling |
| `feature_flag_evaluated` | Very high (every request checks flags) | Sample 1 in 50 | Lightweight feature tracking |
| `database_query_slow` | Low (slow queries only) | Dedup same query type per 5 min | Alert once per 5 min per query type, not every occurrence |
| `stock_threshold_breached` | Low (threshold crosses rare) | 1 alert per product per location per 1 hour | Prevent alert spam if threshold oscillates |

**Key Principle:** Throttling is **deterministic** (hash-based sampling) so no event is "lost" — the same requestId always hashes the same way.

---

## 🔀 Correlation Strategy

Every event includes `requestId` to enable **end-to-end tracing**:

```
User clicks "Create Order" button (frontend generates requestId: req_123)
  ↓ Frontend emits feature_clicked with requestId: req_123
  ↓ User submits form via API
  ↓ Backend receives request; logs it with requestId: req_123
  ↓ Backend creates inbound_order_created event with requestId: req_123
  ↓ Database writes order; triggers audit log with requestId: req_123
  ↓ All events correlated by requestId: req_123
```

This enables questions like:
- "What events happened during this user's session?"
- "What backend events were triggered by this frontend click?"
- "What errors occurred during this order creation attempt?"

---

## 📖 Developer Implementation Guide

### For Each Event, You Must:

1. **Identify instrumentation point** (location in code where event is emitted)
2. **Generate eventId** (UUID v4)
3. **Add timestamp** (call now() in UTC)
4. **Retrieve sessionId/userId** (from request context or session storage)
5. **Generate requestId** (or pass from frontend if available)
6. **Build properties object** (match allowlist exactly — nothing extra)
7. **Check payload size** (keep properties <10KB to avoid pipeline rejection)
8. **Emit event** (send to appropriate destination: stream queue or batch collector)

### Example: Instrumentation of `inbound_order_created`

```python
# In FastAPI endpoint that creates inbound order
@app.post("/orders/inbound")
async def create_inbound_order(order: InboundOrderRequest, request: Request):
    # ... validate and create order in database ...
    
    # Emit telemetry event
    event = {
        "eventId": str(uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "sessionId": request.session.get("session_id", "system"),
        "userId": request.user.id if request.user else "system",
        "event_type": "inbound_order_created",
        "schemaVersion": "1.0",
        "requestId": request.headers.get("X-Request-ID", str(uuid4())),
        "properties": {
            "orderId": order.id,
            "supplierId": order.supplier_id,
            "locationId": order.location_id,
            "productCount": len(order.items),
            "totalQuantity": sum(item.quantity for item in order.items),
            "totalCost": order.total_cost,
            "currency": order.currency
        }
    }
    
    # Emit to batch collector
    telemetry_client.emit_batch(event)
```

### Validation Checklist Before Deployment

- [ ] All 32 events implemented
- [ ] All mandatory events (3 total) emit correctly
- [ ] All properties match allowlist (no extra keys)
- [ ] No PII/sensitive data outside sanitization strategy
- [ ] Stream events (7 total) emit to message queue with <1s latency
- [ ] Batch events (24 total) collected to staging area for hourly/daily runs
- [ ] Throttling rules applied (sampling, debouncing, deduplication)
- [ ] Correlation IDs (requestId) flow end-to-end
- [ ] Telemetry payload size <10KB per event
- [ ] No events swallow business-critical exceptions (emit, then re-raise)
- [ ] Error events never cause application failure (best-effort emission)

---

## 🎯 Event Catalog Quick Reference

### By Business Area

**Inventory Management (8 events)**
- `inbound_order_created`, `inbound_order_received`
- `outbound_order_created`, `outbound_order_allocated`, `outbound_order_fulfilled`, `outbound_order_cancelled`
- `stock_validation_failed`, `product_stock_query`

**Stock Alerts (1 event)**
- `stock_threshold_breached` ⚠️ **Stream, Real-time**

**Security (3 events)**
- `direct_stock_edit_rejected` ⚠️ **Stream, Audit**
- `user_login_failed` ⚠️ **Stream (threshold alert)**
- `permission_denied`

**Authentication (3 events)**
- `user_login_successful`, `session_created`, `session_expired`

**Performance (3 events)**
- `api_request_completed`, `api_error_response`, `database_query_slow` ⚠️ **Stream (threshold)**

**System Health (6 events)**
- `service_error_occurred` ⚠️ **Stream (critical 5xx)**
- `background_job_failed` ⚠️ **Stream**
- `cache_invalidated`, `external_api_call`, `feature_flag_evaluated`

**Navigation & Analytics (6 events)**
- `page_viewed`, `feature_clicked`, `workflow_abandoned`, `report_generated`
- `bulk_import_started`, `bulk_import_completed`

**Operational (3 events)**
- `inventory_reconciliation_started`, `inventory_reconciliation_completed`
- `supplier_performance_updated`

### By Delivery Strategy

**Stream (Real-time, 7 events)**
- `stock_threshold_breached`
- `direct_stock_edit_rejected`
- `user_login_failed` (threshold alert)
- `service_error_occurred` (critical 5xx)
- `database_query_slow` (>1000ms)
- `background_job_failed`
- `outbound_order_allocated`
- `outbound_order_fulfilled`

**Batch (Periodic, 24 events)**
- All others (inventory operations, authentication, performance, navigation, reconciliation, supplier performance)

---

## ⚠️ Risks & Exclusions (From telemetry-plan.md)

### Events Considered But Discarded

| Event | Reason |
|-------|--------|
| `user_location_changed` (GPS tracking) | Privacy concern; Brasaland operates in 2 countries with strict data regulations |
| `payment_processed` | PCI-DSS compliance; never log payment details even hashed |
| `email_sent` | External service dependency; not actionable by operations team |
| `keyboard_input_logged` | Privacy & compliance violation; not needed for decision-making |
| `all_database_queries` (verbose logging) | Performance killer; would overwhelm pipeline with noise |

### Data Explicitly NOT Captured

- **Passwords or credentials** (never, not even hashed)
- **Full email addresses** (domain only if business-relevant)
- **Payment information** (amounts only, never card/account details)
- **GPS/location tracking** (legal risk in EU/LATAM operations)
- **Detailed stack traces** (error type + message only)
- **Full request/response bodies** (endpoint + method only)

### Compliance & Legal Considerations

- **GDPR:** EU users (Brasaland Colombian operations may be accessed from EU) — no PII without consent
- **Colombian data protection law:** Similar restrictions — anonymize user identifiers
- **PCI-DSS:** Never log payment data even in sanitized form
- **Business risk:** No compliance = no audit trail = uninsurable

---

## 🔧 Configuration & Customization

### Environment Variables (Recommended)

```bash
# Telemetry configuration
TELEMETRY_ENABLED=true              # Master on/off switch
TELEMETRY_STREAM_DESTINATION=kafka  # or rabbitmq, pubsub, etc.
TELEMETRY_BATCH_WINDOW_HOURS=1      # 1 hour batch windows
TELEMETRY_SAMPLE_RATE=0.1           # 10% sampling for high-frequency events
TELEMETRY_THROTTLE_ENABLED=true     # Apply throttle rules
TELEMETRY_PII_STRATEGY=hash          # hash, redact, or exclude
```

### Customization Points

If your implementation differs from this design, document **why**:
- Different stream destination (Kafka vs. RabbitMQ)?
- Different batch window (hourly vs. daily)?
- Different sampling rate?
- Skip a low-value event?
- **Document the decision** in `TELEMETRY_CUSTOMIZATIONS.md`

---

## 🧪 Testing the Telemetry System

### Unit Tests (Per Event)

```python
# Test that inbound_order_created event is emitted correctly
def test_inbound_order_created_event_emitted():
    client = APIClient()
    response = client.post("/orders/inbound", json=order_payload)
    assert response.status_code == 201
    
    # Verify event was emitted
    event = telemetry_mock.get_last_emitted_event()
    assert event["event_type"] == "inbound_order_created"
    assert event["properties"]["orderId"] == response.json()["id"]
    assert all(k in event["properties"] for k in allowlist)
    assert no_extra_keys(event["properties"], allowlist)
```

### Integration Tests

```python
# Verify stream events reach Kafka within 100ms
# Verify batch events are collected hourly
# Verify throttling rules (1 page_viewed per 30s, etc.)
# Verify correlation IDs flow end-to-end
# Verify no PII in analytics pipeline
```

### Validation Queries (Post-Deployment)

```sql
-- Daily sales per location (business requirement)
SELECT 
  DATE(timestamp) as date,
  userId as location,
  COUNT(DISTINCT CASE WHEN event_type = 'outbound_order_created' THEN orderId END) as orders_per_day
FROM telemetry
GROUP BY date, userId;

-- Which products cause validation errors?
SELECT 
  productId,
  COUNT(*) as error_count,
  ARRAY_AGG(DISTINCT errorType) as error_types
FROM telemetry
WHERE event_type = 'stock_validation_failed'
GROUP BY productId
ORDER BY error_count DESC;

-- Failed login attempts (security)
SELECT 
  DATE_TRUNC('hour', timestamp) as hour,
  COUNT(*) as failed_attempts
FROM telemetry
WHERE event_type = 'user_login_failed'
GROUP BY hour
ORDER BY hour DESC;
```

---

## 📞 Support & Questions

### Common Implementation Questions

**Q: Can I emit extra properties beyond the allowlist?**
A: No. The allowlist is the contract — emit only listed properties. This prevents accidental data leakage.

**Q: What if I need to capture a new event?**
A: Document it, propose to tech lead, add to event-schemas.json with new schemaVersion, deploy in separate release.

**Q: Can I batch stream events?**
A: No. Stream events (stock threshold, security events) must emit immediately for decision-making.

**Q: How do I handle telemetry failures?**
A: Never fail the business operation for telemetry. Log emission errors; alert ops; never re-raise.

**Q: What's the PII policy?**
A: Never emit PII without hashing. Hashing strategy in `sensitive_data_strategy` field per event.

### Contacts

- **Telemetry Design:** Refer to telemetry-plan.md
- **Schema Questions:** Refer to event-schemas.json + this README
- **Implementation Help:** Contact Nicolás (Infrastructure Lead)
- **Privacy/Compliance:** Contact legal team (before capturing new data types)

---

## 📈 Success Metrics (Month 1)

- [ ] All 32 events successfully emitted in production
- [ ] 100% of mandatory events (3) have >99.9% emission rate
- [ ] Stream events <1s latency measured end-to-end
- [ ] Zero PII/sensitive data in analytics pipeline (compliance audit)
- [ ] Operations answers at least 3 questions from mandatory metrics
  - "How many orders per day?" → Yes, via `outbound_order_created` batch
  - "Stock threshold alerts?" → Yes, via `stock_threshold_breached` stream
  - "Failed direct edits?" → Yes, via `direct_stock_edit_rejected` audit trail

---

## 📚 Related Documentation

- [telemetry-plan.md](./telemetry-plan.md) — Full strategy document
- [event-schemas.json](./event-schemas.json) — Structured event definitions
- [CONTEXT.md](../CONTEXT.md) — Company briefing with mandatory metrics
- [/services/admin-api/](../../services/admin-api/) — Implementation location

---

**Version:** 1.0  
**Last Updated:** January 30, 2025  
**Status:** ✅ Design Complete, Ready for Implementation  
**Review:** tech-lead@brasaland.com
