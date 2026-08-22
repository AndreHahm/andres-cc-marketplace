# Development History

This file is the build-time audit trail for this skill's round-budget redesign and the three rounds of
live GitHub review that followed — eval run records, the security-review passes, and the specific
findings each review round caught and fixed. It exists so SKILL.md's own "Testing & Validation" section
can stay a validation checklist (current activation triggers, current test-suite pointer, current pass
rate) rather than a growing changelog. Nothing here is instructional for a live triage run — read
SKILL.md's own Workflow and this skill's other `references/*.md` files for that.

## Eval run records

**Iteration 2 (2026-08-22, Full Pipeline):** `skill-tester` ran all 17 evals defined at that point: 100%
with_skill pass rate vs. 86.6% baseline (+13.4 percentage points); see
`evals/handling-review-findings/workspace/iteration-2/benchmark.json` for the full per-eval breakdown.
The discrimination margin is smaller than iteration 1's (+28.1 points) mostly because several scenario
prompts are detailed enough that a careful general-purpose baseline reconstructs the right answer by
close reading alone, without needing the skill's specific rules — a real eval-design weakness worth
tightening in a future iteration, not a sign the skill itself regressed. Three evals show a genuine,
skill-attributable gap baseline can't close: eval 9 (severity-gate decline — baseline never states the
thread is left unresolved), eval 14 (baseline asks one single-select question with no review-profile
question at all, and guesses Devin's trigger string wrong — 0.25 vs. with_skill's 1.0, the widest margin
in the suite), and eval 12 (baseline incorrectly resolves both reviewers' threads after filing an issue,
contradicting the "deferred findings are never resolved" rule).

Eval 14 also surfaced a real skill bug caught before shipping: Workflow step 8's original wording
implied offering every reviewer's default *and* full mode in one multi-select, which exceeds
`AskUserQuestion`'s own `options` cap (`maxItems: 4`, verified against its schema) for 3 reviewers —
first fixed by showing only each reviewer's default trigger as its option and accepting a full-review
request via `AskUserQuestion`'s free-form "Other" text instead of a second pre-listed option, the same
workaround the eval's own with_skill run independently designed. Eval 14's own `with_skill` grading
record still marked that correctly-designed output down against the retired assertion until a round-1
`chatgpt-codex-connector` review finding on PR #101 caught the mismatch (2026-08-22) — corrected the
assertion and grading record to match the then-shipped design.

That free-form-"Other" design was itself superseded the same day, on direct user feedback, by the
current **two-question** design (Question 1: reviewer multi-select; Question 2: default-vs-full review
profile, single-select) — a cleaner way to stay within the 4-option cap without pushing the full-review
request into unstructured free text. Eval 14 was rewritten a second time to test the two-question
design and re-run; eval 15's `expected_output` had a separate class of staleness (asserting
re-validation of an already-confirmed trigger string that Workflow step 8 explicitly says not to
re-validate) and was corrected the same pass, with no change to its pass rate.

The old iteration-1 result (100% vs. 71.9%, built on the retired "2-round cap, round 3+ always becomes
an issue" policy) is superseded and no longer reflects this skill's current routing logic; see
`evals/handling-review-findings/workspace/iteration-1/benchmark.json` for that historical breakdown
only. The iteration-1 supplementary pressure-test variant is stale for the same reason (built on the
old eval 3's premise) and still needs a fresh run against the current eval 3 — tracked in `evals.json`'s
own `supplementary_pressure_test` field as an open item, not re-run since.

**Iteration 3 (2026-08-22, Quick Workflow, with_skill only):** evals 18-20, written for the round-2
GitHub-review fixes (the batch-marker mechanism, multi-reviewer batch-counts-as-one-cycle, and Question
1 omitting its stop option below `min_rounds`) — 3/3 assertions passed on all three
(`evals/handling-review-findings/workspace/iteration-3/`). No baseline comparison was run (Quick
Workflow only checks the with_skill configuration); these three scenarios require reading the skill's
own documented marker/batch mechanics to answer correctly at all, so a baseline delta would likely be
large, but that hasn't been measured.

## Security review passes

The `guard-raw-pr-review.sh` hook extension this skill required historically (two new `gh api` guard
branches) went through a live `security-reviewer` pass on 2026-08-21, per
`.claude/rules/require-security-review-before-new-gate.md` — it found and fixed 2 Major bypass gaps (a
positional-flag assumption, and a file-supplied GraphQL body that could pass through unguarded); both
fixes were re-verified against the reviewer's own bypass commands as regression cases before the hook
change was committed.

This redesign's own new `gh pr comment` call site went through two more live `security-reviewer` passes
on 2026-08-22: the first found 1 Critical (an unvalidated, settings-derived trigger string reaching
shell interpolation) and 2 Major findings (a reviewer's trigger string not required to match its own
name, and a missing `Bash(git ls-files:*)` grant needed to actually run the tracked-vs-local
trust-boundary check); a follow-up verification pass confirmed the Critical and one Major were fully
closed but found the fix for the name-match Major was incomplete in two ways — the tracked-vs-local
rejection wasn't actually enforced at Workflow step 8's own point of use (only pointed at from a
reference file), and a plain substring match would still have accepted a lookalike handle like
`@codex-evil` for a `codex` entry — both are fixed in Workflow step 8's current three-step validation
order (tracked-ness gate, then anchored regex, then handle-token match) and
`references/settings-and-round-budget.md`'s trust-boundary section. One pre-existing, shared residual
the first pass surfaced (`guard-raw-pr-review.sh` allows unconditionally when its own
`git rev-parse --git-dir` check finds no repository, before the subcommand match even runs) was left
unfixed here — it predates this redesign, affects every skill that hook guards, and reordering it
deserves its own dedicated review rather than a side effect of this narrower round-budget change; it's
now recorded in that hook's own header comment as a disclosed residual rather than left as an
undocumented gap.

## Round-1 GitHub review findings on PR #101 (2026-08-22)

The automated round-1 review that ran when this PR went ready-for-review found two more real gaps
neither prior `security-reviewer` pass caught, both fixed the same round:

1. A reviewer entry's `name` field was substituted into the handle-token regex (`^<name>[a-z0-9]*$`)
   and a scratchpad filename (`trigger-<name>.txt`) with no validation of its own — an unvalidated
   `name` could corrupt the regex or write outside the intended scratchpad directory; fixed by
   requiring `name` to match `^[a-z][a-z0-9_-]{0,31}$` before it's used anywhere, excluding the
   reviewer entirely otherwise.
2. The round-budget check conflated the fix-driven-push "round" definition with the triggered-cycle
   count `min_rounds`/`max_rounds` actually bound — a cycle that comes back clean or produces only
   declined/filed findings never closes a round, so counting by round could let step 8 re-trigger the
   same still-open round indefinitely without ever reaching `max_rounds`; fixed by deriving the
   triggered-cycle count from re-fetched trigger-comment history instead (see "Triggered-cycle count
   vs. round" in `references/round-and-dedup-rules.md`).

Two eval-integrity findings from the same round are covered above under the eval run records (eval
14/15's stale grading records). One Devin finding (`references/settings-and-round-budget.md`
overclaiming that a fourth reviewer needs no special handling) was also corrected to state the
trigger-ask's real 4-option ceiling accurately.

## Round-2 GitHub review findings on PR #101 (2026-08-22)

The automated round-2 review that ran after round 1's fixes were pushed found that round 1's own
triggered-cycle-count fix was itself incomplete — Devin and Codex independently flagged the same root
cause: a raw verbatim match against a reviewer's trigger string can't tell this skill's own proactive
trigger apart from `codex-review-recovery`'s byte-identical `@codex review` retry comment (a
fundamentally different action), so a recovery comment silently inflates the count and can exhaust
`max_rounds` early. Codex separately found a second, related gap: selecting multiple reviewers in one
decision posts one comment per reviewer, but the original design counted each comment as its own cycle,
miscounting a single 2-reviewer selection as 2 cycles instead of 1.

Both are fixed together via a per-decision `<batch-id>` marker
(`<!-- handling-review-findings-trigger:<batch-id> -->`) appended to every trigger comment's body: the
count is now the number of *distinct* batch-ids found, which excludes any comment lacking the marker
(recovery retries, coincidental human text) and correctly counts every comment sharing one batch-id as
one cycle. A third Codex finding, that Question 1 could offer "No further round for now" even while
`min_rounds` wasn't yet met (letting a user defeat the documented floor), was fixed by omitting that
option from Question 1 entirely below `min_rounds`.

Whether the trailing HTML-comment marker changes how Codex/CodeRabbit/Devin's own connectors parse the
mention text has not been live-verified as of this writing — disclosed in
`references/round-and-dedup-rules.md`'s own "Disclosed gap" note, to be confirmed the next time this
skill actually triggers a round in a live session.

A separate self-dispatched `security-reviewer` pass (part of a `plugin-auditor` scoped-diff audit run
the same day, after round 2's fixes and an unrelated R13 restructuring had both landed) found the
batch-id marker itself was still forgeable — its exact text is published in this skill's own SKILL.md,
so any comment containing it, from any author, would satisfy the round-2 fix's marker-presence check.
Closed by additionally requiring the marker-bearing comment's `author.login` to match the account
actually running this skill (resolved via `gh api user --jq '.login'`) — marker-plus-own-authorship
together, never marker alone (Workflow step 8a's current wording).

## Round-3 GitHub review findings on PR #101 (2026-08-22)

The automated round-3 review (Codex, reviewing commit `0e7a079`, the 29-finding plugin-auditor fix
batch) found that fix batch had introduced one real regression and left two pre-existing design gaps
unaddressed:

1. **Regression:** the same batch's own `consistency-reviewer:C1` fix ("`enabled: false` is documented
   as a filter in 5 places but never actually implemented") added the filter as step 8c's very first
   check, unconditionally — ahead of the tracked-vs-local trust-boundary gate that
   `references/settings-and-round-budget.md` already listed `enabled: false` under as one of five
   trust-boundary-protected fields. A tracked `.claude/git-kit.local.json` could therefore silently
   disable Codex/CodeRabbit/Devin from review, bypassing the exact protection the trigger-string check a
   few paragraphs later already had. Fixed by resolving the tracked-ness gate once, before touching
   either `enabled` or trigger text, and applying it uniformly to both.
2. **Design gap:** nothing distinguished a finding produced by the review that the final allowed
   (`max_rounds`-th) triggered batch itself triggered from a genuinely later, post-budget finding — both
   looked identical to a check that only compared the aggregate triggered-cycle count against
   `max_rounds`. Fixed by redefining "budget exhausted" as belonging to a round *after* the round the
   final batch opened, not merely "the count already reads `max_rounds`."
3. **Design gap:** 8b's reviewer/mode question assumed 2-4 validated reviewer options are always
   available; a configuration where 8c's validation leaves 0 or 1 survivors would either construct an
   invalid `AskUserQuestion` (below its 2-option minimum) or silently omit the mandatory stop option's
   compensating slot. Fixed by adding explicit one-survivor and zero-survivor paths to 8b.

None of the three findings had eval coverage before this round; all three are logged as new uncovered
scenarios/gates in `evals/handling-review-findings/evals.json` pending a future iteration's eval-writing
pass, per this skill's own "test the fix, not just describe it" standard — the fixes themselves were
verified by re-reading each against its own finding and cross-checking cited line numbers/quoted text
against the current file state, the lighter of the two mechanisms
`.claude/rules/require-tests-for-behavior-changes.md` allows for a skill not flagged
behavior-critical/frequently-relied-on, rather than a fresh `skill-tester` eval run.
