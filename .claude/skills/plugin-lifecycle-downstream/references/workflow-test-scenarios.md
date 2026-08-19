# Workflow Test Scenarios

The 13 scenario categories this pipeline's own test coverage requires, each traced
against the `SKILL.md`/`workflows/run-qa-pipeline.md` prose rather than executed live.
Scenarios 1-12 were traced before this skill's production cutover, when it wasn't yet
installed anywhere and a real `Skill()` dispatch wasn't possible. This is the same
manual-dry-run discipline used throughout this pipeline's development (see
`feedback_agent_dispatch_ignores_worktree_edits.md`), applied here as the actual test
mechanism rather than a fallback: each scenario states a concrete setup, the exact
SKILL.md/workflow section that governs it, and a pass/fail verdict. Two scenarios found
real gaps during this pass; both were fixed in `SKILL.md`/`run-qa-pipeline.md` before
this document was finalized, and the verdict below reflects the post-fix text. Scenario
13 was added in a later pass (2026-08-19), when Phase 5's Eval Pre-Check sub-step was
introduced — traced the same way, against the prose that added it, not backdated into
the original pre-cutover pass. As of this skill's production cutover, a live end-to-end
dry run against a small real plugin is still outstanding — see the closing note below.

**Verdict key:** PASS (behavior explicitly specified and traced) · FIXED (a gap was
found and closed as part of this milestone; verdict is post-fix) · GAP (a gap remains,
recorded rather than silently passed).

## 1. Scoped and full manifests

**Setup:** Phase 1 invoked with a named-component target, then separately with no
target (whole-plugin).

**Traced against:** `SKILL.md`'s "Scope Manifest" section — `scope_mode: changed | named
| full` is a first-class field; `run-qa-pipeline.md`'s Phase 1 Actions: "identify
changed/named/full coverage... Write `scope.json`". Phase 1's Exit ("A confirmed scope
manifest exists. No target-plugin file was changed.") applies identically to all three
modes.

**Verdict:** PASS — both scoped and full manifests are explicit, first-class scope-manifest
states with no divergent exit criteria between them.

## 2. Prepare declined and Prepare approved

**Setup:** scope inventory finds a missing smoke test; user declines, then (separately)
approves creating it.

**Traced against:** Phase 2 Entry: "The scope inventory identifies missing smoke tests or
evals and the user opts to create them. Otherwise record `skipped` with the reason."
Approved path's Actions run the Open-PR/Branch-scope preflight, present cost, create only
approved assets, and demonstrate each new test against a controlled negative before
Exit — "Each approved asset exists and has a meaningful baseline result, or the phase is
explicitly skipped."

**Verdict:** PASS — both paths have distinct, complete Actions/Exit text; the declined
path's `skipped`-with-reason state is not silently treated as a failure.

## 3. Validation success, repair success, and bounded repair failure

**Setup:** (a) no validation findings; (b) a Critical structural finding, fixed within
the attempt limit; (c) the same finding, still open after the attempt limit.

**Traced against:** Phase 3 Exit ("If successful, continue. If blocking findings exist,
continue only to Phase 4."); Phase 4 Entry ("Phase 3 has blocking validation findings. If
none exist, record `not_needed`.") and Decision's three branches (Succeeded /
Attempt-limit-reached-ask / Failed); `SKILL.md`'s "Success and Stop Rules" section, which
additionally makes REQUIRED rulebook violations and failing required tests **ineligible**
for risk acceptance — they always stop the run at the attempt limit, with no ask.

**Verdict:** PASS — all three sub-cases have distinct, traceable text, including the
REQUIRED-violation carve-out that prevents scenario (c) from silently becoming a
risk-accepted pass.

## 4. Audit success, repair success, and bounded repair failure

**Setup:** same three sub-cases as #3, against Phase 5 (Audit)/Phase 6 (Fix & Re-audit)
instead of Phase 3/4.

**Traced against:** Phase 5 Exit and Phase 6 Entry/Decision mirror Phase 3/4's structure
exactly (three-way Decision: Succeeded / Attempt-limit-reached-ask / Failed). `SKILL.md`'s
"Success and Stop Rules" covers audit success separately ("no unresolved Critical
dependency, consistency, or security finding").

**Verdict:** PASS — structurally symmetric with #3, independently confirmed rather than
assumed identical.

## 5. Deep Test skipped, Scoped, and Full

**Setup:** Phase 7 reached after Validation and Audit both succeed; user picks each of
the three options in turn.

**Traced against:** Phase 7 Entry: "Ask: **Skip**, **Scoped**, or **Full**. Explain that
Full tests every eligible component and costs one or more executions per trigger/eval."
Actions specify per-type dispatch (agent trigger battery, `skill-tester`
baseline-comparison, `smoke-tester` batch sweep, hook tests) and explicit `skipped`
recording for unsupported types. Exit: "Every eligible in-scope component has a detailed
result, or the phase is explicitly skipped."

**Verdict:** PASS — all three modes are named options with distinct cost/coverage
framing, not an implicit default.

## 6. External Phase 8 entry with valid, stale, and malformed evidence

**Setup:** (a) a well-formed, current findings bundle; (b) a well-formed bundle whose
evidence no longer matches live files; (c) a bundle that fails schema validation
(missing a required Finding field).

**Traced against (pre-fix):** the original `SKILL.md` External Entry text only said
"Stale or unverifiable findings remain open and cannot be represented as confirmed" —
covering (b), but with no explicit statement for (c). **Gap found:** a structurally
malformed bundle had no defined pipeline behavior — unclear whether Phase 8 would attempt
a partial fix plan from broken data.

**Fix applied:** `SKILL.md`'s "External Entry" section now explicitly states a bundle
that fails schema validation is refused entirely (with the specific failing field(s)
named), separately from a stale-but-parseable bundle, whose findings stay open and are
explicitly excluded from the fix plan rather than silently dropped or silently trusted.
`run-qa-pipeline.md`'s Phase 8 Actions cross-reference both cases.

**Verdict:** FIXED — (a) and (b) were already PASS; (c) is now explicitly specified
post-fix.

## 7. Documentation invalidating evidence

**Setup:** Phase 9 authors a doc change that also changes a component's activation
description.

**Traced against:** `SKILL.md`'s "Documentation Boundary" section: "If documentation work
changes executable behavior, activation descriptions, permissions, component
instructions, or dependency relationships, invalidate the affected evidence and include
those checks in Phase 10." Phase 9 Actions restate this exact condition inline.

**Verdict:** PASS — the invalidation trigger list and its Phase 10 follow-through are
both explicit and appear in two independent places (`SKILL.md` and the workflow file),
not asserted once and assumed to propagate.

## 8. Final verification detecting a regression

**Setup:** Phase 10 re-runs a check that passed earlier in the run; it now fails.

**Traced against (pre-fix):** the original Phase 10 Decision only said "Recommend Grading
only when required evidence is current and all blocking criteria pass. Otherwise
recommend stopping..." — a regression and a merely-missing/stale piece of evidence were
handled identically (both just "recommend stopping"), with no path back into a fix phase
for the regression case. **Gap found:** a real regression had no defined route back to
Phase 8.

**Fix applied:** Phase 10's Decision now distinguishes a regression (write it as a new
open finding, route to Phase 8) from missing/stale evidence with nothing to route
(recommend stopping, state the gap). Phase 8's own Entry condition was extended to name
"a regression Phase 10 discovered on a prior pass through this run" as a valid reason to
re-enter Phase 8.

**Verdict:** FIXED — a regression now has an explicit, traceable path back to a fix
phase instead of only ending the run.

## 9. Grading skipped, evidence-only success, qualified score, and refusal

**Setup:** (a) user declines Phase 11; (b) all evidence current, full score computed; (c)
some optional evidence missing/stale; (d) required evidence missing/stale.

**Traced against:** Phase 11 Entry ("Ask whether to run Grading... If declined, record
`skipped`.") covers (a). Actions: "invoke `plugin-grader` in evidence-only mode... If
required evidence is missing or stale, produce only a qualified score or refuse scoring
according to the grader contract" — (b)/(c)/(d) are explicitly delegated to
`plugin-grader`'s own already-built evidence-only mode, which is the correct single
source of truth for the qualified-vs-refuse distinction rather than a second, potentially
divergent restatement here.

**Verdict:** PASS — delegation to `plugin-grader`'s own contract, rather than
re-deriving the qualify/refuse logic in this pipeline's own text, is the correct design
(avoids the exact kind of duplicated-fact drift R20 exists to catch).

## 10. Handoff present and absent

**Setup:** (a) a prior `build-handoff-writer` report exists for this target; (b) none
does.

**Traced against:** Phase 12 Actions: "If an existing handoff report was found... dispatch
`build-handoff-writer`... in update mode... Do not fabricate a handoff report when none
exists."

**Verdict:** PASS — both branches are explicit; the "no fabrication" rule is stated
directly rather than left as an inferred default.

## 11. No fixer self-verification

**Setup:** a fix is applied through a development skill; that skill's own summary of the
fix is offered as evidence the fix worked.

**Traced against:** three independent statements of the same rule — Core Contract #3
("The component that applies a fix does not verify its own work. The originating
validator or reviewer rechecks live files."), the dedicated "Independent Recheck" section
("Do not accept a fixer summary, diff description, or score recomputation as
verification."), and Quality Gates ("Fixers never self-verify.").

**Verdict:** PASS — this is the one guarantee restated three times in three different
sections (contract, procedure, and gate checklist), each independently sufficient to
catch a violation; no single point of failure in the documentation itself.

## 12. No shippable target mutation before the first-write preflight and approval

**Setup:** (a) a normal run reaching Phase 2's first write; (b) an External Entry run
where Phase 8 is the actual first phase that runs at all.

**Traced against:** "Mutation and Confirmation" section: "Phase 1 is read-only. Phase 2
is the first potentially mutating phase, so run the shared Open-PR and Branch-scope
preflight... immediately before its first write. This check runs at most once per
run... Phases 2, 4, 6, and 8 (including Phase 8 under External Entry, which can skip
Phases 1-7 entirely) each check this before their own first write and run the preflight
only if it hasn't already run this run." Per-fix-batch approval (distinct from the
once-per-run preflight) is a separate, always-required step: "1. Present finding IDs...
2. Obtain per-item or clearly bounded batch approval."

**Verdict:** PASS — this was also the subject of a real bug found and fixed earlier in
this pipeline's development (the preflight was documented but never actually wired into
every mutating phase); this trace re-confirms the fix holds for both the normal-run and
External-Entry-as-first-write cases specifically.

## 13. Eval Pre-Check declined, approved, and nested-dispatch suppression

**Setup:** Phase 5 reached with an in-scope skill that has `evals/<skill>/evals.json`
and/or `scripts/smoke_test.*`; user declines the pre-check, then (separately) approves
it. A third case: Phase 5 reached with no in-scope skill carrying either asset. A fourth
case: the pre-check is approved, and `reviewing-evals` itself reaches its own Quick Start
step 5 (which asks whether to dispatch `plugin-auditor`) for one of the qualifying
skills.

**Traced against (pre-fix):** the original Phase 5 Actions text told the operator to
"run it per skill and let the operator resolve any FAIL locally before continuing," with
no instruction covering `reviewing-evals`'s own step 5. **Gap found:** `reviewing-evals`
Quick Start step 5 unconditionally asks whether to dispatch `plugin-auditor` once all of
its own checks pass — for every qualifying skill in the pre-check loop, on top of Phase
5's own single dispatch over the whole declared scope two sentences later. Accepting the
nested ask would trigger a redundant, expensive per-skill audit; declining it produces a
repetitive prompt per qualifying skill that Phase 5's own single gate never advertised.

**Fix applied:** `run-qa-pipeline.md`'s Phase 5 Actions now explicitly instructs, as part
of each per-skill invocation, that `reviewing-evals` skip its own Quick Start step 5 —
`reviewing-evals/SKILL.md`'s step 5 itself now states this same skip condition on its own
side ("skip this step entirely when the caller explicitly says so"), matching the
reciprocal loop-breaker pattern `create-pr`/`commit`/`collaborating-on-a-pr` already use
for the same class of nested-dispatch problem (see `create-pr/SKILL.md`'s "Loop-Breaker
Convention").

**Verdict:** FIXED — all four branches (declined, approved, no qualifying skill, and the
nested-dispatch case) now converge on exactly one `plugin-auditor` dispatch per Phase 5
run, never zero and never more than one; the "never runs by default" guarantee for the
pre-check itself is still stated in three independent places (Actions, Optional Phases,
Quality Gates), matching this document's own established pattern (see #11) for a
guarantee worth restating across sections rather than asserted once.

## Summary

10 of 13 scenario categories: PASS on first trace. 3 of 13 (external-entry malformed
evidence; final-verification regression routing; Eval Pre-Check's nested-dispatch
suppression) found real, previously undocumented gaps — all three fixed in
`SKILL.md`/`run-qa-pipeline.md` before this document was finalized, not deferred.
`scripts/smoke_test.py` was re-run after each fix (including scenario 13's later
addition and its own subsequent fix) and continued to pass (frontmatter,
referenced-file, Bash-grant, phase-sequence, and report-fixture checks unaffected by
these prose-only edits).

**What this is not:** a live end-to-end pipeline execution. No `Agent()`/`Skill()`
dispatch was made against a real target plugin for any of the 13 scenarios during their
respective traces — scenarios 1-12 were blocked pre-cutover, since the skill wasn't yet
installable; scenario 13 was traced the same documentation-only way for consistency with
the rest of this document, not because live dispatch is still blocked. As of the
production cutover, a real end-to-end dry run against a small real plugin — which would
now also exercise Phase 5's Eval Pre-Check live — is still a needed, separate follow-up,
not a substitute this document claims to provide.
