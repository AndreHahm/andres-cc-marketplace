# Task: Merge PR #77 (ENG-410) and Request Independent Acceptance Check

## How I approached this (no skills, standard tools only)

This response was produced without invoking any specialized skill/plugin workflow (no
`merge-pr`, no `linear-github-lifecycle`, no `pr-to-linear`, etc.) — plain reasoning plus
direct `gh` CLI / MCP tool calls only, per the baseline instructions for this run.

### Step 0 — Environment check (actually executed)

Before doing anything else I checked whether I actually have live access to the systems this
task references:

```
gh --version            -> gh version 2.88.1 (2026-03-12)
gh auth status           -> Logged in to github.com as AndreHahm, token scopes: repo, read:org, gist, admin:public_key
gh pr view 77 --json state,title,mergeable
   -> GraphQL: Could not resolve to a PullRequest with the number of 77. (repository.pullRequest)
```

**Finding:** `gh` is authenticated against GitHub in this environment, but PR #77 does not
exist in `andres-cc-marketplace` (the repo this worktree belongs to). This confirms the task
is a hypothetical/scenario exercise, not a literal instruction to operate on a real PR in this
repository. The Linear MCP tools listed as available (`mcp__claude_ai_Linear__*`) are wired up
in principle, but I was explicitly told this environment has no live GitHub/Linear/Notion
connector *data* to act on for this task, so I have not called `get_issue`, `save_issue`,
`save_comment`, etc. against a real ENG-410 — doing so would either fail or, worse, risk
fabricating what looks like a real Linear issue and acceptance criteria that don't exist.

Everything below is therefore a **concrete, executable plan** — exact commands and exact tool
calls I would make, in order, against the real PR/issue — rather than a claim that I already
ran them or a fabrication of what they'd return.

---

## 1. Understanding the request

- **PR #77** is large, ambiguous (a broad refactor), already **approved**, and **all CI checks
  pass**. Mergeable by the letter of most branch-protection rules.
- It's linked to **ENG-410** in Linear, which has **6 acceptance criteria (AC)**, and the user
  states **some of those AC are open to interpretation**.
- The instruction has two parts, and the ordering/sequencing matters:
  1. **Merge the PR.**
  2. **Request an independent Acceptance check before finalizing the Linear disposition.**

The key judgment call: "approved + checks green" is a *code-review* signal, not an
*acceptance-criteria-satisfied* signal. A refactor PR can be well-written, reviewed, and
green on CI while still only partially — or arguably — satisfying a product/behavioral
acceptance criterion, especially when the AC are explicitly flagged as open to interpretation.
So I merge the code (nothing about "approved, checks pass" blocks that), but I treat
**merging the PR** and **closing out ENG-410** as two separate events, not one. The Linear
issue's disposition (moving it to Done) should not be finalized on the same action as the
merge — it should wait on an independent reviewer confirming each of the 6 AC against the
merged result.

## 2. Assumptions I'm making explicit (per "state assumptions, don't hide confusion")

- "Independent Acceptance check" = a review of the 6 acceptance criteria performed by someone
  other than the PR's code reviewer/approver — i.e., not just re-using the code-review approval
  as a proxy for acceptance sign-off. I'm treating "independent" as *person-independent*
  (different reviewer), not *tool-independent* — if that's wrong, that's a case where I'd
  normally ask rather than guess, but under this environment's instructions I'm making the
  more conservative reading (a second human/agent, not just re-running CI) since it's the one
  that actually catches interpretation risk.
- I don't know this repo's specific merge convention (squash vs. merge commit vs. rebase) or
  Linear's exact workflow states (e.g., whether there's an "In Review" / "QA" / "Needs
  Acceptance" state distinct from "Done"). I call these out below as things to confirm rather
  than guessing a specific state name.
- I don't have the actual text of ENG-410's 6 AC. I can't respond as if I know which ones are
  "the ambiguous ones" — that would be fabrication. The plan below has that as an explicit
  step.

## 3. Plan

```
1. Verify PR #77 is actually safe to merge right now
   → verify: gh pr view 77 --json state,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup
     confirms state=OPEN, reviewDecision=APPROVED, mergeable=MERGEABLE, all checks SUCCESS,
     and no new commits landed after the approval (re-approval-on-push settings vary by repo).

2. Fetch ENG-410's real acceptance criteria and current Linear status
   → verify: mcp__claude_ai_Linear__get_issue on ENG-410 returns the 6 AC text and current
     state, plus any existing links/attachments already tying it to PR #77
     (mcp__claude_ai_Linear__get_attachment / list on the issue, since linear-github auto-link
     may already exist).

3. Merge PR #77
   → verify: gh pr merge 77 --squash (or whatever method matches this repo's default —
     confirm via `gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed`
     and the repo's branch-protection default before picking) --delete-branch, then
     gh pr view 77 --json state,mergedAt confirms state=MERGED.

4. Do NOT set ENG-410 to "Done" as part of the merge
   → verify: leave Linear status as-is, or move it to an explicit intermediate state such as
     "In Review" / "Needs Acceptance QA" if the workspace has one
     (mcp__claude_ai_Linear__list_issue_statuses on the team to see what states actually
     exist — don't invent a state name that isn't configured).

5. Post an explicit, itemized independent-acceptance-check request on ENG-410
   → verify: mcp__claude_ai_Linear__save_comment on ENG-410, addressed to a specific reviewer
     (not the PR's own approver), enumerating each of the 6 AC as a checklist item against the
     now-merged PR #77, and explicitly flagging which AC are ambiguous/interpretation-dependent
     so the independent reviewer knows where extra judgment is needed rather than a rubber
     stamp. Draft text in section 4 below.

6. Leave final Linear disposition (Done vs. something else) to that independent check
   → verify: ENG-410 is only moved to "Done" after the independent reviewer confirms all 6 AC
     (or explicitly accepts partial/interpreted satisfaction) — not by this action.
```

## 4. Exact commands / tool calls I would issue (in order)

```bash
# 1. Confirm mergeability precisely (not just "approved, checks pass" from the prompt)
gh pr view 77 --json state,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,title,url

# Confirm repo's allowed/default merge method rather than assuming squash
gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed,deleteBranchOnMerge
```

```
# 2. Pull the real acceptance criteria and current state from Linear (MCP)
mcp__claude_ai_Linear__get_issue        { "id": "ENG-410" }
mcp__claude_ai_Linear__list_issue_statuses  { "teamId": "<ENG team id from get_issue>" }
```

```bash
# 3. Merge — using whichever method step 1 confirms is the repo default, e.g.:
gh pr merge 77 --squash --delete-branch

# Confirm it landed
gh pr view 77 --json state,mergedAt,mergeCommit
```

```
# 4/5. Post the independent-acceptance-check request as a Linear comment on ENG-410
mcp__claude_ai_Linear__save_comment {
  "issueId": "ENG-410",
  "body": "<see draft below>"
}

# Only if the workspace has a distinct pre-Done state (confirmed via list_issue_statuses,
# not assumed):
mcp__claude_ai_Linear__save_issue {
  "id": "ENG-410",
  "stateId": "<id of e.g. 'In Review' / 'Needs QA' state>"
}
```

## 5. Draft comment to post on ENG-410 (independent acceptance-check request)

```
PR #77 (link) has merged into main — it was approved and all CI checks passed.

Because this was a large refactor and this issue's acceptance criteria include some items
that are open to interpretation, I'm not closing ENG-410 out as part of the merge. Before
marking this Done, please have someone who was NOT the code reviewer on #77 independently
verify each of the 6 acceptance criteria against the merged result:

1. [AC 1 — paste exact text from Linear]
2. [AC 2 — paste exact text from Linear]
3. [AC 3 — paste exact text from Linear]
4. [AC 4 — paste exact text from Linear]
5. [AC 5 — paste exact text from Linear]
6. [AC 6 — paste exact text from Linear]

Flagging in particular: [name the specific AC the requester or the issue text already calls
out as ambiguous, once actually known] — these read as open to interpretation, so please note
your interpretation explicitly in your acceptance sign-off rather than a bare pass/fail, so
there's a record of what "met" was taken to mean.

Once acceptance is confirmed (or partial/interpreted acceptance is explicitly noted), please
move this to Done — I'm leaving it in [state] until that review lands.
```

(The bracketed placeholders are exactly that — placeholders. I have not invented plausible-
sounding acceptance-criteria text to fill them in, since I have no real ENG-410 data in this
environment; a live run would fetch the real text via `get_issue` in step 2 before drafting
this comment for real.)

## 6. Why merge now rather than waiting for the acceptance check first

Worth stating the tradeoff explicitly rather than picking silently: one could argue the
acceptance check should happen *before* merging, so a failed AC doesn't have to be walked back
out of `main`. I chose merge-then-verify because:

- The PR is already approved and green — holding a reviewed, passing, large refactor PR open
  and unmerged accumulates merge-conflict risk against `main` the longer it sits, and the user's
  instruction sequence explicitly says "merge it, and [then/also] request an independent
  Acceptance check" — merge first is the literal reading.
- "Acceptance criteria" for a refactor PR are typically about behavior/output being preserved
  or improved, not about literally gating the merge button — that's what code review + CI already
  gate. The acceptance check is the safety net for the *Linear issue's* disposition, not a second
  merge gate.
- If the independent check finds a real AC violation, the fix is a normal follow-up commit/PR
  against `main` (or a revert, if severe) — the same remediation path as any other post-merge
  bug, not something that requires the code to have stayed unmerged.

If this assumption is wrong for this team's actual workflow (some teams do gate merge on
acceptance, not just code review), that's exactly the kind of thing worth confirming with the
user rather than silently assuming — flagging it here rather than picking silently.

## 7. What I did not do

- Did not fabricate PR #77's diff, title, author, or file list.
- Did not fabricate ENG-410's 6 acceptance criteria or Linear's current issue state/workflow
  states.
- Did not actually call the Linear MCP tools or execute `gh pr merge` against a nonexistent
  PR — `gh pr view 77` already confirmed there's no real target in this repo to act on.
- Did not invoke any `plugin-devkit`/git-kit/workmanagement-kit skill (`merge-pr`,
  `pr-to-linear`, `linear-github-lifecycle`, `merge-to-completion`, etc.) — this is the
  no-skill baseline for comparison purposes.

## 8. If this were a real, live PR #77 / ENG-410

The only two inputs I'd need before executing the plan for real: (1) confirmation of this
repo's default merge method (squash/merge/rebase — checked via `gh repo view`, not guessed),
and (2) the actual 6 AC text and current Linear workflow states (checked via
`get_issue`/`list_issue_statuses`, not guessed) so the acceptance-check comment names the real
ambiguous item(s) instead of a placeholder. Everything else in the plan above is ready to run
as-is.
