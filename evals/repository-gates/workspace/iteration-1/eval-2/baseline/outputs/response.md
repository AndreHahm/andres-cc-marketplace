# Repository Policy Profile & Gate Discovery — andres-cc-marketplace

Grounded entirely in this repo's real, on-disk configuration plus one live GitHub API read (`gh api repos/AndreHahm/andres-cc-marketplace/branches/main/protection`, confirmed working and authenticated as `AndreHahm`). No assumptions below are un-sourced; each section names the file(s) or API call it came from.

## 1. Provider / Platform Profile

- **Host:** GitHub.com, repo `AndreHahm/andres-cc-marketplace`, **public**, default branch `main` (confirmed both in `.github/settings.yml` and live via `gh api repos/.../` → `visibility: public`, `default_branch: main`).
- **Merge methods enabled:** squash, merge-commit, and rebase all allowed; `delete_branch_on_merge: true`; `allow_update_branch: true` (live API matches `.github/settings.yml`).
- **Workflow kill switch:** `.github/WORKFLOW_KILLSWITCH` currently reads `STATUS: ENABLED` (last updated 2026-09-05). Every job in every workflow restores and checks this marker from the trusted base SHA before doing anything else — if flipped to `DISABLED`, all workflows below would short-circuit and exit immediately without enforcing anything.
- **Third-party static-analysis integrations layered on top of git-native gates** (config files present; live pass/fail status not independently verifiable via `gh api`, so treat these as configured-but-unverified from this pass): Codacy (`.codacy.yml` — sole source of truth for its ignore-list once present, with disclosed narrow exclusions for smoke-test fixtures, `tests/**`'s bandit B101 false positives, and the generated `.claude/**` mirror tree, each trading away secret-scan coverage on that path deliberately), DeepSource (`.deepsource.toml`, Python/JS/shell analyzers), Gitleaks (`.gitleaks.toml`), Secretlint (`.secretlintrc.json` + `.secretlintignore`), plus CodeRabbit (below).

## 2. Local Developer-Machine Gates (`.pre-commit-config.yaml`)

`fail_fast: true`. `default_install_hook_types` installs `pre-commit`, `pre-push`, `commit-msg`, `post-checkout`, `post-merge`, `post-rewrite` git hooks, but `default_stages: [pre-commit]` — **only the two locally-defined hooks below declare their own explicit `stages:`; every other hook in the file only actually runs at the `pre-commit` stage**, even though a `commit-msg` hook script gets installed.

**At `git commit` (pre-commit stage):**
- `validate-pyproject`, `check-github-workflows` (schema-checks all `.github/workflows/*.yml`)
- `uv-lock`, `uv-sync --locked --all-packages`
- `ruff-check --fix` / `ruff-format`, scoped to `^(scripts|tests|plugins/session-kit/(scripts|tests|skills))/.*\.py$`
- `gitleaks` (secret scan)
- `markdownlint-cli2`, scoped to `^docs/.*\.md$`
- `yamllint` (`.yaml`/`.yml`, excluding `mkdocs.yml`)
- `shellcheck`
- Standard hygiene hooks: trailing-whitespace, end-of-file-fixer, check-yaml, check-json, check-added-large-files (`--maxkb=1000`), check-merge-conflict, check-toml, mixed-line-ending, check-executables-have-shebangs
- **Local hook `marketplace-ci-check-staged`**: `uv run python -m scripts.marketplace_ci check-all --staged`, `stages: [pre-commit]`, `always_run: true`

**At `git push` (pre-push stage):**
- **Local hook `marketplace-ci-check-all`**: `uv run python -m scripts.marketplace_ci check-all --committed HEAD`, `stages: [pre-push]`, `always_run: true` — the deeper, whole-commit-range version of the same check-all logic run against `--staged` at commit time.

**Commit message format:** no `commit-msg`-stage hook is actually configured in `.pre-commit-config.yaml` (despite the hook type being installed), so Conventional Commit formatting is **not** enforced locally at commit time by pre-commit. It's enforced instead in CI (§4) via `.commitlintrc.cjs` (types: feat/fix/docs/style/refactor/perf/test/chore/ci/build/experiment; header ≤100 chars; `never` sentence-case/start-case/pascal-case/upper-case subject; kebab-case scope; blank line required before body and footer).

## 3. CI Gates That Run on Every PR (not all block merge)

- **`.github/workflows/commit-branch-guard.yml`** ("Commit & Branch Guard" → job "Validate commits and branch"), on `pull_request: [opened, synchronize, reopened, ready_for_review]` plus manual/`repository_dispatch` triggers:
  - Validates branch naming: preferred `feature|fix|hotfix|refactor|test|docs|chore/...`; legacy `feat|fix|docs|chore|refactor|test|build|ci|perf|style|hotfix|release/...` still accepted; `dependabot/`/`renovate/` automation branches exempted.
  - Runs commitlint against the PR's actual commits, using an **isolated** toolchain under `.github/commitlint-tools/` whose `package.json`/lockfile/`.commitlintrc.cjs` copy are restored from the **trusted base SHA** before install (defense against a PR redirecting a scoped npm registry via a malicious root `.npmrc`, even under `--ignore-scripts`).
  - **This job is not in the required-status-checks list below** — it runs and reports, but as configured today it does not itself block merging.
- **CodeRabbit** (`.coderabbit.yaml`): auto-review enabled on base branch `main`, `chill` profile, `request_changes_workflow: false` (never formally blocks via a GitHub "changes requested" review), path-scoped instructions per component type (`plugins/*/skills/**/SKILL.md`, `agents/**/*.md`, `commands/**/*.md`, `**/rules/*.md`, `scripts/marketplace_ci/**/*.py`, `tests/**/*.py`, `.github/workflows/**`), learns from `REVIEW.md`, ignores bot authors and WIP/DRAFT-titled PRs. Advisory commentary, not a required check.

## 4. Required PR Status Checks (Branch Protection on `main`)

Live-verified via `gh api repos/AndreHahm/andres-cc-marketplace/branches/main/protection` — matches `.github/settings.yml`'s declared config exactly:

| Setting | Value |
|---|---|
| `required_status_checks.strict` | `true` — branch must be up to date with `main` before merge |
| `enforce_admins` | `true` — **no admin-override escape hatch**, even the owner must pass all required checks |
| `required_linear_history` | `true` |
| `allow_force_pushes` / `allow_deletions` | `false` / `false` |
| `required_signatures` | `false` (disabled) |
| `required_conversation_resolution` | `false` (disabled) |
| `restrictions` | `null` (no push-restriction list beyond normal collaborator permissions) |
| `required_pull_request_reviews` | **absent from the live API response — disabled** (see §6) |

**The 9 required status-check contexts** (all reported by the GitHub Actions app, `app_id: 15368`), mapped to their real job source:

| Required context | Workflow / job |
|---|---|
| Hygiene (PR contract) | `marketplace-ci.yml` → `hygiene` |
| Python quality (ruff, ty, pytest) | `marketplace-ci.yml` → `python-quality` |
| Marketplace mirror/export parity | `marketplace-ci.yml` → `marketplace-parity` |
| Fork PR (unsupported — explicit terminal result) | `marketplace-ci.yml` → `fork-unsupported` |
| Publish Codex policy result | `marketplace-ci.yml` → `publish` |
| Validate Repository Structure | `validate-marketplace.yml` → `validate-structure` |
| Validate Marketplace Plugin Entries | `validate-marketplace.yml` → `validate-marketplace-plugins` |
| Validate Individual Plugins | `validate-marketplace.yml` → `validate-plugins` |
| Check for Duplicate Plugin Names | `validate-marketplace.yml` → `check-duplicates` |

Note the fork behavior specifically: `fork-unsupported` runs `if: github.event.pull_request.head.repo.fork` and **deliberately fails** ("Marketplace Codex review does not support fork-origin PRs — no trusted secret access for the Codex API key"), so a fork-origin PR is structurally unmergeable rather than left with a silently-pending required check.

## 5. Codex Delta Review Chain

Three chained jobs inside `marketplace-ci.yml`, only the last of which is a required check:

1. **`compute-scope`** ("Compute Codex review scope") — restores the scope-decision code and its dependency spec from the trusted base SHA (a PR can't edit its own review-scoping logic to weaken it), then determines whether this PR's diff qualifies for an automatic reviewer-scope bypass.
2. **`codex-review`** ("Codex delta review") — checks out the PR's merge commit, verifies the trusted base SHA resolves, **refuses to dispatch Codex at all if the PR modifies its own review-dispatch code** (another trust-boundary guard), installs a pinned (never-floating) Codex CLI, authenticates/smoke-checks it, dispatches reviewers and aggregates findings, and uploads the result as an artifact. *Not itself a required context.*
3. **`publish`** ("Publish Codex policy result") — **the actual required, blocking check.** Resolves whether the run should be treated as bypassed via a SHA-bound attestation protocol, either:
   - a `CODEX_CI_REVIEW_BYPASS` repo variable path combined with resolving the attesting actor from PR comments, or
   - a comment-plus-label protocol (`s: codex review bypassed` label; the attesting actor is resolved from *who applied the label* via the issue-events timeline, not the PR author).
   Every bypass path requires an exact head-SHA match, a non-empty attested reason, and the attesting actor holding **live write/maintain/admin permission** (checked against the real collaborators API at run time) — a bypass is explicitly never presented as a clean review, and all deterministic/branch-protection/PR-author-privilege gates still apply unchanged underneath it.

Separately, **`await-codex-review.yml`** ("Codex review status" → job "Await Codex review") waits up to 33 minutes for Codex's own external auto-review connector (`chatgpt-codex-connector[bot]`) to actually post review commentary — triggered by a PR opened non-draft/marked ready, or an explicit `@codex review` / `@codex full review` PR comment. This is the human-visible review-comment bot, distinct from the `codex-review` dispatch job above, and is also **not** one of the 9 required contexts.

## 6. Review Requirements

`required_pull_request_reviews` is **explicitly disabled** — confirmed both by its absence from the live protection API response and by an inline comment in `.github/settings.yml`:

> "disabled for now. This repository currently has a single collaborator (the owner, per CODEOWNERS), and GitHub does not allow a PR author to approve their own pull request — requiring review here (with `enforce_admins: true` removing the admin-override escape hatch) would make `main` permanently unmergeable through the normal PR flow. Re-enable once a second real collaborator/CODEOWNER exists."

`.github/CODEOWNERS` currently has a single blanket rule: `* @AndreHahm` — since `AndreHahm` is also the sole collaborator, this requests self-review rather than an independent human gate. In this repo's current single-maintainer state, the automated Codex delta-review policy check (§5) and CodeRabbit's advisory pass (§3) are the substitute review signal in place of a required human approval.

## 7. Merge Rights

Live-verified via `gh api repos/AndreHahm/andres-cc-marketplace/collaborators`:

- **Sole collaborator:** `AndreHahm`, with `admin: true, maintain: true, push: true, pull: true, triage: true`.
- The repo is **not** org-owned, so the `permission:` field noted as org-only in `.github/settings.yml` doesn't apply here.
- Practically: only `AndreHahm` can push/merge into `main`. Because `enforce_admins: true`, even the owner is **not** exempt from the 9 required status checks — admin status only removes the (currently moot, since no review is required anyway) review-approval gate, not the status-check gate.

## Summary for Wave 2

Any Wave 2 PR against `main` must, to be mergeable: pass local pre-commit hooks on commit and the `marketplace-ci check-all --committed HEAD` gate on push; carry a Conventional-Commits-compliant branch name and commit history (checked, but currently non-blocking, via Commit & Branch Guard); and pass all 9 required GitHub status checks — Hygiene, Python quality, Marketplace mirror/export parity, the fork-PR terminal check (N/A for same-repo pushes), the four `validate-marketplace.yml` structural checks, and critically **Publish Codex policy result**, which will fail the merge unless Codex's delta review passes or a properly SHA-bound, permission-checked bypass attestation is present. No human-approval review is currently required, and merging is restricted to `AndreHahm` as the sole collaborator.
