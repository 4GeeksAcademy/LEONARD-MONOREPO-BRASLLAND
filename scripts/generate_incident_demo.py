import argparse
import csv
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages"))

from incident_analysis import FIELDS
from incident_analysis.test_analysis import benchmark_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SYNTHETIC Brasaland demo data, not the course attachment.")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("incidents-brasaland-demo.csv"))
    arguments = parser.parse_args()
    try:
        with arguments.output.open("x", encoding="utf-8", newline="") as destination:
            writer = csv.DictWriter(destination, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(benchmark_rows())
    except (OSError, csv.Error) as error:
        print(f"Unable to create the demo CSV: {error}", file=sys.stderr)
        return 1
    print(f"Synthetic demo created: {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())