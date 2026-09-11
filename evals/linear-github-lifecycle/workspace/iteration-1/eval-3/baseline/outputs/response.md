Before anything else: I don't have a live connection to Linear or GitHub in this environment, so I can't actually query ENG-288, the `acme/api` repo, or PR state right now. Everything below is the plan I would execute if I did, plus the assumptions and checks baked into each step. Treat the plan as a script to run against live data, not as a conclusion already reached from the evidence you've pasted.

## What the evidence implies (and what it doesn't)

- `work-started` → `commit-linked` → `pr-published`, all on `feat/eng-288-webhook-retries`, is a normal, unbroken progression — nothing here looks like a skipped or out-of-order step.
- `pr-published` with `gates: [lint: pass, unit-tests: pass]` tells me only that *those two named checks* passed as of whenever that evidence entry was recorded. It does **not** tell me:
  - whether the PR is still in **draft** state or was opened ready-for-review,
  - whether those are the **only** required checks on this repo, or just the only two that happened to be reported into this array,
  - whether the PR has any **review approvals** or outstanding change requests,
  - whether it's **mergeable** (no conflicts) right now,
  - whether anything happened **after** this evidence snapshot was taken (new commits, a force-push, someone closing the PR, etc.).
- The absence of a `pr-ready` entry is genuinely ambiguous to me without knowing how your tooling defines that event. Two plausible readings:
  1. It marks the draft→ready-for-review transition, and its absence means the PR is likely still a draft.
  2. It's a separate "all gates satisfied" marker distinct from the individual gate results, and its absence means something is still outstanding even though lint/unit-tests passed.
  Linear already showing **"In Review"** is a point in favor of reading (1) being resolved already (a PR being open at all commonly flips a linked issue to "In Review" automatically), but I wouldn't bet the merge decision on that inference alone.
- The absence of `pr-merged` is unambiguous: as of the last recorded evidence, this has not been merged.

**Working assumption**, stated explicitly rather than silently applied: the interruption happened somewhere between "PR opened, lint/unit-tests green" and "merge," and the issue is *not* actually done — "In Review" is the true current stage. I'm not going to assume it's safe to jump straight to merging just because two gates are green.

## Step-by-step resume plan

**1. Re-fetch live state before trusting the cached evidence at all.**
Interrupted runs are exactly the case where stale state bites you — pull fresh data rather than acting on the array as given.
- Get the current PR state via `gh pr view feat/eng-288-webhook-retries --repo acme/api --json state,isDraft,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup`.
- Get the current Linear issue state (status, any comments/activity since the last evidence entry) to see if a human already acted while the run was interrupted.
- *Check:* do these agree with what you pasted? If the PR is already merged, already closed, or the issue status has moved past "In Review," stop and re-plan — don't proceed on the stale assumption.

**2. Confirm draft-vs-ready status.**
- If `isDraft: true`, this explains the missing `pr-ready` signal cleanly. Confirm with the PR author (or the commit history) whether it's still a work-in-progress or was just never flipped to ready.
- *Check:* if it's genuinely finished and just never marked ready, mark it ready for review (`gh pr ready`) and note that as the resumed action, rather than silently treating "gates passed" as equivalent to "ready."
- If it's already ready-for-review, move on — this branch of the ambiguity is resolved.

**3. Get the full picture of required checks, not just the two in the evidence array.**
- Pull the repo's actual branch protection / required status checks for the target branch (`gh api repos/acme/api/branches/main/protection` or the repo settings) and the PR's full check-run list, not just lint/unit-tests.
- *Check:* are lint and unit-tests the *complete* required set, or are there others (integration tests, type-check, build, security/dependency scan, coverage threshold) that simply hadn't reported yet — or failed — when this evidence snapshot was taken? Don't assume two green gates means "all gates green."

**4. Check review status.**
- Look at actual review state: any approvals, any "changes requested," any assigned-but-not-yet-responded reviewers.
- *Check:* if there's an outstanding change-request, the correct resume action is addressing that feedback (or discussing it), not merging. If it's approved and waiting, the correct action is proceeding toward merge. If no reviewer is assigned at all, the resume action is requesting review, not silently merging.

**5. Check mergeability.**
- Confirm no conflicts with the base branch and that the branch is reasonably up to date (not badly behind `main`, depending on your repo's merge policy — rebase/update if needed).
- *Check:* `mergeable`/`mergeStateStatus` from step 1's fetch. If behind or conflicted, resolve that before anything else.

**6. Branch on what steps 2-5 actually show, rather than assuming a single next action:**
- **All green** (ready, all required checks pass, approved, mergeable): proceed to merge using whatever merge method this repo's convention dictates (squash/merge/rebase), respecting branch protection. Then verify the merge actually landed (check `main` for the commit, check the PR shows `MERGED`).
- **Checks incomplete or still running**: wait/re-poll rather than forcing a decision; don't treat "not yet reported" the same as "failed" or the same as "passed."
- **Checks failed**: this needs a fix, not a merge — flag it back to whoever owns the branch (or pick it up if that's your role here) rather than pushing through.
- **No review yet**: request review from the appropriate owner/CODEOWNERS match; don't self-approve or bypass review to unblock the lifecycle.
- **Still draft with real work remaining**: leave status as "In Review" (or whatever more accurately reflects "in progress"), and don't advance the issue further until the PR is genuinely ready.

**7. After a successful merge (only in the "all green" branch above):**
- Update the Linear issue status to whatever your workflow maps a merged PR to (commonly "Done" or "Merged" — confirm your team's actual status mapping rather than guessing "Done" by default).
- Record the merge back into whatever evidence/history mechanism your Linear-GitHub integration uses, so a future resume of this same issue sees a `pr-merged` entry and doesn't re-run this whole check.
- Handle branch cleanup per your repo's convention (delete the merged branch if that's standard practice here).
- Post a brief note/comment on the issue summarizing what happened (merged, when, by what mechanism) so there's a human-readable trail, not just machine evidence.

## Things I'd confirm with you before executing any of this for real

- What "Wave 2" refers to in your process — I have no context for what that wave boundary means operationally (e.g., does it gate something else downstream, is there a batch of sibling issues that need to reach the same state together), so I'm treating this purely as "resume ENG-288 to completion" rather than assuming it's coupled to other work.
- What your team's actual required-check list is for `acme/api`, since the evidence you have only shows two gates and I don't want to assume that's exhaustive.
- Your merge method convention (squash vs. merge commit vs. rebase) and your Linear status taxonomy (what status a merged PR should land the issue in) — I'd rather ask than guess and get either wrong on a live issue.
