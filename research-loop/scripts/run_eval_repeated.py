#!/usr/bin/env python3
import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path


def parse_metric(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def summarize(rows):
    numeric = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key, value in row.items():
            metric = parse_metric(value)
            if metric is not None:
                numeric.setdefault(key, []).append(metric)

    summary = {}
    for key, values in sorted(numeric.items()):
        summary[key] = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.fmean(values),
        }
        if len(values) > 1:
            summary[key]["stdev"] = statistics.stdev(values)
        else:
            summary[key]["stdev"] = 0.0
    return summary


def main():
    parser = argparse.ArgumentParser(description="Run an eval command repeatedly and summarize JSON output.")
    parser.add_argument("--cmd", required=True, help="Command to run. It must print one JSON object.")
    parser.add_argument("--runs", type=int, default=5, help="Number of repeated runs.")
    parser.add_argument("--cwd", default=".", help="Working directory for the command.")
    parser.add_argument("--output", help="Optional JSON file for the run record.")
    args = parser.parse_args()

    if args.runs < 1:
        print("error: --runs must be >= 1", file=sys.stderr)
        return 2

    cwd = Path(args.cwd).resolve()
    records = []
    failures = []

    for index in range(1, args.runs + 1):
        completed = subprocess.run(
            args.cmd,
            cwd=str(cwd),
            shell=True,
            text=True,
            capture_output=True,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        parsed = None
        parse_error = None

        if completed.returncode == 0:
            try:
                parsed = json.loads(stdout.splitlines()[-1])
            except (IndexError, json.JSONDecodeError) as error:
                parse_error = str(error)
                failures.append(index)
        else:
            failures.append(index)

        records.append(
            {
                "run": index,
                "returncode": completed.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "json": parsed,
                "parse_error": parse_error,
            }
        )

    parsed_rows = [record["json"] for record in records if record["json"] is not None]
    result = {
        "command": args.cmd,
        "cwd": str(cwd),
        "runs": args.runs,
        "successful_json_runs": len(parsed_rows),
        "failed_runs": failures,
        "summary": summarize(parsed_rows),
        "records": records,
    }

    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    print(text)

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
