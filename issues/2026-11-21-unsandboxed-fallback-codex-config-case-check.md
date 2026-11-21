## Summary
The unsandboxed fallback's `.codex/config.toml` check compares the path by exact case, so on a case-insensitive checkout a branch's `.Codex/config.toml` may be loaded by Codex while the fallback is still granted.

## Environment
- **Product/Service**: `run-codex-review --allow-unsandboxed-fallback` (`scripts/marketplace_ci/review.py`: `CHECKOUT_READ_FILES`, `fallback_files_changed`) and git-kit's parity wrapper (`plugins/git-kit/scripts/git-codex-parity-review.py`: `fallback_touches`)
- **Region/Version**: `main` at `772f5c26` (2026-11-21); behaviour present since the snapshot fallback of #676
- **Browser/OS**: Windows (where the fallback runs); the case folding also applies on macOS

## Reproduction Steps
Not reproduced: found by a static security review (issue #713's PR, finding M-A, marked unverified); no Windows machine was available.
1. On Windows, use a checkout in which `.codex/config.toml` does not exist, or a branch that changes it only through a path differing in case.
2. Add `.Codex/config.toml` with a different `[features]` table or an MCP server entry, and commit it.
3. Run `run-codex-review --allow-unsandboxed-fallback` directly, with the Codex sandbox unavailable.

## Expected Behavior
The fallback is refused when any path in the branch's tree equals a `CHECKOUT_READ_FILES` entry (or lies under `.codex/`) once case is folded but differs from it, and when the tree has two paths that differ only in case.

## Actual Behavior
`fallback_files_changed` and `fallback_touches` diff the literal path `.codex/config.toml`. A branch path `.Codex/config.toml` is a different path to git, so the check reports no change, while a case-insensitive file system can let Codex read it as `.codex/config.toml`. The fallback then grants `danger-full-access` with a configuration the branch controls.

## Error Details
~~~
No error: the comparison passes when it should refuse.
~~~

## Visual Evidence
None.

## Impact
**Medium** - It needs a crafted branch reviewed locally on Windows with the fallback enabled. When it applies, the reviewer runs unsandboxed under a branch-controlled Codex configuration, which can start MCP servers. In this repository the parity wrapper already limits it (see below), so the open path is a direct `run-codex-review` call.

## Additional Context
- **Partly covered by issue #713's PR:** the parity wrapper now refuses (exit 2) a branch whose tree has two paths that differ only in case, and the result's `advisory` field matches names without case. With this repository's tracked `.codex/config.toml`, a branch that keeps it and adds `.Codex/config.toml` hits that refusal, and a branch that deletes it shows up in the literal diff. A direct `run-codex-review --allow-unsandboxed-fallback` call outside the wrapper, or a repository without a tracked `.codex/config.toml`, is still exposed.
- **Suggested fix:** compare `CHECKOUT_READ_FILES` case-insensitively in `fallback_files_changed` and `fallback_touches`, and refuse the fallback on any case collision in the branch's tree, before it is granted.
- **Process:** `review.py` is a Tier-1 file, so the PR needs the maintainer bypass attestation.
- **Related:** #676 (the snapshot fallback), #650 (a different fallback gap: time of check to time of use), #713, #644.
