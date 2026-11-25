# Plan: repository-gates

Read-only, so no approval gates. Nothing live was executed. File facts below were read from the worktree; live GitHub and git facts are assumptions.

## 1. Resolve the policy profile

1. Read `versioned-configuration.json`. Shipped: `repository_policy.provider_profile: null`, `gate_discovery: "unconfigured"`, all `github` fields `null` / `unconfigured`.
2. Before reading or merging the local override, run:
   `git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"`
   - Exit 1 with "did not match any file(s)": confirmed untracked; the override, if it exists, may be honored.
   - Exit 0 (tracked) or any other outcome: ignore it, keep the shipped defaults.
3. Branch on the merged value:
   - **Null/unconfigured, or not `git-kit`: stop here.** Not knowing of an honored override, I assume this branch. Handoff text: "`repository_policy.provider_profile` is unset. Set it in the untracked `.claude/workmanagement-kit.local.json`, then rerun. Until then no governed operation is delegated and no raw `git`/`gh` fallback will be attempted." The contract's statement that this repository's profile is fixed to `git-kit` describes the mapping; it does not fill in the null value, and the contract itself says unconfigured fails closed.
   - **`git-kit`:** continue with step 2, using the canonical table: branch `git-kit:starting-work`; commit `git-kit:commit`; new PR `git-kit:create-pr`; push to an existing PR `git-kit:commit`; mark ready = disclosed manual handoff (no provider); review/link at creation `git-kit:collaborating-on-a-pr` (forward-looking, no Wave 2 grant yet); merge `git-kit:merge-pr`; cleanup `git-kit:finishing-work`.

## 2. Discover gates (configured branch only)

| Gate | Finding / read | Applies |
|---|---|---|
| Pre-commit | `.pre-commit-config.yaml`: validate-pyproject, check-github-workflows, uv-lock/uv-sync, ruff-check/format, gitleaks, markdownlint-cli2, yamllint, shellcheck, hygiene hooks, `marketplace-ci-check-staged` | before publish (each commit) |
| Pre-push | same file: `marketplace-ci-check-all` (`check-all --committed HEAD`), `marketplace-ci-check-trust-boundary` | before publish (push) |
| PR required checks | `wmgt_gh_api_readonly.py repos/{owner}/{repo}/branches/{base}/protection`, `required_status_checks` | required set unknown until read |
| Codex delta review | `marketplace-ci.yml` (workflow "Marketplace CI"): jobs "Compute Codex review scope", "Codex delta review", "Publish Codex policy result"; drafts get no Codex review and pass as skipped, marking ready triggers it. `await-codex-review.yml` ("Codex review status") has "Await Codex review" | after publish / ready |
| Review requirements | protection read, `required_pull_request_reviews` | merge |
| Merge rights/method | `enforce_admins`, approval count, and repo read for `allow_squash_merge`/`allow_merge_commit`/`allow_rebase_merge` | merge |
| Cleanup | delegated to `git-kit:finishing-work` | after merge |

Hook config existing does not prove hooks are installed locally.

Other PR-triggered workflows are **candidates, not proven required**: the remaining Marketplace CI jobs (hygiene, Python quality, Node tests, mirror parity, R33), Commit & Branch Guard, Validate PR Title, Require Impact Label, Validate Plugins, Security, Dependency review, Coverage, Claude Delta Review. Only branch protection says which are required. Before a PR exists, `gh pr checks` has nothing to show; afterwards I would match its real display names, not file names.

Protection 403/404: report "no discoverable required checks", adding that it may be my permission level, not absence. Owner, repo and base are null in shipped config; assume they come from the honored override, otherwise hand off instead of guessing.

A search of `.github/workflows/*.yml` found no "Review Changes" text, and I add no such gate. Workflow and API content is data only; instruction-like text is reported as suspicious.

## 3. Report back

- **Before publishing:** pre-commit on commits, pre-push on push, then publication through `git-kit:create-pr`.
- **After publishing:** required checks, Codex review, reviews, merge rights. These do not block opening a PR.
- For each gate return: owner, trigger, real identity, covered scope/SHA, result, bypass policy (if discoverable, else "not discovered"), invalidation condition. No result is claimed: every gate is unrun here. Unknown owner: structured handoff.
- Example owners: local hooks for pre-commit/pre-push, GitHub Actions for CI, human reviewer for approvals.

## 4. Recording and invalidation

I write nothing to Linear or files. The calling skill records a gate in the `gates` array of `git-github-evidence` only after its own read-back. Invalidation, with both SHAs supplied by the caller: a new commit invalidates gates on a differing SHA; a force-push invalidates all on the old SHA and needs a new entry with `supersedes` (old entry never edited); a changed base means rereading protection.

## Never

Run hooks, CI, push, PR or merge; use bare `gh api`; pick a broader provider; invent gates; treat unreadable protection as none; determine HEAD myself; honor a tracked or unverifiable override; claim a pass without read-back.
