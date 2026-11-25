# Plan: "Mark PR #77 ready for review" (linked to ENG-230)

## Assumptions (unverified, plan-only)
- PR #77 is currently a draft. Its head SHA, check results, reviews and unresolved threads are unknown.
- ENG-230's state and acceptance criteria are unknown.
- Repository policy resolution through `repository-gates` is unknown. If the profile is unconfigured, the flow stops at a manual handoff.
- The user's "looks done to me" is treated as a claim to verify, not as evidence of readiness.

## Step-by-step plan

1. **Classify intent.** This is a readiness request. It is not a pure summary, and it must not fall through to a summary-only path. Per step 1.5, run the triage step first.

2. **Read current state (step 1).** Run `gh pr view 77` for head SHA, draft state, mergeability, reviews and the check rollup. Run `gh pr checks 77` for required checks. Run `Skill(repository-gates)` for the policy profile. Unresolved-thread state is not readable by this skill. No confirmation is needed for reads.

3. **Delegate triage and fix (step 2).** Invoke `Skill(git-kit:handling-review-findings)` for PR #77. That skill owns classification, fix, file and decline decisions, and reply/resolve. It may ask its own approvals, and any fix it applies goes through `git-kit:commit`. I would not do any of that myself. If it reports an unresolved Critical or Major finding, I stop and report it instead of continuing toward ready.

4. **Re-read GitHub state (step 3).** Because step 2 ran, re-run `gh pr view 77` and `gh pr checks 77`. Do not assume the triage outcome without confirming it.

5. **Reflect blockers to Linear (step 4).** Via `Skill(linear-work-management)`, post a concise ENG-230 comment: fixed, filed and declined per finding, plus any remaining gap. Do not paste check logs or review text.

6. **Verify for marking ready (step 5).** Immediately before the mutation, re-read draft state, head SHA, required checks, reviews, PR description and the Linear link. Unresolved threads rely on the step 2 report. If meaningful time has passed and a new inline comment could have landed, re-dispatch `handling-review-findings` before continuing.

7. **Revalidate Linear context (step 6).** Via `Skill(linear-work-management)`, check ENG-230's acceptance criteria and known blockers. If any criterion is open, surface it. This may contradict the user's "looks done" view.

8. **Present and confirm (step 7).** Ask via `AskUserQuestion`:
   - Question: "PR #77 head is `<sha>`, checks are `<status>`, and the triage report shows `<n>` findings fixed, `<m>` filed, `<k>` declined. Mark ready for review?"
   - Options: (a) "Yes, I will run `gh pr ready 77` myself now"; (b) "Hold as draft"; (c) "Other" (the tool's free-text fallback).

9. **Ready-state handoff (step 8).** No `git-kit` skill owns draft-to-ready. I do not run `gh pr ready` or any raw `gh pr` mutation. I ask the user to run `gh pr ready 77` outside this flow.

10. **Read back and record (step 9).** After the user confirms, re-read `gh pr view 77 --json isDraft,headRefOid`. Confirm `isDraft` is false and that the SHA matches the one checked in step 6. Only then record `pr-ready` via `Skill(linear-github-linking)`, bound to that exact SHA, with `provider: "manual (gh pr ready, per pr-to-linear's disclosed handoff)"`. If the SHA changed, re-verify from step 6. Do not record against a stale SHA.

11. **Linear status (step 10).** Ask via `AskUserQuestion` whether ENG-230 should move to In Review, but only if the approved Linear workflow calls for that as a distinct step. Otherwise I do not move it.

## Failure branches
- **Native automation already marked the PR ready, or changed Linear status:** this is drift. Preserve the current state and report it to the user for `linear-github-reconciliation`. I do not invoke that skill.
- **User declines at step 8:** stop with the PR still a draft. Record nothing as `pr-ready`. Keep the step 3 reflection on Linear.

## Recorded
- A concise ENG-230 summary comment (step 5).
- A `pr-ready` evidence entry, only after read-back and only for the confirmed SHA (step 10).
- Base transition writes under the next-write convention.

## Never
- Run `gh pr ready` or any raw `gh pr review`, `gh pr comment` or mutation myself.
- Re-triage, fix, reply to or resolve a finding outside `handling-review-findings`.
- Copy check logs or review transcripts into Linear.
- Record `pr-ready` against an unverified or stale SHA.
- Infer a Linear status change from GitHub's own automation.
- Treat unresolved threads as verified without step 2's report.
- Skip the step 2 triage just because the request says "mark ready" and not "triage".
