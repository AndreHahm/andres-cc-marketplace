## Summary
A bare, no-argument `gh repo view` call silently resolves to the current checkout's repository rather than the repository an operation is actually targeting — when a PR reference points to a different repository (a full cross-repo URL), a step re-deriving `{owner}/{repo}` via a fresh `gh repo view` queries the wrong repo entirely.

## Environment
- **Product/Service**: `git-kit` plugin — `merge-pr`'s branch-protection readiness check
- **Region/Version**: this repo, found during PR #148 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Accept a PR reference as a full cross-repo URL (a PR belonging to a different repository than the current checkout).
2. Step 1 correctly fetches that PR using its own resolved coordinates.
3. A later branch-protection/readiness lookup derives `{owner}/{repo}` via a fresh, bare `gh repo view` call instead of reusing the PR's already-resolved repository.
4. `gh repo view --help` confirms this call's documented default behavior: "With no argument, the repository for the current directory is displayed" — so the readiness check queries the *current checkout's* repository, not the PR's actual one.

## Expected Behavior
Once an operation has resolved its real target repository from a specific input (a PR URL, an explicit `--repo` flag), every subsequent API call in the same operation should reuse that resolved value — never re-derive repo coordinates via a bare, context-dependent command that silently assumes "the current directory."

## Actual Behavior
The readiness decision could fail or be evaluated against an unrelated repository's required status checks, since the protection lookup silently targeted the wrong repo.

## Impact
[Severity: Medium] A readiness/protection check silently evaluating the wrong repository's rules can produce an incorrect merge-readiness verdict without any visible error. Fixed in `git-kit`'s PR #148 (commit `d9bfdc1`): step 1 now derives `{owner}/{repo}` from the PR's own `url` field (added to the `gh pr view` `--json` fields), and step 2's branch-protection call reuses that value instead of a fresh `gh repo view`. Verified: `gh pr view --json url` confirmed live that `url` always reflects the repository the PR actually belongs to; added `check_step1_owner_repo_from_pr_url` to `scripts/smoke_test.py` to assert this going forward, and it passes.

## Additional Context
Mined from PR #148's own review history (`chatgpt-codex-connector[bot]`; 12 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #148` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/148#discussion_r3872420081
