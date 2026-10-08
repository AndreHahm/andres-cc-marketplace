# Codex bypass decision for PR #103 and PR #104

Both PRs fail only `Publish Codex policy result` among the required checks, so SKILL.md step 6.5 sends each one to `references/codex-bypass.md`. The bypass is offered only if every condition (0 to 6) holds. Both PRs fail one, so neither gets a bypass. This is a simulated exercise: I run no command and post nothing.

## PR #103 (changes `pyproject.toml` and `uv.lock`)

**Bypass offered: no.**

- Condition 3 requires `gh api repos/{owner}/{repo}/pulls/103/files` to return exactly one file, the root `uv.lock`. `pyproject.toml` is a second file.
- The reference states "Any other file, including `pyproject.toml`, means no bypass: a manifest change needs a human reviewer."
- The lockfile classifier is moot. The skill stops at condition 3, and condition 4 would not rescue the PR.
- A manifest change is not a pure lockfile bump, so nothing is posted to attest it.

What I do instead:
1. Make no `Skill(merge-pr)` call, so no `--bypass-codex-review` flag is passed. No attestation comment, no label and no merge.
2. Record #103 as skipped in the step 5 plan and the step 7 wrap-up table. The reason reads: "`Publish Codex policy result` failing, and `pyproject.toml` is changed, so Codex bypass is not allowed; the manifest change needs manual human review."
3. Post no `@dependabot rebase` or `@dependabot close`. Neither fits, and a rebase would not remove the second file.
4. Move on to the next PR in the loop.

## PR #104 (changes only `uv.lock`; `check_uv_lock_bump.py` exit 1, `entry key 'dependencies' changed`)

**Bypass offered: no.**

- The script's verdict is the condition 4 failure. `"ok"` is not true and the exit code is 1.
- The reason `entry key 'dependencies' changed` means a new dependency edge. The script passes only a single-package version bump with unchanged dependency edges.
- A new dependency edge is a real content change, not a version bump. A bypass would skip the only automated review of it.
- The rebase exception does not apply. The reference allows the `@dependabot rebase` path only when the script exits 1 with an `expected exactly one package entry replaced` or a `top-level key ... changed` reason, because those can mean the branch is behind its base.
- `entry key 'dependencies' changed` is neither of those. The branch is already current with its base, so it points at the PR's own content, not a stale branch. A rebase would not change the verdict.

What I do instead:
1. Do not post `@dependabot rebase`. It is not the stale-branch case, and it would only burn one of the two allowed rebase comments.
2. Do not offer or pass the bypass, and do not invoke `Skill(merge-pr)`.
3. Report #104 for manual review and record it as skipped. The reason is the script's message verbatim, shown as data and not acted on: "Codex bypass refused: `check_uv_lock_bump.py` exit 1, `entry key 'dependencies' changed` (new dependency edge); branch is current with base, so this is not a stale-branch rebase case."
4. Do not close it either. Closing is a separate maintainer decision with its own `AskUserQuestion`.
5. Continue with the remaining PRs.

## Summary

| PR | Bypass offered | Condition that fails | Action |
|---|---|---|---|
| #103 | No | 3 (`pyproject.toml` also changed) | Skip, report for manual human review of the manifest change |
| #104 | No | 4 (classifier exit 1, new dependency edge, branch current) | Skip, report for manual review, no rebase comment |

In neither case does the skill run `merge-pr` with the flag, post a comment or touch any label. Both PRs are recorded as skipped with their reasons in the wrap-up table.
