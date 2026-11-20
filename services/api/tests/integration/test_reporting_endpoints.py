"""
Integration tests for reporting endpoints.

Tests the full endpoint stack:
- GET /reporting/status
- POST /reporting/run-now
- GET /reporting/kpi-query

These tests assume a running Supabase instance with the reporting schema.
"""

import pytest
from datetime import datetime, date, timedelta, timezone
from fastapi.testclient import TestClient
import uuid

from services.api.app.main import app
from services.api.app.database import get_db
from services.api.auth import get_current_user


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_current_user():
    """Mock current user."""
    return type('User', (), {
        'id': 'test-user',
        'role': 'backoffice',
        'email': 'test@example.com'
    })()


@pytest.fixture
def client(mock_current_user):
    """Create test client with mocked auth and db."""
    def override_get_current_user():
        return mock_current_user
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    return TestClient(app)


# ============================================================================
# Tests: GET /reporting/status
# ============================================================================

class TestGetPipelineStatus:
    """Test GET /reporting/status endpoint."""
    
    def test_status_returns_200(self, client):
        """Test status endpoint returns 200."""
        response = client.get("/reporting/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "last_run" in data
        assert "next_scheduled" in data
        assert "is_running" in data
    
    def test_status_response_structure(self, client):
        """Test status response has correct structure."""
        response = client.get("/reporting/status")
        data = response.json()
        
        # Verify structure
        assert isinstance(data["is_running"], bool)
        assert "next_scheduled" in data
        
        # last_run can be null or object
        if data["last_run"] is not None:
            assert "run_id" in data["last_run"]
            assert "status" in data["last_run"]
            assert "records_loaded" in data["last_run"]


# ============================================================================
# Tests: POST /reporting/run-now
# ============================================================================

class TestTriggerPipelineManual:
    """Test POST /reporting/run-now endpoint."""
    
    def test_trigger_accepts_valid_mode(self, client):
        """Test trigger accepts valid modes."""
        for mode in ["normal", "late_event_recompute"]:
            response = client.post(
                "/reporting/run-now",
                json={"mode": mode}
            )
            # Should return 202 (Accepted) or 409 (Conflict if already running)
            assert response.status_code in [202, 409]
    
    def test_trigger_response_structure(self, client):
        """Test trigger response structure."""
        response = client.post(
            "/reporting/run-now",
            json={"mode": "normal"}
        )
        
        # May be 202 (success) or 409 (already running)
        if response.status_code == 202:
            data = response.json()
            assert "run_id" in data
            assert data["status"] == "RUNNING"
            assert "started_at" in data
            # Verify UUID format
            assert len(data["run_id"]) == 36  # UUID format
    
    def test_trigger_default_mode(self, client):
        """Test trigger uses default mode if not specified."""
        response = client.post(
            "/reporting/run-now",
            json={}
        )
        # Should use default mode "normal"
        assert response.status_code in [202, 409]


# ============================================================================
# Tests: GET /reporting/kpi-query
# ============================================================================

class TestQueryBusinessKPIs:
    """Test GET /reporting/kpi-query endpoint."""
    
    def test_kpi_query_requires_dates(self, client):
        """Test KPI query requires date parameters."""
        response = client.get("/reporting/kpi-query")
        # Should fail without required parameters
        assert response.status_code == 422  # Unprocessable entity
    
    def test_kpi_query_accepts_valid_dates(self, client):
        """Test KPI query accepts valid date parameters."""
        response = client.get(
            "/reporting/kpi-query",
            params={
                "start_date": "2026-11-13",
                "end_date": "2026-11-20",
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "query" in data
        assert "data" in data
        assert "summary" in data
    
    def test_kpi_query_response_structure(self, client):
        """Test KPI query response structure."""
        response = client.get(
            "/reporting/kpi-query",
            params={
                "start_date": "2026-11-13",
                "end_date": "2026-11-20",
            }
        )
        
        data = response.json()
        
        # Check query echo
        assert data["query"]["start_date"] == "2026-11-13"
        assert data["query"]["end_date"] == "2026-11-20"
        
        # Check data array
        assert isinstance(data["data"], list)
        
        # Check summary structure
        summary = data["summary"]
        assert "total_sales_cop" in summary
        assert "total_sales_usd" in summary
        assert "total_fulfillment_count" in summary
        assert "total_stock_breach_count" in summary
    
    def test_kpi_query_with_location_filter(self, client):
        """Test KPI query with location filter."""
        response = client.get(
            "/reporting/kpi-query",
            params={
                "start_date": "2026-11-13",
                "end_date": "2026-11-20",
                "location_id": "COL-01",
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["query"]["location_id"] == "COL-01"
        
        # All returned data should be for the specified location
        for kpi in data["data"]:
            assert kpi["location_id"] == "COL-01"
    
    def test_kpi_query_date_validation(self, client):
        """Test KPI query validates date format."""
        response = client.get(
            "/reporting/kpi-query",
            params={
                "start_date": "invalid-date",
                "end_date": "2026-11-20",
            }
        )
        # Should fail validation
        assert response.status_code in [422, 400]
    
    def test_kpi_query_all_brasaland_locations(self, client):
        """Test KPI query works with all Brasaland location IDs."""
        locations = [
            "COL-01", "COL-02", "COL-03", "COL-04", "COL-05",
            "COL-06", "COL-07", "COL-08", "COL-09", "COL-10",
            "FLA-01", "FLA-02", "FLA-03", "FLA-04",
        ]
        
        for location_id in locations:
            response = client.get(
                "/reporting/kpi-query",
                params={
                    "start_date": "2026-11-13",
                    "end_date": "2026-11-20",
                    "location_id": location_id,
                }
            )
            assert response.status_code == 200


# ============================================================================
# Integration Tests: Full Pipeline Flow
# ============================================================================

class TestPipelineIntegration:
    """Integration tests for the full pipeline flow."""
    
    def test_pipeline_workflow(self, client):
        """Test typical pipeline workflow."""
        # 1. Check initial status
        response = client.get("/reporting/status")
        assert response.status_code == 200
        initial_status = response.json()
        
        # 2. Query KPIs (may be empty initially)
        response = client.get(
            "/reporting/kpi-query",
            params={
                "start_date": "2026-11-13",
                "end_date": "2026-11-20",
            }
        )
        assert response.status_code == 200
        
        # 3. Try to trigger pipeline
        response = client.post(
            "/reporting/run-now",
            json={"mode": "normal"}
        )
        # Should be 202 (accepted) or 409 (conflict)
        assert response.status_code in [202, 409]
        
        # 4. Check status again
        response = client.get("/reporting/status")
        assert response.status_code == 200


# ============================================================================
# Authentication Tests
# ============================================================================

class TestAuthenticationRequired:
    """Test that endpoints require authentication."""
    
    def test_endpoints_without_override(self):
        """Test endpoints fail without authentication override."""
        # Remove auth override to test real auth requirement
        client = TestClient(app)
        
        # These endpoints require auth
        endpoints = [
            ("GET", "/reporting/status"),
            ("POST", "/reporting/run-now"),
            ("GET", "/reporting/kpi-query?start_date=2026-11-13&end_date=2026-11-20"),
        ]
        
        for method, path in endpoints:
            if method == "GET":
                response = client.get(path)
            elif method == "POST":
                response = client.post(path, json={"mode": "normal"})
            
            # Should require authentication (usually 401 or 403)
            assert response.status_code in [401, 403, 422]
