# Deep Test Coverage By Component Type

`plugin-lifecycle-downstream`'s optional Deep Test step (exhaustive per-trigger-phrase/eval
testing, distinct from the bounded smoke check other phases run) has a real, working test
path for three component types today and none for the other two. This file is the single
place that states which is which, so a caller building a Deep Test report doesn't have to
rediscover the gap per run — and so a component type without a test path is always reported
as `skipped`, never silently dropped from the results as if it had passed or wasn't part of
the scope.

## Coverage By Type

| Type | Test path | Mechanism |
|---|---|---|
| Skill | Yes | `skill-tester` — Quick Workflow (fast pass/fail) or Full Pipeline (baseline-comparison benchmark); see its own `references/eval-schema.md` |
| Agent | Yes | `agent-development/scripts/test-agent-trigger.sh` — full trigger-phrase battery, `--json`/`--yaml` for structured output |
| Hook | Yes | `hook-development/scripts/test-hook.sh` against every event type the hook's `matcher` configures — see `hook-development/SKILL.md`'s "Deep Test coverage for a hook" |
| Command | **No** | No exhaustive test path exists yet |
| Rule | **No** | No exhaustive test path exists yet |

## Reporting a Type With No Test Path

When Deep Test's scope includes a command or rule component, represent it in the result set
as:

```json
{"component": "<name>", "type": "command", "status": "skipped", "reason": "no exhaustive test path exists yet for this component type"}
```

Never omit the entry entirely — an omitted component reads as "not in scope," which is a
different claim than "in scope, but nothing to run." A caller aggregating Deep Test results
across a whole plugin (e.g. `plugin-lifecycle-downstream`'s Deep Test step, or M11's future
`smoke_test.py` upgrade) should count `skipped` entries separately from `pass`/`fail`, and
must not treat a plugin's coverage as complete when it still contains any.

## Adding a Test Path Later

If a command or rule test mechanism is built in the future, add its row to the table above in
the same pass — don't leave this file's own claim stale once the gap it documents is closed.
