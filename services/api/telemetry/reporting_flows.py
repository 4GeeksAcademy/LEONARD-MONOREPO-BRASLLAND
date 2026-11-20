"""
Prefect flows for Brasaland business performance data pipeline.

This module orchestrates the daily business KPI pipeline:
1. Extract telemetry events from the last 24-72 hours
2. Transform events into business metrics (sales, inventory, fulfillment)
3. Load aggregated metrics into the reporting schema

Idempotency is enforced through UPSERT by (report_date, location_id) and
phase checkpoints for failure recovery.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from prefect import flow, task, get_run_logger
from sqlalchemy import text
from sqlmodel import Session

from services.api.app.database import get_db_engine

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER: Database Connection
# ============================================================================

def get_db_session():
    """Get database session for reporting operations."""
    engine = get_db_engine()
    with Session(engine) as session:
        return session


# ============================================================================
# TASK 1: EXTRACT TELEMETRY EVENTS
# ============================================================================

@task(
    name="extract_telemetry_events",
    description="Extract and deduplicate telemetry events from the last 24-72 hours",
    retries=2,
    retry_delay_seconds=30,
)
def extract_telemetry_events(
    lookback_hours: int = 24,
    late_event_recompute: bool = False,
) -> pd.DataFrame:
    """
    Extract telemetry events from public.telemetry_events.
    
    Deduplicates by eventId and enriches with product/location metadata.
    
    Args:
        lookback_hours: How far back to query (24 for normal, 72 for late-event recompute)
        late_event_recompute: If True, include 48-hour window for late-arriving events
    
    Returns:
        DataFrame with deduplicated events, enriched with metadata
    
    Raises:
        Exception: If database query fails
    """
    logger = get_run_logger()
    logger.info(f"Extracting telemetry events (lookback: {lookback_hours}h)")
    
    try:
        engine = get_db_engine()
        
        # Query events from last N hours, deduplicated by eventId
        query = """
        SELECT DISTINCT ON (tags->>'eventId')
            id as event_id,
            timestamp,
            tags->>'eventId' as event_id_envelope,
            tags->>'eventType' as event_type,
            tags->>'locationId' as location_id,
            (tags->>'amountCOP')::numeric as amount_cop,
            (tags->>'amountUSD')::numeric as amount_usd,
            (tags->>'quantity')::numeric as quantity,
            tags->>'productId' as product_id,
            tags->>'userId' as user_id,
            tags->>'requestId' as request_id
        FROM public.telemetry_events
        WHERE timestamp >= now() - interval '{} hours'
        ORDER BY tags->>'eventId', timestamp ASC
        """.format(lookback_hours)
        
        df = pd.read_sql(query, engine)
        logger.info(f"Extracted {len(df)} deduplicated events")
        
        # Count late events (timestamp > 24 hours old)
        if not df.empty:
            late_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            late_count = (df['timestamp'] < late_cutoff).sum()
            logger.info(f"Late events detected: {late_count}")
        
        return df
    
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        raise


# ============================================================================
# TASK 2: TRANSFORM TO BUSINESS METRICS
# ============================================================================

@task(
    name="transform_to_business_metrics",
    description="Aggregate telemetry events into daily business KPIs by location",
)
def transform_to_business_metrics(events_df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform raw telemetry events into business metrics.
    
    Groups by location and report_date, computes:
    - daily_sales_cop / daily_sales_usd
    - fulfillment_count
    - avg_fulfillment_time_hours
    - stock_breach_count
    
    Args:
        events_df: DataFrame from extract task
    
    Returns:
        Aggregated DataFrame ready for load
    """
    logger = get_run_logger()
    logger.info(f"Transforming {len(events_df)} events into business metrics")
    
    if events_df.empty:
        logger.warning("No events to transform; returning empty metrics")
        return pd.DataFrame()
    
    # Add report_date column (date portion of timestamp)
    events_df['report_date'] = events_df['timestamp'].dt.date
    
    # Aggregate by location and date
    metrics_df = events_df.groupby(['report_date', 'location_id']).agg({
        'amount_cop': 'sum',
        'amount_usd': 'sum',
        'quantity': 'count',  # Count of fulfilled orders
    }).reset_index()
    
    # Rename columns to match schema
    metrics_df.rename(columns={
        'amount_cop': 'daily_sales_cop',
        'amount_usd': 'daily_sales_usd',
        'quantity': 'fulfillment_count',
    }, inplace=True)
    
    # Add placeholder columns (Part 2 will populate from full telemetry)
    metrics_df['avg_fulfillment_time_hours'] = None
    metrics_df['stock_breach_count'] = 0
    
    # Add run metadata
    metrics_df['run_id'] = str(uuid.uuid4())
    
    logger.info(f"Computed metrics for {len(metrics_df)} location-date combinations")
    
    return metrics_df


# ============================================================================
# TASK 3: LOAD TO REPORTING SCHEMA
# ============================================================================

@task(
    name="load_to_reporting_schema",
    description="Upsert aggregated metrics into reporting.daily_operations_rollup",
    retries=2,
    retry_delay_seconds=30,
)
def load_to_reporting_schema(metrics_df: pd.DataFrame, run_id: str) -> int:
    """
    Load metrics into reporting.daily_operations_rollup via UPSERT.
    
    Strategy: UPSERT by (report_date, location_id)
    - If row exists: UPDATE metrics and updated_at
    - If new: INSERT
    - Prevents duplicates on re-run
    
    Args:
        metrics_df: Aggregated metrics from transform task
        run_id: Unique pipeline run identifier
    
    Returns:
        Number of rows upserted
    
    Raises:
        Exception: If database write fails
    """
    logger = get_run_logger()
    logger.info(f"Loading {len(metrics_df)} metrics rows into reporting schema")
    
    if metrics_df.empty:
        logger.warning("No metrics to load")
        return 0
    
    try:
        engine = get_db_engine()
        
        # Prepare data for upsert
        metrics_df['run_id'] = run_id
        metrics_df['created_at'] = datetime.now(timezone.utc)
        metrics_df['updated_at'] = datetime.now(timezone.utc)
        
        # Build UPSERT query (PostgreSQL ON CONFLICT syntax)
        insert_query = """
        INSERT INTO reporting.daily_operations_rollup
        (report_date, location_id, daily_sales_cop, daily_sales_usd, 
         fulfillment_count, avg_fulfillment_time_hours, stock_breach_count, 
         run_id, created_at, updated_at)
        VALUES
        """
        
        # Prepare value tuples
        value_tuples = []
        for _, row in metrics_df.iterrows():
            value_tuples.append(f"""
            ('{row['report_date']}'::date, 
             '{row['location_id']}', 
             {row['daily_sales_cop'] or 0}, 
             {row['daily_sales_usd'] or 0},
             {row['fulfillment_count'] or 0},
             {row['avg_fulfillment_time_hours']},
             {row['stock_breach_count'] or 0},
             '{row['run_id']}'::uuid,
             '{row['created_at'].isoformat()}',
             '{row['updated_at'].isoformat()}')
            """)
        
        insert_query += ",".join(value_tuples)
        
        # UPSERT: on conflict, update metrics
        insert_query += """
        ON CONFLICT (report_date, location_id) DO UPDATE SET
            daily_sales_cop = EXCLUDED.daily_sales_cop,
            daily_sales_usd = EXCLUDED.daily_sales_usd,
            fulfillment_count = EXCLUDED.fulfillment_count,
            avg_fulfillment_time_hours = EXCLUDED.avg_fulfillment_time_hours,
            stock_breach_count = EXCLUDED.stock_breach_count,
            run_id = EXCLUDED.run_id,
            updated_at = EXCLUDED.updated_at
        """
        
        with engine.begin() as conn:
            conn.execute(text(insert_query))
        
        logger.info(f"Successfully upserted {len(metrics_df)} rows")
        return len(metrics_df)
    
    except Exception as e:
        logger.error(f"Load failed: {str(e)}")
        raise


# ============================================================================
# TASK: RECORD PIPELINE RUN
# ============================================================================

@task(
    name="record_pipeline_run",
    description="Record pipeline execution metadata in reporting.pipeline_runs",
)
def record_pipeline_run(
    run_id: str,
    status: str,
    extraction_count: int,
    transformation_count: int,
    load_count: int,
    start_time: datetime,
    end_time: Optional[datetime] = None,
    error_message: Optional[str] = None,
    invalidation_trigger: str = "scheduled",
    late_event_count: int = 0,
    phase_checkpoint: str = "LOAD_COMPLETE",
) -> None:
    """
    Record pipeline run metadata for auditing and observability.
    
    Args:
        run_id: Unique run identifier
        status: RUNNING, COMPLETED, or FAILED
        extraction_count: Number of events extracted
        transformation_count: Number of aggregated rows computed
        load_count: Number of rows loaded
        start_time: When pipeline started
        end_time: When pipeline finished (None if still running)
        error_message: Error details if status = FAILED
        invalidation_trigger: Reason for run (scheduled, manual_trigger, late_event_recompute)
        late_event_count: Count of events with timestamp > 24h old
        phase_checkpoint: Last completed stage
    """
    logger = get_run_logger()
    
    try:
        engine = get_db_engine()
        
        insert_query = f"""
        INSERT INTO reporting.pipeline_runs
        (run_id, run_start_time, run_end_time, extraction_record_count,
         transformation_record_count, load_record_count, status, error_message,
         invalidation_trigger, late_event_count, phase_checkpoint)
        VALUES (
            '{run_id}'::uuid,
            '{start_time.isoformat()}',
            {'NULL' if end_time is None else f"'{end_time.isoformat()}'"},
            {extraction_count},
            {transformation_count},
            {load_count},
            '{status}',
            {f"'{error_message}'" if error_message else 'NULL'},
            '{invalidation_trigger}',
            {late_event_count},
            '{phase_checkpoint}'
        )
        """
        
        with engine.begin() as conn:
            conn.execute(text(insert_query))
        
        logger.info(f"Recorded pipeline run {run_id}: {status}")
    
    except Exception as e:
        logger.error(f"Failed to record pipeline run: {str(e)}")
        # Don't re-raise; audit failure shouldn't block pipeline


# ============================================================================
# MAIN FLOW: DAILY BUSINESS PERFORMANCE
# ============================================================================

@flow(
    name="daily_business_performance_flow",
    description="Daily pipeline: extract telemetry, transform to KPIs, load to reporting schema",
)
def daily_business_performance_flow(
    lookback_hours: int = 24,
    invalidation_trigger: str = "scheduled",
    late_event_recompute: bool = False,
) -> dict:
    """
    Main Prefect flow for business performance pipeline.
    
    Orchestrates:
    1. Extract: Pull telemetry events from last 24-72 hours
    2. Transform: Aggregate into daily KPIs by location
    3. Load: UPSERT into reporting.daily_operations_rollup
    4. Record: Audit execution in pipeline_runs
    
    Args:
        lookback_hours: Query window (24 for normal, 72 for late-event recompute)
        invalidation_trigger: Reason for run
        late_event_recompute: If True, include 48-hour window for late events
    
    Returns:
        Dictionary with execution summary
    """
    logger = get_run_logger()
    run_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)
    
    logger.info(f"Starting business performance pipeline (run_id: {run_id})")
    logger.info(f"Trigger: {invalidation_trigger}, Lookback: {lookback_hours}h")
    
    extraction_count = 0
    transformation_count = 0
    late_event_count = 0
    
    try:
        # PHASE 1: EXTRACT
        logger.info("=" * 60)
        logger.info("PHASE 1: EXTRACT")
        logger.info("=" * 60)
        events_df = extract_telemetry_events(lookback_hours, late_event_recompute)
        extraction_count = len(events_df)
        
        if not events_df.empty:
            late_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            late_event_count = (events_df['timestamp'] < late_cutoff).sum()
        
        logger.info(f"Checkpoint: EXTRACT_COMPLETE (extracted: {extraction_count}, late: {late_event_count})")
        
        # PHASE 2: TRANSFORM
        logger.info("=" * 60)
        logger.info("PHASE 2: TRANSFORM")
        logger.info("=" * 60)
        metrics_df = transform_to_business_metrics(events_df)
        transformation_count = len(metrics_df)
        logger.info(f"Checkpoint: TRANSFORM_COMPLETE (transformed: {transformation_count})")
        
        # PHASE 3: LOAD
        logger.info("=" * 60)
        logger.info("PHASE 3: LOAD")
        logger.info("=" * 60)
        load_count = load_to_reporting_schema(metrics_df, run_id)
        logger.info(f"Checkpoint: LOAD_COMPLETE (loaded: {load_count})")
        
        # Record successful run
        end_time = datetime.now(timezone.utc)
        record_pipeline_run(
            run_id=run_id,
            status="COMPLETED",
            extraction_count=extraction_count,
            transformation_count=transformation_count,
            load_count=load_count,
            start_time=start_time,
            end_time=end_time,
            invalidation_trigger=invalidation_trigger,
            late_event_count=late_event_count,
            phase_checkpoint="LOAD_COMPLETE",
        )
        
        duration_seconds = (end_time - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info(f"PIPELINE COMPLETED in {duration_seconds:.1f}s")
        logger.info(f"Run ID: {run_id}")
        logger.info("=" * 60)
        
        return {
            "run_id": run_id,
            "status": "COMPLETED",
            "extraction_count": extraction_count,
            "transformation_count": transformation_count,
            "load_count": load_count,
            "duration_seconds": duration_seconds,
        }
    
    except Exception as e:
        # Record failed run
        end_time = datetime.now(timezone.utc)
        logger.error(f"Pipeline failed: {str(e)}")
        
        record_pipeline_run(
            run_id=run_id,
            status="FAILED",
            extraction_count=extraction_count,
            transformation_count=transformation_count,
            load_count=0,
            start_time=start_time,
            end_time=end_time,
            error_message=str(e),
            invalidation_trigger=invalidation_trigger,
            phase_checkpoint="",
        )
        
        # Re-raise so Prefect marks flow as failed
        raise


if __name__ == "__main__":
    # Test run (local execution)
    result = daily_business_performance_flow()
    print(f"Pipeline result: {result}")
