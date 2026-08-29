## Summary
A workflow's own precondition-check gate (the Open-Question Gate in a "resolve an issue" workflow) never itself fetched the state it gates on — it assumed a separate, sibling workflow ("work an existing issue") had already fetched issue comments. A direct entry into the gating workflow (bypassing the sibling) reached the gate with no real state to check against.

## Environment
- **Product/Service**: `git-kit` plugin — `github-issue-lifecycle`'s Workflow 3 (`resolve-an-issue.md`)
- **Region/Version**: this repo, found during PR #172 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Invoke `github-issue-lifecycle` directly with "resolve issue #N" — `SKILL.md` routes straight to Workflow 3.
2. Read Workflow 3's Step 1 (Open-Question Gate) as originally written: it checks whether an open question remains, but never itself calls `gh issue view <number> --comments`.
3. Only Workflow 2 (`work-an-existing-issue.md`) contained that fetch. On a direct Workflow-3 entry, the gate has no comment data to check against at all.

## Expected Behavior
A workflow step that gates on external state must fetch that state itself whenever the step is a possible direct-entry point, never assume a sibling workflow already populated it.

## Actual Behavior
`gh issue view --help` confirms comments are opt-in via `-c/--comments`, not returned by default — so without an explicit fetch, the agent had nothing to check the gate against on a direct "resolve issue #N" request, and could close an issue based on absent or stale information.

## Impact
[Severity: Medium] A safety gate that silently has nothing to check against on one of its own documented entry paths isn't actually a gate on that path. Fixed in `git-kit`'s PR #172 (commit `de36493`): Workflow 3's Step 1 now runs `gh issue view <number> --comments` itself, verified live against `gh issue view --help`, so a direct "resolve issue #N" entry no longer depends on Workflow 2 having already run.

## Additional Context
Mined from PR #172's own review history (`chatgpt-codex-connector[bot]`; 11 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (an addition to the existing `## PR #172` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/172#discussion_r3882155769
