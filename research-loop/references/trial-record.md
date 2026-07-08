# Trial Record

Store trial records under `.research/trials/NNN/record.md`. Use zero-padded numbers so order is stable.

## Required Format

```markdown
# Trial NNN

## Hypothesis

If we change ..., then ... should improve because ....

## Scope

Changed:
- path/to/file

Frozen:
- path/to/frozen-artifact

## Commands

| Command | Status | Evidence |
| --- | --- | --- |
| `command here` | pass/fail/blocked | short output or path to log |

## Metrics

| Metric | Before | After | Direction | Result |
| --- | ---: | ---: | --- | --- |
| primary_metric | value | value | higher/lower/pass-fail | improved/regressed/unchanged/unknown |

## Decision

keep | rollback | needs-review

## Reason

One paragraph tying the decision to the program rule.

## Next Question

The next hypothesis, blocker, user decision, or early-stop reason exposed by this trial.
```

## Evidence Rules

- Record exact commands, not paraphrases.
- Record blockers as evidence.
- Link large logs by path instead of pasting them.
- Include changed files even when the final decision is rollback.
- For rollback, include restore evidence or identify where the failed attempt was saved for audit.
- For keep, identify the new current kept state when that is not obvious from the working tree.
- For early stop, record why continuing would be wasteful, overfit-prone, blocked, or outside the trial budget.
- Do not rewrite old trial records except to append a correction note.
