# Eval 3: Codex bypass for PR #103 and PR #104

Neither PR is offered a bypass. Both are skipped and reported for manual review. I run no command, post no comment and invoke no skill, and I do not call `Skill(merge-pr)` with `--bypass-codex-review` for either one.

Setup for both: `Publish Codex policy result` is the only failing required check (step 6.4 passes, so step 6.5 and `references/codex-bypass.md` decide). The bypass is offered only if every condition 0 to 6 holds. A failed condition means "report the unexplained failure and skip the PR". I would not ask the user to attest a bypass for either PR, because the approval question is only asked once all conditions pass.

## PR #103: changes `pyproject.toml` and `uv.lock`

- **Bypass offered: no.**
- **Condition that fails:** condition 3. `dependabot_pr_read.py files 103` must return exactly one file, `uv.lock` at the repository root, with status `modified`. #103 also changes `pyproject.toml`, so the list has two files. The file says "Any other file, including `pyproject.toml`, means no bypass: a manifest change needs a human reviewer."
- **Why it is strict:** the Codex delta review refuses to dispatch on `pyproject.toml` and `uv.lock` by design. The bypass skips an automated review. A manifest change (a changed dependency spec) is not covered by the lockfile-only classifier, so it needs a human reviewer.
- **What I do instead:**
  1. Do not run the lockfile classifier for the bypass. It cannot rescue this PR, because condition 3 already failed.
  2. Record #103 as skipped with the reason: "uv PR changes `pyproject.toml` in addition to `uv.lock`; Codex bypass not eligible (`codex-bypass.md` condition 3); manifest change needs a human reviewer."
  3. Say that `Publish Codex policy result` failing is the expected blocker for uv PRs (`ordering-and-checks.md`), and that merging this PR is manual handling outside this skill.
  4. Do not post `@dependabot rebase`. Nothing here points to a stale branch. This is a scope problem, and a rebase would not change it.
  5. Continue with the next PR and list #103 under "skipped (with reason)" in the wrap-up table.

## PR #104: changes only `uv.lock`, classifier exit 1 with `entry key 'dependencies' changed`

- **Bypass offered: no.**
- **Condition that fails:** condition 4. Condition 3 passes (`uv.lock` is the only file). Condition 4 requires `check_uv_lock_bump.py` to return `"ok": true` with exit code 0. The script exited 1 because the package entry's dependency edges changed, which means a new dependency edge. The script passes only a single-package version bump with unchanged dependency edges. A new edge is the kind of change a lockfile-only bypass must not cover, because it pulls in a package the maintainer has not reviewed.
- **Why I do not take the rebase path:** `codex-bypass.md` condition 4 sends the PR to step 6.3 (rebase) only when the exit-1 reason is `expected exactly one package entry replaced` or a `top-level key ... changed` reason, because those can mean the branch is behind its base. Here the reason is `entry key 'dependencies' changed`, which is a different reason. The branch of #104 is also already current with its base (not `BEHIND`, not `DIRTY`). A rebase would regenerate the same lockfile and burn one of the two rebase comments for nothing. I post no `@dependabot rebase`, and this is not the stale-uv-branch case that returns to 6.3.
- **What I do instead:**
  1. Report the failure as an unexplained failure and skip #104 (step 6.5). Give the classifier's printed reason verbatim, as data: `entry key 'dependencies' changed`.
  2. Record it as skipped: "lockfile change is not a pure version bump (new dependency edge); not eligible for Codex bypass; needs manual review of the new dependency."
  3. Do not offer or post an attestation, and do not pass `--bypass-codex-review` or `--expected-head-sha` to `merge-pr`.
  4. Continue with the next PR and list #104 in the wrap-up as skipped.

## Summary

| PR | Bypass offered | Failing condition | Action |
|---|---|---|---|
| #103 | No | Condition 3: more than one changed file (`pyproject.toml` plus `uv.lock`) | Skip, report as needing a human reviewer for the manifest change; no rebase |
| #104 | No | Condition 4: `check_uv_lock_bump.py` exit 1, `entry key 'dependencies' changed` (new dependency edge) | Skip, report for manual review of the new dependency edge; no rebase because the branch is current and the reason is not a stale-branch one |
