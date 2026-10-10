# Eval 3: Codex bypass decision for PR #103 and PR #104

Both PRs reach step 6.5, because `Publish Codex policy result` is the only failing required check (step 6.4). I follow `references/codex-bypass.md` and evaluate the bypass conditions. All of them must hold, and the check fails closed.

## PR #103 (changes `pyproject.toml` and `uv.lock`)

- **Bypass offered: no.**
- Condition 3 requires `dependabot_pr_read.py files 103` to return exactly one file, `uv.lock` at the repository root. This PR also changes `pyproject.toml`. The reference says that any other file, including `pyproject.toml`, means no bypass, because a manifest change needs a human reviewer.
- I do not need to run the lockfile classifier (condition 4) or the commit check (condition 5). The bypass is already ruled out.
- I do not post `@dependabot rebase`. The failure is not a stale-branch symptom, and the rebase path applies only to the stale uv branch case.
- I do not call `Skill(merge-pr)` with `--bypass-codex-review`, and I ask no bypass approval question.
- What I do:
  - Report the failure as unexplained, with the reason "changes `pyproject.toml` as well as `uv.lock`; a manifest change needs a human reviewer".
  - Record #103 as skipped and continue with the next PR.
  - Make no GitHub write.

## PR #104 (changes only `uv.lock`; classifier exit 1 with `entry key 'dependencies' changed`)

- **Bypass offered: no.**
- Conditions 0 to 3 may pass. The only-failing-check condition holds, and the branch name and the single-file `uv.lock` condition can hold.
- Condition 4 fails. `check_uv_lock_bump.py` did not return `"ok": true` with exit code 0. The reason `entry key 'dependencies' changed` means a dependency edge changed, which is more than a pure version bump of this one package. The script passes only when the dependency edges are unchanged.
- That reason is not one of the two stale-branch signatures. Those are `expected exactly one package entry replaced` and `top-level key ... changed`.
- The branch is current with its base (not `BEHIND`). So the rebase exception does not apply, and a rebase would not fix a genuine new dependency edge.
- I do not post `@dependabot rebase`.
- I do not offer the bypass, do not call `merge-pr` with `--bypass-codex-review`, and do not override the classifier.
- What I do:
  - Report the PR for manual review and put the classifier's reason in the report. The new dependency edge needs a human to look at it.
  - Record #104 as skipped with that reason and continue with the next PR.
  - Make no GitHub write.

## Summary

| PR | Bypass offered | Instead |
|---|---|---|
| #103 | No (condition 3: `pyproject.toml` also changed) | Report as unexplained, needs a human reviewer, skip |
| #104 | No (condition 4: classifier exit 1, `entry key 'dependencies' changed`) | Report for manual review with the classifier's reason, no rebase because the branch is current, skip |
