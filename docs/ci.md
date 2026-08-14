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
| `Codex delta review` | `codex-review` | Dispatches the reviewer set from `derive_review_scope` via `codex-review-bridge`; fails closed on `full`-mode escalation (no reviewer set defined yet — see the skill doc above) |
| `Publish Codex policy result` | `publish` | The single check branch protection should actually require for Codex policy: passes if `codex-review` succeeded, OR if a valid SHA-bound bypass attestation + `codex-review-bypassed` label is present for the current head SHA |

Configure branch protection to require: `Hygiene (PR contract)`, `Python quality (ruff, ty, pytest)`,
`Marketplace mirror/export parity`, `Fork PR (unsupported — explicit terminal result)`, and
`Publish Codex policy result`. Do **not** separately require `Codex delta review` — `publish` already
depends on it (`needs: [codex-review]`) and is the check that knows about the bypass path; requiring
both would make a legitimately-bypassed PR's `Codex delta review` failure block the merge again,
defeating the bypass entirely.

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
to `mode == "full"`. No automated reviewer set is defined for `full` mode yet, so `run-codex-review`
fails closed (exit 2) with an explicit message rather than silently passing with zero review coverage.
A `full`-mode PR requires human review and, if otherwise ready, the same SHA-bound bypass protocol above
to merge.
