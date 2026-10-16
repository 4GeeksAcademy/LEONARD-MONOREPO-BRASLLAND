import re
from datetime import date
from enum import Enum
from typing import Mapping


INCIDENT_CATEGORIES = (
    "CUSTOMER_COMPLAINT", "EQUIPMENT", "SUPPLY", "FOOD_QUALITY", "STAFF",
)
INCIDENT_STATUSES = ("open", "in_progress", "resolved", "discarded")
INCIDENT_ORIGINS = ("customer", "branch", "internal")
INCIDENT_BRANCHES = ("central", *(f"COL-{number:02}" for number in range(1, 11)), *(f"FLA-{number:02}" for number in range(1, 5)))
CSV_STATUSES = ("OPEN", "CLOSED", "DISCARDED")
CSV_STATUS_TO_INCIDENT = {
    "OPEN": "open",
    "CLOSED": "resolved",
    "DISCARDED": "discarded",
}
CSV_FIELDS = (
    "incident_id", "date", "location_id", "category", "description", "status",
    "customer_id", "satisfaction_score", "reporter_id",
)
CSV_RULES = {
    "location": "Missing or invalid location_id",
    "category": "Invalid or missing category",
    "description": "Empty or too-short description",
    "reporter": "Missing or invalid reporter_id",
    "closed_score": "Closed case, no score",
    "score": "Invalid satisfaction_score (integer 1-5 required)",
    "incident_id": "Missing or invalid incident_id",
    "duplicate_id": "Duplicate incident_id",
    "date": "Missing or invalid date (YYYY-MM-DD required)",
    "status": "Missing or invalid status",
    "customer_id": "Invalid customer_id",
    "row_shape": "Incorrect number of CSV fields",
}


class IncidentCategory(str, Enum):
    CUSTOMER_COMPLAINT = "CUSTOMER_COMPLAINT"
    EQUIPMENT = "EQUIPMENT"
    SUPPLY = "SUPPLY"
    FOOD_QUALITY = "FOOD_QUALITY"
    STAFF = "STAFF"


class IncidentStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISCARDED = "discarded"


class IncidentOrigin(str, Enum):
    CUSTOMER = "customer"
    BRANCH = "branch"
    INTERNAL = "internal"


IncidentBranch = Enum(
    "IncidentBranch",
    {
        "CENTRAL": "central",
        **{branch.replace("-", "_"): branch for branch in INCIDENT_BRANCHES if branch != "central"},
    },
    type=str,
)


def validate_incident_values(values: Mapping[str, object]) -> dict[str, str]:
    errors = {}
    for field in ("title", "description", "category", "status", "origin", "branch"):
        value = values.get(field)
        if value is None or not str(value).strip():
            errors[field] = "This field is required."

    title = str(values.get("title") or "").strip()
    description = str(values.get("description") or "").strip()
    category = getattr(values.get("category"), "value", values.get("category"))
    status = getattr(values.get("status"), "value", values.get("status"))
    origin = getattr(values.get("origin"), "value", values.get("origin"))
    branch = getattr(values.get("branch"), "value", values.get("branch"))
    if title and len(title) > 160:
        errors["title"] = "Use 160 characters or fewer."
    if description and len(description) < 5:
        errors["description"] = "Use at least 5 characters."
    if category and category not in INCIDENT_CATEGORIES:
        errors["category"] = "Choose a valid incident category."
    if status and status not in INCIDENT_STATUSES:
        errors["status"] = "Choose a valid incident status."
    if origin and origin not in INCIDENT_ORIGINS:
        errors["origin"] = "Choose a valid incident origin."
    if branch and branch not in INCIDENT_BRANCHES:
        errors["branch"] = "Choose a valid branch."
    return errors


def validate_csv_record(values: Mapping[str, str], seen_ids: bytearray, row_shape: bool = False) -> set[str]:
    problems = set()
    if row_shape:
        problems.add("row_shape")
    if values["location_id"] not in INCIDENT_BRANCHES[1:]:
        problems.add("location")
    if values["category"] not in INCIDENT_CATEGORIES:
        problems.add("category")
    if len(values["description"]) < 5:
        problems.add("description")
    if not re.fullmatch(r"MGR-[0-9]{2}", values["reporter_id"]):
        problems.add("reporter")
    if not re.fullmatch(r"BRS-[0-9]{6}", values["incident_id"]):
        problems.add("incident_id")
    else:
        identifier = int(values["incident_id"][4:])
        if seen_ids[identifier]:
            problems.add("duplicate_id")
        seen_ids[identifier] = 1
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", values["date"]):
            raise ValueError
        date.fromisoformat(values["date"])
    except ValueError:
        problems.add("date")
    if values["status"] not in CSV_STATUSES:
        problems.add("status")
    if values["customer_id"] and not re.fullmatch(r"CLI-[0-9]{6}", values["customer_id"]):
        problems.add("customer_id")
    score = values["satisfaction_score"]
    if values["status"] == "CLOSED" and not score:
        problems.add("closed_score")
    if score and score not in ("1", "2", "3", "4", "5"):
        problems.add("score")
    return problems