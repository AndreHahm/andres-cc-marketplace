# Round and Dedup Rules

- [What counts as a round, and where its boundary sits](#what-counts-as-a-round-and-where-its-boundary-sits)
- [Triggered-cycle count vs. round](#triggered-cycle-count-vs-round)
- [No persisted round-counter file](#no-persisted-round-counter-file)
- [Dedup mechanism: file+line match is a candidate signal, never sufficient by itself](#dedup-mechanism-fileline-match-is-a-candidate-signal-never-sufficient-by-itself)
- [Scope-based deferral is a separate, unlimited axis from the round budget](#scope-based-deferral-is-a-separate-unlimited-axis-from-the-round-budget)
- [Hard Cap exception: Critical/Major findings never silently proceed](#hard-cap-exception-criticalmajor-findings-never-silently-proceed)
- [Severity-gate interaction](#severity-gate-interaction)
- [Already-fixed threads get resolved with commit-SHA evidence; deferred ones don't get resolved at all](#already-fixed-threads-get-resolved-with-commit-sha-evidence-deferred-ones-dont-get-resolved-at-all)
- [Why the next-round trigger doesn't poll](#why-the-next-round-trigger-doesnt-poll)
- [Worked example](#worked-example)

## What counts as a round, and where its boundary sits

A round is the window between two fix-driven pushes: round *N* opens at the push that applied round
*N-1*'s accepted fixes (round 1 opens at the PR's first push-for-review, with no prior fix), and stays
open until the *next* fix-driven push happens. Any external reviewer's findings against the current
head SHA — regardless of which tool posted them or how long that tool took relative to others — belong
to whichever round's window they arrived in. Two reviewers (e.g. Codex and Devin) finishing hours apart
against the same head SHA still belong to the same round, because no fix-driven push happened between
their two arrivals.

A `security-reviewer` (or other self-invoked) verification pass run *before* pushing a round's fix — to
confirm the fix itself doesn't introduce a new Critical/Major problem — is **not** a new round; it's
part of finishing the round already in progress, and its own findings are fixed within that same round
regardless of the cap (this stays consistent with
`.claude/rules/require-security-review-before-new-gate.md`, which mandates resolving Critical/Major
findings before a new gate ships — that mandate isn't suspended by the round budget). Without this
distinction, a thorough self-review pass could burn through the round budget before an external
reviewer even sees the diff once.

**The round counter is per-PR, not per-reviewer.** Two tools reviewing the same head SHA in the same
cycle count as one round — the cap tracks review *cycles* against the diff, not how many distinct tools
produced findings in that cycle.

**The round counter only advances on fix-driven pushes.** A SHA change from an unrelated cause — a
rebase onto `main`, an unrelated commit landing on the same branch, or an issue-draft-only commit (see
the Issue path) — does not itself open a new window; the next reviewer pass against that new SHA still
belongs to whichever round's window the PR was already in.

## Triggered-cycle count vs. round

Workflow step 8's `review_findings_min_rounds`/`review_findings_max_rounds` bound a **triggered-cycle
count** — how many times this skill has proactively triggered a review — not the "round" defined above.
The two usually track each other, but not always: a round only closes on a fix-driven push, while a
review cycle this skill triggers can come back clean, or produce only declined/filed findings, with no
fix and therefore no push. If step 8 counted by round in that case, the still-open round would never
register as "completed," and the budget check would never see a count reach `max_rounds` — step 8 would
keep re-triggering the same round indefinitely, the exact ceiling it exists to enforce.

Step 8 instead derives the triggered-cycle count from re-fetched state directly: 1 for round 1's
automatic CI trigger, plus the number of this skill's own trigger comments already posted to the PR —
top-level `gh pr comment`s whose body, verbatim, matches one of `review_findings_reviewers`'
`default_review_trigger`/`full_review_trigger` strings. This stays consistent with "No persisted
round-counter file" below: the count is re-derived from GitHub state every time, not stored anywhere,
and it advances the moment step 8 posts a trigger comment — independent of whether that cycle's review
ever produces a fix.

## No persisted round-counter file

Round classification is a judgment call made fresh at Workflow
step 2 each time findings are triaged, from re-fetched PR state (each finding's own posted timestamp,
compared against the PR's commit/push history) — never a separately maintained state file. This keeps
classification consistent with the "state is always re-fetched, never reused" discipline the whole
Workflow already follows (step 1), and avoids inventing a persistence mechanism the reviewed concept
for this skill never specified. When it's genuinely ambiguous which round a finding belongs to (e.g.
the push history is unclear about which commits were "the fix" versus incidental), treat it as the more
conservative classification — the later round — rather than guessing toward the earlier one, since a
wrongly-early round assignment risks fixing a finding that should have been filed, while a wrongly-late
one only risks filing a finding that could have been fixed (recoverable — the user can always ask for
it to be fixed anyway).

## Dedup mechanism: file+line match is a candidate signal, never sufficient by itself

A same-file/same-or-overlapping-line match narrows which earlier findings to compare against — it does
not by itself declare a repeat. Always additionally compare the finding's actual content (what defect
it describes, not just where) against each candidate before declaring a match; two distinct findings
can legitimately land on the same line (e.g. an authorization defect and a missing error-path test on
that same line), and a location-only rule would silently discard the second one.

**When content comparison is uncertain, classify the finding as new, never as a repeat** — a false
"new" costs an extra look at a real repeat; a false "repeat" silently drops a real finding, which is
the worse failure.

A finding is "new" only if it wasn't already raised (and accepted-and-fixed, or explicitly declined) in
an earlier round. A reviewer re-raising the same finding on unchanged code doesn't reset or advance the
counter for that specific finding.

## Scope-based deferral is a separate, unlimited axis from the round budget

Scope-based deferral (too large to fix in-session) is one of the three named exceptions that route a
finding to the Issue path regardless of round — see `references/settings-and-round-budget.md`'s
"Issue-filing is the exception" section (Exception 3) for the full rule and judgment guidance. The
short version: it can happen in any round, including round 1, and never consumes a round-budget slot —
the round budget only governs how many review *cycles* this skill proactively triggers, not how many
oversized findings get punted to issues along the way.

## Hard Cap exception: Critical/Major findings never silently proceed

Filing an issue instead of fixing never applies to a Critical or Major finding on the strength of the
Issue path alone. A Critical/Major finding may still end up *filed* as an issue — via one of the three
named exceptions in `references/settings-and-round-budget.md`, or via `review_findings_generate_issues:
true` once the round budget is exhausted — but the PR does not proceed to merge on the strength of that
filing alone. Filing the issue and reporting it (Workflow step 7) is not itself an acceptance decision;
merging with a known, unfixed Critical/Major finding requires a separate, explicit `AskUserQuestion`
confirming the risk is accepted, before `merge-pr` is invoked. This invariant survives this skill's
round-budget redesign unchanged — only *which* findings can reach the Issue path in the first place has
changed (the three named exceptions, or budget exhaustion), not what happens once a finding is there.

Severity here means the reviewer's own stated severity (Codex P1/Critical, Devin's equivalent, a human
reviewer's explicit "this blocks merge") — a live re-read of the finding at classification time
(Workflow step 2), not a cached judgment carried over from an earlier round.

## Severity-gate interaction

`review_findings_severity_gate` (see SKILL.md's Settings section) is orthogonal to the Hard Cap
exception above: regardless of `true`/`false`, a Critical/Major finding never gets silently
deferred-and-merged — that protection doesn't depend on this setting. The gate never overrides an
explicit instruction: if the user or a human reviewer explicitly asks for a specific Minor/nit finding
to be fixed, that instruction always wins over the gate's default decline — the setting only changes
the *automatic* default for findings nobody has separately weighed in on.

## Already-fixed threads get resolved with commit-SHA evidence; deferred ones don't get resolved at all

Resolving a thread asserts "this is handled"; a deferred finding isn't handled, it's redirected —
resolving it anyway would misrepresent the state to anyone reading the PR later. Deferred findings
still get a paper trail on the PR, not just an issue: every deferred finding's review thread gets a
reply pointing at the new issue number, even though the thread itself is left unresolved — an issue
filed with no trace on the PR reads as the finding being silently dropped.

## Why the next-round trigger doesn't poll

Workflow step 8 posts a trigger comment (`gh pr comment`) to start the next round, then ends this
skill's own run for that round rather than waiting for the review to actually post back. This is a
deliberate difference from `codex-review-recovery`, which does poll (up to 10 times, 30 seconds apart)
after posting its own retry comment — that skill can poll because it's watching one specific,
already-known-fast GitHub check (`Await Codex review`, a ~30-minute timeout, queried directly via the
Checks API). This skill's own trigger step has no equivalent uniform signal to poll: CodeRabbit and
Devin have no comparable named check this skill could query the same way, review completion time is
unbounded (unlike a check with a fixed timeout), and building three separate polling mechanisms — one
per reviewer, each with its own unknown completion signal — for a skill whose actual job is triage, not
orchestration, isn't worth the complexity. Re-invoking this skill once a review has actually posted is
the mechanism instead — the same "state is always re-fetched, never persisted" discipline this file's
"No persisted round-counter file" section already applies to round classification applies here too:
there's no state file recording "round 2 was triggered at time X, expect a response by time Y," just a
fresh re-fetch of whatever's actually posted when the skill runs next.

This is also why the reviewer/mode choice (Workflow step 8) is remembered only for the lifetime of the
current conversation, not persisted to disk: a genuinely new session invoking this skill for what turns
out to be round 3 has no way to know what was decided for round 2 without a persistence mechanism this
skill deliberately doesn't have, so it asks again rather than guessing or silently reusing a stale
default.

## Worked example

The sequence that originally produced this policy (a real PR, condensed) — from before this skill's
round-budget redesign, when the cap was a fixed two rounds and round 3+ automatically became an issue:

| Round | Trigger | Findings | Disposition |
|---|---|---|---|
| 1 | Initial two-reviewer round after CI went green | 3 | Fixed, re-committed, re-pushed |
| *(within round 1)* | `security-reviewer` verification pass on round 1's own fix | 1 Critical + 3 Major | Fixed — same round, not a new one |
| 2 | Re-review of round 1's pushed fix | 2 | Fixed, re-committed, re-pushed |
| 3 | Re-review of round 2's pushed fix | 1 | Not fixed — filed as an issue, thread replied-to but left unresolved |

Under the current round-budget design (default `min_rounds: 1`, `max_rounds: 3`,
`generate_issues: false`), the same sequence plays out differently at round 3: the round 3 finding
still gets **fixed** (it's within the `max_rounds` budget, and none of the three named exceptions in
`references/settings-and-round-budget.md` apply to it) rather than automatically filed. A finding would
only be filed today if it matched one of the three named exceptions, or if it arrived in a round beyond
`max_rounds` with `generate_issues: true` set.
