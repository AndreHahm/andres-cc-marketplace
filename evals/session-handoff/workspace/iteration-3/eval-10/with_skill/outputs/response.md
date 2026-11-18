Context mode: none

Reason: Step 2 item 5 allows `ship` only when a PR already exists and is not a draft, and allows `review` only when a PR is open. No PR exists here, so neither applies, even though the user expects to merge next session. This is not `admin` work either. The skill's own eval summary says `none` before a PR exists, so I'd write `none`. Note that the rule's text for `none` ("starting a worktree or implementing") doesn't clearly cover a session whose next step is opening a PR, which is a gap in the skill's wording.
