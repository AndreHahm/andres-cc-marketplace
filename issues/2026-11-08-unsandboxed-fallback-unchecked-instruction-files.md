## Summary
The unsandboxed review fallback does not check project instruction files or user-level Codex config before it runs with full access.

## Environment
- **Product/Service**: `run-codex-review` unsandboxed fallback (`scripts/marketplace_ci/review.py`, `scripts/marketplace_ci/__main__.py`)
- **Region/Version**: branch `fix/windows-reviewer-sandbox-latch` (follow-up to #676)
- **Browser/OS**: Windows, Codex sandbox unavailable (#644)

## Reproduction Steps
1. Edit `AGENTS.md` (or another project instruction file Codex loads) on a branch.
2. Run the parity review on Windows so the reviewers fall back to `codex-windows-guardrails` (`danger-full-access`).
3. Compare what the fallback checks against base with what Codex actually loads.

## Expected Behavior
Every file that Codex loads from the checkout or the user profile and that can steer a full-access reviewer is either checked against the base, hashed, or explicitly accepted with a stated reason.

## Actual Behavior
Only the dispatcher closure (run from a base-tip snapshot) and `.codex/config.toml` (compared with base) are covered. These are not checked:
- `AGENTS.md` and other project instruction files loaded from the checkout
- the untracked guardrails override `.claude/codex-windows-guardrails.local.json`
- `~/.codex/config.toml`

## Impact
**Medium** - A changed instruction file can influence a reviewer that runs with this account's permissions and network access. The risk is already disclosed in `plugins/plugin-devkit/KNOWN_ISSUES.md`, and the security review of #676's fix rated it as disclose-only (finding M3).

## Additional Context
- Owner decision in the #676 PR: disclose only. Refusing whenever `AGENTS.md` changes would bring #676 back, because this repository edits `AGENTS.md` often.
- Proposed work: first find out which files Codex really loads (project and user level), then decide per file whether to check, hash or accept.
- Suggested labels: `t: security`, `p: medium`.
- Related: #676, #652, #644.
