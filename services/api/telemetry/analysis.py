import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import text
from sqlmodel import Session


def events_by_type_and_day(session: Session, start_date: datetime, end_date: datetime) -> list[dict]:
    """
    Calculate event volume by type and by day.
    
    Returns a list of dicts with: date, event_type, count
    """
    query = text("""
        SELECT DATE(timestamp) as date, event_type, COUNT(*) as count
        FROM public.telemetry_events
        WHERE timestamp >= :start_date AND timestamp < :end_date
        GROUP BY DATE(timestamp), event_type
        ORDER BY date, event_type
    """)
    
    result = session.execute(query, {"start_date": start_date, "end_date": end_date})
    rows = result.fetchall()
    
    if not rows:
        return []
    
    df = pd.DataFrame(rows, columns=["date", "event_type", "count"])
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.date.astype(str)
    
    return df.reset_index(drop=True).to_dict(orient="records")


def error_rate_by_type(session: Session, start_date: datetime, end_date: datetime) -> list[dict]:
    """
    Calculate error rate (error events / total events) by event type.
    
    Returns a list of dicts with: event_type, error_count, total_count, error_rate
    """
    query = text("""
        SELECT 
            event_type,
            COUNT(*) FILTER (WHERE level = 'error') as error_count,
            COUNT(*) as total_count
        FROM public.telemetry_events
        WHERE timestamp >= :start_date AND timestamp < :end_date
        GROUP BY event_type
        ORDER BY event_type
    """)
    
    result = session.execute(query, {"start_date": start_date, "end_date": end_date})
    rows = result.fetchall()
    
    if not rows:
        return []
    
    df = pd.DataFrame(rows, columns=["event_type", "error_count", "total_count"])
    df["error_count"] = df["error_count"].astype(int)
    df["total_count"] = df["total_count"].astype(int)
    df["error_rate"] = (df["error_count"] / df["total_count"]).round(4)
    
    return df[["event_type", "error_count", "total_count", "error_rate"]].reset_index(drop=True).to_dict(orient="records")


def api_latency_by_day(session: Session, start_date: datetime, end_date: datetime) -> list[dict]:
    """
    Calculate average API latency by day for api_request_completed events.
    
    Returns a list of dicts with: date, avg_latency_ms, min_latency_ms, max_latency_ms
    """
    query = text("""
        SELECT 
            DATE(timestamp) as date,
            AVG(CAST(value AS FLOAT)) as avg_latency,
            MIN(CAST(value AS FLOAT)) as min_latency,
            MAX(CAST(value AS FLOAT)) as max_latency
        FROM public.telemetry_events
        WHERE event_type = 'api_request_completed'
            AND timestamp >= :start_date 
            AND timestamp < :end_date
            AND value IS NOT NULL
        GROUP BY DATE(timestamp)
        ORDER BY date
    """)
    
    result = session.execute(query, {"start_date": start_date, "end_date": end_date})
    rows = result.fetchall()
    
    if not rows:
        return []
    
    df = pd.DataFrame(rows, columns=["date", "avg_latency", "min_latency", "max_latency"])
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.date.astype(str)
    df["avg_latency_ms"] = df["avg_latency"].round(2)
    df["min_latency_ms"] = df["min_latency"].round(2)
    df["max_latency_ms"] = df["max_latency"].round(2)
    
    return df[["date", "avg_latency_ms", "min_latency_ms", "max_latency_ms"]].reset_index(drop=True).to_dict(orient="records")


def auth_failure_rate(session: Session, start_date: datetime, end_date: datetime) -> list[dict]:
    """
    Calculate daily login failure rate: user_login_failed / (user_login_failed + user_login_succeeded).
    
    Returns a list of dicts with: date, login_failed, login_succeeded, failure_rate
    """
    query = text("""
        SELECT
            DATE(timestamp) as date,
            COUNT(*) FILTER (WHERE event_type = 'user_login_failed') as login_failed,
            COUNT(*) FILTER (WHERE event_type = 'user_login_succeeded') as login_succeeded
        FROM public.telemetry_events
        WHERE event_type IN ('user_login_failed', 'user_login_succeeded')
            AND timestamp >= :start_date 
            AND timestamp < :end_date
        GROUP BY DATE(timestamp)
        ORDER BY date
    """)
    
    result = session.execute(query, {"start_date": start_date, "end_date": end_date})
    rows = result.fetchall()
    
    if not rows:
        return []
    
    df = pd.DataFrame(rows, columns=["date", "login_failed", "login_succeeded"])
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.date.astype(str)
    df["login_failed"] = df["login_failed"].astype(int)
    df["login_succeeded"] = df["login_succeeded"].astype(int)
    df["total_logins"] = df["login_failed"] + df["login_succeeded"]
    df["failure_rate"] = (df["login_failed"] / df["total_logins"]).round(4)
    
    return df[["date", "login_failed", "login_succeeded", "total_logins", "failure_rate"]].reset_index(drop=True).to_dict(orient="records")
