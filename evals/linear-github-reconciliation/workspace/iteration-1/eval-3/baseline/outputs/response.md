# Reconciliation Review: Linear ENG-311 (Full Lifecycle) — Before Closing

## Important caveat up front

I have **no live access** to Linear, GitHub, or any MCP/API in this exercise — I did not and cannot query the real ENG-311 issue, its real history, or a real PR/branch. Everything below is therefore one of two things, and I've labeled each accordingly:

- **Method** — the concrete steps I would take, and the exact fields/records I would pull, if I had access.
- **Hypotheses / known failure patterns** — the specific kinds of lifecycle mismatches this class of investigation typically surfaces, based on how Linear↔GitHub integrations generally behave. These are things to *check for*, not claims that they occurred on the real ENG-311. I have zero verified facts about the real issue's actual state.

If this were a live investigation, step 0 would be: pull the real data before drawing any conclusion. Nothing below should be read as "ENG-311 has these problems" — it's "here is what I would check, and here is what commonly goes wrong when it isn't checked."

---

## 1. What "full lifecycle reconciliation" means here

Closing an issue on the strength of its *current* Linear status alone only tells you where it ended up, not whether it got there validly. A full reconciliation needs three independent data sources, cross-checked against each other, not just read individually:

1. **Linear's current state** — status, assignee, labels, cycle/project, priority, and critically the *linked* GitHub references (branch, PR, commits) Linear's integration has attached to the issue.
2. **Linear's history of changes** — the issue's activity/audit log: every status transition, who/what made it (a human vs. the GitHub integration bot vs. an automation rule), every re-link/unlink of a branch or PR, every comment, every time it was reopened.
3. **GitHub's current state** — the actual PR(s)/branch(es) that reference ENG-311: open/closed/merged/draft, which base branch, CI/check status, review state, merge commit (if any), and the commit messages/PR description for the literal "Fixes ENG-311" / "Closes ENG-311" style magic-word linkage.

The reconciliation is the exercise of building one combined timeline from (2) and (3) and looking for any point where they diverge — not just comparing the two *endpoints*.

---

## 2. Investigation steps I would take (in order)

1. **Pull the Linear issue record for ENG-311** — `get_issue` (or equivalent): status, assignee, team, cycle, project, priority, labels, and the list of linked GitHub attachments/branches/PRs Linear has associated with it.
2. **Pull the full comment/activity history** — `list_comments` and the issue's history/audit trail if exposed. I'm specifically looking for: every status change event (with actor — human vs. "Linear" bot vs. a named automation/workflow — and timestamp), every attachment added/removed, every reopen, every reassignment.
3. **Enumerate every GitHub reference tied to the issue**, not just the one Linear currently shows as "the" linked PR. Linear surfaces links via (a) an explicit attachment, (b) magic words in a PR/commit/branch name (`ENG-311`, `fixes ENG-311`, etc.), or (c) a manual paste of the Linear URL into the PR description. These three mechanisms can disagree — e.g., someone opens a first PR that gets abandoned, a second PR actually ships the fix, and Linear's auto-link may point at whichever satisfied the magic-word rule first, not necessarily the PR that merged.
4. **Pull GitHub state for every PR/branch found in step 3**: open/closed/merged, draft vs. ready, base branch, merge commit SHA, CI status, review approvals/change-requests outstanding, and whether the branch was force-pushed/rebased after the PR was opened (which can silently detach a previously-valid link or leave stale commit SHAs referenced in Linear comments).
5. **Check the commit(s) actually on the target base branch** (e.g., `main`) — confirm the PR that Linear thinks closed the issue is the PR that actually landed, on the branch that actually ships, not a PR merged into a long-lived feature branch that hasn't itself reached `main`/production yet.
6. **Build one merged timeline** from steps 2 and 4, ordered by timestamp, and diff it for inconsistencies (see checklist below).
7. **Check for duplicate/related issues** — search Linear for other issues referencing the same PR/branch, or ENG-311 referencing multiple unrelated PRs, which can indicate a split-work or duplicate-issue situation that the current single-issue view hides.
8. Only after all of the above is consistent would I treat "close ENG-311" as safe.

---

## 3. Specific mismatch patterns to check for (the actual reconciliation checklist)

### A. Status vs. PR state mismatches
- Linear shows **Done/Closed**, but the linked PR is still **open** or **draft** — the status was likely moved manually rather than by the automation, or the automation fired on the wrong PR.
- Linear shows **Done**, but the PR was **closed without merging** (abandoned) — the issue may have been marked complete based on a different, unlinked change, or in error.
- Linear shows **In Progress** or **In Review**, but GitHub shows the PR **already merged** — automation may have failed to fire (e.g., merge commit didn't contain the magic word, or squash-merge rewrote the commit message and dropped it).
- Linear shows **Done**, but the merge target was a **feature/staging branch**, not the branch that actually ships to production — "merged" isn't the same as "released."

### B. Timestamp ordering problems
- The Linear "moved to Done" activity-log timestamp **precedes** the GitHub merge timestamp — this indicates a human moved the status manually (anticipating merge) rather than the integration doing it automatically after the fact, which is a signal to double check the merge actually landed as expected and nothing changed between the manual close and the real merge (e.g., additional commits, a force-push, a merge conflict resolution).
- A comment or status change appears **after** the PR was merged that suggests follow-up work was still expected (e.g., "will follow up on the edge case") — that's a sign the issue may have been closed prematurely relative to its own recorded history, even if the PR itself is legitimately merged.

### C. Reopen / regression history
- The issue was moved to Done at some point earlier in its history, then **reopened**, then moved to Done again — I'd want to know *why* it reopened (a bug found post-merge? a revert?) and confirm the second close corresponds to a distinct, later fix rather than the same original PR being re-flagged as done without any new commit.
- A **revert commit** exists on the target branch for the original merge, but nothing in Linear's history reflects that reversion — this is one of the highest-value things to catch, since it means the issue is currently marked Done for a change that is no longer actually present in the codebase.

### D. Linkage integrity problems
- **Multiple PRs** reference ENG-311 (common when a PR is split, or a first attempt is abandoned and redone) — confirm which one is the actual ship vehicle and that Linear's automation followed *that* one, not a stale earlier attempt.
- **Branch name doesn't match Linear's expected convention** (e.g., missing the `eng-311` slug) — this is a common reason auto-status-transition silently never fires at all, leaving the issue stuck in whatever status a human last set it to, disconnected from the PR's real lifecycle from that point forward.
- A PR references ENG-311 in its **description** but not in its merge/commit message (or vice versa) — squash-merge in particular can drop the original PR description's magic words from the final commit that lands on the base branch, which can break the close-on-merge automation even though the PR itself is genuinely merged.
- The GitHub attachment on the Linear issue points at a PR in a **different repository** than expected, or at a **stale URL** (PR renumbered/repo transferred) — worth a sanity check if the org has done any repo migrations.

### E. Ownership/attribution mismatches
- Linear's assignee differs from the PR's actual author, with no comment explaining the handoff — not necessarily wrong, but worth surfacing since it can indicate the work was picked up by someone else without the Linear record being updated to reflect it.

### F. Scope drift
- The PR's actual diff addresses something **narrower or broader** than what ENG-311's description/title says — this isn't something I can check without reading both texts, but it's a standard reconciliation step: does the shipped change match the issue as written, or did scope silently shift mid-implementation without the Linear description being updated to match?

---

## 4. What "doesn't line up" would mean concretely for ENG-311

Since I have no real data, I can't assert which (if any) of the above actually applies to ENG-311. What I *can* say is the shape of a credible finding, so it's clear what "flag it" should look like once real data is pulled:

> Example finding shape: "Linear's activity log shows ENG-311 moved to Done on `<date>` by `<actor>`. The PR Linear has attached (`<PR link>`) shows a merge timestamp of `<later/earlier date>`, on branch `<branch>`, targeting `<base branch>`. `<Describe the specific discrepancy — e.g., merge came after the Done transition, or the PR is still in draft, or a second PR superseded this one>`. This means `<why it matters — e.g., the issue may have been closed before the fix actually shipped>`."

Any conclusion should be phrased with exactly this level of source-grounding — a specific Linear activity-log entry compared against a specific GitHub state/timestamp — not a general impression.

---

## 5. Recommendation

**Do not close ENG-311 on the strength of its current Linear status alone.** Before closing:

1. Pull the full Linear activity/history log for the issue (not just current fields).
2. Enumerate *every* GitHub PR/branch/commit that references it, not only the one currently shown as linked.
3. Build a single chronological timeline merging both sources.
4. Walk that timeline against the checklist in Section 3 (status/PR mismatches, timestamp ordering, reopen/revert history, linkage integrity, ownership, scope drift).
5. If everything lines up — the linked PR is merged to the real target branch, the merge timestamp is consistent with (at or before) the Done transition, no revert exists, no competing PR/branch is a better match, and the shipped diff matches the issue's stated scope — then closing is safe, and it's worth noting in a closing comment which PR/commit was verified as the actual fix (for future auditability).
6. If **any** item doesn't line up, don't silently close: leave a comment on the issue documenting the specific discrepancy found (with the concrete evidence — timestamps, PR links, actor names), and either reopen/re-route it or get explicit confirmation from the assignee/reporter that the discrepancy is expected (e.g., a deliberate manual override) before closing.

The general principle: **a clean current status is not evidence of a clean history** — the whole point of this reconciliation is that a status can be correct *right now* while having gotten there through a sequence of manual overrides, failed automations, or superseded PRs that a "current state only" check would never surface.
