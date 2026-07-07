#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path


PROGRAM_HEADINGS = [
    "Goal",
    "Editable Scope",
    "Frozen Scope",
    "Primary Metric",
    "Guardrail Metrics",
    "Verification Commands",
    "Decision Rule",
    "Trial Budget",
]

TRIAL_HEADINGS = [
    "Hypothesis",
    "Scope",
    "Commands",
    "Metrics",
    "Decision",
    "Reason",
    "Next Question",
]

VALID_DECISIONS = {"keep", "rollback", "needs-review"}


def read_text(path):
    return path.read_text(encoding="utf-8")


def has_heading(text, heading):
    return re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.MULTILINE) is not None


def section_text(text, heading):
    pattern = rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s+|\Z)"
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def validate_program(research_dir):
    errors = []
    warnings = []
    program_path = research_dir / "program.md"

    if not program_path.exists():
        return {
            "path": str(program_path),
            "status": "missing",
            "errors": ["missing .research/program.md"],
            "warnings": warnings,
        }

    text = read_text(program_path)
    for heading in PROGRAM_HEADINGS:
        if not has_heading(text, heading):
            errors.append(f"program missing heading: {heading}")
            continue
        content = section_text(text, heading)
        if not content or "TODO" in content:
            warnings.append(f"program heading may be incomplete: {heading}")

    for decision in VALID_DECISIONS:
        if decision not in text:
            errors.append(f"program decision rule missing: {decision}")

    return {
        "path": str(program_path),
        "status": "ok" if not errors else "invalid",
        "errors": errors,
        "warnings": warnings,
    }


def extract_decision(text):
    content = section_text(text, "Decision")
    for line in content.splitlines():
        value = line.strip().strip("`").lower()
        if value:
            return value
    return ""


def validate_trial(record_path):
    errors = []
    warnings = []
    text = read_text(record_path)

    for heading in TRIAL_HEADINGS:
        if not has_heading(text, heading):
            errors.append(f"trial missing heading: {heading}")
            continue
        content = section_text(text, heading)
        if not content or "TODO" in content:
            warnings.append(f"trial heading may be incomplete: {heading}")

    decision = extract_decision(text)
    if decision not in VALID_DECISIONS:
        errors.append(f"invalid decision: {decision or '<empty>'}")

    if "Changed:" not in text:
        warnings.append("trial scope does not list changed files")
    if "| Command | Status | Evidence |" not in text:
        warnings.append("trial commands table not found")
    if "| Metric | Before | After | Direction | Result |" not in text:
        warnings.append("trial metrics table not found")

    return {
        "path": str(record_path),
        "decision": decision,
        "status": "ok" if not errors else "invalid",
        "errors": errors,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate a research-loop task directory.")
    parser.add_argument("--root", default=".", help="Project root containing .research.")
    parser.add_argument("--strict", action="store_true", help="Require at least one trial record.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    research_dir = root / ".research"
    errors = []
    warnings = []

    if not research_dir.exists():
        errors.append("missing .research directory")
        result = {
            "root": str(root),
            "status": "invalid",
            "errors": errors,
            "warnings": warnings,
            "program": None,
            "trials": [],
        }
    else:
        program = validate_program(research_dir)
        trials = [
            validate_trial(path)
            for path in sorted((research_dir / "trials").glob("*/record.md"))
        ]

        if args.strict and not trials:
            errors.append("strict mode requires at least one trial record")
        errors.extend(program["errors"])
        warnings.extend(program["warnings"])
        for trial in trials:
            errors.extend(trial["errors"])
            warnings.extend(trial["warnings"])

        result = {
            "root": str(root),
            "status": "ok" if not errors else "invalid",
            "errors": errors,
            "warnings": warnings,
            "program": program,
            "trials": trials,
        }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"status: {result['status']}")
        for error in result["errors"]:
            print(f"error: {error}")
        for warning in result["warnings"]:
            print(f"warning: {warning}")
        if result.get("trials") is not None:
            print(f"trials: {len(result['trials'])}")

    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
