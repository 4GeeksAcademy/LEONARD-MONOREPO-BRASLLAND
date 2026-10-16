import csv
import io
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from typing import TextIO

from shared.incidents import CSV_FIELDS as FIELDS
from shared.incidents import CSV_RULES as RULES
from shared.incidents import INCIDENT_CATEGORIES as CATEGORIES
from shared.incidents import CSV_STATUSES as STATUSES
from shared.incidents import validate_csv_record


class AnalysisError(ValueError):
    pass


def analyze_csv(source: TextIO) -> dict:
    reader = csv.reader(source, strict=True)
    try:
        headers = next(reader, None)
        if not headers:
            raise AnalysisError("The CSV file is empty.")
        headers[0] = headers[0].removeprefix("\ufeff")
        if len(headers) != len(set(headers)):
            raise AnalysisError("The CSV header contains duplicate columns.")
        if set(headers) != set(FIELDS):
            raise AnalysisError("Expected exactly these CSV columns: " + ", ".join(FIELDS))

        total = valid = scored = score_sum = 0
        seen_ids = bytearray(1_000_000)
        categories = Counter({category: 0 for category in CATEGORIES})
        statuses = Counter({status: 0 for status in STATUSES})
        scores = Counter({str(score): 0 for score in range(1, 6)})
        invalid = Counter({rule: 0 for rule in RULES})
        for raw_row in reader:
            total += 1
            row = dict(zip(headers, raw_row))
            values = {field: (row.get(field) or "").strip() for field in FIELDS}
            problems = validate_csv_record(values, seen_ids, len(raw_row) != len(headers))
            if problems:
                invalid.update(problems)
                continue
            valid += 1
            categories[values["category"]] += 1
            statuses[values["status"]] += 1
            score = values["satisfaction_score"]
            if values["status"] == "CLOSED" and score:
                scored += 1
                score_sum += int(score)
                scores[score] += 1
        if not total:
            raise AnalysisError("The CSV contains a header but no incident records.")
    except (csv.Error, UnicodeError) as error:
        raise AnalysisError("The file must be a correctly quoted, comma-separated UTF-8 CSV.") from error

    return {
        "total_records": total,
        "valid_records": valid,
        "invalid_records": total - valid,
        "invalid_breakdown": dict(invalid),
        "categories": dict(categories),
        "statuses": dict(statuses),
        "satisfaction": {
            "scored_cases": scored,
            "closed_cases": statuses["CLOSED"],
            "average": float((Decimal(score_sum) / scored).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )) if scored else None,
            "scores": dict(scores),
        },
    }


def metric_rows(summary: dict):
    for metric in ("total_records", "valid_records", "invalid_records"):
        yield metric, summary[metric], ""
    for rule, count in summary["invalid_breakdown"].items():
        yield f"invalid.{rule}", count, ""
    for group in ("categories", "statuses"):
        for name, count in summary[group].items():
            percentage = f"{count / summary['valid_records'] * 100:.1f}" if summary["valid_records"] else "0.0"
            yield f"{group}.{name}", count, percentage
    for name in ("scored_cases", "closed_cases", "average"):
        value = summary["satisfaction"][name]
        yield f"satisfaction.{name}", "" if value is None else value, ""
    for score, count in summary["satisfaction"]["scores"].items():
        yield f"satisfaction.score.{score}", count, ""


def results_csv(summary: dict) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(("metric", "value", "percentage"))
    writer.writerows(metric_rows(summary))
    return output.getvalue()