## Summary
Both Codex dispatch paths in `cross-model-review` are currently broken on Windows: the sandboxed
path silently no-ops instead of failing, and the Windows guardrails fallback refuses to run at all.

## Environment
- **Product/Service**: `codex-kit` (`codex-review-bridge`, `codex-windows-guardrails`), consumed by
  `git-kit`'s `cross-model-review`
- **Region/Version**: local Windows machine; `codex-cli 0.148.0`
- **Browser/OS**: Windows (Git Bash)

## Reproduction Steps
1. On a Windows machine, run `cross-model-review` (or dispatch either script directly) against any
   diff, with the Windows guardrails override already enabled
   (`.claude/codex-windows-guardrails.local.json` → `windows_guardrails.enabled: true`).
2. Step 1 (`codex-review-bridge/scripts/bridge-invoke.mjs`, `--execution-profile read-only`)
   completes and returns a schema-valid envelope with `findings: []` and `verdict: "approve"`.
3. Step 2 fallback (`codex-windows-guardrails/scripts/guarded-dispatch.mjs`) is attempted anyway,
   to get an actual review.

## Expected Behavior
Either the sandboxed path performs a real review (or fails with a typed error that triggers
automatic fallback), or the Windows guardrails fallback dispatches successfully and performs a real
review.

## Actual Behavior
**Path 1 (sandboxed, read-only):** returns a "successful" envelope, but its own `inspection_limits`
field says: *"The terminal could not create a process in the workspace (Windows error 1920), so the
requested git diff and target files could not be inspected."* Nothing was actually reviewed, but the
envelope is schema-valid and indistinguishable from a genuine clean pass unless a caller manually
reads `inspection_limits`.

**Path 2 (Windows guardrails fallback):** refuses to dispatch at all:
```
{"ok":false,"category":"secret_file_in_scope","detail":".agents\\skills\\skill-development\\references\\secrets-and-credentials.md matches sensitive-filename pattern /secret/"}
```

## Error Details
```
Path 1 inspection_limits:
"The terminal could not create a process in the workspace (Windows error 1920), so the requested git diff and target files could not be inspected."

Path 2 typed failure:
{"ok":false,"category":"secret_file_in_scope","detail":".agents\\skills\\skill-development\\references\\secrets-and-credentials.md matches sensitive-filename pattern /secret/"}
```

## Impact
**High** — Codex is unavailable for cross-model review on Windows right now; every run degrades to
single-model (Claude-only) mode, silently in Path 1's case unless the caller checks
`inspection_limits`. No workaround exists for Path 2 without a code/config change.

## Additional Context

**Root cause 1 (Path 1, likely the actual regression — reported working yesterday):**
`plugins/codex-kit/scripts/lib/codex-exec.mjs:419` only classifies a failure as the
`isolation_profile_unavailable` typed failure when the *outer* `codex exec` subprocess itself exits
non-zero with stderr matching `/CreateProcessAsUserW|sandbox|permission denied|access is denied/i`.
In this failure mode the outer `codex exec` process exits `0` — it's Codex's own inner tool call
(e.g. attempting `git diff` inside its read-only sandbox) that fails with "Windows error 1920", a
different error shape the regex doesn't match. Per commit `5bacd34` (2026-08-18, "fix(codex-kit):
teach reviewers to use inspection_limits, not fabricated findings"), Codex now correctly reports
this as `inspection_limits` instead of fabricating findings — but that same fix means this
total-sandbox-failure mode now produces a "successful" envelope instead of a typed failure, so it no
longer triggers the documented "on `isolation_profile_unavailable`, fall back to Step 2" resolver
behavior described in `plugins/git-kit/skills/cross-model-review/SKILL.md` and
`plugins/codex-kit/skills/codex-review-bridge/references/typed-failures.md`. This looks like an
unintended side effect of the 2026-08-18 commit, which landed 2 days before this report.

**Root cause 2 (Path 2, independent, pre-existing):**
`guarded-dispatch.mjs:428` runs `checkSecretFiles(["."], repoRoot)` — an unconditional, whole-repo
scan (not scoped to `--target-paths`) before granting `danger-full-access`, since Codex gets full
filesystem read access in this fallback mode. The flagged file
(`.agents/skills/skill-development/references/secrets-and-credentials.md`, present since commit
`72848d2`, 2026-08-06) is a documentation/reference file *about* secrets and credentials, not an
actual secret — a false positive against the `/secret/` filename pattern. Since the scan is
unconditional and whole-repo, it now permanently blocks the Windows guardrails fallback for *any*
dispatch in this repo, regardless of scope, until the file is renamed/excluded or the pattern gains
a docs/reference-file exception.

**Combined effect:** on this Windows machine right now, neither Codex dispatch path can produce a
real review. Path 1 silently no-ops (looks clean, but `inspection_limits` says it saw nothing) and
Path 2 refuses outright before even attempting a dispatch.

**Suggested next steps** (not prescribing the fix):
- Decide whether a "successful" envelope with non-empty `inspection_limits` and zero findings should
  be resolver-visible as a fallback trigger, not just an inert field a caller might not check.
- Decide whether `checkSecretFiles`'s pattern set needs a docs/reference-file exception (e.g. skip
  files under a `references/`/`docs/` directory, or require a stronger match than a bare filename
  substring) so a file *about* secrets doesn't block all full-access dispatch forever.

Discovered as a side investigation while running a normal `cross-model-review` request on branch
`feat/cross-model-review-pre-push-gate`; the review itself proceeded single-model (Claude only, by
explicit user choice) and was not blocked on this issue.
