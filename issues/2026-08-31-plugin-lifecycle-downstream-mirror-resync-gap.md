## Summary
`plugin-lifecycle-downstream`'s Phase 6 (Fix & Re-audit) re-dispatch loop has no step requiring a mirror resync (`.claude/`/`.codex/` copies) before re-dispatching reviewers/agents against canonical files just edited — reproduced twice for real in one session.

## Context
- **Product/Service**: `plugin-devkit` plugin, `plugins/plugin-devkit/skills/plugin-lifecycle-downstream/SKILL.md` (and its `.claude/` mirror)
- **Related work**: `plugin-lifecycle-downstream` QA run against `workmanagement-kit`, 2026-08-30/31

## What Happened

Reproduced twice in the same session:

1. **First occurrence**: Phase 6 round 1 fixed two Codex-bridge agent files' Output Format and description. Round 2's re-dispatch of the same 7 reviewer types then read the stale, un-resynced `.claude/agents/` and `.codex/agents/` copies — the "already live" standalone path per the target plugin's own README — producing false confidence that round 1's fix hadn't landed, when it actually had.
2. **Second occurrence**: the identical mistake recurred later in the same session, during a separate follow-up fix batch (narrowing `Skill` grants, adding foundation-contract citations). Caught only because a `plugin-rulebook-checker` dispatch happened to flag the resulting R19 mirror-divergence violation as a blocking `FAIL` — not because the pipeline itself has any check for this.

## Proposed Fix

Add `uv run python -m scripts.marketplace_ci sync-plugin-mirrors` and `convert-codex-exports` (no `--stage` flag, since nothing is being committed at that point in the phase) as an explicit step in Phase 6's re-dispatch procedure, in `plugins/plugin-devkit/skills/plugin-lifecycle-downstream/SKILL.md` — mirroring the command form already used in `plugins/git-kit/skills/commit/SKILL.md`'s own step 8. Mirror the same edit into `.claude/skills/plugin-lifecycle-downstream/SKILL.md` per R19's multi-mirror sweep convention.

## Impact
**Medium** — no data loss or incorrect final state occurred either time (both were eventually caught), but the failure mode is a false-confidence read with no error signal: a fix applied to canonical files silently doesn't propagate to the "live" mirror path, and nothing in the pipeline's own procedure would catch this without an incidental rulebook check happening to run afterward.

## Additional Context
Originally surfaced by an `enhancement-suggestor` dispatch run against `workmanagement-kit`'s Phase 11 `plugin-grader` report; classified there as a Quick Win (low complexity, low risk, medium benefit) specifically because the fix is small, isolated, and closes a defect class that already reproduced twice for real in one session.
