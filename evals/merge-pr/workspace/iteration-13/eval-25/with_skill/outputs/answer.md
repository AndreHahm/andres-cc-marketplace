# PR 911: step 2 classification of `SonarCloud Code Analysis`

Simulated exercise. I ran no `gh` or `git` command and edited no repository file. The facts below are the ones the exercise supplied.

## Inputs (treated as data)

- Required-check list. It is the union of classic protection (`/branches/<base>/protection`) and the ruleset contexts (`/rules/branches/<base>`), each name counted once. Here it holds one context: `SonarCloud Code Analysis`.
- `statusCheckRollup` has two entries with that name:
  1. A `StatusContext` with `state: SUCCESS`, createdAt 10:00:00Z.
  2. A `CheckRun` with `status: COMPLETED`, `conclusion: SUCCESS`, empty `workflowName`, startedAt 10:03:00Z.

## Step-by-step, following step 2's rule for entries that share a name

1. **Pending test first.** If any `CheckRun` with this name is not `COMPLETED`, or any `StatusContext` with this name has `state: PENDING`, the context is pending, whatever the timestamps say.
   - The CheckRun is `COMPLETED`.
   - The StatusContext's state is `SUCCESS`, not `PENDING`.
   - So the context is not pending.
2. **Group the entries by source.**
   - Every `StatusContext` with this name forms one group, because a commit status keeps one entry per name. Group A holds entry (1).
   - `CheckRun` entries are grouped by `workflowName`. Entry (2) has an empty `workflowName`, which is typical of a third-party app's check run rather than an Actions workflow. It forms its own CheckRun group, group B, keyed on the empty name.
   - The StatusContext and the CheckRun are separate sources, never one group. So one source cannot supersede the other: I do not just take the later 10:03 CheckRun and ignore the StatusContext.
3. **Take the latest entry in each group.** In both groups the latest entry is the only one.
   - Group A: entry (1).
   - Group B: entry (2), using its `startedAt`.
4. **Classify each group's latest entry with the four-state rules.**
   - Group A: a `StatusContext` with `state: SUCCESS` is **passing**.
   - Group B: a `CheckRun` with `COMPLETED` / `SUCCESS` is **passing**.
5. **Combine the groups.** The context passes only when every group's latest entry passes. A second source with the same name therefore cannot hide a failing one. Both groups pass here.

## Result

- **`SonarCloud Code Analysis` classifies as passing.** It is not failing, pending or missing. Both sources report success for the current head.
- **The status-checks gate passes.** It is the only required context, and it is passing. No bypass exception is needed or used. `--bypass-codex-review` is irrelevant here: `Publish Codex policy result` is not in the required list.

## Caveats and next steps

- **App identity is not checked.** A ruleset entry's `integration_id` (the app that must report the check) is not compared, so the skill cannot tell which app reported each same-name entry. GitHub's own ruleset enforcement still covers that, unless the merging user can bypass the ruleset.
- **No self-caused CI wait applies.** The wait for this skill's own runs (issue #850) applies only when step 1.5 pushed or step 1.6 edited the body. The wait's "newer `startedAt`" condition would also skip this context: its latest CheckRun has an empty `workflowName`, so it is not a context a workflow reports.
- **The other checks still run.** Passing this gate does not finish step 2. The remaining required checks still apply before step 3's merge-rights check: not draft, no outstanding change requests, `mergeable: MERGEABLE`, not behind base, and review outcomes recorded.
