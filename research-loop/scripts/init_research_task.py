#!/usr/bin/env python3
import argparse
from pathlib import Path


PROGRAM_TEMPLATE = """# Research Program

## Goal
TODO

## Editable Scope
- TODO

## Frozen Scope
- TODO

## Primary Metric
- Name: TODO
- Direction: higher-is-better | lower-is-better | pass-fail
- Minimum useful movement: TODO
- Measurement command: TODO

## Guardrail Metrics
- Name: TODO
- Failure threshold: TODO
- Measurement command: TODO

## Verification Commands
1. Command: TODO
   Purpose: TODO
   Required for decision: yes

## Decision Rule
- keep: TODO
- rollback: TODO
- needs-review: TODO

## Trial Budget
- Max changed files: TODO
- Max runtime: TODO
- Max trials before review: TODO
"""


GITIGNORE_TEMPLATE = """logs/
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a research-loop task directory.")
    parser.add_argument("--root", default=".", help="Project root where .research should be created.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    research_dir = root / ".research"
    trials_dir = research_dir / "trials"
    program_path = research_dir / "program.md"
    gitignore_path = research_dir / ".gitignore"

    research_dir.mkdir(parents=True, exist_ok=True)
    trials_dir.mkdir(parents=True, exist_ok=True)

    if not program_path.exists():
        program_path.write_text(PROGRAM_TEMPLATE, encoding="utf-8")

    if not gitignore_path.exists():
        gitignore_path.write_text(GITIGNORE_TEMPLATE, encoding="utf-8")

    print(f"initialized: {research_dir}")
    print(f"program: {program_path}")
    print(f"trials: {trials_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
