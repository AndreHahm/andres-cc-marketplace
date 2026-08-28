# Staging Fix Verification Log

Full verification-run narratives for behavior changes to `commit`'s staging steps, extracted out of
`SKILL.md`'s own `## Testing & Validation` section per `plugin-rulebook`'s R30 (a full walkthrough
narrative belongs in `references/`, not inline — only the short checklist items stay in `SKILL.md`
itself).

## Step 6 (interactive staging via `stage-selected-files.sh`) — verified live, 2026-08-28

Built a throwaway repo with two files deliberately named `$(touch INJECTION_PROOF).py` and
`other$(touch INJECTION_PROOF2).txt`, alongside two ordinary unstaged files. `--list` printed all four
as a numbered list (each command-substitution filename shown literally, unexecuted). Staging all four by
index (`stage-selected-files.sh 1 2 3 4`) correctly staged every file, including the two crafted names —
confirmed via `git status --porcelain` showing them as staged, quoted, literal paths — and confirmed no
`INJECTION_PROOF*` file was ever created, i.e. the embedded `$(...)` never executed. Also verified: an
out-of-range index (`99`) exits 1 with an error and stages nothing; a non-digit argument (`abc`) exits 2
with an error and stages nothing.

## Step 8 (marketplace CI targeted repair, `--stage` flag) — added 2026-08-28

Alongside `tests/marketplace_ci/test_hooks.py`'s existing `check_staged_parity` coverage (2026-08-13,
deterministic, not blind A/B — see `SKILL.md`'s own rationale for why this skill uses this mechanism
instead of a `skill-tester` blind-comparison eval), `tests/marketplace_ci/test_sync.py` gained two new
tests for the `--stage` flag's `stage_generated_destinations` helper, both run against a real temporary
git repository (the `git_repo` fixture), not a mock:
- `test_stage_generated_destinations_stages_only_actions_with_staged_source` — confirms `--stage` only
  `git add`s a create/update action's destination when its own canonical source is already staged
- `test_stage_generated_destinations_skips_actions_without_staged_source` — confirms an unrelated repair
  (drift the sync happened to also fix) stays unstaged when its canonical source isn't staged

Also dogfooded for real, in the same session, against this exact fix's own staged changes: running
`sync-plugin-mirrors --stage` correctly staged the `.claude/skills/commit/SKILL.md` mirror once its
canonical source (`plugins/git-kit/skills/commit/SKILL.md`) was already staged, and
`check-all --staged` reported OK afterward.
