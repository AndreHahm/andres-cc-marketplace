# Component Testing

## What counts as a test

Per component type, any of these count — pick whichever fits the change, don't force a heavier mechanism than it warrants:

- **Skill, behavior-critical or frequently relied on**: a `skill-tester` blind-comparison eval run, persisted to the git-tracked `evals/<skill-name>/` directory at the repo root.
- **Skill, most other cases**: a documented "Testing & Validation" section in the SKILL.md itself — concrete scenarios, pass/fail criteria, a quality-gates checklist. Not automated, but concrete and checkable by re-reading it against the change.
- **Agent**: `agent-development/scripts/test-agent-trigger.sh`'s trigger-phrase battery — cheap, deterministic, no LLM cost.
- **Deterministic scripts/code** (a `scripts/*.py`/`.sh` file's own logic): direct execution against fixtures/known-good output — not blind agent testing.

## When a test is required

Mandatory for any change that alters what a component actually does when followed on some input. See `.claude/rules/skill-evaluation-protocol.md`'s Scope section for the precise, already-established definition (a change to SKILL.md/agent-file/`references/` prose or guidance that changes behavior) and its two carve-outs, which apply here too: deterministic script/code logic changes, and prose fixes that only restore an already-documented/already-intended behavior without changing it. Still legitimately N/A for genuine documentation-only changes, typo fixes, and those two carve-out categories.

## Fix Completeness: Sweep Sibling Occurrences

When a review finding (or a bug you find yourself) identifies a defect in one function/code block, grep the rest of the same file/component for the same anti-pattern signature before considering the fix complete — a fix scoped to only the flagged line/function leaves an identical, not-yet-flagged instance sitting a few lines away. This is a completeness check on the fix itself, not a substitute for the test required above: the fix still needs its own test/verification per "When a test is required."

`.claude/THIRD_PARTY_REVIEW_LEARNINGS.md`'s Master pre-push checklist names this pattern directly: "when a review finding identifies a bug in one function/code block: grepped the rest of the file/component for the same anti-pattern signature before considering the fix complete?" — a lower-frequency but real recurring gap distinct from whether the fix itself was tested.

## Enforcement

`commit` (git-kit) gates on this directly: when the staged diff includes a behavior change per the definition above, it asks via `AskUserQuestion` whether the change has been tested and by which mechanism, before writing the commit message — see `commit`'s own Instructions for the exact step. `create-pr` relies on this same gate rather than duplicating it, since its own pre-flight check already routes uncommitted changes through `commit` first. Two paths aren't covered by this enforcement and rely on the author's judgment instead: a PR built entirely from commits made outside git-kit (e.g. a raw `git commit`), and commits made through git-kit's `standalone-commits` skill — its step 6 gates only on an `AskUserQuestion` message confirmation (6b), and its own note under that step states it deliberately does not add `commit`'s step-9 behavior-change test gate.

Don't silently mark a PR's "Tests added/updated where applicable" checklist item as N/A without this check having actually run — N/A is a legitimate answer, but it should follow from the gate saying so, not from skipping the gate.
