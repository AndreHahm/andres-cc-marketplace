## Summary
`handling-review-findings`'s `references/next-round-trigger.md` contains 5 imperative "see
`references/X.md` for..." directives pointing to two other reference files, potentially forcing a
second/third context load on an agent that already loaded this file to execute Workflow step 8.

## Environment
- **Product/Service**: `plugins/git-kit/skills/handling-review-findings/references/next-round-trigger.md`
  (mirrored under `.claude/`)
- **Region/Version**: this repo, found by a `skill-reviewer` pass, 2026-09-26

## Reproduction Steps
1. Read `references/next-round-trigger.md` in full.
2. Five lines match the mandatory chain-violation check's own example pattern ("see references/bar.md"):
   - "see `references/round-and-dedup-rules.md`'s 'Triggered-cycle count vs. round' for the full rationale"
   - "see `references/settings-and-round-budget.md`'s 'The floor is 4 options, not 3' for the exact ... paths"
   - "see `references/round-and-dedup-rules.md`'s 'No persisted round-counter file' section for why"
   - "see `references/github-api-mechanics.md`'s 'Posting a review-trigger comment' section for the exact shape"
   - "see `references/round-and-dedup-rules.md` for why"

## Expected Behavior
A workflow/procedure reference file should be self-contained for anything actually load-bearing —
required to execute the step — with only genuinely optional supplementary rationale pushed to another
reference.

## Actual Behavior
5 pointers exist; most are short one-clause rationales that could be inlined, but whether each is
genuinely load-bearing (needed to execute) vs. supplementary "why" context is a judgment call the
originating check's own text doesn't resolve on its own.

## Impact
**Minor** — this is a workflow-clarity/self-containment observation, not a confirmed functional defect.
The reviewer that found this explicitly noted: "this style of cross-referencing between reference files
is a widespread convention across this plugin/repo... most other cross-references I found in this
skill's `references/` tree are non-imperative citations like 'per `references/X.md`' and were *not*
flagged" — so this may be an acceptable, disclosed exception rather than something needing a fix.

## Additional Context
**Not fixed in PR #407** — `next-round-trigger.md` is not a file that PR's diff touches; filed
separately per `merge-pr`'s step 1.5 session open-issues check. Suggested next step: either inline the
short rationales, or explicitly document this file's cross-reference density as an accepted exception
to the chain-violation check (matching how the reviewer itself distinguished it from the sibling
`resolve-an-issue.md` chain-violation, which does look like a genuine gap — see the linked related
issue).
