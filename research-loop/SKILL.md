---
name: research-loop
description: Research loop for goal-driven agent work. Use when a user asks an agent to improve, optimize, investigate, benchmark, tune, compare approaches, run experiments, or make progress toward a measurable target across code, prompts, RAG systems, models, data pipelines, or workflows.
---

# Research Loop

Use a research loop to turn open-ended improvement work into auditable trials. Treat each trial as one hypothesis tested against a fixed program.

## Step 1: Frame the Program

Before changing files, identify whether the user already supplied a program. A program has:

- Goal
- Editable scope
- Frozen scope
- Primary metric
- Guardrail metrics
- Verification commands
- Decision rule
- Trial budget

If any item can change the target, architecture, data model, interface, UX, safety boundary, or acceptance criteria, stop and ask. Otherwise make the smallest explicit assumption and continue.

When the project has no `.research/program.md`, offer to create one. To initialize the directory, run:

```bash
python <skill-dir>/scripts/init_research_task.py --root <project-root>
```

For the exact program fields, read `references/program-contract.md`.

Completion criterion: a current program exists or the missing fields have been surfaced to the user.

## Step 2: Make One Hypothesis

Write one falsifiable hypothesis before editing. It must name:

- Expected mechanism
- Files or artifacts likely to change
- Metric expected to move
- Guardrail most likely to fail

Reject broad hypotheses such as "improve performance" or "clean up implementation". Split them until one trial can test them.

Completion criterion: one trial hypothesis can be disproved by the planned verification commands.

## Step 3: Run the Trial

Change only the editable scope. Do not alter frozen scope, benchmark data, tests, metric definitions, or verification commands unless the program explicitly says the trial is about those artifacts.

Keep the trial minimal. If the change needs a new abstraction, dependency, schema, public interface, or UX behavior, pause unless the program already authorizes that class of change.

Completion criterion: every modified line traces directly to the hypothesis.

## Step 4: Verify Against the Program

Run the verification commands from the program. Capture enough output to justify the decision, including metric values before and after when available.

For JSON-emitting eval commands that need repeated runs, use:

```bash
python <skill-dir>/scripts/run_eval_repeated.py --cmd "<verification-command>" --runs 5 --cwd <project-root>
```

If a command cannot run, record the blocker as evidence. Do not substitute a weaker check without marking the decision `needs-review`.

Completion criterion: primary metric, guardrails, and command status are known or explicitly blocked.

## Step 5: Decide

Use only the program decision rule:

- `keep`: primary metric improves enough and all guardrails pass.
- `rollback`: primary metric fails, guardrails fail, or the change violates scope.
- `needs-review`: evidence is incomplete, noisy, or requires user judgment.

Do not call a trial successful because the implementation looks plausible.

Completion criterion: the trial has one decision and the evidence supports it.

## Step 6: Record the Trial

Create or update a trial record under `.research/trials/`. Include hypothesis, changed files, commands, metrics, decision, and next question.

For the exact record format, read `references/trial-record.md`.

Before finalizing, validate the task record:

```bash
python <skill-dir>/scripts/validate_research_task.py --root <project-root> --strict
```

For dashboard or report consumers, export a canonical snapshot:

```bash
python <skill-dir>/scripts/export_research_snapshot.py --root <project-root>
```

To inspect the run in a read-only live local dashboard, serve the project:

```bash
python <skill-dir>/scripts/serve_research_ui.py --root <project-root> --port 8765
```

The dashboard uses server-sent events for live updates and falls back to polling when the browser cannot keep the event stream open.

Completion criterion: a future agent can understand what was tried, why, what happened, and whether to build on it.

## Branches

For code tasks, use the repository's normal test and benchmark commands as verification commands.

For prompt, RAG, or agent workflow tasks, freeze the eval set before trials start. Do not edit examples, rubrics, or judge prompts during an optimization trial.

For exploratory research without a measurable metric, the first trial is to create the metric or evaluation harness. Do not optimize before the judge exists.
