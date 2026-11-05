## Summary
The codex-windows-guardrails fallback (`guarded-dispatch.mjs`) ignores `CODEX_KIT_REVIEW_MODEL` and `CODEX_KIT_REVIEW_TIMEOUT_MS`, so a parity review that falls back runs reviewers on the local default model with a 240 s timeout instead of CI's model and timeout.

## Environment
- **Product/Service**: codex-kit, `plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs`, used by the parity review's unsandboxed fallback
- **Region/Version**: PR #646 head `2ae7461e`; Codex CLI 0.162.1 locally, CI pins 0.147.0
- **Browser/OS**: Windows 11

## Reproduction Steps
1. On Windows, set the repository variables the parity wrapper resolves (`CODEX_KIT_REVIEW_MODEL`, `CODEX_KIT_REVIEW_TIMEOUT_MS`) and run the local CI-parity review so that it switches to the guardrails fallback (for example with `--sandbox-down`).
2. Compare what a reviewer runs with: the normal path (`bridge-invoke.mjs`) reads both variables; the fallback does not.
3. In `guarded-dispatch.mjs`, find the `runCodexExec({ prompt, schema, sandbox: "danger-full-access", cwd, dispatchId, dryRun })` call and check that neither a model nor a timeout is passed.

## Expected Behavior
The fallback reads and validates the same two overrides as the bridge (same allowed-character check for the model, same positive-integer check for the timeout), so a fallback run matches what the wrapper advertised.

## Actual Behavior
`bridge-invoke.mjs` reads `CODEX_KIT_REVIEW_MODEL` and `CODEX_KIT_REVIEW_TIMEOUT_MS` (lines 620 and 635). `guarded-dispatch.mjs` reads neither, and `runCodexExec` falls back to the local default model and a 240000 ms timeout. A run advertised as using CI's model and a 600000 ms workflow timeout can therefore use a different model and end reviewers after four minutes. This may explain the repeated `skill-reviewer` timeouts seen in the unsandboxed parity runs (observed, not proven).

## Error Details
~~~
No error: the overrides are silently dropped.
run-codex-review: skill-reviewer timed out (attempt 3); retrying
run-codex-review: skill-reviewer timed out (attempt 4); retrying
(from an unsandboxed parity run; whether the 240 s default caused them is not established)
~~~

## Visual Evidence
None.

## Impact
**Medium** - Only the unsandboxed fallback path is affected, but that is the path used when the Windows sandbox is down. It makes a local parity result less comparable with CI and can turn slow-but-valid reviews into timeouts.

## Additional Context
- **Why this is a separate issue:** the fix edits `guarded-dispatch.mjs`, which is on `FALLBACK_FILES` (the files a branch must not change if it wants the fallback). Changing it inside the PR that introduces the fallback would make that branch's own fallback refuse itself, so it is deferred to a follow-up.
- **Suggested fix:** have `guarded-dispatch.mjs` read and validate both variables the way `bridge-invoke.mjs` does and pass them to `runCodexExec`; add a test for each; keep the two validators in one shared place if possible.
- **Related:** #644 (parent bug), PR #646.

## Review Finding Source
- **PR:** https://github.com/AndreHahm/andres-cc-marketplace/pull/646
- **Head SHA the finding was raised against:** 2ae7461e72d0eba0b719370546f828ea41d207c0
- **Review comment:** https://github.com/AndreHahm/andres-cc-marketplace/pull/646#discussion_r4483226772 (comment id 4483226772)
- **Reviewer:** the Codex GitHub connector
- **Severity as stated:** P2
