# CI Claude Delta Review: User Requirements

The maintainer's requirements for the `Claude delta review` CI workflow
(`.github/workflows/claude-review-ci.yml`). It reviews the changes of a pull request since the head it
last reviewed, using the Anthropic API. Its implementation is described in [`docs/ci.md`](ci.md),
section "Claude delta review (advisory)". Where the two disagree, this document states the intent and
`docs/ci.md` must be corrected.

The Codex delta review in `.github/workflows/marketplace-ci.yml` stays as it is. Its requirements are in
[`docs/ci-codex-review-user-requirements.md`](ci-codex-review-user-requirements.md); this document refers
to them as "Codex R<n>".

**Problem:** the repository gets a monthly Anthropic API budget of $200 and wants a second, independent
model vendor reviewing pull requests in CI. The local `cross-model-review` skill already does this before a
pull request is created, but nothing does it after.

Each requirement carries a status: `proposed` (written from the design discussion, not yet confirmed) or
`approved` (confirmed by the maintainer).

## R1. Advisory, not a merge gate

- The Claude delta review is a separate workflow with its own check. It is not a required status check,
  and nothing in branch protection or in `Publish Codex policy result` depends on it.
- Its findings are advice. A human or `handling-review-findings` decides what to do with them.
- Promoting it to a required gate is a separate, later decision (R12).

Status: approved

## R2. Which pull requests and events get a review

- Only pull requests from this repository. A pull request from a fork gets no review and no failure: no
  secret is available there.
- No review on pull requests opened by `dependabot[bot]`.
- No review while a pull request is a draft. Moving it to ready (`ready_for_review`) reviews the whole
  pull request minus the exclusions (R4), as Codex R14 does.
- Triggers: `opened`, `synchronize`, `reopened`, `ready_for_review`. `edited` and `labeled` are not
  triggers, because they bring no new commits.
- No on-demand trigger: no `workflow_dispatch`, no comment command. Re-running the job reviews the same
  delta again (as Codex R11).
- A newer push cancels a review that is still running for the same pull request.

Status: approved

## R3. Only the delta since the last Claude review is reviewed

- The anchor is the pull request head that the newest earlier run of this workflow reviewed. That run must
  have completed before the current run was created, and its result must name its own head and its latest
  attempt (the same rules as Codex R5 and R11, applied to this workflow's own runs and result artifact).
- With an anchor, only files whose pull-request-side change differs from the anchor are reviewed (as
  Codex R6). Without an anchor, the whole pull request minus the exclusions (R4) is reviewed.
- An anchor that the pull request could have influenced is not trusted, and the whole pull request is
  reviewed instead (as Codex R10).
- The delta is computed by the same trusted code as the Codex review (`check-scope-bypass --ci-delta`),
  restored from the base SHA.
- The lookup of the last reviewed head moves out of `marketplace-ci.yml`'s inline shell into one trusted
  `scripts/marketplace_ci` subcommand. Both workflows call it, each with its own workflow, job and result
  artifact names. The Codex anchor behavior must not change.
- When nothing is left to review, no API call is made.
- A run that reviewed counts as an anchor whether or not it found something (R7). A cancelled run, a run
  that could not review, and a skipped run do not count.
- The anchor never comes from a pull request comment or anything else the author can edit.

Status: approved

## R4. Paths excluded from the review

The Claude review leaves out fewer paths than the Codex review (Codex R2):

- Not reviewed: `issues/`, `evals/` and `reviewer-eval/` at the repository root, and generated agent
  mirrors whose content and mode equal their source (as in Codex R2).
- Reviewed, unlike Codex: test directories (`tests`, `test`, `__tests__`), `fixtures` directories, and
  test files (`smoke_test.<ext>`, `test_*.py`, `*_test.py`, `*.test.{js,mjs,cjs,ts}`), anywhere.
- Gate-critical paths (Codex R3) are never excluded.
- The shared scope code gets an option for this narrower exclusion set. The Codex review keeps its own
  set unchanged.

Status: approved

## R5. What the reviewer is told and allowed to do

- **General review.** Every review runs one general pass that follows [`REVIEW.md`](../REVIEW.md): its
  four-tier severity scale (Critical, Major, Minor, Informational) and its `LGTM` or `Changes Requested`
  verdict. Every finding cites a file path and line.
- **Security pass.** When the reviewed delta contains a gate-critical path (Codex R3), a second pass runs
  that follows this repository's `security-reviewer` agent instructions, read from the base SHA.
- `REVIEW.md`, the reviewer prompt and the security-reviewer instructions are read from the base SHA,
  never from the pull request.
- The reviewer may only read files and post review comments. It gets no shell, no file writes and no web
  access.
- Pull request content is untrusted data. The prompt says so, and nothing in it can widen the reviewer's
  permissions.
- Hooks and settings from the repository's `.claude/` directory do not run during the review.

Status: approved

## R6. Where findings appear

- Critical and Major findings are posted as inline review comments on the changed lines.
- One summary comment per pull request carries the verdict, the reviewed head, the anchor, the model,
  whether the security pass ran, and the cost. Each run updates that comment instead of adding a new one.
- Each run uploads a machine-readable result file (status, verdict, reviewed head, run attempt, anchor,
  reviewed paths, model, cost per pass).

Status: approved

## R7. The check result

- The check fails when the run found a Critical or Major finding, in either pass.
- The check also fails when the review could not run: an invalid setting, an API error, a per-pass cap
  (R9) reached, or a timeout. Such a run is not an anchor (R3).
- Otherwise it passes, including when only Minor or Informational findings were raised.
- The check is not required (R1), so a failure never blocks a merge.
- Findings are not carried forward. A later run reviews only its own delta, so its check can pass while
  an earlier finding is still unfixed. That finding's inline comment stays open in the pull request until
  someone resolves it.

Status: approved

## R8. Model and timeout settings

- `CLAUDE_KIT_REVIEW_MODEL` (repository variable) selects the model for both passes. When it is unset,
  the workflow uses `claude-sonnet-5-5`. An invalid value (anything outside `^[A-Za-z0-9._-]{1,64}$`)
  fails the check with a clear message.
- `CLAUDE_KIT_REVIEW_TIMEOUT_MS` (repository variable) limits one review pass, in milliseconds. The
  workflow uses the variable when it is set, and a default of 1200000 (20 minutes) when it is unset. A
  value that is not a positive whole number, or that does not fit in the job's own time limit, fails the
  check with a clear message. The job's time limit leaves room for both passes at the full value.

Status: approved

## R9. Cost limits

- The monthly limit of $200 is enforced by a spend limit on the Anthropic Console workspace that holds
  the API key. When it is reached, reviews fail as could-not-run (R7).
- Each pass has its own cap: an estimated cost of $1.00, and 50 turns for the general pass or 25 for
  the security pass. A pull request with a security pass can therefore cost up to about $2.00 per run.
  The caps are starting values to tune from the recorded costs; the general pass's turn cap was raised
  from 25 after PR #703's first funded run stopped at it (26 turns, $0.07).
- Every run records its cost per pass, so the model choice and the caps can be tuned from real numbers.

Status: approved

## R10. Kill switch (`CLAUDE_CI_REVIEW_BYPASS`)

- `1`: no review and no API call. The check passes with a notice saying the review is switched off.
- `0` or unset: the review runs normally.
- Any other value fails the check with a clear message until it is corrected.
- This meaning holds only while the review is advisory (R1). If it becomes a gate (R12), the variable
  takes the meaning `CODEX_CI_REVIEW_BYPASS` has for the Codex review: it lets the gate find a SHA-bound
  bypass attestation without the label, and never bypasses anything by itself.

Status: approved

## R11. Security review before the first run

The workflow runs next to an API key on content a pull request controls. Before it is first merged, the
`security-reviewer` agent reviews it, and any Critical or Major finding is fixed. The pull request that
adds the workflow touches gate-critical paths (`.github/`, `scripts/marketplace_ci/`), so the Codex delta
review refuses it and it needs the manual bypass attestation.

Status: approved

## R12. Later promotion to a gate (out of scope for now)

Promotion to a required gate needs a separate decision, based on measured cost and false-positive rate
from the advisory period. A gate would add a publish job, carried findings, waivers and a SHA-bound
bypass, like Codex R7, R8 and R12.

Status: proposed
