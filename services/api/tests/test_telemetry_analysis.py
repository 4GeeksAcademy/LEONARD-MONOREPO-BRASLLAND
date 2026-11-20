import pytest
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from services.api.telemetry.analysis import (
    events_by_type_and_day,
    error_rate_by_type,
    api_latency_by_day,
    auth_failure_rate,
)
from sqlalchemy import text


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS telemetry_events (
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
        session.commit()
        
        yield session


def test_events_by_type_and_day_empty(session):
    """Test events_by_type_and_day with no data"""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, tzinfo=timezone.utc)
    
    result = events_by_type_and_day(session, start, end)
    assert result == []


def test_error_rate_by_type_empty(session):
    """Test error_rate_by_type with no data"""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, tzinfo=timezone.utc)
    
    result = error_rate_by_type(session, start, end)
    assert result == []


def test_api_latency_by_day_empty(session):
    """Test api_latency_by_day with no data"""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, tzinfo=timezone.utc)
    
    result = api_latency_by_day(session, start, end)
    assert result == []


def test_auth_failure_rate_empty(session):
    """Test auth_failure_rate with no data"""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, tzinfo=timezone.utc)
    
    result = auth_failure_rate(session, start, end)
    assert result == []
