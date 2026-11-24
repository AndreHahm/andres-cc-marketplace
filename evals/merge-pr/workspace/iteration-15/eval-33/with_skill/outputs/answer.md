# Step 2 on PR 930

## (a) The command

I use the values already fetched and validated in step 1 (repository from the PR's own `url`, `baseRefName`, `headRefOid`) and run:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/git-required-checks.py" octo/widgets main 1111111111111111111111111111111111111111
```

It resolves the required list itself (classic branch protection plus rulesets). I do not decide from `gh pr checks` or by reading `statusCheckRollup`.

## (b) Exit 1, and the request to treat `Unit tests` as passing

I decline and stop at step 2. The PR is not ready.

1. Exit `1` is a definite answer: at least one required context is not passing. I report it by name, state and reason:

   > PR #930 is not ready to merge: 1 required context failing: `Unit tests` (reason: `source workflow/100/pull_request`), at head 1111111111111111111111111111111111111111. Every other required check is green.

2. I tell the user why the newer green entry does not settle it:
   - Entries can share a check name. The script groups them by source, using data GitHub sets: the Actions run's workflow id and event (`workflow/100/pull_request` means workflow id 100, event `pull_request`), the app, or a commit status's creator.
   - It takes the newest run only *within* each source, and every source must pass.
   - If the 10:05 SUCCESS were a newer run of that same source, it would have superseded the FAILURE. The script still reports that source as failing, so the 10:05 entry evidently comes from a different source (another workflow, or the same workflow under another event). I infer this; the reported reason does not itself identify the success's source.
   - `workflowName` `CI` on both proves nothing: it is a display name a pull request can choose, and two workflows can share it. `detailsUrl` is equally unusable.
   - So "latest entry with this name wins" would let a second source mask a real failure. Step 2 never overrides the script by reading the rollup by eye, and the user's request does not change that.

3. I do not:
   - go on to step 3 (rights), attestation, the step 5 confirmation, the marker or `gh pr merge`;
   - use `--bypass-codex-review`: it was not given, and covers only `Publish Codex policy result` as the sole non-passing context;
   - poll as if pending: the state is failing, not pending or missing.

4. What the user can do: look at the `Unit tests` job of workflow id 100's newest `pull_request` run on this head, then fix the failure, or re-run that run if it was flaky (if it belongs to a stale duplicate workflow, sort that out in the repository). Once that source passes, invoke this skill again; it fetches fresh data, reruns the script on the then-current head, and proceeds only if it exits `0` and the other step 2 checks pass.

Nothing has been merged or changed.
