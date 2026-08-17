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
review from `chatgpt-codex-connector[bot]` for the pull request's current head commit (a
commit-exact signal), or the connector posts a `+1` reaction on the pull request at or after this
push (its no-findings signal — confirmed live, 2026-08-17: a clean review produces no review
object and no commit-scoped signal at all, only an issue-level reaction with **no commit ID**,
so this second path is a best-effort match, not a commit-exact one — see "Result semantics"
below). It fails if neither appears within 30 minutes (job `timeout-minutes: 33` gives that
failure message headroom over GitHub's own hard job-timeout cancellation).

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
4. Polls two signals every 30 seconds, both fully paginated: GitHub's pull-request reviews
   endpoint (`gh api .../pulls/<PR>/reviews`), and the pull request's reactions endpoint
   (`gh api .../issues/<PR>/reactions`).
5. Accepts either a review whose author is `chatgpt-codex-connector[bot]` and whose `commit_id`
   equals the current pull request head SHA, or a `+1` reaction from `chatgpt-codex-connector[bot]`
   whose `created_at` is at or after the triggering event's own `pull_request.updated_at`
   timestamp — captured once, at trigger time, before this job even starts. Anchoring to the
   event's own timestamp (rather than a snapshot taken once this job happens to run) means a
   reaction the connector posts before this job starts polling still counts, while a stale
   reaction from an earlier commit still doesn't.

## Result semantics

A successful check means one of two things, with different confidence:

- **Review-object match (commit-exact, high confidence):** Codex submitted a review — clean or
  with findings — whose `commit_id` equals the current head SHA. This is a certain match.
- **Reaction match (best-effort, not commit-exact):** Codex posted a `+1` reaction at or after
  this push's own timestamp. This does **not** prove the reaction was for the current commit
  specifically — GitHub reactions carry no commit ID at all, which is a structural limitation of
  the API, not a gap a smarter client-side heuristic can close. **Confirmed live, 2026-08-17**
  (`chatgpt-codex-connector[bot]`'s own PR review, PR #49): if a clean review of an earlier commit
  is still in flight when a newer commit is pushed, the earlier commit's late `+1` can land after
  the newer commit's own event timestamp and be misattributed to it. The check accepts this
  tradeoff for visibility-only use; it is a real reason **not** to promote this check to a
  required status check without accepting that occasional false positive.

A failed check means no matching review or reaction was observed before the timeout. It does not
prove Codex failed; the review may have been delayed, omitted, or represented through a different
GitHub object.

**Known limitation (partially confirmed):** the reaction match also can't distinguish "still
clean" from "already counted" if the connector reuses the same reaction across multiple clean
pushes without ever removing and re-adding it — GitHub reactions are idempotent per (user,
content, target), so this would only be safe if re-reacting refreshes `created_at` rather than
silently no-oping on an existing reaction.

Observed live on PR #49, 2026-08-17: commit `7494d53`'s clean pass produced reaction ID
`457464461` at `16:58:19Z`; two intervening commits (`d5096f3`, `6ab1689`) each got a
findings-review instead of a reaction; commit `b24a47b`'s later clean pass then produced a
**different** reaction ID (`457502472`) at a **later** timestamp (`17:28:17Z`), with the first
reaction no longer present on the issue at all. This confirms the connector removes and re-adds
its `+1` rather than leaving a stale one in place across separate clean passes — but since a
findings-review happened in between rather than two genuinely back-to-back clean pushes, it
doesn't yet rule out a narrower edge case: two clean pushes in a row with *no* intervening
findings-review event. That specific scenario still hasn't been observed live.

## Recovering a stuck check

A distinct failure mode from both signals above, confirmed live on PR #50 (2026-08-17): Codex finished
the review on its own dashboard (chatgpt.com/codex) and the connector never posted a review object *or*
a `+1` reaction to GitHub within the 30-minute window — a GitHub-side write-back gap, not a delay in
either signal this workflow polls for. The check fails as designed in this case; nothing here is a bug.

This workflow deliberately does not attempt to recover from that gap itself (see "Out of scope" below —
detecting or retrying is not this job's responsibility). Recovery is a separate, human-gated skill,
`Skill(git-kit:codex-review-recovery)`: it asks the human to confirm on Codex's own dashboard that the
review actually finished — the one piece of information nothing running inside this repository can see —
then posts an `@codex review` comment (the connector's own documented retry trigger) and re-runs the
failed check, since posting the comment alone does not itself re-trigger this workflow (its `on:` trigger
list has no `issue_comment` entry). See that skill's own SKILL.md for the exact procedure.

**Do not react with a manual 👍 as a workaround.** The reaction-match check filters strictly on
`user.login == "chatgpt-codex-connector[bot]"` — a reaction from any other account, including the PR
author, is not something a human can spoof from the GitHub UI, by design.

## Adoption modes

Currently visibility-only: the check runs on every non-draft pull request but is not required by
branch protection. Making `Await Codex review` a required status check is a real option — a
missing or late external review would block merging after the workflow times out — but it comes
with a real, structural tradeoff, not just a pending-validation item; see "Validation before
requiring this check" below before deciding.

## Validation before requiring this check

Confirmed live, 2026-08-17: a review with findings appears in the pull-request reviews endpoint
with `user.login` equal to `chatgpt-codex-connector[bot]` and `commit_id` equal to the reviewed
pull request head SHA — a commit-exact, reliable signal. A clean review instead produces no
review object at all — only a `+1` reaction on the pull request issue, with no commit correlation
GitHub's API can provide. The workflow polls both signals (see "Workflow contract" above), but the
reaction path can only ever be a best-effort match, per "Result semantics" above — this is a
permanent characteristic of using reactions this way, not something further observation will
resolve.

Before making this check required, weigh that tradeoff deliberately: a required check inherits the
reaction path's occasional false-positive risk (a clean review of a stale commit misattributed to
the current head), so "required" mode should either accept that risk explicitly, or the workflow
would need to drop the reaction path and accept that a genuinely clean PR always times out instead.
Separately, the known limitation above is now partially confirmed rather than fully open: still
verify the narrower remaining case — two clean commits pushed back-to-back, with no intervening
findings-review in between — succeeds on both, not just the first.

## Out of scope

- Detecting whether Codex has actually started processing.
- Triggering or retrying a Codex review — see "Recovering a stuck check" above for the separate,
  human-gated skill that handles this deliberately, rather than folding it into this workflow.
- Parsing findings or turning their severity into a merge verdict.
- Configuring branch protection or repository rulesets.
- Supporting merge queues before their desired semantics are defined.
