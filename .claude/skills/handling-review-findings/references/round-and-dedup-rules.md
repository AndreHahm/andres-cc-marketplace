# Round and Dedup Rules

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
findings before a new gate ships — that mandate isn't suspended by the round cap). Without this
distinction, a thorough self-review pass could burn through the two-fix budget before an external
reviewer even sees the diff once.

**The round counter is per-PR, not per-reviewer.** Two tools reviewing the same head SHA in the same
cycle count as one round — the cap tracks review *cycles* against the diff, not how many distinct tools
produced findings in that cycle.

**The round counter only advances on fix-driven pushes.** A SHA change from an unrelated cause — a
rebase onto `main`, an unrelated commit landing on the same branch, or an issue-draft-only commit (see
the Issue path) — does not itself open a new window; the next reviewer pass against that new SHA still
belongs to whichever round's window the PR was already in.

**No persisted round-counter file.** Round classification is a judgment call made fresh at Workflow
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

## Scope-based deferral is a separate, unlimited axis from the round cap

A finding can also be deferred to an issue purely for being too large to fix in-session (e.g. "needs
real data-flow analysis, not a text-only fix") — this judgment can happen in any round, including round
1, and does not consume one of the two fix-round slots. The round cap only governs how many review
*cycles* get chased across pushes; it doesn't cap how many oversized findings get punted to issues along
the way. A scope-deferred finding follows the same Issue path (Workflow step 5) as a round-3+ finding
regardless of which round it was raised in.

## Hard Cap exception: Critical/Major findings never silently proceed

The round cap's auto-file-and-proceed behavior never applies to a Critical or Major finding, in any
round. A Critical/Major finding may still be *filed* as an issue in round 3+ rather than fixed — that
part of the cap is unchanged — but the PR does not proceed to merge on the strength of the round cap
alone. Filing the issue and reporting it (Workflow step 7) is not itself an acceptance decision; merging
with a known, unfixed Critical/Major finding requires a separate, explicit `AskUserQuestion` confirming
the risk is accepted, before `merge-pr` is invoked.

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

## Worked example

The sequence that originally produced this policy (a real PR, condensed):

| Round | Trigger | Findings | Disposition |
|---|---|---|---|
| 1 | Initial two-reviewer round after CI went green | 3 | Fixed, re-committed, re-pushed |
| *(within round 1)* | `security-reviewer` verification pass on round 1's own fix | 1 Critical + 3 Major | Fixed — same round, not a new one |
| 2 | Re-review of round 1's pushed fix | 2 | Fixed, re-committed, re-pushed |
| 3 | Re-review of round 2's pushed fix | 1 | Not fixed — filed as an issue, thread replied-to but left unresolved |
