# Program Contract

A research program is the single source of truth for a run. Store it at `.research/program.md`.

## Required Fields

```markdown
# Research Program

## Goal
One sentence describing the outcome.

## Editable Scope
- Paths, files, prompts, configs, or artifacts the agent may change.

## Frozen Scope
- Paths, data, tests, evals, public interfaces, or metrics the agent must not change.

## Primary Metric
- Name:
- Direction: higher-is-better | lower-is-better | pass-fail
- Minimum useful movement:
- Measurement command:

## Guardrail Metrics
- Name:
- Failure threshold:
- Measurement command:

## Verification Commands
1. Command:
   Purpose:
   Required for decision: yes | no

## Decision Rule
- keep:
- rollback:
- needs-review:
- stop:

## Trial Budget
- Max changed files:
- Max runtime:
- Max trials before review:
- Continue/stop rule:
- Restore method for rollback:
```

## Rules

- Freeze the program before optimization trials.
- Change the program only through an explicit meta-trial or user confirmation.
- Treat unclear metrics as blockers, not as permission to invent success.
- Prefer one primary metric. Use guardrails for everything that must not regress.
- Keep scope narrow enough that one trial can be reviewed from its diff and record.
- Treat "Max trials before review" as an upper bound. Do not run trials mechanically after the success threshold is reached, after repeated non-improvement, or when the next hypothesis would mainly overfit a visible evaluator.
- Establish a baseline or current kept state before optimization. Record enough metric, guardrail, and restore information to compare each trial and roll back failed changes.
- Keep `stop` as a run-level decision, not a trial outcome. Individual trials still decide `keep`, `rollback`, or `needs-review`.
- For skill, prompt, or agent-strategy self-improvement tests, make the active production skill frozen scope unless the user explicitly authorizes editing it. Use a disposable copy, mini-skill, candidate skill, prompt, or strategy artifact as editable scope.

## Metric Examples

Code performance:
- Primary metric: P95 latency from a fixed benchmark.
- Guardrails: tests pass, accuracy stays within threshold.

RAG quality:
- Primary metric: score on a frozen eval set.
- Guardrails: answer citation rate, latency, cost.

Prompt optimization:
- Primary metric: judge score on frozen examples.
- Guardrails: invalid format rate, token cost, refusal policy checks.

Bug fixing:
- Primary metric: reproducer test passes.
- Guardrails: existing test suite passes.
