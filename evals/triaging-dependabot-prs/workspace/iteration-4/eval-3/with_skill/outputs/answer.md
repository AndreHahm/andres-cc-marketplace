# Codex bypass decision: PR #103 and PR #104

Context: for both PRs `Publish Codex policy result` is the only failing required check, so SKILL.md step 6.5 sends me to `references/codex-bypass.md`. The bypass is offered only if every condition (0 to 6) holds. Each condition denies on its own, and the flow fails closed.

## PR #103 (changes `pyproject.toml` and `uv.lock`)

**Bypass offered: no.**

- Condition 3 requires `gh api repos/{owner}/{repo}/pulls/103/files --method GET -f per_page=100` to return exactly one file, `uv.lock` at the repository root. It returns two, because `pyproject.toml` changed too. The same condition requires the 6.1 `files` list to be exactly `uv.lock`, and that fails as well.
- The reference says a manifest change needs a human reviewer, because the lockfile classifier only reasons about a lockfile-only version bump.
- Since condition 3 already fails, I do not fetch the two lockfiles and do not run `check_uv_lock_bump.py`. A pass from it could not make the bypass available.

What I do instead:
1. No bypass. I do not invoke `Skill(merge-pr)` with `--bypass-codex-review` or `--expected-head-sha`.
2. Following step 6.5, I report the failure as unexplained and record #103 as skipped. The reason I state is "`pyproject.toml` changed alongside `uv.lock`; the Codex policy failure needs a human reviewer, and no bypass is offered for a manifest change."
3. I post no `@dependabot rebase`. Nothing in the classifier path points to a stale branch, since the classifier never ran. The only exception is if the live read shows `mergeStateStatus` `BEHIND` or `DIRTY`. Then step 6.3 would apply on its own terms: I ask first, then use the marker-then-comment sequence. That would not make the bypass available, though, because condition 3 still fails.
4. I tell the user that #103 is left for manual review. I take no other GitHub write on it (no close, no comment) unless the user asks, and then only with the separate `AskUserQuestion` the skill requires.
5. I continue with the next PR in the list.

## PR #104 (only `uv.lock` changed; classifier exit 1, `entry key 'dependencies' changed`)

**Bypass offered: no.**

- Condition 3 passes (single `uv.lock` file) and the branch is current with its base. Condition 4 fails, and that decides it.
- `check_uv_lock_bump.py` passes only when exactly one package entry was replaced, that entry is `<package>` going from `<old>` to `<new>`, and its dependency edges are unchanged. `entry key 'dependencies' changed` means the bump adds or changes a dependency edge, which the classifier treats as a new package or dependency edge. I need `"ok": true` with exit 0, and I have exit 1.
- The stale-branch exception does not apply. Condition 4 only reroutes to a rebase when the classifier exits 1 with `expected exactly one package entry replaced` or a `top-level key ... changed` reason, because those can mean the branch is merely behind its base. `entry key 'dependencies' changed` is neither of those. The branch is also current, so a rebase would not change the lockfile diff. I do not post `@dependabot rebase`, and the rebase cap is not consumed.

What I do instead:
1. No bypass. I do not invoke `Skill(merge-pr)` with `--bypass-codex-review` or `--expected-head-sha`.
2. I report the classifier's reasons verbatim, as data (the `dependencies` entry change, meaning a new dependency edge). I record #104 as skipped, and the reason I state is that a lockfile change adding a dependency edge is more than a single-package version bump and needs manual review.
3. I tell the user that someone must read the new dependency before this can merge, because the Codex review that would have covered it is the one being skipped.
4. I post no comment and do not close the PR. If the user asks for something else, each action is separately offered and approved:
   - `@dependabot recreate`.
   - `gh pr close` plain.
   - `@dependabot ignore ...`, with the scope chosen by the user.
5. I continue with the next PR.

## Summary

| PR | Bypass offered | Failing condition | Action |
|---|---|---|---|
| #103 | No | 3 (two files, `pyproject.toml` included) | Skip, report for human review, no rebase for this reason, no merge-pr call |
| #104 | No | 4 (classifier exit 1, `entry key 'dependencies' changed`, not a stale-branch reason) | Skip, report classifier reasons for manual review, no rebase because branch is current, no merge-pr call |

Neither PR gets an attestation comment, a label, or a `merge-pr` call from this skill. Both stay open and are listed as skipped in the step 7 wrap-up table with these reasons.
