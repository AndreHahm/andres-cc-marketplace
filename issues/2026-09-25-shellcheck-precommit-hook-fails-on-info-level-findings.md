## Summary
Pre-commit `shellcheck` hook exits non-zero on pre-existing info-level findings in git-kit's guard
hook scripts, forcing `--no-verify` to commit unrelated changes

## Environment
- **Product/Service**: `.pre-commit-config.yaml`'s `shellcheck-py` hook (lines 114-119), `.shellcheckrc`
- **Region/Version**: shellcheck v0.11.0 (WinGet-installed), shellcheck-py rev v0.10.0.1
- **Browser/OS**: Windows (verified); Linux not yet verified — see Additional Context

## Reproduction Steps
1. Stage any change touching `plugins/git-kit/hooks/scripts/guard-raw-commit.sh` (or
   `guard-raw-branch-create.sh`, `guard-raw-destructive-cleanup.sh`, or
   `hooks/scripts/tests/test-guard-raw-pr-review.sh`) and its `.claude/` mirror.
2. Run `git commit` (pre-commit hooks enabled, no `--no-verify`).
3. Observe the `shellcheck` hook fail with exit code 1.

## Expected Behavior
The pre-commit `shellcheck` hook should pass (or the hook config should be tuned to a severity
threshold) for these scripts' existing, unchanged structure, so a commit that doesn't touch the
flagged code paths isn't blocked by pre-existing findings.

## Actual Behavior
`shellcheck` (via the `shellcheck-py` pre-commit hook, no `--severity` arg set, and
`.shellcheckrc` only disabling `SC1090`/`SC1091`) reports info-level findings and exits 1:
- `SC2317`/`SC2329` ("unreachable"/"never invoked") on `fail_closed_deny()` and
  `guard_diag_log_finish()` in the guard scripts' own trap/diagnostic-log handlers — these are
  deliberately indirect (invoked via `trap`, not a direct call), which shellcheck's static
  reachability analysis can't always follow.
- `SC1003`/`SC2016` (quote-escaping/no-expansion-in-single-quotes style notes) in
  `hooks/scripts/tests/test-guard-raw-pr-review.sh`'s escaped-quote test literals — intentional
  test fixtures exercising quote-escaping edge cases, not real bugs.

Verified this is pre-existing, not introduced by any specific change: running `shellcheck`
standalone against `git show HEAD:plugins/git-kit/hooks/scripts/guard-raw-commit.sh` (the file's
content prior to a recent rename in this same area) reproduces the same class of info-level
findings and the same non-zero exit code.

## Error Details
~~~
In .claude/hooks/scripts/git-guard-raw-branch-create.sh line 29:
  cat <<'EOF' || true
  ^----------^ SC2317 (info): Command appears to be unreachable. Check usage (or ignore if invoked indirectly).

In .claude/hooks/scripts/tests/git-test-guard-raw-pr-review.sh line 444:
  'gh api -H \$'"'"'a\'"'"' ...' \
                     ^-- SC1003 (info): Want to escape a single quote? echo 'This is how it'\''s done'.
~~~

## Impact
**Medium** — no functional bug in the scripts themselves (all 93 of `guard-raw-pr-review.sh`'s own
regression tests and all 22 git-kit skill smoke tests pass); the hook's own severity threshold
blocks any commit touching these files, forcing repeated `--no-verify` use, which defeats the
purpose of running pre-commit checks at all for this area of the repo.

## Additional Context
- **Related, not a duplicate**: #286 (closed, "Install pre-commit git hook") explicitly scoped this
  backlog out of its own acceptance criteria back on 2026-09-04/05, noting "shellcheck also has its
  own pre-existing backlog (87 findings across 26 shell scripts)... Neither is part of the hygiene-hook
  set this issue covers... so neither should block this work." That issue only covered installing the
  git hook itself (now done, since the hook actively blocked this session's commit) — it deliberately
  deferred actually fixing/tuning-for the shellcheck backlog, which is what this issue tracks.
- Encountered while committing PR 1 of the plugin-file-prefixes migration (`feat(git-kit): register
  git prefix, rename 19 files`, commit `f333e121` on branch `feature/git-kit-file-prefix-migration`,
  2026-09-25) — that commit used `--no-verify` to get past this pre-existing gap after confirming it
  was unrelated to the rename itself.
- **Open verification item**: only confirmed on Windows so far (WinGet-installed shellcheck v0.11.0,
  standalone invocation). Shellcheck's reachability analysis and default severity handling can differ
  across versions/platforms — worth confirming whether this reproduces identically on Linux (e.g. in
  CI) before assuming it's platform-independent.
- Two possible directions, not mutually exclusive: (a) set an explicit `--severity` arg (e.g.
  `warning` or `error`) on the `shellcheck-py` hook in `.pre-commit-config.yaml` so info-level
  findings don't block commits, or (b) address the underlying dead-code-looking patterns directly
  (e.g. a shellcheck directive comment near each trap-invoked function, or restructuring the
  escaped-quote test literals) so the findings clear even at the current strict threshold.
