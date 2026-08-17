# Marketplace CI

This repository's pull requests are gated by a single consolidated GitHub Actions workflow,
`.github/workflows/marketplace-ci.yml`, triggered on `pull_request` (`opened`, `synchronize`,
`reopened`, `edited`, `labeled`). It runs deterministic checks plus a Codex-dispatched delta review
against `scripts/marketplace_ci/`'s own logic — see `.draft/2026-08-07-plugin-marketplace-ci-implementation-plan.md`
for the full design history and `plugins/codex-kit/skills/plugin-marketplace-review/SKILL.md` for the
Codex review policy itself.

## Required status checks

These are the exact check-run names GitHub reports for this workflow (verified live against a real PR,
not hand-typed):

| Check name | Job | What it verifies |
|---|---|---|
| `Hygiene (PR contract)` | `hygiene` | PR title/template conformance, author-privilege policy (`check-pr`) |
| `Python quality (ruff, ty, pytest)` | `python-quality` | `ruff format --check`, `ruff check`, `ty check`, `pytest -q` against `scripts/`+`tests/` |
| `Marketplace mirror/export parity` | `marketplace-parity` | `check-all` — every plugin's generated `.claude`/`.agents`/`.codex` mirror/export is in sync with its canonical source |
| `Fork PR (unsupported — explicit terminal result)` | `fork-unsupported` | Only runs (`if:`) when the PR head is a fork; fails explicitly rather than leaving Codex review silently pending. **Reports `skipped` on a same-repo PR** — a `skipped` conclusion satisfies a required check in GitHub's branch protection, so this doesn't block ordinary same-repo PRs. |
| `Codex delta review` | `codex-review` | Dispatches the reviewer set from `derive_review_scope` via `codex-review-bridge` — including `full`-mode escalation's own defined, bounded reviewer set (see "Full-mode escalation" below) |
| `Publish Codex policy result` | `publish` | The single check branch protection should actually require for Codex policy: passes if `codex-review` succeeded, OR if a valid SHA-bound bypass attestation + `codex-review-bypassed` label is present for the current head SHA |

Configure branch protection to require: `Hygiene (PR contract)`, `Python quality (ruff, ty, pytest)`,
`Marketplace mirror/export parity`, `Fork PR (unsupported — explicit terminal result)`, and
`Publish Codex policy result`. Do **not** separately require `Codex delta review` — `publish` already
depends on it (`needs: [codex-review]`) and is the check that knows about the bypass path; requiring
both would make a legitimately-bypassed PR's `Codex delta review` failure block the merge again,
defeating the bypass entirely.

## Configuring the review model

`codex-review-bridge` never passes `--model` to `codex exec` by default — every dispatch falls through
to whatever `~/.codex/config.toml` resolves after the workflow's own `codex login --with-api-key` step,
which is an account/API-key-level default this repo doesn't control. If that default resolves to an
expensive model, set the **repository variable** `CODEX_KIT_REVIEW_MODEL` (Settings → Secrets and
variables → Actions → Variables — not Secrets, since a model slug isn't sensitive) to a specific model
slug. The workflow passes it through as an environment variable to the `codex-review` job; `codex-review-bridge`'s
`bridge-invoke.mjs` reads it and passes `--model <value>` to every reviewer it dispatches in that run.
Leave it unset to keep using the account default. Invalid values (anything outside
`^[A-Za-z0-9._-]{1,64}$`) fail the job with a clear message rather than surfacing as an opaque Codex CLI
error.

## Configuring the review timeout

Every `codex-review-bridge` dispatch shares `runCodexExec`'s own 240000ms (4 min) default timeout unless
overridden. On a large delta PR, a single reviewer's one-call review can legitimately need longer than
that to complete against its full scope — confirmed live: a 100-changed-path PR pushed
`plugin-rulebook-checker`'s dispatch past the default, first as a strained/malformed response, then as a
hard timeout on retry. The `codex-review` job sets `CODEX_KIT_REVIEW_TIMEOUT_MS: "600000"` (10 min)
directly in the workflow (not a repository variable, unlike the model override above — this is a
self-contained workflow default, not something a maintainer needs to configure separately), giving every
dispatched reviewer more headroom within the job's own 20-minute budget. Invalid values (non-numeric or
non-positive) fail the job with a clear message, same as the model override.

## Fork PR limitation

`codex-review` needs `OPENAI_API_KEY`, which GitHub Actions does not expose to workflows triggered by a
fork PR (no trusted secret access, by design — a fork PR's workflow content is untrusted). Rather than
leaving the Codex check permanently pending on a fork PR (which would silently block merge forever with
no actionable signal), `fork-unsupported` fails explicitly and immediately when `github.event.pull_request.head.repo.fork`
is true. A fork-originated PR against this repository cannot currently pass Codex review automatically —
it requires either becoming a same-repo branch (push access) or a maintainer's attested bypass (see below).

## SHA-bound bypass protocol

A PR whose *only* failing required check is `Publish Codex policy result` can be unblocked by a
maintainer (live `write`/`maintain`/`admin` permission) attesting a bypass, bound to the exact head SHA:

1. Post a PR comment containing a hidden marker:
   `<!-- marketplace-ci-bypass-attestation {"schema_version":1,"actor":"<login>","head_sha":"<sha>","reason":"<reason>","created_at":"<ISO-8601 UTC>"} -->`
2. Apply the `codex-review-bypassed` label (must already exist in the repo — nothing creates it
   automatically; create it once via `gh label create codex-review-bypassed`).
3. Applying the label re-triggers the workflow (`labeled` is in the `pull_request` trigger types);
   `publish` re-checks the attestation via `scripts/marketplace_ci/review.py`'s `check_bypass` — exact
   actor + exact head SHA match, plus a live permission check — and reports `Publish Codex policy result`
   as passing, explicitly annotated as bypassed, never as a clean review. Applying a label that's
   **already present** on the PR is a GitHub Actions no-op and does not fire a fresh `labeled` event — a
   re-attestation after a superseded bypass attempt must remove the label first (`gh pr edit --remove-label
   codex-review-bypassed`), then re-add it, to force a fresh check run.
4. A new commit changes the head SHA, invalidating any prior attestation — it must be re-attested.

`Skill(git-kit:create-pr)` and `Skill(git-kit:merge-pr)` both support `--bypass-codex-review "<reason>"`
to run this protocol as part of the normal PR-creation/merge flow rather than by hand. Neither skips any
other check, the merge-rights check, or the explicit human merge confirmation — see each skill's own
Boundaries section.

## Full-mode escalation

A PR touching a shared-governance path (the marketplace registry file, `marketplace.json`, or
`plugin-rulebook`'s own `SKILL.md`) or an oversized dependency closure escalates `derive_review_scope`
to `mode == "full"`. Both triggers now dispatch a defined, bounded reviewer set — a dependency-closure
overflow reuses delta's own baseline reviewers scoped to the full closure; a shared-governance-path
change dispatches a small, fixed set targeted at that file (`plugin-rulebook-checker` +
`consistency-reviewer` for a rulebook change, `plugin-validator` for a registry/manifest change) — never
a marketplace-wide re-review of every plugin. `run-codex-review` still fails closed (exit 2) as a
defensive backstop only if a future escalation trigger is ever added without a matching reviewer set
defined for it; that path is not reachable through either of today's two triggers. See
`plugin-marketplace-review/SKILL.md`'s "Full review escalation" section for the exact per-trigger
reviewer sets.
