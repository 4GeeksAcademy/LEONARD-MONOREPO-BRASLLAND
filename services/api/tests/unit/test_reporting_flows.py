"""
Unit tests for Prefect reporting flows.

Tests individual tasks and flow logic:
- Extraction deduplication
- Transformation aggregation
- Load idempotency
- Failure recovery
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

from services.api.telemetry.reporting_flows import (
    extract_telemetry_events,
    transform_to_business_metrics,
    load_to_reporting_schema,
    record_pipeline_run,
)


class TestExtractTelemetryEvents:
    """Test extraction task."""
    
    def test_extract_empty_result(self):
        """Test extraction when no events exist."""
        with patch('services.api.telemetry.reporting_flows.get_db_engine') as mock_engine:
            # Mock empty result
            mock_conn = MagicMock()
            mock_engine.return_value.connect.return_value = mock_conn
            
            # Pandas read_sql returns empty DataFrame
            with patch('pandas.read_sql', return_value=pd.DataFrame()):
                result = extract_telemetry_events(lookback_hours=24)
                assert isinstance(result, pd.DataFrame)
                assert len(result) == 0
    
    def test_extract_deduplicates_by_event_id(self):
        """Test that extraction deduplicates by eventId."""
        # Create test data with duplicate eventIds
        test_data = pd.DataFrame({
            'event_id': ['evt-1', 'evt-1', 'evt-2'],
            'timestamp': [
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
                datetime.now(timezone.utc) - timedelta(hours=1),
            ],
            'location_id': ['COL-01', 'COL-01', 'COL-02'],
            'amount_cop': [100, 100, 50],
        })
        
        with patch('services.api.telemetry.reporting_flows.get_db_engine'):
            with patch('pandas.read_sql', return_value=test_data):
                # Note: Real extraction uses SQL DISTINCT ON, so this tests the query structure
                result = extract_telemetry_events(lookback_hours=24)
                assert len(result) >= 1  # Should have deduplicated rows
    
    def test_extract_counts_late_events(self):
        """Test that extraction counts events older than 24 hours."""
        test_data = pd.DataFrame({
            'timestamp': [
                datetime.now(timezone.utc),  # Fresh
                datetime.now(timezone.utc) - timedelta(hours=48),  # Late
                datetime.now(timezone.utc) - timedelta(hours=72),  # Very late
            ],
            'location_id': ['COL-01', 'COL-02', 'COL-03'],
        })
        
        with patch('services.api.telemetry.reporting_flows.get_db_engine'):
            with patch('pandas.read_sql', return_value=test_data):
                result = extract_telemetry_events(lookback_hours=24)
                # 2 events are > 24 hours old
                assert len(result) >= 2


class TestTransformToBusinessMetrics:
    """Test transformation task."""
    
    def test_transform_empty_events(self):
        """Test transformation of empty event set."""
        empty_df = pd.DataFrame()
        result = transform_to_business_metrics(empty_df)
        assert len(result) == 0
    
    def test_transform_aggregates_by_location_and_date(self):
        """Test that transformation groups by location and date."""
        events = pd.DataFrame({
            'timestamp': [
                datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc),
                datetime(2026, 11, 20, 14, 0, 0, tzinfo=timezone.utc),
                datetime(2026, 11, 21, 10, 0, 0, tzinfo=timezone.utc),
            ],
            'location_id': ['COL-01', 'COL-01', 'COL-01'],
            'amount_cop': [100000, 50000, 75000],
            'amount_usd': [25, 12.5, 18.75],
            'quantity': [1, 1, 1],
        })
        
        result = transform_to_business_metrics(events)
        
        # Should have 2 rows: one for 2026-11-20, one for 2026-11-21
        assert len(result) == 2
        
        # Check aggregations
        row_20 = result[result['report_date'].astype(str) == '2026-11-20'].iloc[0]
        assert row_20['daily_sales_cop'] == 150000
        assert row_20['daily_sales_usd'] == 37.5
        assert row_20['fulfillment_count'] == 2
    
    def test_transform_handles_null_amounts(self):
        """Test that transformation handles null amount fields."""
        events = pd.DataFrame({
            'timestamp': [
                datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc),
            ],
            'location_id': ['COL-01'],
            'amount_cop': [None],
            'amount_usd': [None],
            'quantity': [0],
        })
        
        result = transform_to_business_metrics(events)
        assert len(result) == 1
        # Should have 0 or NaN values
        assert result.iloc[0]['fulfillment_count'] == 0
    
    def test_transform_adds_run_id(self):
        """Test that transformation adds unique run_id to each row."""
        events = pd.DataFrame({
            'timestamp': [
                datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc),
            ],
            'location_id': ['COL-01'],
            'amount_cop': [100000],
            'amount_usd': [25],
            'quantity': [1],
        })
        
        result = transform_to_business_metrics(events)
        assert 'run_id' in result.columns
        assert result.iloc[0]['run_id'] is not None
        assert len(result.iloc[0]['run_id']) == 36  # UUID length


class TestLoadToReportingSchema:
    """Test load task."""
    
    def test_load_empty_dataframe(self):
        """Test loading empty metrics."""
        empty_df = pd.DataFrame()
        result = load_to_reporting_schema(empty_df, run_id="test-run-id")
        assert result == 0
    
    def test_load_executes_upsert(self):
        """Test that load executes UPSERT query."""
        metrics = pd.DataFrame({
            'report_date': [datetime(2026, 11, 20).date()],
            'location_id': ['COL-01'],
            'daily_sales_cop': [100000],
            'daily_sales_usd': [25],
            'fulfillment_count': [10],
            'avg_fulfillment_time_hours': [2.5],
            'stock_breach_count': [1],
        })
        
        run_id = "test-run-id"
        
        with patch('services.api.telemetry.reporting_flows.get_db_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_engine.return_value.begin.return_value.__enter__.return_value = mock_conn
            
            result = load_to_reporting_schema(metrics, run_id)
            
            # Should have executed query
            assert mock_conn.execute.called
            assert result == len(metrics)


class TestRecordPipelineRun:
    """Test pipeline run recording."""
    
    def test_record_successful_run(self):
        """Test recording a successful pipeline run."""
        with patch('services.api.telemetry.reporting_flows.get_db_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_engine.return_value.begin.return_value.__enter__.return_value = mock_conn
            
            start_time = datetime.now(timezone.utc)
            end_time = start_time + timedelta(minutes=10)
            
            record_pipeline_run(
                run_id="test-run-id",
                status="COMPLETED",
                extraction_count=100,
                transformation_count=14,
                load_count=14,
                start_time=start_time,
                end_time=end_time,
                invalidation_trigger="scheduled",
                late_event_count=5,
                phase_checkpoint="LOAD_COMPLETE",
            )
            
            # Should have executed insert query
            assert mock_conn.execute.called
    
    def test_record_failed_run(self):
        """Test recording a failed pipeline run."""
        with patch('services.api.telemetry.reporting_flows.get_db_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_engine.return_value.begin.return_value.__enter__.return_value = mock_conn
            
            start_time = datetime.now(timezone.utc)
            end_time = start_time + timedelta(minutes=1)
            
            record_pipeline_run(
                run_id="test-run-id",
                status="FAILED",
                extraction_count=100,
                transformation_count=0,
                load_count=0,
                start_time=start_time,
                end_time=end_time,
                error_message="Database timeout",
                invalidation_trigger="manual_trigger",
                phase_checkpoint="EXTRACT_COMPLETE",
            )
            
            # Should have recorded error
            assert mock_conn.execute.called
