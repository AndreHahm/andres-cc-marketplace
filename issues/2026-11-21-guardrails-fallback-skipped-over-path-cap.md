# Parity review: the Windows guardrails fallback is skipped silently for a diff over about 20,000 characters of paths

## Summary
`run-codex-review` does not offer the unsandboxed `codex-windows-guardrails` fallback when a reviewer's comma-joined path list is over 20,000 characters. With the sandbox reported down, it still prints that the reviewers run unsandboxed, runs them in the sandbox instead, and the result file does not say which mode each reviewer ran in.

## Environment
- **Product/Service**: `scripts/marketplace_ci/review.py` (`_dispatch_one`, `run-codex-review`), reached through `.claude/scripts/git-codex-parity-review.py`; fallback dispatcher `plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs`
- **Region/Version**: `main` at `772f5c26` (2026-11-21), Codex CLI 0.170.0, Node 22.23.1, Python 3.13.14
- **Browser/OS**: Windows 11

## Reproduction Steps
1. In a scratch clone, commit 800 new files (`fixture611/pkg<n>/mod_<nnnnnn>.py`, 1 KiB each). The comma-joined path list is 23,999 characters.
2. Enable guardrails in the clone (`.claude/codex-windows-guardrails.local.json`, `enabled: true`).
3. Run `python .claude/scripts/git-codex-parity-review.py --sandbox-down --output <scratch>/r800.json`.

## Expected Behavior
Either every reviewer runs through the fallback as the startup message says, or the run states that a reviewer's scope was over the fallback cap and records the mode each reviewer actually ran in.

## Actual Behavior
- The log says `Codex sandbox probe failed (reported down by the caller ...); running the reviewers unsandboxed (--allow-unsandboxed-fallback)`.
- `_dispatch_one` builds the fallback argv only when `len(",".join(reviewer_scope)) <= _MAX_GUARDED_TARGET_PATHS_CHARS` (20,000; Windows refuses a command line over 32,767 characters). Above it, `guarded_argv` is `None`, so `unsandboxed = start_unsandboxed and guarded_argv is not None` is false, and every reviewer makes the sandboxed bridge call.
- The run exited 0 after 503 s, status `clean`, 800 reviewed paths, one attempt per reviewer. It passed only because the sandbox works on this machine. The result file has no field recording the mode.
- By the code, on a machine whose sandbox is actually down, a diff over about 667 paths of 29 characters (about 526 of 37) gets no fallback and the review fails. That case was not run.

The sandboxed path itself handles large lists since #614 (`--target-paths-file`). The fallback still takes one comma-joined `--target-paths`.

## Impact
**Medium**: affects the local parity review on Windows when the Codex sandbox is down and the diff is large. Workarounds: fix the sandbox, or split the PR. CI is not affected.

## Additional Context
- Evidence: https://github.com/AndreHahm/andres-cc-marketplace/issues/611#issuecomment-7059564597
- Relates to #611 (Phase 5, large diffs), #614 (paths file for the bridge) and #676 (fallback files snapshot).
- **Owner decision needed:**
  - (a) give `guarded-dispatch.mjs` a paths file too. This is a `codex-kit` change to a fallback file: `review.py` is Tier-1, and the change needs its own `security-reviewer` pass.
  - (b) at least make the startup message and the result file say that a reviewer ran sandboxed because its scope was over the cap.
- Tests first, using fixtures, not live runs.
- Out of scope: Linux and CI behaviour.
