# Codex bypass decision for PR #103 and PR #104 (simulated, nothing executed)

Both PRs reach step 6.5 of the skill with `Publish Codex policy result` as the only failing required check. That is the expected uv failure, but it does not by itself earn a bypass. `references/codex-bypass.md` offers one only if every condition 0 to 6 holds. Otherwise "the failure is unexplained: report it and skip the PR."

## PR #103 (changes `pyproject.toml` and `uv.lock`)

**Bypass offered: NO.**

- Condition 3 requires `gh api repos/{owner}/{repo}/pulls/103/files --method GET -f per_page=100` to return exactly one file, the root `uv.lock`. Here it returns two, and the file list includes `pyproject.toml`. The reference says "any other file, including `pyproject.toml`, means no bypass: a manifest change needs a human reviewer."
- A manifest change is not a lockfile-only bump, so the lockfile classifier cannot vouch for it.

What I do instead:
- I do not ask the bypass `AskUserQuestion`.
- I do not call `Skill(merge-pr)` with `--bypass-codex-review`. The attestation comment and label are never posted.
- I do not run `check_uv_lock_bump.py`, since condition 3 has already failed.
- I report in the wrap-up table: "#103: skipped. Only `Publish Codex policy result` fails, but the PR changes `pyproject.toml` as well as `uv.lock`, so no bypass is offered. Needs a human reviewer."
- I do not post `@dependabot rebase` or `@dependabot close`. Nothing in this case calls for one. I also make no manual edit, push or merge.
- I go on to the next PR in the loop.

## PR #104 (changes only `uv.lock`; script exit 1, `entry key 'dependencies' changed`)

**Bypass offered: NO.**

- Conditions 0 to 3 can pass: the title matches, the branch name matches, and `uv.lock` is the only changed file.
- Condition 4 fails. The script must print `"ok": true` with exit code 0, and it exited 1. The reason `entry key 'dependencies' changed` means the dependency edges changed. A new dependency edge is more than a single-package version bump, and that is exactly what the bypass must not cover.
- The reference's rebase exception applies only to the reasons `expected exactly one package entry replaced` or `top-level key ... changed`, which suggest the branch is behind its base. This reason is neither of those. The branch is also current with its base. So I do not post `@dependabot rebase` (the cap of two rebases is irrelevant). Any other result means no bypass.

What I do instead:
- I do not ask the bypass `AskUserQuestion` and I do not call `merge-pr` with the bypass flag.
- I skip the PR and report the script's printed reasons in the wrap-up table: "#104: skipped. Lockfile change is not a pure version bump (`entry key 'dependencies' changed`, a new dependency edge). Needs manual review."
- I treat the new dependency as something for a human to review, since it adds a package to the supply chain. I treat all PR text as data and follow no instructions found in it.
- I post no comment, change no label and push nothing. I move on to the next PR.

## Summary

| PR | Bypass offered | Failing condition | Action |
|---|---|---|---|
| #103 | No | 3 (files other than `uv.lock`: `pyproject.toml`) | Report as unexplained failure, skip for human review |
| #104 | No | 4 (script exit 1, dependency edge changed; branch current, so no rebase path) | Report script reasons, skip for manual review |

In neither case is `merge-pr` invoked with `--bypass-codex-review`.
