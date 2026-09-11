# Repository Policy Profile and Gate Discovery — `andres-cc-marketplace`

*(Discovered live against `AndreHahm/andres-cc-marketplace`, branch `main`, 2026-09-11, per `workmanagement-kit`'s `repository-gates` skill.)*

## 1. Provider Profile

**Source of truth conflict, disclosed rather than silently resolved:**

- `plugins/workmanagement-kit/versioned-configuration.json` (schema v2) — this installation's *resolved* value — ships **unconfigured**:
  ```json
  "github": {"repository_slug": null, "canonical_url": null, "default_branch": null, "native_automation": "unconfigured"},
  "repository_policy": {"provider_profile": null, "gate_discovery": "unconfigured"}
  ```
  This field has never been Bootstrap-populated for this installation.
- **Local override check (run exactly as the skill specifies):**
  ```
  git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"
  → exit 1: "did not match any file(s) known to git"
  ```
  Confirmed-untracked outcome (the only one eligible to honor an override) — but the file doesn't exist on disk at all (confirmed by a direct glob for it), so there is no override to merge in either way.
- `plugins/workmanagement-kit/FOUNDATION_CONTRACTS.md`'s canonical **Repository Policy Profile** section, however, hardcodes this specific repository's profile as a stated fact (not a default): *"For this repository, the profile is fixed — `git-kit` for every governed operation."*

Per the skill's own step 3 ("read that table directly rather than trusting a paraphrase"), the canonical table governs. **Resolved profile: `git-kit`, for every governed operation:**

| Logical operation | Provider |
|---|---|
| Create branch/worktree | `git-kit:starting-work` |
| Commit | `git-kit:commit` |
| Create a new PR | `git-kit:create-pr` |
| Push to an already-existing PR's branch | `git-kit:commit` (its own push step) |
| Mark a PR ready for review | **No provider yet** — disclosed manual handoff |
| Review/comment/link an issue at creation | `git-kit:collaborating-on-a-pr` (forward-looking) |
| Merge | `git-kit:merge-pr` |
| Post-merge sync/cleanup | `git-kit:finishing-work` |

**Flag for Wave 2 housekeeping:** the JSON config's own `provider_profile`/`github.*` fields being still `null`/`unconfigured` is itself a gap worth closing (Bootstrap has apparently never run for this installation, or has run only informally into the doc rather than the versioned config) — not something this discovery pass should paper over.

## 2. Pre-commit

`.pre-commit-config.yaml` exists at repo root. Hooks installed for `pre-commit` stage (plus `pre-push`/`commit-msg`/`post-checkout`/`post-merge`/`post-rewrite` types, per `default_install_hook_types`):

- `validate-pyproject` — schema-check `pyproject.toml`
- `check-github-workflows` (check-jsonschema) — validate `.github/workflows/*.yml`
- `uv-lock`, `uv-sync --locked --all-packages`
- `ruff-check --fix`, `ruff-format` — scoped to `^(scripts|tests|plugins/session-kit/(scripts|tests|skills))/.*\.py$`
- `gitleaks` — full-history secret scan
- `markdownlint-cli2` — scoped to `^docs/.*\.md$`
- `yamllint` (`-c .yamllint.yaml`) — scoped to `\.ya?ml$`, excludes `mkdocs.yml`
- `shellcheck`
- Standard `pre-commit-hooks` (v5.0.0): trailing-whitespace, end-of-file-fixer, check-yaml, check-json, check-added-large-files (max 1000KB), check-merge-conflict, check-toml, mixed-line-ending, check-executables-have-shebangs
- **Local hook** `marketplace-ci-check-staged`: `uv run python -m scripts.marketplace_ci check-all --staged`, `always_run: true`, `stages: [pre-commit]`

`fail_fast: true` is set repo-wide.

## 3. Pre-push

Same `.pre-commit-config.yaml`, one dedicated local hook:

- `marketplace-ci-check-all`: `uv run python -m scripts.marketplace_ci check-all --committed HEAD`, `always_run: true`, `stages: [pre-push]`

This is the repo's only pre-push gate — a full `marketplace_ci check-all` run against everything committed on the branch (vs. the pre-commit hook's `--staged`-only scope).

## 4. PR Required Checks (live branch-protection read)

`plugins/workmanagement-kit/scripts/gh_api_readonly.py repos/AndreHahm/andres-cc-marketplace/branches/main/protection` — invoked live via an authenticated `gh` session (`AndreHahm`, admin on this repo) — returned a real 200 response, not a 403/404, so this is a clean read, not an ambiguous absence:

```json
"required_status_checks": {
  "strict": true,
  "contexts": [
    "Hygiene (PR contract)",
    "Python quality (ruff, ty, pytest)",
    "Marketplace mirror/export parity",
    "Fork PR (unsupported — explicit terminal result)",
    "Publish Codex policy result",
    "Validate Repository Structure",
    "Validate Marketplace Plugin Entries",
    "Validate Individual Plugins",
    "Check for Duplicate Plugin Names"
  ]
}
```
All nine checks carry `app_id: 15368` (GitHub Actions). `strict: true` means the branch must be up to date with `main` before merge. `enforce_admins.enabled: true`, `required_linear_history.enabled: true`, `allow_force_pushes: false`, `allow_deletions: false`, `block_creations: false`, `required_conversation_resolution: false`, `lock_branch: false`.

## 5. Codex Delta Review — two distinct mechanisms, not one

Discovered from `.github/workflows/*.yml` directly (never assumed):

1. **`marketplace-ci.yml`'s `codex-review` → `publish` jobs** (job `publish`, display name `"Publish Codex policy result"`) — runs `uv run python -m scripts.marketplace_ci run-codex-review --base-sha "$BASE_SHA"` against the PR's actual diff. **This one is in the required-status-checks list above** — it is a real GitHub-enforced blocking gate.
2. **`.github/workflows/await-codex-review.yml`** (workflow name `"Codex review status"`, job `await-codex-review`, display name `"Await Codex review"`) — a *separate* mechanism that waits (up to 33 min) for GitHub's own Codex connector app (`chatgpt-codex-connector[bot]`) to actually post a review/reaction against the current head SHA, triggered on PR-opened/ready-for-review or an `"@codex review"`/`"@codex full review"` comment. **This display name does *not* appear in `required_status_checks.contexts` above** — it exists and functions as a real CI job, but is not itself a GitHub branch-protection-enforced required check on `main`. (No open PR exists right now to cross-check this against a live `gh pr checks` run, so this is workflow-file-only evidence for this check's identity — per the skill, match on the real display name, never the file name, if/when a PR exists to verify against.)

Do not conflate these two — different job, different display name, different enforcement status.

## 6. Review Requirements

The branch-protection response above returned **no `required_pull_request_reviews` key at all** (this was a clean 200 as an admin token, not a 403/404 permission gap). GitHub's protection API only includes that key when PR-review requirements are actually configured — its absence means **no required-approving-reviewer count or code-owner-review requirement is currently enforced via branch protection on `main`**. `.github/CODEOWNERS` does exist (`* @AndreHahm` — single blanket owner) and will still auto-request review, but nothing in branch protection *blocks* merge on it.

**Never invented a "Review Changes" gate** — none of the discovered configuration (branch protection, workflow files, CODEOWNERS) names anything by that identity.

## 7. Merge Rights / Method

- `repos/AndreHahm/andres-cc-marketplace`: `default_branch: "main"`, `allow_squash_merge: true`, `allow_merge_commit: true`, `allow_rebase_merge: true`, `allow_auto_merge: false`, `delete_branch_on_merge: true`, `allow_update_branch: true`.
- Current authenticated user (`AndreHahm`) permission on this repo: `admin` (`repos/.../collaborators/AndreHahm/permission` → `"role_name": "admin"`, `permissions: {admin:true, maintain:true, push:true, triage:true, pull:true}`) — full merge rights, and `enforce_admins: true` on branch protection means even this admin is still bound by the required checks above (no bypass).
- CODEOWNERS: `* @AndreHahm` — the same account is the sole code owner repo-wide.

## Summary

- **Profile:** `git-kit` for every governed operation (per `FOUNDATION_CONTRACTS.md`'s canonical table — the versioned-config JSON itself is still unconfigured/`null` and should be flagged for Bootstrap).
- **Pre-commit:** `.pre-commit-config.yaml`, 10 upstream hook repos + 1 local (`marketplace-ci-check-staged`).
- **Pre-push:** one local hook, `marketplace-ci-check-all` (full `check-all --committed HEAD`).
- **PR required checks:** 9 GitHub Actions contexts, `strict: true`, `enforce_admins: true`.
- **Codex delta review:** two separate mechanisms — `"Publish Codex policy result"` (required, blocking) and `"Await Codex review"` (real CI job, not currently a required status check).
- **Review requirements:** none enforced via branch protection (`required_pull_request_reviews` absent); CODEOWNERS exists but isn't a blocking gate.
- **Merge rights:** current user has `admin`, all three merge methods enabled, `enforce_admins` still applies, branches auto-delete on merge.
