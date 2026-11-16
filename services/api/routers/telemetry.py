import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


logger = logging.getLogger(__name__)
router = APIRouter()


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eventId: UUID
    timestamp: AwareDatetime
    sessionId: str = Field(min_length=1, max_length=128)
    userId: str = Field(min_length=1, max_length=128)
    event_type: str = Field(pattern=r"^[a-z]+_[a-z]+(?:_[a-z]+)*$")
    schemaVersion: str = Field(min_length=1, max_length=32)
    requestId: str = Field(min_length=1, max_length=128)
    properties: dict[str, Any]


class TelemetryBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[TelemetryEvent] = Field(max_length=100)


@router.post("/events")
def receive_events(batch: TelemetryBatch):
    logger.info("Received %d telemetry events", len(batch.events))
    for event in batch.events:
        logger.info("Received telemetry event type=%s", event.event_type)
    return {"received": len(batch.events)}
