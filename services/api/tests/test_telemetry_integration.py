"""Integration tests for telemetry analysis pipeline and endpoint."""
import json
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from sqlalchemy import text
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from services.api.telemetry.analysis import (
    events_by_type_and_day,
    error_rate_by_type,
    api_latency_by_day,
    auth_failure_rate,
)


@pytest.fixture
def test_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create telemetry_events table
    engine.execute(text("""
        CREATE TABLE telemetry_events (
            id TEXT PRIMARY KEY,
            timestamp DATETIME,
            service TEXT,
            event_type TEXT,
            level TEXT DEFAULT 'info',
            value REAL,
            message TEXT,
            tags TEXT
        )
    """))
    
    with Session(engine) as session:
        yield session


def insert_event(session, timestamp, event_type, level='info', value=None):
    """Helper to insert a test event."""
    session.execute(text("""
        INSERT INTO telemetry_events (id, timestamp, service, event_type, level, value, tags)
        VALUES (:id, :timestamp, :service, :event_type, :level, :value, :tags)
    """), {
        "id": f"event-{timestamp.timestamp()}",
        "timestamp": timestamp,
        "service": "backoffice",
        "event_type": event_type,
        "level": level,
        "value": value,
        "tags": "{}",
    })
    session.commit()


class TestEventsPerDay:
    """Tests for events_by_type_and_day metric."""
    
    def test_empty_database(self, test_session):
        """Should return empty list when no events."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        result = events_by_type_and_day(test_session, start, end)
        assert result == []
    
    def test_single_event(self, test_session):
        """Should count single event."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        insert_event(test_session, datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc), 'api_request_completed')
        
        result = events_by_type_and_day(test_session, start, end)
        assert len(result) == 1
        assert result[0]['event_type'] == 'api_request_completed'
        assert result[0]['count'] == 1
    
    def test_multiple_events_same_day(self, test_session):
        """Should aggregate events on same day."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        for hour in range(5):
            insert_event(test_session, datetime(2024, 1, 1, hour, tzinfo=timezone.utc), 'api_request_completed')
        
        result = events_by_type_and_day(test_session, start, end)
        assert len(result) == 1
        assert result[0]['count'] == 5
    
    def test_multiple_event_types(self, test_session):
        """Should separate different event types."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'api_request_completed')
        insert_event(test_session, datetime(2024, 1, 1, 11, tzinfo=timezone.utc), 'user_login_successful')
        
        result = events_by_type_and_day(test_session, start, end)
        assert len(result) == 2
        
        event_types = {r['event_type'] for r in result}
        assert event_types == {'api_request_completed', 'user_login_successful'}
    
    def test_date_filtering(self, test_session):
        """Should respect date boundaries."""
        insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'api_request_completed')
        insert_event(test_session, datetime(2024, 1, 2, 10, tzinfo=timezone.utc), 'api_request_completed')
        insert_event(test_session, datetime(2024, 1, 3, 10, tzinfo=timezone.utc), 'api_request_completed')
        
        # Query only 2024-01-02
        start = datetime(2024, 1, 2, tzinfo=timezone.utc)
        end = datetime(2024, 1, 3, tzinfo=timezone.utc)
        result = events_by_type_and_day(test_session, start, end)
        
        assert len(result) == 1
        assert result[0]['date'] == '2024-01-02'


class TestErrorRate:
    """Tests for error_rate_by_type metric."""
    
    def test_empty_database(self, test_session):
        """Should return empty list when no events."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        result = error_rate_by_type(test_session, start, end)
        assert result == []
    
    def test_no_errors(self, test_session):
        """Should show 0% error rate when no errors."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        for _ in range(10):
            insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'api_request_completed', level='info')
        
        result = error_rate_by_type(test_session, start, end)
        assert len(result) == 1
        assert result[0]['error_count'] == 0
        assert result[0]['total_count'] == 10
        assert result[0]['error_rate'] == 0.0
    
    def test_all_errors(self, test_session):
        """Should show 100% error rate when all errors."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        for _ in range(5):
            insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'api_request_completed', level='error')
        
        result = error_rate_by_type(test_session, start, end)
        assert len(result) == 1
        assert result[0]['error_count'] == 5
        assert result[0]['error_rate'] == 1.0
    
    def test_partial_errors(self, test_session):
        """Should calculate correct ratio for partial errors."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        # 3 errors out of 10
        for _ in range(3):
            insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'api_request_completed', level='error')
        for _ in range(7):
            insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'api_request_completed', level='info')
        
        result = error_rate_by_type(test_session, start, end)
        assert len(result) == 1
        assert result[0]['error_rate'] == pytest.approx(0.3, rel=0.01)


class TestAPILatency:
    """Tests for api_latency_by_day metric."""
    
    def test_empty_database(self, test_session):
        """Should return empty list when no events."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        result = api_latency_by_day(test_session, start, end)
        assert result == []
    
    def test_single_latency(self, test_session):
        """Should calculate stats for single event."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'api_request_completed', value=50.5)
        
        result = api_latency_by_day(test_session, start, end)
        assert len(result) == 1
        assert result[0]['avg_latency_ms'] == pytest.approx(50.5, rel=0.01)
        assert result[0]['min_latency_ms'] == pytest.approx(50.5, rel=0.01)
        assert result[0]['max_latency_ms'] == pytest.approx(50.5, rel=0.01)
    
    def test_multiple_latencies(self, test_session):
        """Should calculate min/max/avg correctly."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        latencies = [10.0, 20.0, 30.0]
        for latency in latencies:
            insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'api_request_completed', value=latency)
        
        result = api_latency_by_day(test_session, start, end)
        assert len(result) == 1
        assert result[0]['min_latency_ms'] == 10.0
        assert result[0]['max_latency_ms'] == 30.0
        assert result[0]['avg_latency_ms'] == pytest.approx(20.0, rel=0.01)
    
    def test_null_values_ignored(self, test_session):
        """Should ignore events with null value."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'api_request_completed', value=50.0)
        insert_event(test_session, datetime(2024, 1, 1, 11, tzinfo=timezone.utc), 'api_request_completed', value=None)
        
        result = api_latency_by_day(test_session, start, end)
        assert len(result) == 1
        assert result[0]['avg_latency_ms'] == pytest.approx(50.0, rel=0.01)


class TestAuthFailureRate:
    """Tests for auth_failure_rate metric."""
    
    def test_empty_database(self, test_session):
        """Should return empty list when no events."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        result = auth_failure_rate(test_session, start, end)
        assert result == []
    
    def test_no_failures(self, test_session):
        """Should show 0% failure rate when no failures."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        for _ in range(10):
            insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'user_login_succeeded')
        
        result = auth_failure_rate(test_session, start, end)
        assert len(result) == 1
        assert result[0]['login_failed'] == 0
        assert result[0]['login_succeeded'] == 10
        assert result[0]['failure_rate'] == 0.0
    
    def test_all_failures(self, test_session):
        """Should show 100% failure rate when all failures."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        for _ in range(5):
            insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'user_login_failed')
        
        result = auth_failure_rate(test_session, start, end)
        assert len(result) == 1
        assert result[0]['login_failed'] == 5
        assert result[0]['login_succeeded'] == 0
        assert result[0]['failure_rate'] == 1.0
    
    def test_mixed_success_failure(self, test_session):
        """Should calculate correct ratio."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        for _ in range(3):
            insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'user_login_failed')
        for _ in range(7):
            insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'user_login_succeeded')
        
        result = auth_failure_rate(test_session, start, end)
        assert len(result) == 1
        assert result[0]['failure_rate'] == pytest.approx(0.3, rel=0.01)
        assert result[0]['total_logins'] == 10


class TestDataIntegrity:
    """Tests for data integrity across functions."""
    
    def test_json_serializable(self, test_session):
        """All results should be JSON-serializable."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'api_request_completed', value=50.5)
        insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'user_login_failed')
        
        # All results should be JSON serializable
        json.dumps(events_by_type_and_day(test_session, start, end))
        json.dumps(error_rate_by_type(test_session, start, end))
        json.dumps(api_latency_by_day(test_session, start, end))
        json.dumps(auth_failure_rate(test_session, start, end))
    
    def test_idempotency(self, test_session):
        """Calling twice with same params should give same result."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        
        insert_event(test_session, datetime(2024, 1, 1, 10, tzinfo=timezone.utc), 'api_request_completed')
        
        result1 = events_by_type_and_day(test_session, start, end)
        result2 = events_by_type_and_day(test_session, start, end)
        
        assert result1 == result2
