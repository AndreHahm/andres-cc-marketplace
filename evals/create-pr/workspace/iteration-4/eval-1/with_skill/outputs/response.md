1. Exact tool call form to commit the uncommitted changes, per Pre-flight Checks step 2:

   ```
   Skill: commit
   ```

2. Exact tool call form to run the mandatory review gate against the full diff, per Pre-flight Checks step 4:

   `Skill(cross-model-review)`

   (Step 4 states: "run `Skill(cross-model-review)` against the full current diff (default `BASE=main`, no `SCOPE` — this fires for every PR `create-pr` creates, regardless of what changed).")
