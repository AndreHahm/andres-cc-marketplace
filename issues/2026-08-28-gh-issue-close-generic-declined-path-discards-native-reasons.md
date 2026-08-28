## Summary
Folding several distinct "declined"/close sub-cases into one generic `gh issue close --reason "not
planned"` path silently discards tool-native state that a more specific `--reason`/flag would have
preserved (e.g. `duplicate` + `--duplicate-of`)

## Environment
- **Product/Service**: `git-kit`'s `github-issue-lifecycle` skill, `workflows/resolve-an-issue.md`
- **Region/Version**: this repo, PR #172, Codex review round 1 (2026-08-28)

## Reproduction Steps
1. Write a "resolve/decline" workflow step that closes a GitHub issue via `gh issue close`.
2. Route every declined sub-case (not-planned, duplicate, wontfix, etc.) through one shared branch using
   a single generic `--reason` value.
3. Compare against `gh issue close --help`: the CLI actually exposes more specific reasons/flags for at
   least one sub-case (`--reason duplicate --duplicate-of <canonical>`), which preserves GitHub's native
   duplicate-issue relationship and link to the canonical issue.
4. The generic branch never uses the specific flag, so that native relationship is never recorded.

## Expected Behavior
Before folding several sub-cases into one generic tool-call path, check the tool's own `--help` (or
equivalent schema) for a case-specific flag/reason that preserves data the generic path would otherwise
silently drop.

## Actual Behavior
The one confirmed instance (`github-issue-lifecycle`'s Declined-duplicate path) used the generic
`not planned` reason for a duplicate closure, discarding the duplicate relationship `--duplicate-of`
would have recorded. Already fixed live in PR #172 itself (round 1, same session) — see
`plugins/git-kit/skills/github-issue-lifecycle/workflows/resolve-an-issue.md`'s current Step 2 for the
corrected dedicated-duplicate branch.

## Impact
**Low** — the one known instance is already fixed; this issue tracks the *generalizable* authoring
pattern itself (not a live bug), so a future skill/script that folds several tool-call sub-cases into
one shared path can be checked against this same shape before it ships, rather than being caught only
by a later external review round.

## Additional Context
Surfaced by `analysis-kit`'s `mining-review-learnings`/`managing-review-learnings` pipeline (Wave 3),
which mines merged PR review history for recurring, generalizable review-finding patterns. A
rule-coverage check against this repo's `.claude/rules/*.md` found no existing rule covering this
generalized shape — it's currently captured only as one specific instance in
`.claude/THIRD_PARTY_REVIEW_LEARNINGS.md`'s `## PR #172` entry (see that document for the exact
before/after `gh issue close --help` verification). Consider whether this pattern is worth its own
`.claude/rules/*.md` entry (e.g. as an addition to `verify-tool-behavior-before-instructing.md`'s
existing "check the tool's full schema" guidance) rather than staying issue-only.

Found via review of PR #172.
