I would write `state: ready-to-merge` and `context_mode: ship`. I read SKILL.md in full and did not need the reference files: CREATE Step 2, item 5 settles it. I ran nothing and edited nothing.

**What I would do, in order (CREATE Step 2, item 5):**

1. **Set `state`.** The skill says: "set the frontmatter's `state` to where the work stands, judged from what this session knows about the next step". The `ready-to-merge` row requires: "The next step is `merge-pr` and nothing else is left before it: the PR is not a draft, no review findings are left to triage, no fix commits are pending, and when last checked the required checks were green and secretlint had passed (or its failure was triaged), as the ship profile requires". The scenario meets every condition:
   - The only next step is `merge-pr`.
   - PR #901 is ready for review, not a draft.
   - Every finding is resolved and its threads are closed, so none are left to triage.
   - No fix commits are pending.
   - When last checked, the required checks were green and the Security workflow's secretlint job had passed.

   I would write `state: ready-to-merge`.

2. **Rule out the other rows.**
   - `in-review` fits when "a non-draft PR is open and review or fix work may still be needed". No review or fix work is left here.
   - `pr-draft` fits when "A draft PR is open". The PR is not a draft.
   - `blocked` fits when "Work cannot go on until a blocker is resolved". There is no blocker.
   - The tie-breaker, "When unsure between `in-review` and `ready-to-merge`, choose `in-review`", does not apply. Every listed condition is explicitly met, so I am not unsure.

3. **Set `context_mode` from the same row.** The skill says: "then set `context_mode` (the mode the next session should start in) from the same row". The `ready-to-merge` row gives `ship`, so I would write `context_mode: ship`.

4. **Do not override it.** The skill says: "Override `context_mode` only with the reason stated in Important Context, for example `admin` when the next session is configuration, permission or setup work". The next session is a merge, not configuration, permission or setup work. So there is no override, nothing to add to Important Context for it, and nothing for `validate_handoff.py` to report as an override note.

5. **Make the Resume Card match.** When I fill the Resume Card last, it states `ready-to-merge` and gives next step 1 verbatim (`merge-pr` for PR #901).

There is nothing to ask the user at this step. The skill's only `AskUserQuestion` for context mode comes in RESUME Step 5, in the next session.
