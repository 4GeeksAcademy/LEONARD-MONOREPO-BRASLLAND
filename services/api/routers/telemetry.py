import json
import logging
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    UUID4,
    ValidationError,
    model_validator,
)
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Session

from services.api.app.database import get_db
from services.api.auth import CurrentUser
from services.api.cache import TTLCache
from services.api.telemetry.analysis import (
    events_by_type_and_day,
    error_rate_by_type,
    api_latency_by_day,
    auth_failure_rate,
)

logger = logging.getLogger(__name__)
router = APIRouter()

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "docs" / "telemetry" / "event-schemas.json"
with SCHEMA_PATH.open(encoding="utf-8") as schema_file:
    TELEMETRY_SCHEMA = json.load(schema_file)

SCHEMA_VERSION = TELEMETRY_SCHEMA["version"]
EVENT_DEFINITIONS = {
    definition["event_type"]: definition
    for definition in TELEMETRY_SCHEMA["events"]
}
SERVICE_NAME = "backoffice"
DATETIME_ADAPTER = TypeAdapter(AwareDatetime)

INSERT_EVENTS = text(
    """
    INSERT INTO public.telemetry_events
        (id, timestamp, service, event_type, level, value, message, tags)
    VALUES
        (:id, :timestamp, :service, :event_type, :level, :value, :message, :tags)
    ON CONFLICT (id) DO NOTHING
    """
).bindparams(bindparam("tags", type_=JSONB))

report_cache = TTLCache(ttl=60.0)


def validate_event_properties(event_type: str, properties: dict[str, Any]) -> None:
    definition = EVENT_DEFINITIONS.get(event_type)
    if definition is None:
        raise ValueError(f"Unknown telemetry event type: {event_type}")

    allowlist = set(definition["property_allowlist"])
    unexpected = properties.keys() - allowlist
    if unexpected:
        raise ValueError(f"Unapproved properties for {event_type}: {', '.join(sorted(unexpected))}")

    property_definitions = definition["properties"]
    for name, property_definition in property_definitions.items():
        required = property_definition.get("required", False)
        if name not in properties or properties[name] is None:
            if required:
                raise ValueError(f"Missing required property for {event_type}: {name}")
            continue

        value = properties[name]
        property_type = property_definition["type"]
        valid_type = (
            (property_type == "string" and isinstance(value, str))
            or (property_type == "integer" and isinstance(value, int) and not isinstance(value, bool))
            or (
                property_type == "number"
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and (not isinstance(value, float) or math.isfinite(value))
            )
            or (property_type == "boolean" and isinstance(value, bool))
            or (property_type == "object" and isinstance(value, dict))
            or (property_type == "array" and isinstance(value, list))
        )
        if not valid_type:
            raise ValueError(f"Property {name} for {event_type} must be {property_type}")
        if "enum" in property_definition and value not in property_definition["enum"]:
            raise ValueError(f"Property {name} for {event_type} has an unsupported value")
        if property_definition.get("format") == "date-time":
            try:
                DATETIME_ADAPTER.validate_python(value)
            except ValidationError as error:
                raise ValueError(f"Property {name} for {event_type} must be an aware date-time") from error
        if property_type == "string":
            if len(value) < property_definition.get("minLength", 0):
                raise ValueError(f"Property {name} for {event_type} is too short")
            if len(value) > property_definition.get("maxLength", math.inf):
                raise ValueError(f"Property {name} for {event_type} is too long")


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eventId: UUID4
    timestamp: AwareDatetime
    sessionId: str = Field(min_length=1, max_length=128)
    userId: str = Field(min_length=1, max_length=128)
    event_type: str = Field(pattern=r"^[a-z]+_[a-z]+(?:_[a-z]+)*$")
    schemaVersion: str = Field(min_length=1, max_length=32)
    requestId: str = Field(min_length=1, max_length=128)
    properties: dict[str, Any]

    @model_validator(mode="after")
    def validate_schema(self):
        if self.schemaVersion != SCHEMA_VERSION:
            raise ValueError(f"Unsupported telemetry schema version: {self.schemaVersion}")
        validate_event_properties(self.event_type, self.properties)
        return self


class TelemetryBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[TelemetryEvent] = Field(max_length=100)


@router.post("/events")
def receive_events(batch: TelemetryBatch, session: Session = Depends(get_db)):
    rows = []
    for event in batch.events:
        properties = event.properties
        tags = {
            **properties,
            "_telemetry": {
                "sessionId": event.sessionId,
                "userId": event.userId,
                "requestId": event.requestId,
                "schemaVersion": event.schemaVersion,
            },
        }
        rows.append({
            "id": event.eventId,
            "timestamp": event.timestamp,
            "service": SERVICE_NAME,
            "event_type": event.event_type,
            "level": properties.get("severity", "info"),
            "value": properties.get("value"),
            "message": properties.get("message", properties.get("errorMessage")),
            "tags": tags,
        })

    if rows:
        session.execute(INSERT_EVENTS, rows)
        session.commit()

    logger.info("Received %d telemetry events", len(batch.events))
    return {"received": len(batch.events)}


class TelemetryReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    period: dict[str, str]
    metrics: dict[str, Any]


@router.get("/report", response_model=TelemetryReport)
def get_telemetry_report(
    start_date: str | None = Query(None, description="ISO 8601 start date (inclusive)"),
    end_date: str | None = Query(None, description="ISO 8601 end date (exclusive)"),
    session: Session = Depends(get_db),
    current_user: CurrentUser = Depends(),
):
    """
    Get operational metrics for the system based on telemetry events.
    
    If start_date and end_date are not provided, defaults to the last 7 days.
    Results are cached with a 60-second TTL.
    
    Requires authentication.
    """
    now = datetime.now(timezone.utc)
    
    if start_date and end_date:
        try:
            parsed_start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            parsed_end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            raise HTTPException(400, "start_date and end_date must be in ISO 8601 format") from e
    else:
        parsed_end = now
        parsed_start = now - timedelta(days=7)
    
    cache_key = f"{parsed_start.isoformat()}:{parsed_end.isoformat()}"
    
    def compute_report():
        metrics = {
            "events_per_day": events_by_type_and_day(session, parsed_start, parsed_end),
            "error_rate_by_type": error_rate_by_type(session, parsed_start, parsed_end),
            "api_latency_by_day": api_latency_by_day(session, parsed_start, parsed_end),
            "auth_failure_rate": auth_failure_rate(session, parsed_start, parsed_end),
        }
        return {
            "period": {
                "from": parsed_start.isoformat(),
                "to": parsed_end.isoformat(),
            },
            "metrics": metrics,
        }
    
    return report_cache.get_or_set(cache_key, compute_report)

