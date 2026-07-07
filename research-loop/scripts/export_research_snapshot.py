#!/usr/bin/env python3
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


VALID_DECISIONS = {"keep", "rollback", "needs-review"}


def read_text(path):
    return path.read_text(encoding="utf-8")


def section_text(text, heading):
    pattern = rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s+|\Z)"
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def first_content_line(text):
    for line in text.splitlines():
        value = line.strip()
        if value:
            return value
    return ""


def bullet_list(text):
    values = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            values.append(stripped[2:].strip())
    return values


def key_value_bullets(text):
    values = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        values[normalize_key(key)] = parse_scalar(value.strip())
    return values


def normalize_key(value):
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def parse_scalar(value):
    stripped = value.strip().strip("`")
    if not stripped:
        return ""
    try:
        if re.fullmatch(r"[-+]?\d+", stripped):
            return int(stripped)
        if re.fullmatch(r"[-+]?\d+\.\d+", stripped):
            return float(stripped)
    except ValueError:
        pass
    return stripped


def parse_program(program_path):
    text = read_text(program_path)
    decision_rule = {}
    for item in bullet_list(section_text(text, "Decision Rule")):
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        decision_rule[normalize_key(key)] = value.strip()

    return {
        "path": str(program_path),
        "goal": first_content_line(section_text(text, "Goal")),
        "editable_scope": bullet_list(section_text(text, "Editable Scope")),
        "frozen_scope": bullet_list(section_text(text, "Frozen Scope")),
        "primary_metric": key_value_bullets(section_text(text, "Primary Metric")),
        "guardrails": parse_guardrails(section_text(text, "Guardrail Metrics")),
        "verification_commands": parse_verification_commands(section_text(text, "Verification Commands")),
        "decision_rule": decision_rule,
        "trial_budget": key_value_bullets(section_text(text, "Trial Budget")),
        "raw": text,
    }


def parse_guardrails(text):
    guardrails = []
    current = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        normalized = normalize_key(key)
        if normalized == "name" and current:
            guardrails.append(current)
            current = {}
        current[normalized] = parse_scalar(value.strip())
    if current:
        guardrails.append(current)
    return guardrails


def parse_verification_commands(text):
    commands = []
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"^\d+\.\s+Command:\s*(.+)$", stripped)
        if match:
            if current:
                commands.append(current)
            current = {"command": match.group(1).strip()}
            continue
        if current and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[normalize_key(key)] = parse_scalar(value.strip())
    if current:
        commands.append(current)
    return commands


def parse_scope(text):
    changed = []
    frozen = []
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "Changed:":
            current = changed
            continue
        if stripped == "Frozen:":
            current = frozen
            continue
        if current is not None and stripped.startswith("- "):
            current.append(stripped[2:].strip())
    return {"changed": changed, "frozen": frozen}


def parse_markdown_table(text):
    rows = []
    table_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return rows

    headers = [normalize_key(cell) for cell in split_table_row(table_lines[0])]
    for line in table_lines[2:]:
        cells = split_table_row(line)
        if len(cells) != len(headers):
            continue
        rows.append({headers[index]: parse_scalar(cells[index]) for index in range(len(headers))})
    return rows


def split_table_row(line):
    stripped = line.strip().strip("|")
    return [cell.strip().strip("`") for cell in stripped.split("|")]


def parse_decision(text):
    value = first_content_line(text).strip().strip("`").lower()
    if value in VALID_DECISIONS:
        return value
    return value


def parse_trial(record_path):
    text = read_text(record_path)
    scope = parse_scope(section_text(text, "Scope"))
    return {
        "id": record_path.parent.name,
        "path": str(record_path),
        "hypothesis": section_text(text, "Hypothesis"),
        "changed_files": scope["changed"],
        "frozen_files": scope["frozen"],
        "commands": parse_markdown_table(section_text(text, "Commands")),
        "metrics": parse_markdown_table(section_text(text, "Metrics")),
        "decision": parse_decision(section_text(text, "Decision")),
        "reason": section_text(text, "Reason"),
        "next_question": section_text(text, "Next Question"),
        "raw": text,
    }


def collect_logs(research_dir):
    logs_dir = research_dir / "logs"
    logs = []
    if not logs_dir.exists():
        return logs
    for path in sorted(logs_dir.glob("*.json")):
        entry = {"path": str(path)}
        try:
            data = json.loads(read_text(path))
            entry["summary"] = data.get("summary")
            entry["runs"] = data.get("runs")
            entry["successful_json_runs"] = data.get("successful_json_runs")
        except (OSError, json.JSONDecodeError) as error:
            entry["error"] = str(error)
        logs.append(entry)
    return logs


def build_summary(trials):
    decisions = Counter(trial["decision"] for trial in trials)
    metric_names = sorted(
        {
            metric.get("metric")
            for trial in trials
            for metric in trial["metrics"]
            if metric.get("metric")
        }
    )
    return {
        "trial_count": len(trials),
        "decisions": {decision: decisions.get(decision, 0) for decision in sorted(VALID_DECISIONS)},
        "metric_names": metric_names,
    }


def build_snapshot(root):
    research_dir = root / ".research"
    if not research_dir.exists():
        raise FileNotFoundError(f"missing .research directory: {research_dir}")

    program_path = research_dir / "program.md"
    if not program_path.exists():
        raise FileNotFoundError(f"missing program file: {program_path}")

    trials_dir = research_dir / "trials"
    trials = [
        parse_trial(path)
        for path in sorted(trials_dir.glob("*/record.md"))
    ]

    return {
        "schema_version": 1,
        "root": str(root),
        "program": parse_program(program_path),
        "trials": trials,
        "logs": collect_logs(research_dir),
        "summary": build_summary(trials),
    }


def main():
    parser = argparse.ArgumentParser(description="Export .research records to .research/snapshot.json.")
    parser.add_argument("--root", default=".", help="Project root containing .research.")
    parser.add_argument("--output", help="Output JSON path. Defaults to .research/snapshot.json.")
    parser.add_argument("--stdout", action="store_true", help="Also print the snapshot JSON.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output_path = Path(args.output).resolve() if args.output else root / ".research" / "snapshot.json"

    try:
        snapshot = build_snapshot(root)
    except (OSError, FileNotFoundError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    text = json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text + "\n", encoding="utf-8")

    if args.stdout:
        print(text)
    else:
        print(f"snapshot: {output_path}")
        print(f"trials: {len(snapshot['trials'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
