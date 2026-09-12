## Summary
No `git-kit` skill owns "mark a draft PR ready for review" as a callable, gated action

## Environment
- **Product/Service**: `git-kit` plugin (this marketplace)
- **Region/Version**: n/a

## Reproduction Steps
1. Have an open draft PR in this repository.
2. Look for a `git-kit` skill whose job is to flip that PR to ready-for-review (the equivalent of
   `create-pr` for creation, `merge-pr` for merging, `collaborating-on-a-pr` for reviewer actions).
3. Note that `gh-operations` lists `gh pr ready` in its `allowed-tools`, but its own frontmatter
   description states its `gh pr`/`gh issue` examples are raw reference material only, "never a
   substitute" for a dedicated lifecycle skill.
4. No other `git-kit` skill (`create-pr`, `merge-pr`, `collaborating-on-a-pr`, `cross-model-review`)
   actually performs or gates the draft-to-ready transition end to end.

## Expected Behavior
A `git-kit` lifecycle skill (an existing one extended, or a small new one) owns marking a draft PR
ready for review the same way the other lifecycle actions are owned: confirm the PR is actually a
draft, ensure `Skill(git-kit:cross-model-review)` has cleared against the current diff (running it if
it hasn't), confirm with the user via `AskUserQuestion`, call `gh pr ready`, and read back the result.

## Actual Behavior
No such skill exists. The only path today is the raw `gh pr ready` command via `gh-operations`, with
no readiness/review gating and no read-back convention — the same gap every other raw `gh` command in
that skill is explicitly documented as *not* a substitute for.

## Impact
**Medium** — a workaround exists (asking the user to run `gh pr ready` directly, or informally running
`cross-model-review` first before doing so), but the gap means the draft-to-ready transition is the one
PR lifecycle action with no dedicated skill backing, no consistent review gate, and no read-back
verification, unlike every other stage of the PR lifecycle this plugin already owns.

## Additional Context
Surfaced independently in two places during a `plugin-lifecycle-downstream` QA pass on
`workmanagement-kit` (PR #314, 2026-09-11/12):

1. `plugins/workmanagement-kit/skills/development-to-pr/SKILL.md` (a downstream plugin) used to carry
   a disclosed-gap note pointing at this exact missing capability, since its own existing-PR push path
   has nowhere to route a "flip to ready" request even though it now runs its own pre-push
   `cross-model-review` gate for regular pushes.
2. `plugins/git-kit/skills/cross-model-review/SKILL.md`'s own "When to Use" section explicitly names
   "before a draft PR is flipped to ready" as one of its own trigger conditions — implying a skill is
   expected to exist that performs that flip and calls `cross-model-review` from it, but no such skill
   currently does.

Proposed fix direction (a suggestion, not a mandate): add a "mark ready" action to an existing
lifecycle skill that already does readiness/gate checks (e.g. `merge-pr`), or a new small skill, that:
(a) confirms the PR is actually a draft, (b) runs `Skill(git-kit:cross-model-review)` against the diff
if it hasn't already cleared this session, (c) confirms via `AskUserQuestion`, (d) calls `gh pr ready`,
(e) reads back the result.
