# Walkthrough: Merge PR #51 and Disposition ENG-203

Task: "PR #51 (linked to Linear issue ENG-203) is approved and all checks pass. Merge it and
disposition the Linear issue." This invokes `merge-to-completion`. No live GitHub/Linear/Notion
connector access is available in this environment, so each step below states exactly which
tool/skill call I would make, what I would expect back, and — since none of that is actually
reachable here — what I did instead (stopped rather than fabricated a result).

## Step 0 — Skill selection

Confirmed `merge-to-completion` is the right skill, not a neighbor:
- Not `pr-to-linear` (that's pre-merge readiness marking).
- Not `linear-github-reconciliation` (that's drift repair unrelated to a fresh merge).
The request explicitly says "merge it and disposition the Linear issue," which is exactly this
skill's stated trigger phrase.

## Merge phase

### Step 1 — Resolve policy: `Skill(repository-gates)`

Call: `Skill(repository-gates)` scoped to this repository, asking "is git-kit the required merge
provider here?"

Expected read: `repository-gates` reads the repo's own governance config (e.g. a
`repository-gates` settings file or equivalent policy record) and confirms/denies that `git-kit`
owns merge for this repo, the same first step every other Wave 2 skill runs.

What I'd actually do here: invoke it and stop if it says a different provider is required (in
which case this whole flow would hand off rather than proceed). For this walkthrough I'm assuming
the expected/common case — `git-kit` confirmed as the required provider — since the task gives no
signal of an exotic provider setup, and note that assumption explicitly rather than hiding it.

### Step 2 — Verify readiness: delegate to `Skill(git-kit:merge-pr)`'s own checks

I do **not** re-implement or second-guess merge-pr's checks myself. The task states "approved and
all checks pass," but per the skill's own instructions I still delegate the actual verification —
current-SHA state, required status checks, no changes-requested, no merge conflicts, not-behind-
base, and merge-rights — to `merge-pr` itself rather than trusting the task description at face
value. If `merge-pr`'s own read contradicts "approved and all checks pass" (e.g. a check re-ran
and failed, or the base moved), `merge-pr` blocks and I stop and report that, I don't override it.

Unresolved review-thread count, if any, is disclosed by `merge-pr` at its confirmation step but is
not a blocking gate — I'd surface it to the user for them to weigh, not treat it as a merge blocker.

### Step 3 — Read Linear context: ENG-203

Call: read ENG-203 (via the Linear MCP tool, e.g. `mcp__claude_ai_Linear__get_issue` for
`ENG-203`, then `mcp__claude_ai_Linear__list_comments`/attachments for the PR link and any
acceptance-criteria text, likely in the issue description or a checklist).

Expected content I'd be looking for specifically:
- The issue's stated acceptance criteria (as a checklist or prose in the description).
- Confirmation that PR #51 is the linked delivery PR (via `linear-github-linking`'s existing
  link record, or Linear's own GitHub attachment).
- Current Linear workflow state (e.g. "In Review") so I can tell later whether GitHub's native
  integration moves it out from under me (Step 8).

This read is informational only — Linear's state (e.g. "In Review," "Blocked") never gates or
authorizes the GitHub merge. Even if ENG-203 looked stale or ambiguous in Linear, that would not
stop the merge in Step 5; it would only feed the disposition step later.

**What actually happened in this environment:** no live Linear connector session is available, so
I cannot pull ENG-203's real description/criteria. I'm flagging this explicitly rather than
inventing plausible-sounding acceptance criteria — doing so would violate the skill's own
data-only boundary (never act on fabricated "evidence") and would make Step 9's criterion-by-
criterion comparison fake. In a real run, this is the point where I would actually call the
Linear tool and read the real content before going further.

### Step 4 — Present and confirm: `AskUserQuestion`

Before touching anything, I present a single confirmation covering three things at once, per the
skill:
1. **Merge method** — squash, merge commit, or rebase (I'd default to asking rather than assuming;
   most repos in this marketplace pattern squash-merge feature branches, so I'd propose squash and
   let the user override).
2. **Branch behavior** — delete the source branch on merge or keep it (default: delete, matching
   `merge-pr`'s own default behavior and `finishing-work`'s expectations).
3. **The disposition workflow about to follow** — i.e., "after merge, I will separately walk
   ENG-203's acceptance criteria one by one and ask you how to close it out — this is not
   automatic."

Example `AskUserQuestion`:
> "PR #51 passes all git-kit merge-pr checks. Merge with squash, delete branch `feature/eng-203-*`
> on merge? After merging I'll separately walk ENG-203's acceptance criteria before deciding how
> to close the Linear issue — nothing closes automatically just because the merge succeeds."

I would wait for explicit approval here before proceeding to Step 5. This is a hard stop — the
skill lists this as one of only two points requiring approval (merge itself, and consequential
Linear disposition).

### Step 5 — Delegate: `Skill(git-kit:merge-pr)`

Call: `Skill(git-kit:merge-pr)` for PR #51, with the confirmed merge method/branch-deletion choice
from Step 4. `merge-pr` runs its own five required checks again internally (not draft, status
checks, no changes-requested, no merge conflicts, not behind base) and its own merge-rights check,
then executes the merge via GitHub. Its own step 8 will separately ask "run `finishing-work` now?"
— I do not pre-empt or duplicate that question myself.

### Step 6 — Read back actual GitHub state

Call: after `merge-pr` reports completion, read PR #51's actual current state directly (e.g. via
`gh pr view 51 --json state,mergedAt,mergeCommit` semantics, or whatever `merge-pr`/`gh-operations`
surfaces) rather than trusting "merge succeeded" as reported in-band. I specifically extract:
- `state: MERGED` (not just "no error returned")
- the actual **merge commit SHA** (`mergeCommit.oid` or equivalent) — this is the value that goes
  into the evidence record next, and it must come from this read-back, never assumed from the
  pre-merge branch tip.

If this read-back came back as anything other than `MERGED` (e.g. still `OPEN`, or `MERGED` but
with no SHA yet due to a delay), I would treat this as the "Unknown merge outcome" failure case and
stop to re-inspect before proceeding — never record `pr-merged` on an unconfirmed request.

### Step 7 — Record `pr-merged`: `Skill(linear-github-linking)`

Call: `Skill(linear-github-linking)` to append a `pr-merged` Git/GitHub Evidence Record entry to
ENG-203, with:
- `merge_commit_sha`: the exact SHA read back in Step 6 (never a value from the pre-merge branch
  tip — squash/rebase merges produce a new SHA never on the branch).
- PR number 51, repo, timestamp, actor.

Per `FOUNDATION_CONTRACTS.md`'s Git/GitHub Evidence Record shape, this goes in the record's own
`merge_commit_sha` field — explicitly **not** appended to `commits[]`, which is reserved for the
PR branch's own pre-merge commit history.

### Step 8 — Confirm native communication didn't overreach

Call: re-read ENG-203's Linear workflow state immediately after Step 7's write. If GitHub's native
Linear integration (if this workspace has it configured) already flipped ENG-203 to a "Done"/
"Closed"-equivalent state purely off the merge event, that is **drift**, not a valid disposition —
I would report it to the user explicitly ("GitHub's Linear integration auto-transitioned ENG-203
to Done on merge; per merge-to-completion this doesn't count as the disposition step — should I
proceed with the separate criterion review anyway, or hand this to `linear-github-reconciliation`
for someone else to sort out the drift?") rather than silently accepting the automatic state as
the real disposition. I do not invoke `linear-github-reconciliation` myself — the skill holds no
tool grant for it.

---

At this point, in a real run, the merge is done, GitHub confirms `MERGED` at a known SHA, and
Linear carries a `pr-merged` evidence entry. The task is only half done per this skill's whole
point: **a merge is not a disposition.**

## Linear disposition phase (separate, explicit)

### Step 9 — Compare delivered change against each acceptance criterion individually

I would pull PR #51's actual diff/description (via `gh pr view 51 --json files,body` or
equivalent) and ENG-203's acceptance criteria (from Step 3's read), then go through each stated
criterion one at a time — never inferring "merged ⇒ all criteria met."

For a large/ambiguous case, the skill allows (not requires) dispatching the plugin's shared Codex
bridge component (`scripts/bridge_caller.py`) to run `work-transition-reviewer` (read-only) as an
independent Acceptance check. I'd use this when the criteria list is long or the diff is large
enough that a second read-only pass materially reduces risk of missing a criterion; for a small,
clearly-scoped PR I'd do the direct comparison myself and skip the extra dispatch, noting that
choice.

**What actually happened in this environment:** without a live PR diff or live Linear issue body,
I cannot perform a real criterion-by-criterion comparison — I have no real criteria and no real
diff to compare. I am not going to fabricate three or four plausible-sounding "criteria" and mark
them "met," because that would be exactly the "merged, therefore done" shortcut this skill exists
to prevent, just with invented inputs instead of a lazy inference. This is the concrete point
where I would stop and ask the user (or pull the real data) before rendering any closure verdict.

### Step 10 — Classify each remaining item

For every criterion not cleanly "met by the diff as merged," classify as one of: completed,
follow-up Linear work, retained Notion question/decision, canceled with rationale, or unresolved.
An "unresolved" classification is reported to the user directly, never silently defaulted to
"completed."

### Step 11 — Present and confirm disposition: `AskUserQuestion`

This is the second (and last) hard approval gate in the skill. I would present, concretely:
- Which criteria are fully met by the merged PR.
- Which are not, with my proposed classification for each (follow-up / Notion / canceled /
  unresolved).
- For any criterion whose only disposition is "follow-up," I present **two distinct options**,
  never collapsed into one: (a) approve the follow-up only, issue stays open until it lands; or
  (b) approve the follow-up **and** separately confirm closing ENG-203 now with that gap tracked.
  Approving (a) is never read as also approving (b) — the skill is explicit that these must be
  separate choices.
- Any candidate Notion learning worth retaining as a decision/question record.

Example shape of that question (illustrative, since I have no real criteria to plug in here):
> "ENG-203 has N acceptance criteria. Based on PR #51's diff: [X] met, [Y] not yet addressed.
> For [Y]: (1) open a follow-up Linear issue and keep ENG-203 open until it lands, or (2) open the
> same follow-up AND close ENG-203 now with [Y] tracked there? Also: retain a Notion note on
> [decision/question], yes/no?"

I would not proceed past this without an explicit answer — this is exactly the kind of
consequential state-change decision the skill flags as always requiring confirmation.

### Step 12 — Create/link approved follow-ups: `Skill(open-item-management)`

For anything approved as a follow-up in Step 11, I hand it to `Skill(open-item-management)` rather
than inventing or directly creating a Linear issue myself. `open-item-management` runs its own
complete pipeline, including its own two separate approvals — I treat my Step 10 classification as
preliminary input to that pipeline, not a final verdict it must honor; if `open-item-management`'s
own revalidation reaches a different conclusion (e.g. decides an item doesn't warrant a new issue,
or scopes it differently), that's expected and correct, not something to override.

### Step 13 — Close ENG-203, only if justified

I close ENG-203 (via `Skill(linear-work-management)`, recording Wave 1's `work-closed` through the
base Transition Contract) **only** if:
- (a) every criterion was literally met, with nothing outstanding — record closure now; or
- (b) an outstanding criterion exists, its follow-up is now actually linked via Step 12, **and**
  the user separately and explicitly confirmed at Step 11 that closing now with that gap tracked
  is acceptable — not inferred from them merely approving the follow-up.

If neither condition is actually satisfied — e.g. a follow-up was approved but the user never gave
the separate "close now anyway" confirmation, or an item is still classified "unresolved" — ENG-203
**stays open**. I do not close it and do not infer closure from "we did a merge and made some
progress."

### Step 14 — Reopen path (contingency, not exercised here)

Noted for completeness: if later evidence contradicts a closure already recorded, that's a
`work-reopened` Git/GitHub Evidence Record entry via `linear-github-linking`, paired with the
actual Linear reopen action via `linear-work-management`. Not applicable to this run unless it's
later invalidated.

### Step 15 — Cleanup: explicitly not re-invoked

`git-kit:merge-pr`'s own step 8 (inside this skill's Step 5) already asked the user whether to run
`finishing-work` post-merge and, on yes, ran it bound to PR #51 directly. This skill holds no tool
grant for `Skill(git-kit:finishing-work)` and I do not call it again here — doing so could either
silently override a "no" the user already gave inside `merge-pr`, or run cleanup a second time
against a checkout that may have already moved to `main`. If cleanup still needs to happen for some
reason step 5 didn't cover it, that's a fresh, separate ask to `finishing-work` outside this flow,
not something folded back in here.

## Final disposition (this run)

Because this environment has no live GitHub or Linear connector access, I cannot actually produce
a real merge SHA, a real ENG-203 criteria list, or a real diff to compare against it — and per the
skill's own explicit design, I will not synthesize any of those and then round-trip a fabricated
"all criteria met, closing ENG-203" result. That would be precisely the "merged, therefore done"
shortcut this skill exists to prevent, just laundered through a made-up acceptance-criteria list
instead of a lazy inference from the merge event.

**What I would actually report to the user in a live run, concretely:**
1. Confirm via `repository-gates` that `git-kit` governs merge here.
2. Run `git-kit:merge-pr`'s real readiness checks against PR #51 (not trust "approved, checks
   pass" from the request alone).
3. Stop at one `AskUserQuestion` to confirm merge method + branch deletion + that a separate
   disposition step follows.
4. Execute the merge via `git-kit:merge-pr`, read back GitHub's actual `MERGED` state and true
   merge commit SHA, and record `pr-merged` on ENG-203 via `linear-github-linking` with that real
   SHA in `merge_commit_sha` (not `commits[]`).
5. Check whether GitHub's native Linear integration auto-transitioned ENG-203 on its own; report
   as drift if so, rather than treating it as the disposition.
6. Pull ENG-203's real acceptance criteria and PR #51's real diff, compare them one by one
   (optionally backed by a `work-transition-reviewer` dispatch for a large/ambiguous case).
7. Stop at a second `AskUserQuestion` presenting exactly which criteria are met/unmet, with
   "approve follow-up only" vs. "approve follow-up **and** close now" offered as genuinely
   separate choices for any unmet criterion.
8. Route any approved follow-up through `open-item-management`'s own independent pipeline —
   never create a Linear issue for it directly myself.
9. **Close ENG-203 only if** every criterion is met outright, or the narrower condition (b) above
   is explicitly satisfied by the user's own separate confirmation; otherwise **leave ENG-203
   open** and report exactly what's still outstanding.

**Given the actual constraints of this environment (no live connector data to compare against),
the honest disposition is: PR #51's merge mechanics are fully specified and ready to execute the
moment `git-kit:merge-pr` is actually invoked against a real PR — but I cannot render a real
closed/open verdict on ENG-203 without ENG-203's real acceptance-criteria text and PR #51's real
diff. In a live session, this is precisely the point where I stop and either pull that real data
via the Linear/GitHub tools or ask the user for it directly, rather than guessing.**
