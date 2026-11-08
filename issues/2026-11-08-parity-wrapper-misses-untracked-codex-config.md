## Summary
Parity wrapper's `fallback_touches` uses `git diff` and misses an untracked `.codex/config.toml`.

## Environment
- **Product/Service**: git-kit `create-pr` step 4.5 (`plugins/git-kit/scripts/git-codex-parity-review.py`)
- **Region/Version**: branch `fix/windows-reviewer-sandbox-latch` (follow-up to #676 and #652)
- **Browser/OS**: Windows, local parity run with the unsandboxed fallback

## Reproduction Steps
1. On a branch, create a new, untracked `.codex/config.toml` (do not `git add` it).
2. Run `git-codex-parity-review.py` on Windows when the Codex sandbox is unavailable.
3. Observe the wrapper's early check for files the fallback depends on.

## Expected Behavior
The wrapper refuses the unsandboxed fallback early, the same way it does for a tracked change to `.codex/config.toml`. Codex reads that file from the checkout, so it must not differ from the base.

## Actual Behavior
`fallback_touches` is built on `git diff`, which trusts the index and does not list an untracked file. The wrapper does not see the file. Not reproduced yet; this is derived from reading the code.

## Impact
**Low** - Not a gate bypass. `run-codex-review`'s own hash check of the checkout-read files still catches the change, so the run is refused there. The gap is only an early, clearer refusal in the wrapper.

## Additional Context
- Raised by the security review of #676's fix (finding m2) and deferred.
- Suggested options: also cover untracked files (for example `git status --porcelain` or `git ls-files --others --exclude-standard`), or document why the wrapper's check is allowed to be narrower than `run-codex-review`'s.
- Suggested labels: `t: security`, `p: low`.
- Related: #676, #652.
