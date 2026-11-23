# PR 911: step 2 status-checks classification for `SonarCloud Code Analysis`

Simulated exercise. No `gh`/`git` command is run and no repository file is edited. The facts given stand in for what the calls would have returned.

## Step by step

1. **Resolve the required-check list (step 2, status-checks bullet).** I would take the union of:
   - classic protection: `gh api repos/{owner}/{repo}/branches/<baseRefName>/protection --jq '.required_status_checks.contexts'`
   - rulesets: `gh api -X GET repos/{owner}/{repo}/rules/branches/<baseRefName> --paginate --jq '.[] | select(.type == "required_status_checks") | .parameters.required_status_checks[].context'`

   Given: the union is exactly one context, `SonarCloud Code Analysis`. It is not empty, so the "no required check could be found" stop does not apply. Neither call failed, so the "could not be resolved" stop does not apply either.

2. **Collect the `statusCheckRollup` entries with that name.** There are two:
   - (1) `StatusContext`, `state: SUCCESS`, createdAt 10:00:00Z
   - (2) `CheckRun`, `status: COMPLETED`, `conclusion: SUCCESS`, `workflowName: ""`, startedAt 10:03:00Z

3. **Apply the same-name rule.** The skill says: "When several `statusCheckRollup` entries share a context's name ... if any of them is not `COMPLETED`, the context is **pending**."
   - Entry (2) is a `CheckRun` with `status: COMPLETED`.
   - Entry (1) is a `StatusContext`. It has no `status` field, but `state: SUCCESS` is a terminal state. Only `PENDING` (pending) or `EXPECTED` (missing) would make a commit status non-terminal. I treat it as completed.
   - Nothing is still running, so the context is not pending on this basis.

4. **Group by source and take the latest entry in each group.** Each `CheckRun` is grouped by its `workflowName`, and every `StatusContext` forms one more group:
   - Group A, the `StatusContext` group: entry (1) alone, so it is the latest by default. `state: SUCCESS` is **passing**.
   - Group B, the `CheckRun` group with `workflowName` `""`: entry (2) alone, so it is the latest by default. `COMPLETED` with `SUCCESS` is **passing**.

   An empty `workflowName` means a GitHub App reported this check run directly (SonarCloud's app), not a GitHub Actions workflow. It is still its own `CheckRun` source group. The commit status and the check run are two independent sources reporting the same name, and the rule says "the context is passing only when every group's entry is passing, so a second source of the same name never masks a failing one." Here both groups pass, so nothing is masked.

   The timestamps (createdAt 10:00:00Z against startedAt 10:03:00Z) do not matter for the result. The "latest `startedAt`" comparison only happens inside a group, and each group has one entry. The later CheckRun does not supersede the StatusContext, and the StatusContext does not supersede the CheckRun.

5. **Classify into the four states.**

   **`SonarCloud Code Analysis` = passing.** It is not failing, because no group's entry is `FAILURE`/`ERROR` or a failing conclusion. It is not pending, because every entry is terminal. It is not missing, because entries exist and neither is `EXPECTED`.

6. **Gate result.** Every required context must classify as passing. The only required context passes, so **the status-checks gate passes.** The `--bypass-codex-review` exception plays no part, since `Publish Codex policy result` is not in the required list and nothing is non-passing.

   Step 2 then goes on to its other required checks (not draft, no outstanding change requests, no merge conflicts, not behind base, review outcomes recorded). Only after all six pass does it reach step 3 (merge rights) and step 5 (the explicit `AskUserQuestion` confirmation).

## Caveats I would disclose

- **App identity is not checked.** The skill does not compare a ruleset entry's `integration_id`. It cannot tell whether the SonarCloud app the ruleset names produced the `CheckRun`, the `StatusContext`, or both. GitHub's own ruleset enforcement covers that case unless the merging user can bypass the ruleset.
- **Not a workflow-run wait.** If this classification ran during the "Waiting for this skill's own runs" case (after a step 1.5 push or a step 1.6 body edit), that wait only requires a fresh post-baseline entry for contexts whose latest pre-baseline entry is a `CheckRun` with a non-empty `workflowName`. This context's `CheckRun` has an empty `workflowName`, so the wait would not require a re-reported entry for it. It would only need it to be passing or failing on two consecutive polls. The prompt does not describe that case, so the plain first-pass classification above applies.
