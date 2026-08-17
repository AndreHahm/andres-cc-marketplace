# Codex Review Status

`.github/workflows/await-codex-review.yml` makes the otherwise invisible wait for the external
`chatgpt-codex-connector[bot]` reviewer visible in a pull request's checks.

## Status

Installed, visibility-only. Its `Await Codex review` check is **not** a required status check —
see "Adoption modes" below.

## What it does

The workflow starts when a pull request is opened, reopened, marked ready for review, or updated
with a new commit (`opened`, `reopened`, `synchronize`, `ready_for_review`), skipping draft pull
requests. Its `Await Codex review` job stays in progress until either GitHub reports a submitted
review from `chatgpt-codex-connector[bot]` for the pull request's current head commit, or the
connector posts a fresh `+1` reaction on the pull request (its no-findings signal — confirmed
live, 2026-08-17: a clean review produces no review object and no commit-scoped signal at all,
only an issue-level reaction). It fails if neither appears within 30 minutes (job
`timeout-minutes: 33` gives that failure message headroom over GitHub's own hard job-timeout
cancellation).

This is an observation wrapper around the third-party reviewer. It does not start Codex and cannot
distinguish an active review from a queued, missed, or unavailable one.

## Workflow contract

1. Runs on `pull_request` events `opened`, `reopened`, `synchronize`, and `ready_for_review`,
   skipping the job while the pull request is a draft. Marking a draft pull request ready for
   review fires `ready_for_review`, which runs normally since the pull request is no longer a
   draft at that point.
2. Requests only `contents: read`, `pull-requests: read`, and `issues: read` permissions (the last
   is needed to read the connector's no-findings reaction — see below) — no checkout, third-party
   action, custom token, or repository secret is used.
3. Uses one concurrency group per pull request (`codex-review-<PR number>`) and cancels the
   previous run when a new commit arrives.
4. Before polling, snapshots the connector's existing `+1` reaction IDs on the pull request issue,
   so a pre-existing reaction from an earlier commit can't be mistaken for a fresh one.
5. Polls two signals every 30 seconds: GitHub's pull-request reviews endpoint
   (`gh api .../pulls/<PR>/reviews`), and the pull request's reactions endpoint
   (`gh api .../issues/<PR>/reactions`).
6. Accepts either a review whose author is `chatgpt-codex-connector[bot]` and whose `commit_id`
   equals the current pull request head SHA, or a `+1` reaction from `chatgpt-codex-connector[bot]`
   whose ID wasn't present in step 4's baseline snapshot.

## Result semantics

A successful check means only that Codex submitted a review for the current commit — it does not
mean the review was clean. A review containing findings and a clean review both satisfy this
check.

A failed check means no matching review or fresh reaction was observed before the timeout. It does
not prove Codex failed; the review may have been delayed, omitted, or represented through a
different GitHub object.

**Known limitation (unverified):** the new-reaction snapshot approach can't distinguish "still
clean" from "already counted" if the connector reuses the same reaction across multiple
consecutive clean pushes without ever removing and re-adding it — GitHub reactions are idempotent
per (user, content, target), and it's unconfirmed whether re-reacting on a second clean commit
produces a new reaction ID or silently no-ops on the existing one. This has only been observed
live for a single clean push so far (2026-08-17); a second consecutive clean push on the same PR
would confirm or disprove this concern.

## Adoption modes

Currently visibility-only: the check runs on every non-draft pull request but is not required by
branch protection. After observing the connector's behavior on real pull requests, the repository
can optionally make `Await Codex review` a required status check — in that mode, a missing or late
external review blocks merging after the workflow times out.

## Validation before requiring this check

Confirmed live, 2026-08-17: a review with findings appears in the pull-request reviews endpoint
with `user.login` equal to `chatgpt-codex-connector[bot]` and `commit_id` equal to the reviewed
pull request head SHA; a clean review instead produces no review object at all — only a `+1`
reaction on the pull request issue, with no commit correlation. The workflow now polls both
signals (see "Workflow contract" above).

Before making this check required, still confirm the known limitation above: push two consecutive
clean commits to the same open pull request and verify the check succeeds on both, not just the
first.

## Out of scope

- Detecting whether Codex has actually started processing.
- Triggering or retrying a Codex review.
- Parsing findings or turning their severity into a merge verdict.
- Configuring branch protection or repository rulesets.
- Supporting merge queues before their desired semantics are defined.
