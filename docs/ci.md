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
| `Compute Codex review scope` | `compute-scope` | Cheap, Node/Codex-CLI-free job that computes whether the diff is eligible for the automatic reviewer-scope bypass (see below) and, on a `synchronize` event, whether this push rebased onto a newer base. Checks out the PR's own head SHA directly (never the async `refs/pull/<n>/merge` ref `codex-review` uses) so its scope decision can't disagree with what `codex-review` actually reviews — then restores `scripts/marketplace_ci/` itself from the **trusted base SHA** before scoring, so the decision logic isn't evaluated by a version of itself the PR could have edited (same principle `prepare_reviewer_instruction` already applies to reviewer instructions). Not a required check itself, but `publish` now depends on it having actually **succeeded** — a failure, cancellation, or timeout (5 min) here fails `publish` closed, it does not silently read as "not eligible, run codex-review normally." |
| `Codex delta review` | `codex-review` | Dispatches the reviewer set from `derive_review_scope` via `codex-review-bridge` — including `full`-mode escalation's own defined, bounded reviewer set (see "Full-mode escalation" below). Skipped when `compute-scope` reports the diff bypass-eligible, in addition to the existing fork-PR skip. |
| `Publish Codex policy result` | `publish` | The single check branch protection should actually require for Codex policy: passes if `compute-scope` succeeded AND (`codex-review` succeeded, OR was skipped **with `compute-scope`'s own `bypass_eligible` output confirming why**), OR if a valid SHA-bound bypass attestation + `codex-review-bypassed` label is present for the current head SHA. Now runs unconditionally for every same-repo PR (only a fork PR skips it) rather than only when `codex-review` itself ran. Keys the "was this skip legitimate?" check off `compute-scope`'s explicit output rather than `codex-review`'s bare result — `codex-review` also depends on `hygiene`/`python-quality`/`marketplace-parity`, any of which failing independently also produces a `skipped` `codex-review`, which the bare-result check alone would have accepted as a clean pass. |

Configure branch protection to require: `Hygiene (PR contract)`, `Python quality (ruff, ty, pytest)`,
`Marketplace mirror/export parity`, `Fork PR (unsupported — explicit terminal result)`, and
`Publish Codex policy result`. Do **not** separately require `Codex delta review` or
`Compute Codex review scope` — `publish` already depends (transitively) on both and is the check that
knows about every skip/bypass path; requiring `Codex delta review` directly would make a
legitimately-bypassed PR's skip block the merge again, defeating the bypass entirely.

## External Codex connector review status

A separate workflow, `.github/workflows/await-codex-review.yml`, makes the otherwise invisible
wait for the *external* `chatgpt-codex-connector[bot]` GitHub App reviewer visible as a pull
request check (`Codex review status / Await Codex review`). This is unrelated to the `codex-review`
job documented above — that job dispatches this repository's own `codex-review-bridge` reviewers
via `OPENAI_API_KEY`; `await-codex-review.yml` only polls for a review submitted by the separate,
externally-connected `chatgpt-codex-connector[bot]` account. It is currently visibility-only, not
a required status check. See [`docs/await-codex-review.md`](await-codex-review.md) for the full
contract, result semantics, and adoption-mode details.

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

## Automatic reviewer-scope bypass

Separate from the manual protocol below, `compute-scope` skips `codex-review` entirely — no maintainer
action needed — when `derive_review_scope`'s own scope for the diff resolves to nothing any reviewer
would look at: today's `mode == "light"` (no `plugins/` path touched at all), and the newer case where
`plugins/` paths were touched but every one of them is excluded anyway. That exclusion is deliberately
**narrower** than `plugin-rulebook-checker`'s own target-path exclusion: only an `evals/`-prefixed path or
a plugin-root `LICENSE`/`NOTICE`/`KNOWN_ISSUES.md` (genuinely inert text) qualifies. A plugin's
`README.md`/`CONTRIBUTING.md`/`CHANGELOG.md`/`INSTALLATION.md` do **not** bypass — a security review found
these can carry real signal (a README's install step piping a script to a shell, a CHANGELOG newly
documenting a dependency) that `dependency-reviewer`/`security-reviewer` should still see, even though
`plugin-rulebook-checker`'s own R1-R27 rules never had an opinion on them. The exclusion also only ever
applies to a basename sitting directly at a plugin's own root or the repo root — a same-named file nested
inside a component directory (e.g. `plugins/<name>/commands/README.md`, a real, Claude-Code-loadable
command file) is never excluded, so a component change can't be smuggled past every reviewer by naming it
after an excluded basename. `mode == "full"` (see "Full-mode escalation" below) is never bypass-eligible,
regardless of scope — that path is inherently high-risk by definition, including its own fail-closed
empty-scope gap case. Nor is a diff touching the gate's own code, its CI dependency spec, the PR template,
or a CODEOWNERS file — `.github/`, `scripts/`, `.codex/agents/`, `.claude/rules/`, `pyproject.toml`,
`uv.lock`, `CODEOWNERS`, `docs/CODEOWNERS` (the three locations `check-pr`'s own merge-privilege matching
reads — `.github/CODEOWNERS` is already covered by the broader `.github/` entry) — ever bypass-eligible,
even mixed with otherwise-eligible files. This is enforced two ways, not just a flag flip:
`derive_review_scope` itself falls through to a real delta dispatch (the baseline three reviewers) for any
diff touching one of these paths, rather than resolving to empty-reviewer `mode == "light"` the way an
equivalent non-self-protected diff would — a security review found an earlier version only forced
`bypass_eligible=False` without also ensuring a reviewer actually ran, so the diff was correctly marked
ineligible but still reviewed by nobody. `is_bypass_eligible`'s own explicit prefix check stays as a
second, independent layer on top. The prefix list covers the whole `scripts/` tree (not just
`scripts/marketplace_ci/`), since `python -m scripts.marketplace_ci` imports `scripts/__init__.py` first —
a narrower list a security review actually found left that one file able to bypass its own review by
sitting just outside the guarded path. It also covers a bare-root `CODEOWNERS` add — a security review
found an unreviewed CODEOWNERS file both grants and denies merge privilege unconditionally (a match is
terminal in `check_merge_rights`, never falling through to the collaborator-permission check), for every
PR after the one that added it, and no such file exists in this repo today, so this is a live gap, not a
hypothetical.

**Trust boundary, stated plainly, not just narrowed further:** `compute-scope` restores
`scripts/`+`pyproject.toml`+`uv.lock` from the **trusted base SHA** — never the PR's own copy — before
computing the scope decision or installing dependencies for it (same principle
`prepare_reviewer_instruction` already applies to reviewer instructions; see the `compute-scope` job's own
"Restore the base SHA's copy..." step), and fails the job outright if that restore itself can't complete,
rather than falling back to scoring with the PR's own copy. `git diff base...HEAD` is unaffected by this
restore — it compares commit objects, not the working tree, so the PR's real diff is still what gets
scored. This raises the bar against an *unaware* PR touching the bypass logic, dependency spec, or
`scripts/__init__.py` and defeating itself by accident. It is **not** an adversarial-proof boundary, and
doesn't claim to be one: a same-repo PR author can edit `.github/workflows/marketplace-ci.yml` itself,
since GitHub runs a `pull_request` workflow using the PR's own copy of the workflow file for a same-repo
PR — a pre-existing property of every check in this workflow (including `codex-review`'s own dispatch,
which has always run from the PR's head checkout), not something this bypass feature introduces or could
close from inside a Python module it doesn't control the invocation of.

Diff-path parsing for both this bypass decision and `codex-review`'s own scope computation uses
`git diff -z --name-only` (NUL-delimited, never C-quoted), not the more common newline-split form — a
security review found that with git's default `core.quotePath=true`, a non-ASCII path is emitted
C-quoted in plain `--name-only` output (e.g. `"plugins/x/skills/y/caf\303\251.py"`), which fails every
`startswith("plugins/")`-style check downstream and would otherwise silently misroute a real component
change into light/bypass-eligible mode.

This bypass never applies to a rebase onto the base branch: on a `synchronize` event, `compute-scope`
checks whether the PR's base commit was newly absorbed this push (reachable from the new head SHA but
not the old one) and, if so, forces `codex-review` to run regardless of what the scope check found. A
rebase can change how already-reviewed code interacts with what the base branch now contains in ways a
bare changed-file-list diff doesn't capture, so it always gets a real Codex pass. This check fails closed
too — if the old/new head SHAs can't be resolved (e.g. already garbage-collected after a force-push), it
treats the push as a rebase rather than silently assuming otherwise. Crucially, `--before`/`--after` are
only present on a `synchronize` event at all — every other `pull_request` action (`opened`, `reopened`,
`edited`, `labeled`) carries neither, and **the bypass is never eligible without both**, not just when a
detected rebase forces it off. An earlier version only checked ancestry *if* both happened to be
present, which a security review found was a one-push bypass of the whole carve-out: push a rebase (a
`synchronize` event correctly detects it and runs `codex-review`), then edit the PR title (an `edited`
event, with no `before`/`after` at all, silently skipped the rebase check and reported eligible again).
Requiring both present unconditionally closes that gap.

Unlike the manual bypass below, this one is never presented as an override — `codex-review` simply never
had anything to review, so `publish` reports the normal `skipped` conclusion, not a bypass annotation.

## Manual SHA-bound bypass protocol

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
