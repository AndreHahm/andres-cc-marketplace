## Summary
A mirror-sync/parity tool's own registration list can be incomplete for one of a skill's three tracked copies, silently disabling parity checking for the unregistered copy with no error at any layer.

## Environment
- **Product/Service**: `plugin-devkit` plugin / `scripts/marketplace_ci` sync-parity tooling
- **Region/Version**: this repo, found during PR #133 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A skill's assets are tracked in three locations: `plugins/<plugin>/...`, `.claude/...`, and `.agents/...`.
2. The sync/parity config (`.claude/marketplace-sync.json`'s `codex_exports.skills`) does not list this skill.
3. Update the canonical `plugins/<plugin>/...` copy and its `.claude/` mirror, but not the `.agents/` copy.
4. Run `plan_exports`/`check_staged_parity` — both pass, because the tool never compares the unregistered `.agents/` copy against anything.

## Expected Behavior
A mirror-sync/parity tool's registration list should be checked for completeness whenever a new skill with a 3-way tracked mirror is added, so every tracked copy is actually covered by parity checking.

## Actual Behavior
The `.agents/` copy of `upstream-sources-registry`'s registry file silently drifted from the canonical source with no CI signal, since it was never registered in `codex_exports.skills` in the first place.

## Impact
[Severity: Medium] Fixed reactively for this one entry in PR #133 (commit `4bd7091`), but the underlying registration gap was explicitly left open — no CI check enforces `.agents/` parity for `upstream-sources-registry` going forward. This is the same category of blind spot already tracked in issue #188 (plugin-level `references/*.md` mirror drift) — a mirror-sync tool whose coverage doesn't match the marketplace's actual full set of tracked copies.

## Additional Context
Mined from PR #133's own review history (`devin-ai-integration[bot]`; 2 review rounds total) via
`mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #133`
section) by `managing-review-learnings`, which found no existing rule covering this subject before filing
this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/133#discussion_r3846398528

**Filed as a sub-issue of #188** (same root-cause category: `scripts/marketplace_ci`'s own registration/
coverage of what it treats as "mirrored" is incomplete relative to what's actually tracked) — relate via
the native sub-issues API once filed, per the user's explicit request for this candidate.
