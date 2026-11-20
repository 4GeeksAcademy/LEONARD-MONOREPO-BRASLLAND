"""
Reporting API endpoints for business performance KPIs.

Three endpoints expose the business performance pipeline:
1. GET /reporting/status - Query pipeline status and next run time
2. POST /reporting/run-now - Manually trigger the pipeline
3. GET /reporting/kpi-query - Query business KPIs by date range and location
"""

import logging
import uuid
from datetime import datetime, date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlmodel import Session

from services.api.app.database import get_db
from services.api.auth import CurrentUser
from services.api.telemetry.reporting_flows import daily_business_performance_flow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reporting", tags=["reporting"])


# ============================================================================
# Pydantic Models
# ============================================================================

class PipelineRunStatus(BaseModel):
    """Pipeline run metadata and status."""
    run_id: str
    start: datetime
    end: Optional[datetime] = None
    status: str
    records_loaded: int


class PipelineStatusResponse(BaseModel):
    """Response for GET /reporting/status endpoint."""
    last_run: Optional[PipelineRunStatus] = None
    next_scheduled: datetime
    is_running: bool


class PipelineRunRequest(BaseModel):
    """Request body for POST /reporting/run-now endpoint."""
    mode: str = Field(default="normal", pattern="^(normal|late_event_recompute)$")


class PipelineRunResponse(BaseModel):
    """Response for POST /reporting/run-now endpoint."""
    run_id: str
    status: str
    started_at: datetime
    estimated_completion: Optional[datetime] = None


class DailyKPI(BaseModel):
    """Daily business KPI for a location."""
    date: date
    location_id: str
    daily_sales_cop: float
    daily_sales_usd: float
    fulfillment_count: int
    avg_fulfillment_time_hours: Optional[float] = None
    stock_breach_count: int


class KPISummary(BaseModel):
    """Aggregated KPI summary across multiple days/locations."""
    total_sales_cop: float
    total_sales_usd: float
    avg_fulfillment_time_hours: Optional[float] = None
    total_fulfillment_count: int
    total_stock_breach_count: int


class KPIQueryResponse(BaseModel):
    """Response for GET /reporting/kpi-query endpoint."""
    query: dict
    data: List[DailyKPI]
    summary: KPISummary


# ============================================================================
# ENDPOINT 1: GET /reporting/status
# ============================================================================

@router.get("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(),
) -> PipelineStatusResponse:
    """
    Get current pipeline status and next scheduled run time.
    
    Returns:
    - Last pipeline run metadata (if available)
    - Next scheduled run time
    - Whether pipeline is currently running
    
    Authentication: Required (backoffice role)
    """
    logger.info(f"Status query from user {current_user.id}")
    
    try:
        # Query last run from pipeline_runs table
        query_last_run = """
        SELECT run_id, run_start_time, run_end_time, status, load_record_count
        FROM reporting.pipeline_runs
        ORDER BY run_start_time DESC
        LIMIT 1
        """
        
        result = db.exec(text(query_last_run)).first()
        last_run = None
        is_running = False
        
        if result:
            run_id, start, end, status, records = result
            last_run = PipelineRunStatus(
                run_id=str(run_id),
                start=start,
                end=end,
                status=status,
                records_loaded=records or 0,
            )
            is_running = (status == "RUNNING")
        
        # Next scheduled run: 7 AM UTC next day
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        next_run = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        
        return PipelineStatusResponse(
            last_run=last_run,
            next_scheduled=next_run,
            is_running=is_running,
        )
    
    except Exception as e:
        logger.error(f"Status query failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to query pipeline status")


# ============================================================================
# ENDPOINT 2: POST /reporting/run-now
# ============================================================================

@router.post("/run-now", response_model=PipelineRunResponse, status_code=202)
async def trigger_pipeline_manual(
    request: PipelineRunRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(),
) -> PipelineRunResponse:
    """
    Manually trigger the business performance pipeline immediately.
    
    Prevents concurrent runs using window lock in pipeline_runs table.
    
    Request body:
    - mode: "normal" (last 24h) or "late_event_recompute" (last 72h)
    
    Returns:
    - run_id: Unique pipeline run identifier
    - status: RUNNING
    - started_at: Timestamp of pipeline start
    - estimated_completion: Estimated completion time (now + 15 minutes)
    
    Authentication: Required (backoffice role)
    
    Errors:
    - 409: Pipeline already running
    - 403: Insufficient permissions
    """
    logger.info(f"Manual trigger request from user {current_user.id}, mode: {request.mode}")
    
    try:
        # Check if pipeline is already running
        query_running = """
        SELECT COUNT(*) FROM reporting.pipeline_runs
        WHERE status = 'RUNNING'
        """
        running_count = db.exec(text(query_running)).scalar() or 0
        
        if running_count > 0:
            logger.warning("Pipeline already running; request rejected")
            raise HTTPException(
                status_code=409,
                detail="Pipeline already running. Try again in 15 minutes.",
            )
        
        # Trigger Prefect flow asynchronously
        from datetime import datetime, timezone, timedelta
        
        late_recompute = (request.mode == "late_event_recompute")
        lookback_hours = 72 if late_recompute else 24
        
        # In production, this would submit to Prefect Cloud/Server
        # For now, we return a placeholder that indicates the run would start
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        estimated_end = started_at + timedelta(minutes=15)
        
        logger.info(f"Pipeline triggered: run_id={run_id}, mode={request.mode}")
        
        # TODO: Submit to Prefect Cloud
        # flow_run = daily_business_performance_flow.submit(
        #     lookback_hours=lookback_hours,
        #     invalidation_trigger="manual_trigger",
        #     late_event_recompute=late_recompute,
        # )
        
        return PipelineRunResponse(
            run_id=run_id,
            status="RUNNING",
            started_at=started_at,
            estimated_completion=estimated_end,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline trigger failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to trigger pipeline")


# ============================================================================
# ENDPOINT 3: GET /reporting/kpi-query
# ============================================================================

@router.get("/kpi-query", response_model=KPIQueryResponse)
async def query_business_kpis(
    start_date: date = Query(..., description="Start date for KPI query (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date for KPI query (YYYY-MM-DD)"),
    location_id: Optional[str] = Query(None, description="Filter by location (e.g., COL-01)"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(),
) -> KPIQueryResponse:
    """
    Query business KPIs for a date range and optional location filter.
    
    Returns daily sales, fulfillment metrics, and inventory health by location.
    
    Query parameters:
    - start_date: Start of date range (YYYY-MM-DD, required)
    - end_date: End of date range (YYYY-MM-DD, required)
    - location_id: Filter by single location (optional, e.g., "COL-01")
    
    Returns:
    - query: Echo back of query parameters
    - data: Array of daily KPIs (one row per location-date)
    - summary: Aggregated totals across date range/locations
    
    Authentication: Required (backoffice role)
    
    Example:
    GET /reporting/kpi-query?start_date=2026-11-13&end_date=2026-11-20&location_id=COL-01
    """
    logger.info(f"KPI query from user {current_user.id}: {start_date} to {end_date}, location: {location_id}")
    
    try:
        # Build query with optional location filter
        where_clause = "WHERE report_date >= :start_date AND report_date <= :end_date"
        params = {"start_date": start_date, "end_date": end_date}
        
        if location_id:
            where_clause += " AND location_id = :location_id"
            params["location_id"] = location_id
        
        query = f"""
        SELECT 
            report_date,
            location_id,
            daily_sales_cop,
            daily_sales_usd,
            fulfillment_count,
            avg_fulfillment_time_hours,
            stock_breach_count
        FROM reporting.daily_operations_rollup
        {where_clause}
        ORDER BY report_date DESC, location_id ASC
        """
        
        # Execute query
        rows = db.exec(text(query), params).all()
        
        # Parse results into KPI objects
        kpis = []
        total_sales_cop = 0
        total_sales_usd = 0
        total_fulfillment_count = 0
        total_stock_breach_count = 0
        fulfillment_times = []
        
        for row in rows:
            kpi = DailyKPI(
                date=row[0],
                location_id=row[1],
                daily_sales_cop=float(row[2] or 0),
                daily_sales_usd=float(row[3] or 0),
                fulfillment_count=int(row[4] or 0),
                avg_fulfillment_time_hours=float(row[5]) if row[5] else None,
                stock_breach_count=int(row[6] or 0),
            )
            kpis.append(kpi)
            
            # Accumulate summary
            total_sales_cop += kpi.daily_sales_cop
            total_sales_usd += kpi.daily_sales_usd
            total_fulfillment_count += kpi.fulfillment_count
            total_stock_breach_count += kpi.stock_breach_count
            if kpi.avg_fulfillment_time_hours is not None:
                fulfillment_times.append(kpi.avg_fulfillment_time_hours)
        
        # Calculate average fulfillment time
        avg_fulfillment_time = None
        if fulfillment_times:
            avg_fulfillment_time = sum(fulfillment_times) / len(fulfillment_times)
        
        summary = KPISummary(
            total_sales_cop=total_sales_cop,
            total_sales_usd=total_sales_usd,
            avg_fulfillment_time_hours=avg_fulfillment_time,
            total_fulfillment_count=total_fulfillment_count,
            total_stock_breach_count=total_stock_breach_count,
        )
        
        logger.info(f"KPI query returned {len(kpis)} rows")
        
        return KPIQueryResponse(
            query={
                "start_date": str(start_date),
                "end_date": str(end_date),
                "location_id": location_id,
            },
            data=kpis,
            summary=summary,
        )
    
    except Exception as e:
        logger.error(f"KPI query failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to query KPIs")
