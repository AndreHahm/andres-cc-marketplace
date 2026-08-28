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

**Follow-up round, same date, after this PR's own automated review found three more real issues in
this same script:**
- **Executable bit**: `git ls-files --stage` confirmed the script was committed as `100644` — this
  repo's `core.fileMode=false` meant a local `chmod +x` never got recorded (the working-tree file
  still *looked* executable regardless). Fixed via `git update-index --chmod=+x`, re-confirmed
  `100755` in the index afterward.
- **Untracked-directory collapsing**: reproduced live — an untracked directory with 2 files showed as
  one `--list` candidate, and staging it staged both files. Added `--untracked-files=all` to the
  `git status --porcelain -z` call; re-verified the same directory now lists as 2 separate candidates,
  and staging only one of the two leaves the other genuinely untracked.
- **Snapshot-based anti-TOCTOU**: `--list` now persists its exact candidate list to
  `$(git rev-parse --git-dir)/stage-selected-files.snapshot`; the indexed staging call reads that
  snapshot back instead of recomputing `git status` fresh. Live-verified: ran `--list` (index 1 =
  `file-b.txt`), then created a new file (`aaa-new.txt`) that would sort first in a live re-scan,
  then staged index `1` — the snapshot's `file-b.txt` was staged, not `aaa-new.txt`, and the snapshot
  file is removed after a successful stage. Also closes GitHub issue #158 (filed for this exact race
  before this same review round independently reconfirmed it as CodeRabbit finding
  `stage-selected-files.sh:13`).
- **Control-byte-safe display**: the numbered `--list` output now prints each candidate through
  bash's `printf '%q'` (display only — the snapshot file and the actual `git add` pathspec still use
  the raw, unescaped bytes). Live-verified against the same command-substitution-crafted filename
  from the original run: displayed as `\$\(touch\ PROOF3\).py`, safely escaped, not run.

## Step 7.5 (lint/format/type-check staged Python files) — verified live, 2026-08-16

Ran `uv run ruff format`/`uv run ruff check --fix`/`uv run ty check` against two newly-written scripts
(`remap-handoff-shas.py`, `check-pr-title.py`) in this repository. `ruff format` reformatted both files on
the first pass; `ruff check` flagged 2 non-auto-fixable `E501` (line-too-long) violations, fixed manually
and reconfirmed clean; `ty check` separately caught 2 real issues `ruff` didn't (an unused blanket
`# type: ignore`, and `sys.stdout.reconfigure`/`sys.stderr.reconfigure` not resolving on the `TextIO`
union type) — confirming `ty check`'s inclusion catches a real class of error `ruff` alone misses. All
three checks passed clean after fixes.

## Step 16 (push) — fixed and verified live, 2026-08-28

This PR's first pass at step 16 replaced "retype/recompose the branch name" with "resolve it fresh
via `git rev-parse --abbrev-ref HEAD` immediately before pushing" — but this PR's own pre-push
automated review (Codex) correctly pointed out that this doesn't close the actual injection vector:
the model still has to interpolate the resolved value into the next command's text, which is the same
composition step that made the original version exploitable. Live-verified both halves in a scratch
repo: created a ref literally named `review/foo;touch${IFS}INJECTED` (confirmed a legal ref via
`git check-ref-format --branch`, exit 0); interpolating the `git rev-parse`-resolved value into a
composed `git push origin <branch>` string and running it did execute the injected `touch` (the
`INJECTED` file was created); `git push origin HEAD` against the identical ref pushed correctly with
no branch text ever appearing in a command the model builds, and created no `INJECTED` file. Step 16
now uses `git push origin HEAD` (`git push -u origin HEAD` with no upstream) instead.

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

**Follow-up round, same date, after this PR's own automated review found three more real issues:**
- **Partial-staging skip**: `test_stage_generated_destinations_skips_partially_staged_source` stages
  a canonical source, then makes a further unstaged edit on top (a partial stage), and confirms
  `--stage` leaves the generated destination unstaged rather than syncing it from the fuller
  working-tree content and staging a mismatch `check_staged_parity` would then reject.
- **`git add` failure handling**: `test_stage_generated_destinations_wraps_git_add_failure_as_sync_error`
  points a `SyncAction`'s destination outside the repository (where `git add` genuinely fails) and
  confirms `stage_generated_destinations` raises `SyncError`, not an uncaught
  `subprocess.CalledProcessError` — the CLI's existing `except SyncError` handling now covers it.
- **Hooks-merge staging**: `test_stage_hooks_merge_result_stages_when_contributing_source_staged` and
  `_skips_when_no_contributing_source_staged` confirm the new `stage_hooks_merge_result` correctly
  stages the merged `.claude/hooks/hooks.json` only when a contributing plugin's own
  `hooks/hooks.json` is staged and fully staged — the per-file `--stage` logic above has no single
  source to match against a merged, N-sources-to-1-destination result, so it never covered this case.

All 16 `tests/marketplace_ci/test_sync.py` tests (and the full 232-test `tests/marketplace_ci/` suite)
pass after this round; `ruff format --check`, `ruff check`, and `ty check` all pass clean on the
changed files.

**Round-2 follow-up, same date, after Codex's automated review found two more real issues in the
just-added `stage_hooks_merge_result` itself:**
- **Cross-contributor safety**: the round-1 version staged the merge as soon as *any one* contributor
  was staged, but `merged_document` is built from *every* contributor's working-tree bytes at once —
  a second, dirty contributor's unstaged edits were already baked into the content being staged, with
  nothing to catch it. Fixed by requiring every contributor with a resolvable in-repo path to pass
  `_is_fully_staged` before staging proceeds at all, not just the one(s) found in the staged set.
  `test_stage_hooks_merge_result_skips_when_another_contributor_is_partially_staged` reproduces this:
  one contributor cleanly staged, a second edited-but-never-staged, and confirms the merge stays
  unstaged.
- **Deleted contributors**: `plan.sources` only lists files that still exist on disk, so deleting a
  plugin's `hooks/hooks.json` made it invisible to the staging check entirely — the regenerated,
  now-smaller `.claude/hooks/hooks.json` never got staged. Fixed by also checking
  `GitState.staged_paths()` for a staged deletion whose old path matches the plugin-hooks-source shape
  (`plugins/<name>/hooks/hooks.json`) or the repo-level default path.
  `test_stage_hooks_merge_result_stages_when_a_contributing_source_is_deleted` reproduces this: deletes
  one of two contributors, re-plans against the now-current registry (so the deleted file is genuinely
  absent from `plan.sources`, matching what the CLI actually does), and confirms the merge still gets
  staged.

Both fixes required correcting the earlier hooks-merge tests too: they had never established a
committed baseline, so an untouched sibling plugin's file showed as genuinely untracked (`??`) rather
than clean — which the new, stricter safety check correctly treats as unsafe, but which made the
*existing* passing tests fail once the stricter check landed. Added a `_commit_baseline()` helper that
commits every fixture file first, matching the realistic case where unrelated plugins are already part
of history. All 18 `tests/marketplace_ci/test_sync.py` tests (234-test full suite) pass after this
round.
