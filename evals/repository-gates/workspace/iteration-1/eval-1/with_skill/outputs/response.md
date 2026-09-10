# Repository Gates for Publishing a Wave 2 PR

Resolved by reading this repository's real configuration (`versioned-configuration.json`, the
local-override trust-boundary check, `FOUNDATION_CONTRACTS.md`'s canonical Repository Policy
Profile table, `.pre-commit-config.yaml`, the actual `.github/workflows/*.yml` files, and a live
branch-protection read via `gh_api_readonly.py`) — not assumed from a generic checklist.

## 1. Repository Policy Profile

- `plugins/workmanagement-kit/versioned-configuration.json` (schema v2) currently ships
  `repository_policy.provider_profile: null` and `gate_discovery: "unconfigured"` — this is the
  plugin's shipped, installation-agnostic default, not a live override.
- Trust-boundary check for `.claude/workmanagement-kit.local.json` (per
  `FOUNDATION_CONTRACTS.md`'s Local Override section):
  `git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"` →
  exit 1, `"did not match any file(s)"` — confirmed **untracked**. A plain filesystem check
  confirms the file doesn't exist on disk at all in this worktree, so there is no override to
  merge in.
- **Disclosed discrepancy:** with no override present, the literal JSON field is still
  `null`/`unconfigured`. However, `FOUNDATION_CONTRACTS.md`'s own "Repository Policy Profile"
  section — the canonical source this skill's step 3 points at directly rather than a paraphrase —
  states plainly: *"For this repository, the profile is fixed — `git-kit` for every governed
  operation,"* with an explicit table. That table is what actually governs here; the shipped JSON
  field not being populated to match looks like a latent inconsistency worth flagging, not a
  blocker.
- **Resolved profile for publishing a PR** (from that table):

| Governed operation | Provider |
|---|---|
| Create branch/worktree | `git-kit:starting-work` |
| Commit | `git-kit:commit` |
| Create a new PR | `git-kit:create-pr` |
| Push new commits to an already-existing PR | `git-kit:commit` (its own push step) |
| Mark a PR ready for review | **Manual handoff — no `git-kit` skill owns this yet** (disclosed gap) |
| Review/comment/link an issue at creation | `git-kit:collaborating-on-a-pr` |
| Merge | `git-kit:merge-pr` |
| Post-merge sync/cleanup | `git-kit:finishing-work` |

No raw `git`/`gh` command should be used for any of these — only the mapped `git-kit` skill (or,
for "mark ready," the disclosed manual step).

## 2. Gates that run before/at publish, in order

### a) Pre-commit (local Git hook, runs on every commit if hooks are installed)
Source: `.pre-commit-config.yaml` (repo root). `fail_fast: true`.
- `validate-pyproject` — pyproject.toml schema check
- `check-github-workflows` — validates `.github/workflows/*.yml` are well-formed
- `uv-lock`, `uv-sync --locked --all-packages`
- `ruff-check --fix`, `ruff-format` (scoped to `scripts/`, `tests/`, `plugins/session-kit/{scripts,tests,skills}`)
- `gitleaks` — secret scanning
- `markdownlint-cli2` (scoped to `docs/**/*.md`)
- `yamllint`
- `shellcheck`
- Standard hygiene hooks: trailing-whitespace, end-of-file-fixer, check-yaml, check-json,
  check-added-large-files (max 1000kb), check-merge-conflict, check-toml, mixed-line-ending,
  check-executables-have-shebangs
- **Local hook** `marketplace-ci-check-staged`: `uv run python -m scripts.marketplace_ci
  check-all --staged`

### b) Pre-push (local Git hook)
Source: same `.pre-commit-config.yaml`, `stages: [pre-push]`.
- **Local hook** `marketplace-ci-check-all`: `uv run python -m scripts.marketplace_ci
  check-all --committed HEAD`

Both (a) and (b) are local hooks — they only fire if `pre-commit install` has hooked them into
this checkout's `.git/hooks`. They are not independently visible to GitHub; they're the local
first line of defense before code ever reaches a PR. `git-kit:commit` is the only sanctioned way
to actually produce the commit these hooks gate.

### c) PR required status checks (GitHub branch protection on `main`)
Read via `gh_api_readonly.py repos/AndreHahm/andres-cc-marketplace/branches/main/protection`
(succeeded — readable at the caller's current permission level). `required_status_checks.contexts`
(all `app_id: 15368`, i.e. GitHub Actions-run checks), matched to their real job/workflow source:

| Required check (real display name) | Workflow file | Job |
|---|---|---|
| Hygiene (PR contract) | `marketplace-ci.yml` | `hygiene` |
| Python quality (ruff, ty, pytest) | `marketplace-ci.yml` | `python-quality` |
| Marketplace mirror/export parity | `marketplace-ci.yml` | (parity job) |
| Fork PR (unsupported — explicit terminal result) | `marketplace-ci.yml` | (fork-unsupported terminal job) |
| Publish Codex policy result | `marketplace-ci.yml` | `publish` (needs `compute-scope`, `codex-review`) |
| Validate Repository Structure | `validate-marketplace.yml` | (structure job) |
| Validate Marketplace Plugin Entries | `validate-marketplace.yml` | (entries job) |
| Validate Individual Plugins | `validate-marketplace.yml` | (per-plugin job) |
| Check for Duplicate Plugin Names | `validate-marketplace.yml` | (dedup job) |

`required_status_checks.strict: true` — branches must be up to date with `main` before merging.

### d) Codex delta review — real mechanism, not an assumed generic gate
- The workflow named **"Codex review status"** (`.github/workflows/await-codex-review.yml`, job
  display name **"Await Codex review"**) triggers on a PR opened non-draft, a draft PR marked
  ready, or an explicit `@codex review`/`@codex full review` PR comment (not on every push), and
  waits (up to 33 min) for the external `chatgpt-codex-connector` app's review to land.
- The *actual* required/blocking check for Codex review is **not** that waiter workflow itself —
  it's `marketplace-ci.yml`'s `codex-review` job (display name **"Codex delta review"**), whose
  result is turned into the required check **"Publish Codex policy result"** (job `publish`) shown
  in the branch-protection table above. Don't conflate "Codex review status"/"Await Codex review"
  (a helper wait-loop, not itself in the required-checks list) with "Publish Codex policy result"
  (the actual gate) — they are two different checks from two different workflows.

### e) Review requirements
- `branches/main/protection.required_pull_request_reviews` came back **empty/absent** — this
  repository's branch protection does **not** configure a required-approving-review-count gate.
  `required_signatures.enabled: false`, `required_conversation_resolution.enabled: false`.
- No `"Review Changes"` gate exists anywhere in this repository's real configuration — not
  invented here. (`git-kit:merge-pr` separately checks CODEOWNERS/merge rights for the *person*
  merging, but that's the merge-rights check below, not a branch-protection review-count gate.)

### f) Merge rights / method
- `enforce_admins.enabled: true` — admins are not exempt from the checks above.
- `required_linear_history.enabled: true`, `allow_force_pushes: false`, `allow_deletions: false`.
- Repo-level merge methods (`repos/AndreHahm/andres-cc-marketplace`): `allow_squash_merge: true`,
  `allow_merge_commit: true`, `allow_rebase_merge: true` — all three merge methods are enabled;
  `delete_branch_on_merge: true` (branch auto-deleted on merge, which is why
  `git-kit:finishing-work` → `/git-cleanup` still needs to run for local/worktree cleanup).
- Actual merge-rights verification (CODEOWNERS match / collaborator permission / repo-owner) for
  the person merging is `git-kit:merge-pr`'s own job, not something branch protection alone
  exposes — it's discovered by that skill at merge time, not duplicated here.

### g) Non-required checks that still run on the PR (disclosed for completeness, not blocking)
`pr-validate-title.yml`, `pr-require-impact-label.yml`, `dependency-review.yml`, `security.yml`,
`pr-auto-label.yml`, `pr-size-labeler*.yml`, `pr-merge-conflict-labeler.yml`,
`pr-status-sync.yml`, `pr-clean-caches.yml`, `pr-impact-autofix.yml` all trigger on PR events but
are **not** in `required_status_checks.contexts` — they can fail or be pending without blocking a
merge per branch protection (though they may still be worth resolving; that's a judgment call, not
a discovered gate).

### h) Cleanup
Not independently discovered here — delegated to `git-kit:finishing-work` (→ `/git-cleanup`) per
this repository's own convention, as the skill specifies.

## 3. Practical sequence for a Wave 2 Linear-issue branch → PR

1. `git-kit:starting-work` — branch/worktree.
2. `git-kit:commit` — triggers pre-commit hooks (2a) on each commit.
3. Before pushing/opening the PR: pre-push hook (2b) runs `marketplace_ci check-all --committed HEAD`.
4. `git-kit:create-pr` — opens the PR; `marketplace-ci.yml` and `validate-marketplace.yml` fire,
   producing the 9 required checks in the table above; `await-codex-review.yml` starts its wait
   loop; the real gating Codex outcome lands as "Publish Codex policy result."
5. No required-approving-review count is configured, so human review is not a blocking
   branch-protection gate — but `handling-review-findings`/`collaborating-on-a-pr` still apply if
   review comments are requested.
6. `git-kit:merge-pr` re-verifies all of the above (checks passing, not draft, no outstanding
   change-request reviews) plus the merger's own rights, before merging.
7. `git-kit:finishing-work` → `/git-cleanup` for post-merge sync and branch/worktree cleanup.

## Caveats

- Branch protection **was** readable in this session (200 response, not 403/404) — so "no
  discoverable required checks" does not apply here; the 9-context list above is real, not a
  fallback default.
- If a future session gets a 403/404 on this same endpoint, that must be reported as "no
  discoverable required checks — ambiguous, may be the caller's permission level rather than an
  actual absence of protection," per this skill's Failure and Resume section — not silently read
  as "no protection configured."
- The `provider_profile: null` vs. `FOUNDATION_CONTRACTS.md`'s fixed-`git-kit` table discrepancy
  (section 1) is disclosed rather than silently resolved one way — worth a maintainer decision on
  whether to populate the JSON field to match the documented table.
