# Codex Review Status

`.github/workflows/await-codex-review.yml` makes the otherwise invisible wait for the external
`chatgpt-codex-connector[bot]` reviewer visible in a pull request's checks.

## Status

Installed, visibility-only. Its `Await Codex review` check is **not** a required status check —
see "Adoption modes" below.

## What it does

The workflow starts only when Codex's own auto-review connector would actually be asked to look at
the pull request: the pull request is opened non-draft (`opened`), a draft pull request is marked
ready for review (`ready_for_review`), or someone posts an explicit `@codex review` comment
(`issue_comment`) — never on a plain `synchronize` push by itself, since the connector no longer
auto-reviews every push (see "Trigger scope" below for why this changed). Its `Await Codex review`
job stays in progress until one of three things happens: GitHub reports a submitted review from
`chatgpt-codex-connector[bot]` for the pull request's current head commit (a commit-exact signal);
the connector posts a plain top-level PR comment containing a `Reviewed commit: <sha>` reference to
the current head, shortly after the label text (its response to a re-triggered round, which has
been observed to come back as a comment rather than a submitted review — confirmed live,
2026-08-30, see "Result semantics" below); or the connector posts a `+1` reaction on the pull
request at or after this push (its no-findings signal — confirmed live, 2026-08-17: a clean review
produces no review object and no commit-scoped signal at all, only an issue-level reaction with
**no commit ID**, so this third path is a best-effort match, not a commit-exact one — see "Result
semantics" below). It fails if none of the three appears within 30 minutes (job
`timeout-minutes: 33` gives that failure message headroom over GitHub's own hard job-timeout
cancellation).

This is an observation wrapper around the third-party reviewer. It does not start Codex and cannot
distinguish an active review from a queued, missed, or unavailable one.

## Workflow contract

1. Runs on `pull_request` events `opened` and `ready_for_review`, and on `issue_comment` events
   (`created`) whose body contains `@codex review` and whose issue is actually a pull request
   (`github.event.issue.pull_request` present) — skipping the job while the pull request is a
   draft (checked directly from the event for `pull_request`; re-fetched live via `gh api` for
   `issue_comment`, since that event carries no pull-request sub-object). A plain `synchronize`
   push is deliberately **not** a trigger — see "Trigger scope" below.
2. Requests `contents: read`, `pull-requests: read`, `issues: read` (the last is needed to read the
   connector's comments, its no-findings reaction, and to read PR state for an `issue_comment`
   trigger), and `checks: write` (needed for point 6 below) — no checkout, third-party action,
   custom token, or repository secret is used.
3. Uses one concurrency group per pull request (`codex-review-<PR number>`, plus a run-id-unique
   suffix for an `issue_comment` event the job's own `if:` will skip — see below) and cancels a
   previous still-running instance of this workflow for the same pull request when a new triggering
   event (not just any new commit — see point 1) arrives.
4. Polls three signals every 30 seconds, all fully paginated: GitHub's pull-request reviews
   endpoint (`gh api .../pulls/<PR>/reviews`), the pull request's own comments endpoint
   (`gh api .../issues/<PR>/comments`), and the pull request's reactions endpoint
   (`gh api .../issues/<PR>/reactions`).
5. Accepts a review whose author is `chatgpt-codex-connector[bot]` and whose `commit_id` equals the
   current pull request head SHA (commit-exact); or a PR comment from `chatgpt-codex-connector[bot]`
   posted at or after the triggering event's own timestamp whose body contains `Reviewed commit`
   with the current head SHA's first 7 hex characters appearing within 20 characters of that label
   (a bounded-adjacency match, not a bare co-occurrence check — two independent substring checks
   would also accept a body whose label refers to an *earlier* commit while the current head SHA
   happens to appear elsewhere in the same comment, e.g. a quoted diff hunk or permalink); or a `+1`
   reaction from `chatgpt-codex-connector[bot]` whose `created_at` is at or after the triggering
   event's own timestamp. The triggering event's own timestamp is `pull_request.updated_at` for a
   `pull_request` event, or the comment's own `created_at` for an `issue_comment` event — captured
   once, at trigger time, before this job even starts. Anchoring every signal to the event's own
   timestamp (rather than a snapshot taken once this job happens to run) means a comment or reaction
   the connector posts before this job starts polling still counts, while a stale one from an
   earlier commit still doesn't. The resolved head SHA is validated as a hex commit SHA before any
   of this runs — an empty or malformed value would otherwise make the comment-signal's substring
   checks vacuously true for any comment mentioning the label at all.
6. For an `issue_comment` trigger, explicitly creates and later finalizes a check-run against the
   pull request's real head SHA via the Checks API (`POST`/`PATCH .../check-runs`), rather than
   relying on the job's own implicit status. `issue_comment` events check out and report their
   `GITHUB_SHA`/`GITHUB_REF` against the *default branch's* latest commit, not the pull request's
   (confirmed against GitHub's own docs) — without this, the job's own status would attach to the
   wrong commit and never appear in `gh pr checks` for this pull request at all. Not needed for the
   `pull_request` path, where `GITHUB_SHA` already correctly equals the pull request's head. A
   check-run created this way is standalone — it has no associated workflow run, so a tool deriving
   a "workflow" label from the check suite (e.g. `gh pr checks`'s own `workflow` field) won't show
   one for it, unlike the `pull_request` path's own check. Best-effort only: if this job is
   cancelled (a newer trigger superseding it via point 7 below, or the hard `timeout-minutes` cutoff)
   before it reaches one of its own normal exits, an `EXIT`/`INT`/`TERM` trap attempts to finalize the
   check-run to `cancelled` rather than leaving it stuck `in_progress` forever — not guaranteed, since
   it races GitHub's own short cancellation grace period.
7. **Any PR comment, not just an `@codex review` one, creates a workflow run in the same
   `codex-review-<PR number>` group** — workflow-level concurrency is evaluated at run-creation
   time, before the job's own `if:` in point 1 above ever runs, so an unrelated comment would
   otherwise cancel a legitimately in-progress wait via `cancel-in-progress`, only to have its own
   job then skipped. The concurrency group (point 3) isolates this: a comment the job's own `if:`
   is about to skip gets a unique, one-off group suffix (this run's own `github.run_id`) instead of
   sharing the real group, so it can never collide with — or cancel — an actual wait.

## Trigger scope

Codex's own auto-review connector was originally configured to re-review on every push, so this
workflow originally mirrored that with a `synchronize` trigger. The connector's own trigger
configuration has since changed (2026-08-21): it now auto-reviews only when a pull request is
opened non-draft, or a draft pull request is marked ready for review — a later round needs an
explicit `@codex review` comment to re-trigger a review. `synchronize` firing this workflow on
every subsequent push produced a guaranteed ~30-minute timeout on a check nobody could act on
without knowing to manually comment `@codex review` first. The trigger list above was narrowed to
match the connector's actual current re-trigger conditions, plus the new `issue_comment` trigger so
that manual `@codex review` comment itself starts a fresh wait.

`reopened` was dropped along with `synchronize` (not just narrowed to the other two) — the
connector's own documented triggers are "opening a PR, marking a draft ready, or [the `@codex
review`] comment" (see `codex-review-recovery`'s SKILL.md), which does not include reopening a
closed pull request.

**Not decided by this change:** whether the `issue_comment` trigger should also filter by comment
author (e.g. only PR collaborators, not any commenter) — left unrestricted for now, matching this
check's existing visibility-only, non-required status. Revisit if that turns out to cause noise.

## Result semantics

A successful check means one of three things, with different confidence:

- **Review-object match (commit-exact, high confidence):** Codex submitted a review — clean or
  with findings — whose `commit_id` equals the current head SHA. This is a certain match.
- **Comment match (SHA-referenced, moderate confidence):** Codex posted a plain top-level PR
  comment, at or after this push's own timestamp, containing a `Reviewed commit` label with the
  current head SHA's first 7 hex characters within 20 characters of *some* occurrence of that
  label — checked across every occurrence of both in the body, not just the first of each. (An
  earlier version of this check compared only the first occurrence of each, which could
  false-negative on a comment that legitimately mentions the label text once in prose or a quoted
  diff before its real, adjacent commit-footer pair later in the body — found live by Codex's own
  automated review of this exact change, on this exact file, whose own comments and this doc's own
  prose now repeat the literal label text multiple times.) This references the correct commit by
  name, but is a text match against a third-party bot's own free-form comment formatting rather
  than a structured API field — less certain than the review-object match, but meaningfully
  stronger than the reaction match below, since it actually names the commit. **Added 2026-08-30**
  after this exact gap caused a real, extended false-negative (see below): Codex's response to a
  re-triggered round (an `@codex review` comment, as opposed to the pull request's own first,
  automatic review) came back as a plain comment rather than a submitted review object at all,
  leaving only the reaction-match signal below to catch it — and that signal failed to, for the
  entire 30-minute window, on data later confirmed to satisfy its own matching condition.
- **Reaction match (best-effort, not commit-exact):** Codex posted a `+1` reaction at or after
  this push's own timestamp. This does **not** prove the reaction was for the current commit
  specifically — GitHub reactions carry no commit ID at all, which is a structural limitation of
  the API, not a gap a smarter client-side heuristic can close. **Confirmed live, 2026-08-17**
  (`chatgpt-codex-connector[bot]`'s own PR review, PR #49): if a clean review of an earlier commit
  is still in flight when a newer commit is pushed, the earlier commit's late `+1` can land after
  the newer commit's own event timestamp and be misattributed to it. The check accepts this
  tradeoff for visibility-only use; it is a real reason **not** to promote this check to a
  required status check without accepting that occasional false positive.

**Confirmed live, 2026-08-30, PR #250:** a re-triggered round's `+1` reaction — later verified,
after the fact, to satisfy the reaction-match condition above exactly (`created_at` at or after the
triggering comment's own timestamp, correct author) — was never observed across 61 consecutive
polls spanning the full 30-minute window, even though an interactive `gh api` call against the same
endpoint saw it immediately, several minutes before the job itself gave up. The job's own resolved
values (head SHA, event timestamp) and matching logic were independently replayed against the live
data afterward and found correct; the check still failed. This points at a GitHub-side read
visibility gap specific to the polling job's own call path, not a logic defect in this workflow —
but since the connector's response to the same re-trigger also included a comment naming the commit
directly, adding the comment-match signal above gives a second, independent path to the same
result, so a future occurrence of this same visibility gap doesn't depend on the reaction endpoint
alone.

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

A distinct failure mode from all three signals above, confirmed live on PR #50 (2026-08-17): Codex
finished the review on its own dashboard (chatgpt.com/codex) and the connector never posted a review
object, a matching comment, *or* a `+1` reaction to GitHub within the 30-minute window — a GitHub-side
write-back gap, not a delay in any signal this workflow polls for. The check fails as designed in this
case; nothing here is a bug.

This workflow deliberately does not attempt to recover from that gap itself (see "Out of scope" below —
detecting or retrying is not this job's responsibility). Recovery is a separate, human-gated skill,
`Skill(git-kit:codex-review-recovery)`: it asks the human to confirm on Codex's own dashboard that the
review actually finished — the one piece of information nothing running inside this repository can see —
then posts an `@codex review` comment (the connector's own documented retry trigger). That comment now
also re-triggers this workflow directly via its `issue_comment` trigger (see "Trigger scope" above), and
since the resulting check-run is explicitly attached to the pull request's own head SHA (point 6 above),
the skill polls the Checks API directly for that commit — not `gh pr checks`, since a standalone
Checks-API-created check-run has no associated workflow run for that CLI's own `workflow` field to match
against — rather than hunting down a separate workflow run or manually rerunning the old, already-failed
one. See that skill's own SKILL.md for the exact procedure.

**Do not react with a manual 👍 as a workaround.** The reaction-match check filters strictly on
`user.login == "chatgpt-codex-connector[bot]"` — a reaction from any other account, including the PR
author, is not something a human can spoof from the GitHub UI, by design.

## Adoption modes

Currently visibility-only: the check runs per the trigger scope above (opened non-draft, marked
ready for review, or an `@codex review` comment) but is not required by branch protection. Making `Await Codex review` a required status check is a real option — a
missing or late external review would block merging after the workflow times out — but it comes
with a real, structural tradeoff, not just a pending-validation item; see "Validation before
requiring this check" below before deciding.

## Validation before requiring this check

Confirmed live, 2026-08-17: a review with findings appears in the pull-request reviews endpoint
with `user.login` equal to `chatgpt-codex-connector[bot]` and `commit_id` equal to the reviewed
pull request head SHA — a commit-exact, reliable signal. A clean review instead produces no
review object at all — only a `+1` reaction on the pull request issue, with no commit correlation
GitHub's API can provide. The workflow polls three signals (see "Workflow contract" above); the
comment-match signal names the commit directly but is a text match against free-form bot
formatting rather than a structured field, and the reaction path can only ever be a best-effort
match, per "Result semantics" above — this is a permanent characteristic of using reactions this
way, not something further observation will resolve.

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
