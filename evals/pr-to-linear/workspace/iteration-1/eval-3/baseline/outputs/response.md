# Marking PR #77 Ready for Review

## 1. Confirm current state before touching anything

First I'd pull up the actual PR and issue rather than trust "looks done to me" at face value — that's a judgment call I want to verify, not just execute.

```
gh pr view 77 --json title,isDraft,state,statusCheckRollup,reviewDecision,baseRefName,headRefName,body,url
```

I'm looking for:
- `isDraft: true` — confirms it's actually still in draft (if it's already `false`, nothing to do, and I'd just say so).
- `statusCheckRollup` — are CI checks passing, pending, or failing? I would not flip a PR to ready with red or still-running checks without flagging it.
- `body` — does the description still contain a task list or "WIP" markers that contradict "looks done"? If so I'd want those reconciled first.
- `baseRefName` — merging into the right branch.

I'd also skim the diff quickly (`gh pr diff 77`) or at least the file list (`gh pr view 77 --json files`) to sanity-check that what's there matches what I'd expect a "done" PR linked to ENG-230 to contain — no leftover debug code, no obviously missing pieces (e.g., a test file with only stubs).

## 2. Check the Linear issue side

Since the PR is linked to ENG-230, I'd check the Linear issue itself:
- Current status (e.g., "In Progress")
- Whether ENG-230's acceptance criteria/sub-issues are all checked off
- Whether there are any linked sub-issues still open that would block calling this "done"

If ENG-230 has open sub-tasks or an unchecked acceptance-criteria checklist, I'd surface that as a discrepancy before proceeding rather than silently ignoring it — "looks done" from the PR side doesn't necessarily mean the Linear issue's own definition of done is satisfied.

## 3. Decide whether to actually flip it, or flag concerns first

If CI is clean, the branch is up to date with base (no conflicts), and the diff looks complete and coherent, I'd proceed. If anything above is questionable (failing checks, stale branch, open Linear sub-issues), I'd stop and report that back rather than marking it ready — "looks done to me" is the user's read, but I wouldn't rubber-stamp it if the mechanical signals disagree.

Assuming everything checks out:

## 4. Flip the PR from draft to ready for review

```
gh pr ready 77
```

This is the actual mechanism — `gh pr ready <number>` calls GitHub's `markPullRequestReadyForReview` mutation under the hood, which:
- Changes the PR's `isDraft` field from `true` to `false`
- Triggers any `pull_request` (`ready_for_review` / synchronize-adjacent) workflow triggers that were suppressed while in draft — so I'd expect required CI checks to (re)run if the repo's workflow config gates on ready state
- Makes the PR eligible for review requests / auto-assignment rules and any CODEOWNERS-based reviewer auto-request that's configured

I'd immediately verify the flip took:

```
gh pr view 77 --json isDraft,statusCheckRollup
```

confirming `isDraft: false` and watching whether new checks kick off.

## 5. Request reviewers (if not automatic)

If the repo doesn't have CODEOWNERS-based auto-assignment, I'd add reviewers explicitly, either ones already implied by prior PR conversation/context or by asking the user who should review:

```
gh pr edit 77 --add-reviewer <handle1>,<handle2>
```

I would not guess reviewer names silently if there's no clear signal (no CODEOWNERS match, no prior @-mentions on the PR) — I'd ask the user rather than pick someone essentially at random.

## 6. Post a short status comment on the PR (optional but useful)

Something like:

```
gh pr comment 77 --body "Marked ready for review — implementation and tests for ENG-230 are complete. CI is green on latest commit."
```

This isn't strictly required, but it gives reviewers context on why it moved out of draft right now, and gives a timestamp/audit trail distinct from the raw state-change event.

## 7. Update Linear (ENG-230)

This is the part that's easy to forget and where the two systems drift. Two ways this typically stays in sync, and I'd check which applies:

- **If the repo already has GitHub↔Linear integration configured** (Linear's GitHub app), moving the PR out of draft state is often already enough — many teams configure the integration so "PR ready for review" auto-transitions the linked issue's status (e.g., from "In Progress" to "In Review"). I'd check whether that automation exists before doing it manually, to avoid double-moving the issue or fighting the automation.
- **If there's no such automation, or I can't confirm it fired**, I'd manually update ENG-230:
  - Move status from "In Progress" → "In Review" (or the workspace's equivalent review-stage state)
  - Add a comment on the issue linking back to the PR and noting it's now ready for review, e.g. "PR #77 is ready for review: `<pr-url>`"

I would not leave ENG-230 sitting in "In Progress" once the PR is out of draft — that's exactly the kind of state where GitHub and Linear visibly disagree about where the work actually stands, and someone glancing at the Linear board would get a stale picture.

## 8. Final confirmation back to the user

I'd report back concretely, not just "done":
- PR #77 is now ready for review (confirmed via `isDraft: false`)
- CI status at time of flip (green/pending/any failures worth watching)
- Reviewers requested (who, or that none were auto-assigned and I need names)
- Linear ENG-230's new status, and whether that came from the integration firing automatically or a manual update I made
- Any discrepancy I noticed (e.g., an unchecked sub-issue) that the user should be aware of even though I proceeded

---

**Note: this is a synthetic evaluation run. No real `gh` commands, GitHub API calls, or Linear MCP/tool calls were executed — PR #77 and ENG-230 are not live, and the steps above are a description of the actions I would take, not an executed trace.**
