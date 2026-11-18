# merge-pr 650 --expected-head-sha cccc...cccc (no bypass flag)

No `gh`/`git` calls are run. Each case describes the steps the skill directs and what I would report.

## Shared start (all cases)

- **Step 1, argument validation:** `650` is digits-only, so it is accepted. `--expected-head-sha` is 40 lowercase hex characters, so it is accepted. Because `--bypass-codex-review` is absent, the SHA is ignored, and I tell the user so (the skill requires this disclosure).
- **Step 1, resolve PR:** `gh pr view 650 --json ...`. Derive `{owner}/{repo}` from the returned `url`. The PR-reference portion was non-empty, so the origin-identity check is skipped.
- **Step 1, validate refs:** `headRefName` and `baseRefName` must match `^[A-Za-z0-9._/@+=-]+$`.
- **Step 1.5, checkout check:** the scenario supplies no local checkout data, so I cannot evaluate it. I would report that step 1.5 could not be evaluated here and would not scan or fix anything.
- **Step 2, readiness:** not draft, all five required contexts passing (per the base-branch protection list), no outstanding `CHANGES_REQUESTED`, `mergeable` is `MERGEABLE`, not behind base. Advisory disclosures (`mergeStateStatus`, unresolved-thread count) are shown at step 5.
- **Step 3, merge rights:** run `references/merge-rights-check.md` with the resolved `{owner}/{repo}`.
- **Step 5, confirm:** `AskUserQuestion` with PR number, title, readiness summary, both advisory disclosures, and the worktree branch-delete note. Proceed only on an explicit yes.
- **Step 6:** read `pr_merge_type` (default `REBASE`) and `merge_auto_delete_branch` (default `true`).
- **Step 7(a):** if the strategy is `REBASE`, count merge commits in the PR. If any exist, ask via `AskUserQuestion` (merge or squash, with the squash tradeoff) before attempting a rebase.
- **Step 7(b):** the marker and merge run only after the final recheck (below). The marker is written immediately before the merge command, never earlier. The merge command is `gh pr merge 650 --<strategy> --match-head-commit <verified SHA>`, plus `--delete-branch` when the setting is `true`.

## Case A: step 1 headRefOid = dddd...dddd

- `--expected-head-sha cccc...` is ignored, since no bypass flag was given. The skill does not stop on the mismatch.
- The head that step 1 fetched is dddd. I run the normal flow from the shared start.
- Because the caller vetted cccc, I put the mismatch in the step-5 `AskUserQuestion`: the caller passed cccc, the PR head is now dddd, and the flag was ignored. I do not merge without the user's explicit yes.
- If the user confirms and the step 7(b) recheck passes with head dddd, I write the `gh-pr-merge` marker and run `gh pr merge 650 --<strategy> --match-head-commit dddd...dddd` (plus `--delete-branch` if configured).
- If the user declines, I stop and merge nothing.

## Case B: step 1 headRefOid = cccc; user confirms at step 5; step 7(b) re-fetch headRefOid = eeee...eeee

- Step 7(b)'s full readiness recheck (fresh fetch) passes.
- The head moved from cccc, which the user confirmed at step 5, to eeee, which the user never saw. The skill does not spell out what to do here. I treat the confirmation as tied to the reviewed head, so I do not write the marker or merge on a head the user did not confirm.
- I stop and re-ask via `AskUserQuestion`, showing cccc (confirmed) versus eeee (now), the readiness result for eeee, and that the `--expected-head-sha` the caller passed (cccc) was ignored.
- If the user confirms eeee: write `bash "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-merge merge-pr` in its own call right before the merge, then run `gh pr merge 650 --<strategy> --match-head-commit eeee...eeee` (plus `--delete-branch` if configured). The bypass-path equality rule does not apply, since there is no bypass.
- If the user declines: stop, merge nothing, and report that the head changed after confirmation.
- After any merge attempt, run the step-7(e) verification (`gh pr view 650 --json state,mergeCommit`, then the `git ls-remote` branch check when applicable), regardless of the exit code.

## Case C: as Case B, but step 7(b) re-fetch headRefOid = cccc...cccc

- Step 7(b)'s recheck passes, and the head equals the head the user confirmed at step 5. No re-ask is needed.
- Write the `gh-pr-merge` marker immediately before the merge, then run `gh pr merge 650 --<strategy> --match-head-commit cccc...cccc` (plus `--delete-branch` if configured).
- Run the step-7(e) verification afterward and report the merge method, the strategy versus the configured `pr_merge_type`, and whether the branch was deleted.
- The `--expected-head-sha` value still has no gating effect here, because there is no bypass. The merged head matches the SHA the caller passed, so there is nothing to disclose beyond the ignored-flag note from step 1.
