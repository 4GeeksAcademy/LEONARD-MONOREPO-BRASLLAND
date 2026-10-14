import argparse
import csv
import sys
from collections import Counter
from datetime import date, datetime, time, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

from shared.incidents import (
    CSV_FIELDS, CSV_RULES, CSV_STATUS_TO_INCIDENT, validate_csv_record,
    validate_incident_values,
)
from services.api.database import open_database


def seed_incidents(csv_path: Path, database) -> tuple[int, int, int]:
    inserted = skipped = rejected = 0
    rejected_rules = Counter()
    seen_ids = bytearray(1_000_000)
    incidents = database.table("incidents")
    headers_expected = set(CSV_FIELDS)

    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, strict=True)
        headers = next(reader, None)
        if not headers or set(headers) != headers_expected or len(headers) != len(set(headers)):
            raise ValueError("CSV must contain the expected incident columns exactly once.")

        for raw_row in reader:
            row = dict(zip(headers, raw_row))
            values = {field: (row.get(field) or "").strip() for field in CSV_FIELDS}
            problems = validate_csv_record(values, seen_ids, len(raw_row) != len(headers))
            if problems:
                rejected += 1
                rejected_rules.update(problems)
                continue

            created_at = datetime.combine(
                date.fromisoformat(values["date"]), time.min, timezone.utc,
            ).isoformat()
            incident = {
                "title": values["description"][:160],
                "description": values["description"],
                "category": values["category"],
                "status": CSV_STATUS_TO_INCIDENT[values["status"]],
                "origin": "customer",
                "branch": values["location_id"],
            }
            model_errors = validate_incident_values(incident)
            if model_errors:
                rejected += 1
                rejected_rules.update(model_errors)
                continue

            if incidents.contains(lambda record: record.get("source_incident_id") == values["incident_id"]):
                skipped += 1
                continue
            incidents.insert({
                **incident,
                "source_incident_id": values["incident_id"],
                "created_at": created_at,
                "updated_at": created_at,
            })
            inserted += 1

    print(f"Incident seeder: inserted {inserted}, skipped {skipped}, rejected {rejected}.")
    for rule, count in rejected_rules.items():
        print(f"  {CSV_RULES.get(rule, rule)}: {count}")
    return inserted, skipped, rejected


def main() -> int:
    default_csv = ROOT / "data" / "raw" / "incidents-brasaland.csv"
    if not default_csv.exists():
        default_csv = ROOT / "scripts" / "incidents-brasaland-demo.csv"
    parser = argparse.ArgumentParser(description="Load historical Brasaland incidents into the API database.")
    parser.add_argument("csv_path", nargs="?", type=Path, default=default_csv)
    arguments = parser.parse_args()
    try:
        with open_database() as database:
            seed_incidents(arguments.csv_path, database)
    except (OSError, csv.Error, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())