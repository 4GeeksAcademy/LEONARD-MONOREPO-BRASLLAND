# Getting Started with Telemetry Analysis Pipeline

## Quick Start Guide

### Step 1: Create the Telemetry Events Table

The telemetry system requires a database table to store events. Follow the setup instructions:

1. Open your Supabase project SQL Editor
2. Run the SQL script from `docs/telemetry/supabase-setup.md`
3. Verify the table structure with the validation queries

**Location**: `docs/telemetry/supabase-setup.md`

### Step 2: Install Dependencies

The analysis pipeline requires Pandas:

```bash
# If using pip
pip install -r services/api/requirements.txt

# If using poetry/pyproject.toml
# Dependencies will be installed automatically when you run the app
```

**Updated files**:
- `services/api/requirements.txt`
- `services/api/pyproject.toml`

### Step 3: Start the API Server

```bash
cd services/api
python -m uvicorn services.api.app.main:app --reload --port 8000
```

The telemetry endpoints will be available at:
- **POST** `/telemetry/events` - Receive telemetry events (public)
- **GET** `/telemetry/report` - Get operational metrics (authenticated)

### Step 4: Access the Dashboard

Navigate to: `http://localhost:8000/backoffice/telemetry/`

**Requirements**:
- Must be authenticated to the backoffice
- API server must be running
- Database must have telemetry_events table with data

## Testing the Endpoint

### Without Date Range (Last 7 Days)
```bash
curl "http://localhost:8000/telemetry/report" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

### With Custom Date Range
```bash
curl "http://localhost:8000/telemetry/report?start_date=2024-11-13T00:00:00Z&end_date=2024-11-20T00:00:00Z" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

### Expected Response
```json
{
  "period": {
    "from": "2024-11-13T00:00:00+00:00",
    "to": "2024-11-20T00:00:00+00:00"
  },
  "metrics": {
    "events_per_day": [...],
    "error_rate_by_type": [...],
    "api_latency_by_day": [...],
    "auth_failure_rate": [...]
  }
}
```

## File Structure

### Backend Analysis Pipeline
```
services/api/telemetry/
├── __init__.py
└── analysis.py          # 4 metric functions
```

### Backend Endpoint
```
services/api/routers/telemetry.py  # POST /events, GET /report
```

### Frontend Dashboard
```
uis/backoffice/
├── public/
│   ├── telemetry.css         # Styling
│   └── telemetry/
│       └── index.html        # Dashboard HTML
└── src/
    └── telemetry.js          # Dashboard logic
```

### Documentation
```
docs/telemetry/
├── ANALYSIS.md               # Technical documentation
├── supabase-setup.md        # Database setup (existing)
└── event-schemas.json       # Event definitions (existing)
```

## Metrics Explained

### 1. Events Per Day (`events_per_day`)
Shows the volume of different event types on each day.

**Use Case**: Understanding system activity patterns, identifying which event types are most frequent.

**Output**: 
```json
[
  {"date": "2024-11-13", "event_type": "api_request_completed", "count": 1234},
  {"date": "2024-11-13", "event_type": "user_login_successful", "count": 567}
]
```

### 2. Error Rate by Type (`error_rate_by_type`)
Shows which event types have the highest error rates.

**Use Case**: Identifying which features or systems are least reliable.

**Output**:
```json
[
  {
    "event_type": "api_request_completed",
    "error_count": 15,
    "total_count": 1234,
    "error_rate": 0.0122
  }
]
```

### 3. API Latency by Day (`api_latency_by_day`)
Shows average, minimum, and maximum response times for API requests.

**Use Case**: Detecting performance degradation, identifying slow days.

**Output**:
```json
[
  {
    "date": "2024-11-13",
    "avg_latency_ms": 45.2,
    "min_latency_ms": 10.5,
    "max_latency_ms": 250.8
  }
]
```

### 4. Auth Failure Rate (`auth_failure_rate`)
Shows daily login success/failure rates.

**Use Case**: Monitoring authentication system health, detecting security issues.

**Output**:
```json
[
  {
    "date": "2024-11-13",
    "login_failed": 3,
    "login_succeeded": 127,
    "total_logins": 130,
    "failure_rate": 0.0231
  }
]
```

## Troubleshooting

### "telemetry_events table does not exist"
- Run the database setup SQL script from `docs/telemetry/supabase-setup.md`
- Verify table is created with `SELECT * FROM telemetry_events LIMIT 1`

### "No data available" on dashboard
- Ensure your app is sending telemetry events (check if events exist in DB)
- Verify date range includes events (try expanding the range)
- Check that at least one of the event types is present in the database

### Cache not updating
- The endpoint caches results for 60 seconds
- Same date range within 60 seconds returns cached data
- Wait 60+ seconds for new data, or use different date range

### Authentication error
- Ensure you have a valid authentication token
- Dashboard requires login to backoffice
- Endpoint requires `Authorization` header with valid JWT

## Development Notes

### Adding More Metrics

To add a new metric function:

1. Create a function in `services/api/telemetry/analysis.py`:
```python
def my_metric(session: Session, start_date: datetime, end_date: datetime) -> list[dict]:
    """Calculate my metric."""
    query = text("""SELECT ... FROM telemetry_events ...""")
    result = session.execute(query, {"start_date": start_date, "end_date": end_date})
    rows = result.fetchall()
    
    if not rows:
        return []
    
    df = pd.DataFrame(rows, columns=[...])
    # Process with Pandas
    return df.reset_index(drop=True).to_dict(orient="records")
```

2. Import in `services/api/routers/telemetry.py`

3. Add to metrics dict in `get_telemetry_report()` endpoint

4. Add table rendering in `uis/backoffice/src/telemetry.js`

### Cache TTL

Default is 60 seconds. To change:

In `services/api/routers/telemetry.py`:
```python
report_cache = TTLCache(ttl=120.0)  # 120 seconds instead
```

## Performance Considerations

- **SQL Optimization**: Queries use indexed columns (timestamp, event_type)
- **Pandas Efficiency**: Uses vectorized operations, no row-by-row processing
- **Caching**: 60-second TTL reduces database hits by ~99% for typical usage
- **Date Filtering**: Exclusive end date ensures consistent results

## Security

- **Authentication Required**: Only authenticated users can access `/report` endpoint
- **SQL Injection Prevention**: All queries use parameterized statements
- **Data Isolation**: Each user sees all data (no per-user filtering in this version)

---

For detailed technical documentation, see `docs/telemetry/ANALYSIS.md`
