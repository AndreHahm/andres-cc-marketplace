Answer (plan-only, following session-handoff SKILL.md CREATE Step 2):

I would write these frontmatter values:
- `state: in-review`
- `context_mode: review`

Why, in order:

1. The skill decides `state` from "where the work stands, judged from what this session knows about the next step", then takes `context_mode` "from the same row" (Step 2, item 5).

2. The next step is to open the PR. The `in-review` row covers exactly that: "The next step opens the PR, or a non-draft PR is open and review or fix work may still be needed | `review`". The user's "next session: open the PR and merge it" makes opening the PR the first action. So the row is `in-review` and the context mode is `review`.

3. `ready-to-merge` does not apply, even though the user said "merge it" and the gates passed locally. That row requires "The next step is `merge-pr` and nothing else is left before it: the PR is not a draft, no review findings are left to triage, no fix commits are pending, and when last checked the required checks were green and secretlint had passed". Here something is still left before `merge-pr`: no PR exists yet. So there is no non-draft PR, no PR review to triage, and no required checks have run on a PR. Local gates passing does not meet the row's conditions.

4. The other rows do not fit either:
   - `implementing` is for when "opening one is not the next step", but here it is.
   - `pr-draft` needs "A draft PR is open".
   - `ready-to-publish` is for a publish outside a PR.
   - `blocked` does not apply because nothing is blocking.
   - `done` needs a merged PR.

5. The tie-breaker points the same way: "When unsure between `in-review` and `ready-to-merge`, choose `in-review`."

6. I would not override the context mode. The skill says to "Override `context_mode` only with the reason stated in Important Context". Nothing here calls for that, so `review` stays as the row gives it, and `validate_handoff.py` will report no override note.

What else I would write in the handoff:
- Under Important Context's User Constraints, the user's instruction verbatim: "next session: open the PR and merge it".
- Immediate Next Steps item 1: open the PR. The merge comes after it, once the PR's checks and review allow it.
- The Resume Card goes last, at most 15 lines. It holds the state (`in-review`), next step 1 verbatim, the branch with "no PR yet", blockers (none), and the user's standing instruction verbatim.

I would ask the user nothing at this point. The table settles the choice, and the skill does not call for a question here.
