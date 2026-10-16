from collections import Counter
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from tinydb import TinyDB

from shared.incidents import (
    INCIDENT_BRANCHES, INCIDENT_CATEGORIES, INCIDENT_ORIGINS, INCIDENT_STATUSES,
)
from services.api.database import get_database
from services.api.models import (
    Incident, IncidentCreate, IncidentOrigin, IncidentCategory,
    IncidentStatus, IncidentStatusUpdate,
)


router = APIRouter(prefix="/api/incidents", tags=["Incidents"])
Database = Annotated[TinyDB, Depends(get_database)]
IncidentId = Annotated[int, Path(gt=0)]
TRANSITIONS = {
    "open": {"in_progress", "discarded"},
    "in_progress": {"resolved", "discarded"},
    "resolved": {"in_progress", "discarded"},
    "discarded": set(),
}


def incident_response(record):
    return {
        **{key: value for key, value in record.items() if key != "source_incident_id"},
        "id": record.doc_id,
    }


def find_incident(database: TinyDB, incident_id: int):
    record = database.table("incidents").get(doc_id=incident_id)
    if record is None:
        raise HTTPException(404, "Incident not found.")
    return incident_response(record)


@router.post("", response_model=Incident, status_code=201)
def create_incident(payload: IncidentCreate, database: Database):
    now = datetime.now(timezone.utc).isoformat()
    incident_id = database.table("incidents").insert({
        **payload.model_dump(mode="json"),
        "created_at": now,
        "updated_at": now,
    })
    return find_incident(database, incident_id)


@router.get("", response_model=list[Incident])
def list_incidents(
    database: Database,
    status: IncidentStatus | None = None,
    origin: IncidentOrigin | None = None,
    branch: str | None = None,
    category: IncidentCategory | None = None,
):
    records = database.table("incidents").all()
    filters = {"status": status, "origin": origin, "branch": branch, "category": category}
    return [
        incident_response(record)
        for record in records
        if all(value is None or record.get(field) == getattr(value, "value", value)
               for field, value in filters.items())
    ]


@router.get("/summary")
def incident_summary(database: Database):
    records = database.table("incidents").all()
    metrics = {
        "status": INCIDENT_STATUSES,
        "category": INCIDENT_CATEGORIES,
        "origin": INCIDENT_ORIGINS,
        "branch": INCIDENT_BRANCHES,
    }
    return {
        "total": len(records),
        **{
            f"by_{field}": {
                value: Counter(record.get(field) for record in records)[value]
                for value in values
            }
            for field, values in metrics.items()
        },
    }


@router.get("/{incident_id}", response_model=Incident)
def get_incident(incident_id: IncidentId, database: Database):
    return find_incident(database, incident_id)


@router.patch("/{incident_id}/status", response_model=Incident)
def update_incident_status(
    incident_id: IncidentId, payload: IncidentStatusUpdate, database: Database,
):
    incident = find_incident(database, incident_id)
    next_status = payload.status.value
    if next_status not in TRANSITIONS[incident["status"]]:
        raise HTTPException(400, "That status change is not allowed.")
    database.table("incidents").update({
        "status": next_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, doc_ids=[incident_id])
    return find_incident(database, incident_id)