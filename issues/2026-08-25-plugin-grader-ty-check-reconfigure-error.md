## Summary
Pre-existing `ty check` type error in `plugin-grader/scripts/compute_score.py`: `sys.stdout.reconfigure` doesn't resolve on `TextIO | Any`

## Environment
- **Product/Service**: andres-cc-marketplace repo, `plugins/plugin-devkit` plugin, `plugin-grader` skill
- **Region/Version**: n/a (local repo tooling — `ty check` via `uv run ty check`)

## Reproduction Steps
1. Stage `plugins/plugin-devkit/skills/plugin-grader/scripts/compute_score.py` (or its `.claude/skills/plugin-grader/scripts/compute_score.py` mirror) for a commit
2. Run this repo's `commit` skill (or directly: `${CLAUDE_PLUGIN_ROOT}/scripts/lint-staged-python.sh`), which runs `ruff format`, `ruff check --fix`, and `ty check` on staged `.py` files
3. Observe `ty check`'s output

## Expected Behavior
`ty check` passes cleanly on `compute_score.py`.

## Actual Behavior
`ty check` reports:
```
error[unresolved-attribute]: Attribute `reconfigure` is not defined on `TextIO` in union `TextIO | Any`
   --> plugins/plugin-devkit/skills/plugin-grader/scripts/compute_score.py:<line>:5
    |
    |     sys.stdout.reconfigure(encoding="utf-8")
    |     ^^^^^^^^^^^^^^^^^^^^^^
```
The offending line is at the top of `main()`, setting stdout encoding to UTF-8 for the script's own printed output.

## Impact
**Low** — does not affect the script's actual runtime behavior (the line executes correctly; this is a static-analysis-only finding). It does block this repo's own `commit` skill's pre-commit lint gate whenever any staged Python file's diff also touches `compute_score.py`, since `ty check` fails the whole file, requiring the committer to explicitly acknowledge and proceed past it each time rather than a clean pass.

## Additional Context
- Confirmed pre-existing: this exact line was present in the file before an unrelated 2026-08-25 change (adding a `plugin_security_score`/Gate P4 whole-plugin rollup feature to the same script) — not introduced by that change.
- Surfaced by this repo's own commit-gate lint/type-check step (`lint-staged-python.sh`, which runs `ty check`) while staging that unrelated feature change.
- Likely fix: either a `# type: ignore[unresolved-attribute]` comment with a short reason, or restructuring the encoding setup to avoid the attribute access `ty` can't resolve on the `TextIO | Any` union (e.g. checking `hasattr` first, or using `io.TextIOWrapper` reconfiguration patterns `ty` can type more precisely).
- Affects both copies of the file (`plugins/plugin-devkit/skills/plugin-grader/scripts/compute_score.py` and its `.claude/skills/plugin-grader/scripts/compute_score.py` mirror) — any fix must be applied to both to keep the mirror convention intact.
