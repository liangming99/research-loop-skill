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

The next hypothesis, blocker, or user decision exposed by this trial.
```

## Evidence Rules

- Record exact commands, not paraphrases.
- Record blockers as evidence.
- Link large logs by path instead of pasting them.
- Include changed files even when the final decision is rollback.
- Do not rewrite old trial records except to append a correction note.
