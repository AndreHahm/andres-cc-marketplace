## Summary
codex-windows-guardrails refuses the tracked template `.env.example`, so the local CI-parity review (`create-pr` step 4.5) can never complete on Windows

## Environment
- **Product/Service**: codex-kit `codex-windows-guardrails` (`plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs`) and git-kit's `.claude/scripts/git-codex-parity-review.py`
- **Region/Version**: Local Codex CLI 0.162.1 against CI's pin 0.147.0. Observed 2026-11-07 while working on issue #656.
- **Browser/OS**: Windows 11

## Reproduction Steps
1. On Windows, use a checkout that contains the tracked file `.env.example` (it arrived with the `decision-kit` plugin merge). The branch's own diff does not matter.
2. Run `uv run python .claude/scripts/git-codex-parity-review.py --sandbox-down --output <fresh scratch file>`.
3. Read the result JSON's `reviewer_results` and the run log.

## Expected Behavior
One of these, none decided:
- Well-known template names (`.env.example`, `.env.sample`, `.env.template`) are recognized as non-secret by the guardrails scan, with a content scan so a real value placed in a template is still caught.
- Or the failure is reported distinctly: a message that names the file and says a tracked template cannot be exempted, instead of failing every reviewer identically.

## Actual Behavior
All four reviewers (`plugin-rulebook-checker`, `dependency-reviewer`, `security-reviewer`, `skill-reviewer`) fail on attempt 1 with the typed category `secret_file_in_scope`. `dispatch_failed` is 4, the status is `could_not_run`, and the script exits 2.

Cause, read from the code and not executed: `guarded-dispatch.mjs` (roughly lines 596-620) never exempts a basename that matches a strict secret-filename pattern, through either exemption tier (the trusted-base `.secretlintignore` tier and the exact-path `.secretlintignore` tier). The repo's own `.secretlintignore` entry for `.env.example` (line 26) therefore has no effect here. The scan covers the whole working tree, not the diff, and skips only gitignored files. `.env.example` is tracked, so no branch change and no rebase can avoid it; it is in neither the branch diff nor the diff against `origin/main`.

## Error Details
~~~
run-codex-review: reviewer dispatch failed for: ['plugin-rulebook-checker', 'dependency-reviewer', 'security-reviewer', 'skill-reviewer']
  <each reviewer> (attempts: 1): {"ok":false,"category":"secret_file_in_scope","detail":".env.example matches sensitive-filename pattern /^\\.env(\\..*)?$/"}
exit=2
~~~

## Impact
**Medium** - Local-only (Windows) workflow with a manual route: a user bypass recorded in the PR's Open Items, and CI's own Codex review still runs on the PR. No wrong verdict is produced. In sandboxed mode the same host hits a different failure (Codex's read-only runner `helper_unknown_error`, tracked in #652; #644 is the closed predecessor), so on this machine the local parity round fails in both modes.

## Additional Context
Directions, none decided:
- Special-case well-known template names in `plugins/codex-kit/scripts/lib/cdx-secret-filenames.mjs` and `guarded-dispatch.mjs`, with a content scan.
- Allow a base-verified exemption for strict-pattern names.
- Make the parity wrapper (`git-codex-parity-review.py`) report this case distinctly.

Any change edits a security guard, so `.claude/rules/require-security-review-before-new-gate.md` applies: run a `security-reviewer` pass before it ships.

Not a duplicate of the related issues, none of which covers a tracked template file blocking the unsandboxed path:
- #652: Windows reviewer parity gaps (probe and retry behavior).
- #644: closed, the sandbox fails against `node_repl.exe`.
- #298: design question about excluding a real `.env` file from agent access.
- #178 and #162: other `guarded-dispatch` secret-scan false positives.

Found while working on #656; related as context only.
