Answer (plan-only, following session-handoff SKILL.md, CREATE Step 2 item 5):

1. Set `state: implementing`. Step 2 item 5 says to "set the frontmatter's `state` to where the work stands, judged from what this session knows about the next step". The table row that matches is: "`implementing` | No PR, and opening one is not the next step (starting a worktree, implementing) | `none`". No PR exists, and the next step is to create a worktree and implement, not to open a PR. That rules out the other rows:
   - `pr-draft` needs "A draft PR is open".
   - `in-review` needs "The next step opens the PR, or a non-draft PR is open".
   - `ready-to-merge` and `ready-to-publish` need a merge-ready PR or a pending publish.
   - `blocked` does not apply because no blocker is named.
   - `done` needs "The PR is merged".

2. Set `context_mode: none`. The skill says to set `context_mode` (the mode the next session should start in) "from the same row", and the `implementing` row gives `none`. I would not override it: "Override `context_mode` only with the reason stated in Important Context, for example `admin` when the next session is configuration, permission or setup work". Creating a worktree and implementing a feature is not that kind of work, so there is no reason to write. Because there is no override, `validate_handoff.py` reports no override note.

3. Carry the state into the Resume Card, which I fill last. Item 6 says it holds "state, next step 1 verbatim, branch and PR, blockers, ..." So the card's State line reads `implementing` with a few words of context, and its PR field says there is no PR yet.

4. In Step 3, `validate_handoff.py` checks "that `state` and `context_mode` hold values from the closed sets above". Both `implementing` and `none` are in those sets.

Supporting file: references/handoff-template.md lines 45-46 list the allowed values. Its `context_mode` line says it is "derived from state, see SKILL.md CREATE Step 2 item 5".

On resume, `none` sets no mode. RESUME Step 5 says: "`none`, a missing value, or any other value sets no mode". So the next session gets no context-mode prompt.
