# Telemetry Analysis Pipeline

## Overview

This telemetry analysis system provides operational metrics for the Brasaland Digital system. It transforms raw telemetry events into actionable technical insights for monitoring system health, performance, and reliability.

## Architecture

### Components

1. **Analysis Pipeline** (`services/api/telemetry/analysis.py`)
   - Four independent metric functions that calculate operational dimensions
   - Each function follows the pattern: load (SQL) → refine (Pandas) → convert types → group → aggregate → serve
   - Functions are side-effect-free and independently callable

2. **Report Endpoint** (`services/api/routers/telemetry.py`)
   - GET `/telemetry/report` - Returns operational metrics as JSON
   - Accepts optional `start_date` and `end_date` query parameters (ISO 8601 format)
   - Defaults to last 7 days if dates not provided
   - Requires authentication
   - Implements 60-second TTL caching

3. **Visual Dashboard** (`uis/backoffice/public/telemetry/`)
   - Provides technical visualization of metrics
   - Interactive date range picker
   - Displays data in both table and chart formats

## Metric Functions

### 1. Events by Type and Day (`events_by_type_and_day`)
**Question**: Which events occur and how often?

**Output**: List of records with:
- `date`: Event date (string)
- `event_type`: Type of event
- `count`: Number of events that day

**Use Case**: Identifying system activity patterns and understanding which event types are most frequent

### 2. Error Rate by Type (`error_rate_by_type`)
**Question**: Which event types have the highest error rates?

**Output**: List of records with:
- `event_type`: Type of event
- `error_count`: Number of events with level='error'
- `total_count`: Total events of this type
- `error_rate`: Ratio of errors to total (0.0 to 1.0)

**Use Case**: Identifying which features or systems are least reliable

### 3. API Latency by Day (`api_latency_by_day`)
**Question**: How fast is the API responding?

**Output**: List of records with:
- `date`: Event date (string)
- `avg_latency_ms`: Average response time in milliseconds
- `min_latency_ms`: Minimum response time
- `max_latency_ms`: Maximum response time

**Use Case**: Detecting performance degradation and identifying slow days

### 4. Authentication Failure Rate (`auth_failure_rate`)
**Question**: How often do login attempts fail?

**Output**: List of records with:
- `date`: Event date (string)
- `login_failed`: Number of failed login attempts
- `login_succeeded`: Number of successful login attempts
- `total_logins`: Total login attempts (failed + succeeded)
- `failure_rate`: Ratio of failures (0.0 to 1.0)

**Use Case**: Monitoring authentication system health and detecting security issues

## Implementation Details

### Formula for Any Report
```
load (SQL) → refine (Pandas) → convert types → group → aggregate → serve
```

**Key principles**:

1. **Load (SQL)**: Fetch only relevant data
   - Filter `event_type` and timestamp range in SQL
   - Use indexed columns for efficiency
   - Load full events for metrics that need all types (e.g., error ratios)

2. **Refine (Pandas)**: Extract and clean data
   - Extract tags dimensions
   - Drop rows with null dimensions
   - Apply row-level filters

3. **Convert Types**: Ensure correct data types
   - **Critical**: Convert timestamps with `pd.to_datetime(..., utc=True)` BEFORE groupby
   - Without UTC conversion, groupby produces incorrect groups silently

4. **Group & Aggregate**: Transform to metrics
   - Group by temporal or operational dimension
   - Aggregate with `.count()`, `.sum()`, or `.mean()`

5. **Serve**: Return JSON-serializable format
   - Use `.reset_index().to_dict(orient='records')`
   - Direct serialization to JSON

### Caching Strategy

The `/telemetry/report` endpoint uses a 60-second TTL cache:

- **Cache Key**: `{start_date}:{end_date}` combination
- **TTL**: 60 seconds (configurable)
- **Thread-safe**: Uses `TTLCache` from `services/api/cache.py`
- **Benefit**: Avoids recalculating expensive aggregations for repeated requests

The metric calculation runs only once per cache entry, with results reused for all subsequent requests within the TTL window.

## API Usage

### Request
```bash
GET /telemetry/report?start_date=2024-11-13T00:00:00%2B00:00&end_date=2024-11-20T00:00:00%2B00:00
Authorization: Bearer <token>
```

### Query Parameters
- `start_date` (optional): ISO 8601 datetime, inclusive, UTC (default: 7 days ago)
- `end_date` (optional): ISO 8601 datetime, exclusive, UTC (default: now)

### Response
```json
{
  "period": {
    "from": "2024-11-13T00:00:00+00:00",
    "to": "2024-11-20T00:00:00+00:00"
  },
  "metrics": {
    "events_per_day": [
      {
        "date": "2024-11-13",
        "event_type": "api_request_completed",
        "count": 1234
      }
    ],
    "error_rate_by_type": [
      {
        "event_type": "api_request_completed",
        "error_count": 15,
        "total_count": 1234,
        "error_rate": 0.0122
      }
    ],
    "api_latency_by_day": [
      {
        "date": "2024-11-13",
        "avg_latency_ms": 45.2,
        "min_latency_ms": 10.5,
        "max_latency_ms": 250.8
      }
    ],
    "auth_failure_rate": [
      {
        "date": "2024-11-13",
        "login_failed": 3,
        "login_succeeded": 127,
        "total_logins": 130,
        "failure_rate": 0.0231
      }
    ]
  }
}
```

## Dashboard Usage

**URL**: `/backoffice/telemetry/`

**Features**:
- **Date Range Picker**: Select custom periods or use "Last 7 days"
- **Automatic Refresh**: Fetches new data when dates change
- **Multiple Views**: Tables and charts for each metric
- **Period Display**: Shows the exact time window being analyzed

## Dependencies

Added to `services/api/requirements.txt` and `pyproject.toml`:
- `pandas>=2.0.0,<3` - Data transformation and aggregation

## Testing

The implementation includes:
- Empty dataset handling (all functions return `[]` when no data)
- Type-safe data handling with Pandas
- Proper UTC timezone handling
- SQL injection prevention via parameterized queries

To test the endpoint:
```bash
curl "http://localhost:8000/telemetry/report" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Future Enhancements

1. **More Metrics**:
   - Availability by feature/endpoint
   - Queue depth and processing latency
   - Custom metric definitions

2. **Alerting**:
   - Define thresholds for error rates, latency
   - Send notifications when thresholds exceeded

3. **Historical Analysis**:
   - Trend detection (is error rate improving?)
   - Anomaly detection (unexpected spikes)

4. **Dashboard Enhancements**:
   - Real-time updates with WebSocket
   - Export to CSV/PDF
   - Comparison between time periods

## Troubleshooting

### "No data available"
- Verify telemetry events are being stored in the database
- Check that `telemetry_events` table has records
- Ensure date range includes events

### Incorrect grouping results
- Verify timestamps are being converted with `pd.to_datetime(..., utc=True)`
- Check SQL query filters are applied correctly
- Ensure no null values in grouping dimensions

### Cache not working
- Verify same `start_date`/`end_date` combination is used
- Check cache TTL hasn't expired (60 seconds default)
- Monitor cache hits/misses via `report_cache.hits` and `report_cache.misses`

## Technical Notes

1. **Why UTC?** All timestamps must be in UTC for consistent grouping and cross-system compatibility
2. **Why Pandas?** Provides efficient in-memory aggregation, handles null values, and produces JSON-serializable output
3. **Why separate functions?** Each metric is independent, allowing targeted queries and independent evolution
4. **Why cache?** Reduces database load and improves response time for dashboards and monitoring tools
