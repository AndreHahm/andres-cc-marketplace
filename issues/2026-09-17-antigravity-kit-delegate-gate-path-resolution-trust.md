## Summary
antigravity-kit's delegation gate assumes PATH resolution is trustworthy

## Environment
- **Product/Service**: Claude Code plugin marketplace (`andres-cc-marketplace`), `plugins/antigravity-kit/hooks/agy-validate-delegate-bash.sh`
- **Region/Version**: `antigravity-kit` v0.1.0

## Reproduction Steps
1. The gate's `base()` function rejects any token containing `/` (a path-qualified command), accepting only a bare PATH name like `agy-delegate`, reasoning that this stops a file the subagent's own delegated agy run wrote from impersonating the real wrapper via a relative/absolute path.
2. However, a delegated agy process running under `--yolo` (the default) has arbitrary file-write access. It could write an impersonating `agy-delegate` executable to a directory that resolves earlier on PATH than the real install (e.g. `~/.local/bin`, if that precedes the real `bin/` on PATH).
3. A later gated call to the bare name `agy-delegate` would then be approved by the gate (`base(t) in WRAPPERS` still matches `agy-delegate`) but could resolve to the impostor at runtime, executing inside the Claude Code session's own process context.
4. Separately, `plugins/antigravity-kit/scripts/agy-job.sh` resolves its own delegate via `DELEGATE="${AGY_DELEGATE:-$HERE/agy-delegate.sh}"` — an environment variable override the gate's command-text scan doesn't account for (the gate blocks `VAR=x cmd` prefixes and inline `$VAR` expansion within a single gated call, but doesn't determine whether `AGY_DELEGATE` could already be set in the session's inherited environment before the gated call ever runs).

## Expected Behavior
The gate's bare-PATH-name check should hold even against a subagent with file-write capability of its own (via the delegated agy process), or the gate's own documentation should not claim impersonation is prevented without that caveat.

## Actual Behavior
The hook's header comment states this check exists specifically so "a file the subagent's own delegated agy run wrote… can never impersonate the real PATH wrapper" — this claim only holds for the relative/absolute-path form of impersonation, not the PATH-ordering form described above.

## Impact
**Medium (disputed/unverified)** — this is a static-analysis finding, not a confirmed live exploit. Whether the delegated agy process can actually write to an earlier-PATH directory, and whether such a write would actually be picked up by a later Bash call in the same session (rather than a fresh PATH resolution), needs live verification.

## Additional Context
Found by an independent `security-reviewer` pass during the #336 fix (removing `cat` from the gate's allowed pipe producers). Rated Major. This is a decision/investigation-tracking issue, not an implementation request — the next step is live-verifying whether this is actually exploitable, then deciding whether to narrow the comment's claim, add environment-variable hardening to `agy-job.sh`, or both.
