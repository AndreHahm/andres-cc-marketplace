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

## Step 13.5 (real-commitlint check) — verified live, 2026-09-10

Installed the isolated toolchain (`pnpm --dir .github/commitlint-tools install --frozen-lockfile`), then
ran `lint-commit-message.sh` directly (not through a live `commit` invocation) against two drafted
messages: one with a 190-character body line (correctly failed, exit 1, reporting
`[body-max-line-length]` — the exact rule name the script's step-13.5 branching logic reads) and one with
a short body (correctly passed, exit 0, no output). Also confirmed commitlint's own `extends` resolution
requires the CLI's cwd to be inside `.github/commitlint-tools/` — running it from the repo root against
the same config threw `Cannot find module "@commitlint/config-conventional"`, matching
`commit-branch-guard.yml`'s own comment on this exact behavior (per
`.claude/rules/verify-tool-behavior-before-instructing.md`, checked against the real tool rather than
assumed) — confirming the script's `cd` into the toolchain directory is load-bearing, not incidental.
Also verified a relative message-file path resolves correctly after that `cd` (the script's
absolute-path resolution step), and that missing-argument/missing-file inputs fail with a clear message
rather than an unhandled error. **Not yet exercised**: a full live `commit` run that reaches step 13.5 as
part of its normal flow (drafts a message, hits a real violation, rewraps, re-checks) — this initial
verification ran the script directly to confirm its own logic and the underlying tool behavior; the
first real `commit` invocation on a message with a genuinely long body line is the next opportunity to
close this out.

**Round 2, 2026-09-11 — `cross-model-review` found the script conflated "couldn't check" with "checked
and clean" (exit 0 either way) and, separately, "install failed" with "message violates a rule" (both
just a non-zero exit under `set -e`):** Claude's own Phase 1 pass found the install-failure case; Codex's
independent Phase 1 pass found the pnpm-missing case; each confirmed the other's finding in Phase 2
cross-examination (both High confidence — Claude's rated major, Codex's rated minor, both retained at
their own severity). Fixed by giving both non-lint-related early exits their own exit code (2, with a
`SKIP:`-prefixed stderr line naming the reason) distinct from exit 1 (a real commitlint violation);
step 13.5 now branches three ways instead of two. Verified live against all four paths: clean pass (exit
0), a real 190-char body-line violation (exit 1, unchanged from round 1), pnpm hidden from `PATH` (exit
2, `SKIP: pnpm not available`), and a deliberately desynced `pnpm-lock.yaml` forcing a real
`--frozen-lockfile` install failure (exit 2, `SKIP: commitlint toolchain install failed`) — the install
failure reproduced pnpm's own `ERR_PNPM_OUTDATED_LOCKFILE` error, not a network-dependent flake, so it's
reproducible without needing an actually unreachable registry. `.github/commitlint-tools/package.json`
was restored via `git checkout --` and the real toolchain reinstalled immediately after, confirmed clean
via `git status`. Still not yet exercised: a live `commit` run reaching either exit-2 path through its
own normal flow rather than a direct script invocation.

**Round 3, 2026-09-11 — a second `cross-model-review` pass (mandatory re-check after round 2's fix,
before push) found two more issues, one substantial:** Codex's independent Phase 1 pass found the `cp`/
final-`commitlint`-invocation misclassification gap (confirmed by Claude's Phase 2, downgraded to minor —
both trigger conditions are rarer/more visible than round 1's, since a broken repo-wide config would also
break CI for everyone). Separately, Codex's own Phase 2 pass (with nothing to cross-examine, since
Claude's Phase 1 found nothing new) did its own fresh independent read and found a **novel, major
security issue**: `.commitlintrc.cjs` is a CommonJS module — commitlint's `--config` flag `require()`s
it, executing arbitrary code, not reading data — and the script was loading the raw checked-out
working-tree copy rather than a trusted ref, contradicting the file's own now-inaccurate comment ("no
trust-boundary step needed locally, since a local commit run only ever lints the developer's own drafted
message") and breaking the exact "attacker-controlled on a fetched branch" threat model every sibling
script in this same file (`scan-staged-files.sh`, `stage-selected-files.sh`, `lint-staged-python.sh`)
already treats as live. User chose the recommended fix: load `.commitlintrc.cjs` from a trusted ref
(`origin/<default-branch>`, resolved the same way `starting-work`/`finishing-work` do) instead of the
working tree, warning (not blocking) on divergence so a developer editing the config on their own branch
isn't silently ignored. **A second, environment-specific bug surfaced while implementing this fix**: on
this Windows git-bash environment, MSYS's automatic path-conversion heuristic silently mangled the
`origin/main:.commitlintrc.cjs` refspec into an invalid argument (verified live —
`git show origin/main:.commitlintrc.cjs` failed until `MSYS_NO_PATHCONV=1` was set, confirming the exact
mechanism per `.claude/rules/verify-tool-behavior-before-instructing.md`'s checked-against-the-real-tool
discipline), which would have made the trusted-ref lookup always silently fail and fall through to the
working-tree copy — defeating the fix's entire purpose on the platform it was written and tested on.
Fixed by setting `MSYS_NO_PATHCONV=1` on that one `git show` call. Verified live end-to-end: a clean
trusted-ref pass (no note printed, matching content); a deliberately diverged working-tree config
(appended a marker line, restored via `git checkout --` afterward) correctly printed the divergence note
and still validated against the trusted copy, not the tampered one; exit 1 (real violation), exit 2
(pnpm missing), and exit 2 (install failure, via the same desynced-lockfile technique as round 2,
package.json restored via `git checkout --` and the real toolchain reinstalled afterward) all still work
unchanged. `git status` confirmed clean (only the intended script edit) after every restore step.

**Self-review, same commit, before dispatching a third `cross-model-review` pass:** re-reading the
just-committed security fix found two more gaps on its own, closed before even re-invoking the reviewer:
(1) the "no trusted ref available" branch (no `origin` remote, or the file doesn't exist there yet) was
still falling back to the raw working-tree copy — silently re-opening the exact execution risk the fix
existed to close, for a caller with no way to tell "genuinely my own branch" apart from "a fetched branch
never inspected." Changed to `exit 2` (skip the check) instead of falling back. (2) Verifying that fix
against a throwaway no-origin-remote test repository (built fresh under the scratchpad, `git init` with
no `origin` configured, `.commitlintrc.cjs`/toolchain manifest copied in) surfaced a real, independent bug:
`DEFAULT_BRANCH="$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed ...)"` aborted the whole
script with exit 128 under this script's own `set -o pipefail` — `git symbolic-ref` failing (no origin)
still fails the *pipeline*, even piped into a `sed` that itself succeeds, and `pipefail` propagates that
into the command-substitution assignment, triggering `set -e` before the new exit-2 logic further down
was ever reached. Neither round 2's test suite nor round 3's Codex dispatch had exercised a genuinely
no-origin repository, since every prior live test ran inside this actual repo (which has `origin`).
Fixed by wrapping the fallible `git symbolic-ref` in an `if` (matching the pattern already used for the
`pnpm install` guard above) instead of piping it. Re-verified against the same no-origin test repo:
correctly prints `SKIP: could not read a trusted origin/main copy...` and exits 2. Also re-ran the full
regression (clean pass, violation, pnpm-missing) against the real repo — all unchanged, `git status` clean
except the one script file.

**Round 4, 2026-09-11 — a third `cross-model-review` pass found the trust boundary from round 2 was
incomplete:** `.commitlintrc.cjs` was now trusted, but the toolchain's `package.json`/`pnpm-lock.yaml`
were still read from the working tree — a fetched branch could alter either to make the isolated install
pull and later execute attacker-controlled code, the exact scenario `commit-branch-guard.yml`'s own CI
workflow already restores both files specifically to prevent. Confirmed independently, and separately
verified live that the existing `pnpm --dir` usage already correctly isolates `.npmrc` registry-redirect
risk the same way an actual `cd` would (`pnpm --dir .github/commitlint-tools config get
@commitlint:registry` and `(cd .github/commitlint-tools && pnpm config get ...)` both correctly returned
`undefined` against a repo-root `.npmrc` override) — that sub-risk was already closed; the manifest/
lockfile content itself was the real gap. Rather than restoring the trusted files on top of the tracked
working-tree copies (which would leave a developer's real `.github/commitlint-tools/package.json`/
`pnpm-lock.yaml` locally modified as a side effect of running a local lint check whenever they differed
from the trusted ref), redesigned the whole install to live under `.git/commitlint-local-check/` —
outside the tracked tree entirely, matching `write-git-kit-marker.sh`'s own convention of using `$GIT_DIR`
for local git-kit state. All three trusted files (`.commitlintrc.cjs`, `package.json`, `pnpm-lock.yaml`)
are fetched from `origin/<default-branch>` into that location; a stale/matching local cache skips
reinstall. Verified live: cold install (fresh `.git/.../commitlint-local-check`, real `pnpm install`);
warm-cache fast path (second run, no install, same exit 0); a corrupted local cache manifest correctly
detected as stale and reinstalled; clean pass, real violation (exit 1), pnpm-missing (exit 2), the
divergence note (working-tree `.commitlintrc.cjs` temporarily modified, restored via `git checkout --`
afterward), and the same no-origin-remote throwaway test repo from round 3 (still correctly exits 2) —
all unchanged in behavior. Confirmed via `git diff --stat` that `.github/commitlint-tools/package.json`/
`pnpm-lock.yaml` are never touched by any of these runs. Also removed the now-stale `.gitignore` entry
and leftover local artifact from round 2's superseded `.github/commitlint-tools/.commitlintrc.cjs`
design. Not re-exercised this round: a genuine install failure (the guard logic itself is unchanged from
round 2's already-verified version, just relocated) and a live `commit` run through the skill's own
normal flow rather than a direct script invocation.

**Round 5, 2026-09-11 — a fourth `cross-model-review` pass found one more gap, correctly rated minor:**
the "does this repo use commitlint at all" no-op check still read only the working tree — a fetched
branch could delete `.commitlintrc.cjs`/`package.json` locally to silently suppress the entire check
while the trusted `origin/<default-branch>` setup was still there. The straightforward fix (always
require a resolvable trusted ref before deciding) would have regressed the common case: every other
git-kit-using repo with no commitlint setup and no `origin` remote would print a confusing
`SKIP: could not resolve a trusted ref` on every commit. Fixed instead by checking both signals
(working tree via `[ -f ... ]`, trusted ref via `git cat-file -e "origin/$DEFAULT_BRANCH:<path>"`) and
exiting 0 only when *neither* indicates a setup — an ordinary repo without commitlint still gets a
silent, fast no-op exactly as before. Verified live: the exact bypass scenario (working-tree
`.commitlintrc.cjs` moved aside via `mv`, trusted ref still has it) still correctly ran the check and
caught a real violation, restored via `mv` back afterward, `git status` clean; a genuinely fresh
throwaway repo with no commitlint setup anywhere and no `origin` still exits 0 silently, no spurious
message; the existing no-origin-remote-but-has-commitlint-files test repo from round 3 still correctly
exits 2 with the `SKIP:` message; and the full regression (clean pass, real violation exit 1,
pnpm-missing exit 2) against the real repo, all unchanged.

**Round 6, 2026-09-11 — a real Codex review round on the live PR (#310) found a cache-invalidation bug
in round 4's `.git/`-based install:** the cache's `package.json`/`pnpm-lock.yaml` were promoted to the
new trusted content *before* `pnpm install` confirmed success. A failed install (reproduced live with
`ERR_PNPM_OUTDATED_LOCKFILE`) then left the next run's `NEEDS_INSTALL` check comparing against
already-promoted files that matched the trusted copy, skipping reinstall and silently executing the
prior, stale `node_modules/.bin/commitlint` against rules that no longer matched `.commitlintrc.cjs`.
Fixed by tracking "last successfully installed" via a separate marker pair
(`.last-installed-package.json`/`.last-installed-pnpm-lock.yaml`), written only after `pnpm install`
actually succeeds — `package.json`/`pnpm-lock.yaml` themselves still get overwritten unconditionally
(pnpm needs them physically present to run install at all), but the marker, not those files, is what
`NEEDS_INSTALL` now compares against. Verified live in three steps: (1) corrupted the marker while the
live cache files already matched trusted content — confirmed this alone forces a reinstall, proving the
marker is genuinely load-bearing, not the raw files; (2) forced a real install failure via a fake `pnpm`
binary on `PATH` that exits 1 — confirmed the marker was left unpromoted (still corrupted) afterward;
(3) reran with the real `pnpm` restored — confirmed the still-mismatched marker correctly triggered a
retry rather than a skip. Also re-ran the full regression (clean pass, real violation exit 1, warm-cache
fast path with no reinstall) — all unchanged. `git status` clean except the one script file throughout.

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
