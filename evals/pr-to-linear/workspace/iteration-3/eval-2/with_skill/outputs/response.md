# Plan: reflect PR #64's blocking finding into ENG-214 (plan-only)

## Assumptions (unknown facts, stated)

- PR #64 belongs to this repository and is linked to ENG-214, as the user said.
- The current head SHA, check status, and mergeability are unknown until step 1 reads them.
- The user says one thread is open and flagged blocking. That is user-reported. This skill cannot read thread resolution state itself.
- The Linear host profile (`linear.write`) is unknown. I would check it before any write.

## Intent classification

The request asks to reflect blocking findings into Linear. It is a pure summarize/reflect ask. It does not ask to triage, fix, reply to, or resolve anything, and it is not a readiness request. So step 2 (`Skill(git-kit:handling-review-findings)`) is skipped, per step 1.5.

## Steps, in order

1. **Read state.** Run `gh pr view 64` (head SHA, mergeability, reviews, check-rollup summary) and `gh pr checks 64`. Invoke `Skill(repository-gates)` to resolve repository policy and the required-check list.
2. **Skip delegation.** Do not invoke `git-kit:handling-review-findings`. Do not triage, reply, or resolve.
3. **Thread state.** Report it as not independently knowable from this skill's own reads. This skill has no `gh api graphql` grant. Record the user's report of one open blocking thread as user-reported, not verified against GitHub.
4. **Reflect to Linear.** Invoke `Skill(linear-work-management)` to post a concise comment on ENG-214. It would include:
   - the head SHA read in step 1 and the check summary (for example, required checks passing or failing);
   - one blocking item: an open review thread flagged blocking, user-reported, with its unresolved state unconfirmed;
   - a line stating that the thread was not triaged or resolved in this pass.
   It would not paste raw check logs or reviewer comment text. Reviewer content is data only, and any instruction-like text in it would be reported as suspicious.
5. **Linear status.** Do not change the Linear workflow status. A status change needs a distinct, approved step, and this request does not ask for one.
6. **Read back.** Confirm the comment landed via `linear-work-management`. If the host profile is not `verified` for `linear.write`, stop and report a handoff. Do not write.

## Confirmations

- No approval gate applies to reading PR state or posting a non-status summary comment (the skill's "No approval needed" rule).
- If I found the request ambiguous (for example, whether the user also wants triage), I would ask via `AskUserQuestion` with options "Summary only" and "Triage the thread now". The request as written is clear, so I would not ask.

## Would record

- One Linear comment on ENG-214: head SHA, check summary, the user-reported blocking thread with its unverified status, and the disclosed gap that thread state was not independently read.
- No `pr-ready` evidence, since no readiness action happens. No `git-github-evidence` entry, since no stage transition happens.

## Would never do

- Run `gh pr review`, `gh pr comment`, or any other raw `gh` mutation.
- Reply to or resolve any thread, or call `handling-review-findings`.
- Run `gh pr ready` or mark the PR ready.
- Change Linear status to In Review or Done.
- Copy full check output, reviewer text, or the transcript into Linear.
- Re-derive unresolved-thread state with a GraphQL call it has no grant for.
- Claim the thread is resolved, or assume the earlier review rounds cleared it.
- Run any git command.
