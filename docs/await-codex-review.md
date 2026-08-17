# Codex Review Status

`.github/workflows/await-codex-review.yml` makes the otherwise invisible wait for the external
`chatgpt-codex-connector[bot]` reviewer visible in a pull request's checks.

## Status

Installed, visibility-only. Its `Await Codex review` check is **not** a required status check —
see "Adoption modes" below.

## What it does

The workflow starts when a pull request is opened, reopened, marked ready for review, or updated
with a new commit (`opened`, `reopened`, `synchronize`, `ready_for_review`), skipping draft pull
requests. Its `Await Codex review` job stays in progress until GitHub reports a submitted review
from `chatgpt-codex-connector[bot]` for the pull request's current head commit, then succeeds
immediately. It fails if no matching review appears within 30 minutes (job `timeout-minutes: 33`
gives that failure message headroom over GitHub's own hard job-timeout cancellation).

This is an observation wrapper around the third-party reviewer. It does not start Codex and cannot
distinguish an active review from a queued, missed, or unavailable one.

## Workflow contract

1. Runs on `pull_request` events `opened`, `reopened`, `synchronize`, and `ready_for_review`,
   skipping the job while the pull request is a draft. Marking a draft pull request ready for
   review fires `ready_for_review`, which runs normally since the pull request is no longer a
   draft at that point.
2. Requests only `contents: read` and `pull-requests: read` permissions — no checkout, third-party
   action, custom token, or repository secret is used.
3. Uses one concurrency group per pull request (`codex-review-<PR number>`) and cancels the
   previous run when a new commit arrives.
4. Polls GitHub's pull-request reviews endpoint (`gh api .../pulls/<PR>/reviews`) every 30
   seconds.
5. Accepts only a review whose author is `chatgpt-codex-connector[bot]` and whose `commit_id`
   equals the current pull request head SHA.

## Result semantics

A successful check means only that Codex submitted a review for the current commit — it does not
mean the review was clean. A review containing findings and a clean review both satisfy this
check.

A failed check means no matching review was observed before the timeout. It does not prove Codex
failed; the review may have been delayed, omitted, or represented through a different GitHub
object.

## Adoption modes

Currently visibility-only: the check runs on every non-draft pull request but is not required by
branch protection. After observing the connector's behavior on real pull requests, the repository
can optionally make `Await Codex review` a required status check — in that mode, a missing or late
external review blocks merging after the workflow times out.

## Validation before requiring this check

Before making this check required, confirm at least one clean review and one review with findings
through GitHub's API. Both must appear in the pull-request reviews endpoint with `user.login`
equal to `chatgpt-codex-connector[bot]` and `commit_id` equal to the reviewed pull request head
SHA. If clean results are instead emitted as issue comments, reactions, or timeline events, extend
the workflow to poll that specific endpoint instead — do not match only human-facing text or an
emoji, since either may change without notice.

## Out of scope

- Detecting whether Codex has actually started processing.
- Triggering or retrying a Codex review.
- Parsing findings or turning their severity into a merge verdict.
- Configuring branch protection or repository rulesets.
- Supporting merge queues before their desired semantics are defined.
