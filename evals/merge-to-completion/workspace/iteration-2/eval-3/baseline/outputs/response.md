## Findings from live verification (per instruction #3)

Ran `gh pr view 92` in this repo. Result: **PR #92 exists, but it is not the PR described in the task.** It's a real, already-merged PR titled *"fix(ci): narrow await-codex-review triggers to Codex's real re-review conditions"* — a CI workflow-trigger fix, with no Linear issue link (its "Related Issue" section literally says "N/A") and no "4 acceptance criteria" framing anywhere in its body.

Also ran `mcp__claude_ai_Linear__get_issue` for `ENG-518` against the connected Linear workspace: **no such issue exists** — the API returned `"Could not find referenced Issue."`

So: the specific PR #92 / ENG-518 pairing described in the task is **synthetic** — it doesn't correspond to real objects in this repo or workspace. Everything below treats the task's PR #92 / ENG-518 as a hypothetical scenario and uses explicit placeholders rather than the real (unrelated) PR #92 content. I will not write to, comment on, or otherwise touch the real PR #92 or any real Linear issue.

## Plan for "record delivery after merge and disposition the Linear issue"

Standard engineering practice for closing the loop once a PR tied to a tracked issue merges cleanly:

**1. Confirm the merge actually landed and gather delivery facts (read-only)**
- `gh pr view 92 --json state,mergedAt,mergeCommit,baseRefName,headRefName,mergedBy` → would give: merge state (`MERGED`), merge commit SHA, merge timestamp, target branch, actor.
- Since the task states this already happened via squash merge with all 4 ACs verified by the implementer, I treat these as given but placeholder (not fabricated real values):
  - `PR: #92 (placeholder title)`
  - `Merge commit SHA: <PLACEHOLDER_SHA>`
  - `Merged at: <PLACEHOLDER_TIMESTAMP>`
  - `Merge method: squash`
  - `Target branch: main (placeholder)`

**2. Check for an existing auto-link before doing anything manually**
- Many GitHub↔Linear integrations auto-transition an issue (e.g., to "In Review"/"Done") when a linked PR merges, if the PR title/branch/description carries the issue's magic-word reference (e.g., `Fixes ENG-518`). Before manually changing state, I would check the Linear issue's activity/attachments (`mcp__claude_ai_Linear__get_issue` with `includeRelations: true`, and `list_comments`) to see whether the integration already recorded the merge. This avoids a duplicate/conflicting state change.
- Placeholder result assumed for this exercise: no auto-link fired (issue not found at all, consistent with it being synthetic), so a manual record is needed.

**3. Record delivery — two touch points**

a) **On the PR** (if it weren't already closed/merged and off-limits, and if this were a real linked PR): post a comment such as:
> Delivered via squash-merge in `<PLACEHOLDER_SHA>` (merged `<PLACEHOLDER_TIMESTAMP>`). Linked issue ENG-518 dispositioned as Done — all 4 acceptance criteria verified complete during development, no open questions.

Command I would run (not executed, since the real PR #92 is unrelated and must not be touched):
```
gh pr comment 92 --body "Delivered via squash-merge in <SHA>... ENG-518 marked Done."
```

b) **On the Linear issue** — this is the primary "delivery record" location: a comment on ENG-518 linking back to the PR/commit, listing the 4 ACs and noting they were verified by the implementer during development. Tool call I would make (not executed — issue doesn't exist):
```
mcp__claude_ai_Linear__save_comment
  issueId: <ENG-518 id>
  body: "Delivered via PR #92 (squash-merged, commit <SHA>, <TIMESTAMP>). All 4 acceptance criteria verified complete during development:
    1. <AC1> — verified
    2. <AC2> — verified
    3. <AC3> — verified
    4. <AC4> — verified
  No open questions or follow-ups identified."
```

If no attachment/link between the PR and the issue exists yet, I'd also add one for traceability:
```
mcp__claude_ai_Linear__create_attachment
  issueId: <ENG-518 id>
  url: <PR #92 URL>
  title: "PR #92 (squash-merged)"
```

**4. Disposition the issue**

Given: clean squash merge via the standard flow, all 4 ACs already verified complete by the implementer, nothing ambiguous or in question — this maps to the issue's terminal "completed" state (commonly labeled "Done" in Linear, exact label depends on the team's workflow states), not "Canceled"/"Duplicate"/"Won't Do" (those are for work that didn't ship) and not left in "In Review"/"In Progress" (those understate that delivery is confirmed).

Tool call I would make (not executed — issue doesn't exist):
```
mcp__claude_ai_Linear__save_issue
  id: <ENG-518 id>
  stateId: <the team's "Done"/Completed workflow-state id>
```

I'd resolve the correct state id first via `mcp__claude_ai_Linear__list_issue_statuses` (or `get_team`) for ENG-518's team, rather than guessing a label string, since exact state names vary per workspace.

**5. Sanity checks before calling it done**
- No Critical/unresolved review threads open on the PR (none indicated — task states it merged cleanly via standard flow).
- No other issues/PRs still reference ENG-518 as blocking or as a sibling task that should move together.
- Confirm the disposition comment and state change both reference the same merge commit SHA, so the audit trail (Linear comment ↔ GitHub commit) is consistent.

## Summary

- Verified for real: PR #92 exists but is unrelated to this scenario; Linear ENG-518 does not exist in the connected workspace. Both are treated as placeholders going forward, per instruction.
- No real side effects were executed (no `gh pr comment`, no Linear `save_issue`/`save_comment`/`create_attachment` calls) — all are described above as the exact calls that would be made, with placeholder IDs/SHAs/timestamps.
- Disposition chosen: move ENG-518 to its "Done"/completed workflow state, with a delivery comment on the issue (and optionally the PR) recording the merge commit, merge method (squash), and the 4 verified acceptance criteria — since nothing in the task indicates ambiguity, partial completion, or need for further review.
