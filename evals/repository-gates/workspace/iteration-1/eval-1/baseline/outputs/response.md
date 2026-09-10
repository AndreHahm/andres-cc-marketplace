# Gates on `andres-cc-marketplace` Before Publishing a PR (Wave 2 Linear-Issue Branch)

## How I resolved this

There's no single settings file inside `plugins/workmanagement-kit` that already answers this for the
current repo — `plugins/workmanagement-kit/versioned-configuration.json` has:

```json
"repository_policy": {
  "provider_profile": null,
  "gate_discovery": "unconfigured"
}
```

So the "policy profile" isn't pre-resolved anywhere in the plugin's own config; I discovered the actual
gates by reading the live GitHub branch protection rule on `main` (`gh api
repos/AndreHahm/andres-cc-marketplace/branches/main/protection`) and cross-referencing it against the
real workflow definitions in `.github/workflows/`. That's a live, current source, not something hardcoded
in this answer — worth re-checking with the same `gh api` call if protection settings change later.

## Branch protection on `main` (live-verified)

- **Required status checks** (strict — your branch must be up to date with `main` before merge):
  1. `Hygiene (PR contract)`
  2. `Python quality (ruff, ty, pytest)`
  3. `Marketplace mirror/export parity`
  4. `Fork PR (unsupported — explicit terminal result)`
  5. `Publish Codex policy result`
  6. `Validate Repository Structure`
  7. `Validate Marketplace Plugin Entries`
  8. `Validate Individual Plugins`
  9. `Check for Duplicate Plugin Names`
- **Required approving reviews:** 1 (`require_code_owner_reviews: false`, `dismiss_stale_reviews: false`,
  `require_last_push_approval: false`, no bypass allowances configured)
- **`enforce_admins: true`** — even the repo owner isn't exempt from the above
- **`required_linear_history: true`** — no merge commits allowed onto `main`; merge must be squash or
  rebase
- Force pushes and branch deletion are disallowed on `main`; conversation resolution and commit
  signatures are **not** required
- No push restrictions (any collaborator with write access can push a branch)

## What each required check actually verifies

| Required check | Workflow / job | What it verifies |
|---|---|---|
| `Hygiene (PR contract)` | `marketplace-ci.yml` → `hygiene` | PR title matches conventional-commit format (`type(scope): desc`, allowed types incl. `feat/fix/docs/refactor/perf/test/chore/experiment`), no emoji; PR body's `##` headings are a valid subsequence of `.github/pull_request_template.md`'s headings in order; the PR author has rights to open a PR (repo owner or collaborator with `write`/`maintain`/`admin`); and merge privilege for the changed paths via CODEOWNERS (today `.github/CODEOWNERS` is just `* @AndreHahm`, so anyone else needs collaborator `write`+ permission). |
| `Python quality (ruff, ty, pytest)` | `marketplace-ci.yml` → `python-quality` | `ruff format --check`, `ruff check`, `ty check`, `pytest -q` against `scripts/` + `tests/`. |
| `Marketplace mirror/export parity` | `marketplace-ci.yml` → `marketplace-parity` | Every plugin's generated `.claude/`/`.agents/`/`.codex/` mirror/export is in sync with its canonical source — relevant if your Wave 2 change touches workmanagement-kit skills/agents that get mirrored. |
| `Fork PR (unsupported...)` | `marketplace-ci.yml` → `fork-unsupported` | Only fails an actual fork-originated PR; reports `skipped` (a pass) for a same-repo branch, which a Wave 2 Linear-issue branch presumably is. |
| `Publish Codex policy result` | `marketplace-ci.yml` → `publish` | The real Codex-review gate. Passes if the delta Codex review ran and passed, or the diff was legitimately scope-bypassed (e.g. no `plugins/` paths touched, or only inert paths like `evals/`), or a maintainer posted a valid SHA-bound bypass attestation + `s: codex review bypassed` label. A change touching `plugins/workmanagement-kit/skills|agents|scripts` will trigger a real Codex delta review, not the bypass. |
| `Validate Repository Structure`, `Validate Marketplace Plugin Entries`, `Validate Individual Plugins`, `Check for Duplicate Plugin Names` | `validate-marketplace.yml` | Structural validation of `marketplace.json` and each plugin's manifest/layout. |

## Checks that run but are **not** required by branch protection right now

These execute on your PR and can show a red X, but — per the live protection data above — none of them
are in the required-status-checks list, so a failure here alone won't block the merge button:

- `Validate PR Title follows Conventional Commits` (`pr-validate-title.yml`) — a second, separate title
  check (Hygiene above already enforces title format as part of a required check).
- `Commit & Branch Guard` (`commit-branch-guard.yml`) — validates your branch name against
  `feature|fix|hotfix|refactor|test|docs|chore/<slug>` (or the legacy `feat|fix|docs|chore|refactor|test|build|ci|perf|style|hotfix|release/<slug>` form) and runs `commitlint` over each commit in the PR.
- `Require Impact Label` (`pr-require-impact-label.yml`) — requires exactly one of
  `i: breaking change` / `i: major change` / `i: minor change` (skipped on drafts).
- `Security` (`security.yml`) — secretlint on changed files, npm audit, CodeQL, on push/PR to `main`.
- `Dependency review` (`dependency-review.yml`) — flags known-vulnerable dependency versions in the diff.
- `await-codex-review.yml` — visibility-only wait on the separate external `chatgpt-codex-connector[bot]`
  reviewer; explicitly documented as not a required check.
- PR size/auto-labelers, merge-conflict labeler, label sync, workflow-health — cosmetic automation, not
  gates.

## Practical checklist for your Wave 2 Linear-issue PR

1. **Branch name** — even though Commit & Branch Guard isn't a required check, still name the branch
   `<type>/<description>` (e.g. `feat/...`, `fix/...`) — it's the convention the repo and
   `plugins/workmanagement-kit/CONTRIBUTING.md` both expect, and it feeds `commitlint`/title consistency.
2. **PR title** — conventional-commit format, one of the allowed types, no emoji (enforced by the
   required `Hygiene` check).
3. **PR body** — use `.github/pull_request_template.md` as-is; don't add headings it doesn't have, and
   keep the ones you use in its order (also enforced by `Hygiene`).
4. **Code quality** — `ruff format`, `ruff check`, `ty check`, and `pytest` must pass over anything under
   `scripts/`/`tests/` you touched.
5. **Plugin mirror parity** — if you changed any workmanagement-kit skill/agent content, make sure the
   generated `.claude/`/`.agents/`/`.codex/` mirrors were regenerated/committed.
6. **Codex review** — expect a real delta Codex review to run (workmanagement-kit skill/script changes
   aren't bypass-eligible); resolve or accept its findings, or get a maintainer's SHA-bound bypass
   attestation if you truly need to skip it.
7. **Marketplace validation** — if `marketplace.json` or the plugin's manifest changed, it must pass
   structural/duplicate-name validation.
8. **Review** — you need 1 approving review from a GitHub account other than the PR author (GitHub
   doesn't let an author's own approval count, and `require_code_owner_reviews` isn't even turned on
   separately, so any collaborator's approval satisfies it — but it can't be self-approval, and CODEOWNERS
   currently names only `@AndreHahm` for merge-privilege purposes on `Hygiene`).
9. **Merge mechanics** — `main` requires linear history, so the merge itself must be squash or rebase, not
   a merge commit; force-pushes/deletions on `main` are blocked regardless.
10. **Behavior-changing work** — the plugin's own `CONTRIBUTING.md` asks you to test any skill/agent
    behavior change per this repo's testing conventions and run `plugin-rulebook` against any new/modified
    component before finalizing. This isn't enforced by a CI status check today — it's a documented
    process expectation, not a blocking gate — so don't rely on CI alone to catch a skipped test.

## Caveat

This is a live snapshot (branch protection settings can be changed by anyone with admin access), and I
deliberately did not consult `plugins/workmanagement-kit/skills/repository-gates` or any other
gate-discovery tooling that might exist in this plugin — everything above comes from directly reading
`.github/workflows/*.yml`, `.github/CODEOWNERS`, `docs/ci.md`, `plugins/workmanagement-kit/CONTRIBUTING.md`,
`plugins/workmanagement-kit/versioned-configuration.json`, and the real GitHub branch-protection API
response for this repository.
