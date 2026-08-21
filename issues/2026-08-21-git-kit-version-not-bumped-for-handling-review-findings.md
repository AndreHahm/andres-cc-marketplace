## Summary
PR #88 adds a new skill (`handling-review-findings`) and changes `guard-raw-pr-review.sh`'s hook behavior, but `git-kit`'s `plugin.json` and its `marketplace.json` entry both remain at `1.0.0-alpha.2` — unchanged from before this PR. Per this repo's own documented plugin-versioning policy, an installation pinned to an explicit version only receives updates when that version actually changes, so existing `alpha.2` installs of `git-kit` will not receive this new skill or hook fix through `claude plugin update`.

## Environment
- **Product/Service**: `git-kit`'s `.claude-plugin/plugin.json` and this repo's root `.claude-plugin/marketplace.json` entry for `git-kit`
- **Region/Version**: this repo, PR #88, found during that PR's own round-3 review

## Reproduction Steps
1. Note `plugins/git-kit/.claude-plugin/plugin.json`'s `version` field is `"1.0.0-alpha.2"`.
2. Note the same version in `.claude-plugin/marketplace.json`'s `git-kit` entry.
3. Compare against the parent commit before this PR's changes — both were already `1.0.0-alpha.2` there too, unchanged across the entire PR.
4. Per `plugins/plugin-devkit/skills/plugin-development/references/manifest-reference.md:71` — "Claude Code resolves a plugin's effective version in this order: explicit `version` in `plugin.json` → the marketplace entry's version → the git commit SHA → `"unknown"`. If an explicit version is set, users receive updates only when that version changes."

## Expected Behavior
A PR that adds a new skill and changes hook behavior should bump `git-kit`'s version in both `plugin.json` and `marketplace.json`, so a version-pinned install actually picks up the change.

## Actual Behavior
Version stays at `1.0.0-alpha.2` in both files, so `claude plugin update` won't deliver this PR's changes to an existing pinned install.

## Error Details
~~~
N/A -- not a runtime error, a missed release-process step.
~~~

## Impact
**Major** -- this PR's entire user-facing deliverable (the new `handling-review-findings` skill, plus a security-relevant hook fix) silently fails to reach any installation that pins `git-kit`'s version, with no error or warning at all -- the update mechanism just reports nothing changed.

## Additional Context
Found by a live Codex review round (round 3) on PR #88. Not fixed as part of PR #88 itself, per `handling-review-findings`'s own round-cap policy: this finding first appears in round 3, which routes to the Issue path per `references/round-and-dedup-rules.md` rather than an in-session fix, regardless of how small the fix itself would be -- the round cap governs review cycles, not per-finding fix difficulty.

**Suggested fix** (not prescriptive): bump `version` in both `plugins/git-kit/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`'s `git-kit` entry (e.g. to `1.0.0-alpha.3`, following this repo's existing alpha-increment convention) as part of merging this PR or a follow-up.

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/88
- **Head SHA at time of finding**: `fd9802afcd72ea726e25064ec5fba71a9c88d0bc`
- **Thread/comment**: https://github.com/AndreHahm/andres-cc-marketplace/pull/88#discussion_r3830100608
- **Reviewer**: Codex (`chatgpt-codex-connector[bot]`)
- **Stated severity**: P1
