---
name: plugin-lifecycle-downstream
description: >-
  Orchestrates the full downstream plugin QA lifecycle — Validate, Audit, Report, and
  optional Fix — as one guided pipeline, dispatching to plugin-rulebook and
  plugin-validator for Validate, plugin-grader for Audit+Report, and enhancement-suggestor
  plus skill-improver-loop for Fix. Use when the user asks to "run full QA on this
  plugin", "validate and audit this plugin", "run the downstream workflow", or completes
  plugin-lifecycle-upstream's Test phase and wants to QA the result. Updates the same
  build-handoff-writer report upstream created, folding in QA results and any Fix-phase
  commits, rather than producing a disconnected report. For a single score with no
  orchestration, invoke plugin-grader directly instead of this pipeline.
argument-hint: "[path to plugin directory]"
allowed-tools: Read Glob Grep Skill Agent Edit Write Bash(git:*) TaskCreate TaskUpdate
---

# Plugin Lifecycle: Downstream

Guides plugin QA through three sequential phases — Validate, Audit+Report, and optional Fix. Unlike the upstream pipeline, downstream phases are not gated by user approval between each — they run automatically in sequence, since none of them are destructive until Fix, which has its own mandatory confirmation.

## Quick Start

**Target:** `$ARGUMENTS`

For the common case (QA an already-built plugin): run Validate → Audit+Report automatically against the target plugin path, then offer Fix. See [run-qa-pipeline.md](workflows/run-qa-pipeline.md) for the full procedure.

## Workflow Selection

| Workflow | Purpose |
|---|---|
| [run-qa-pipeline.md](workflows/run-qa-pipeline.md) | Full 3-phase procedure: Validate → Audit+Report → Fix (optional) |

## When to Use

- QA on a plugin just built via `plugin-lifecycle-upstream`
- QA on any existing plugin the user names, independent of how it was built
- Wanting one combined report covering rule compliance, structural validation, and a weighted quality score, rather than invoking `plugin-rulebook`/`plugin-validator`/`plugin-grader` separately
- Applying an already-produced, `prioritized_next_steps`-shaped findings list (e.g. from `plugin-lifecycle-maintenance`'s `improve-a-plugin`/`enhance-a-plugin` workflows) via Phase 3 directly, without re-running Phases 1-2 — see Phase 3's external-entry condition in `workflows/run-qa-pipeline.md`

## When NOT to Use

- Just a compliance check on one component, not a whole-plugin QA pass — use `Skill(plugin-rulebook)` directly
- Just a weighted score with SWOT and next steps, no separate Validate step wanted — use `plugin-grader` directly (it already includes rule-compliance as one of its 12 dimensions)
- Fixing a specific already-known issue — edit directly or use `skill-improver-loop`, skip the full pipeline

## The Three Phases

| Phase | Dispatches to | Produces |
|---|---|---|
| 1. Validate | `Skill(plugin-rulebook)` (batch mode across all components) + `plugin-validator`, `dependency-reviewer`, and `security-reviewer` agents | Rule-compliance report, structural validation report, dependency-graph report, security report |
| 2. Audit + Report | `plugin-grader` (whole-plugin mode) | Weighted score, SWOT, prioritized next steps — written to `.claude/output/plugin-grader/` |
| 3. Fix (optional) | `enhancement-suggestor` (against Phase 2's `prioritized_next_steps`, or an externally-supplied list of the same shape) → `skill-improver-loop` or direct edits | Applied fixes, re-validated, committed |

There is no separate "Report" phase — `plugin-grader`'s own output already includes the score, SWOT, and prioritized next steps in one written artifact (per this plugin's own design choice to keep scoring and reporting as a single coherent step rather than splitting them the way a naive port of an external QA pipeline might).

There is also an optional, ungated-into-the-phase-count **Deep Test** step (see "Suggested Next Step" and `workflows/run-qa-pipeline.md`) — exhaustive per-trigger-phrase testing and eval suites, moved here from `plugin-lifecycle-upstream`'s Phase 5 (which only runs a bounded smoke check) since this expensive, per-item-cost testing must be an explicit opt-in (plugin-rulebook R26), not something a "quick" build gate runs by default.

**No gates between Phases 1-2** — both are read-only, so they run automatically in sequence. **Phase 3 is opt-in and gated**: always ask before starting it, and `enhancement-suggestor`/`skill-improver-loop`/direct edits carry their own confirmation requirements per their own skill definitions — this orchestrator does not bypass those.

**Deep Test is opt-in and gated, and runs independently of Phases 1-3.** `plugin-lifecycle-upstream`'s own Phase 5 only runs a bounded smoke check (at most 3 checks, confirming a new component doesn't crash the harness) — it deliberately does not exhaustively test every declared trigger phrase or run eval suites, since each check is a nested LLM call and a "quick" gate must not spend that by default. This pipeline's Deep Test step is where that exhaustive, expensive testing belongs, but only when the user explicitly asks for it (plugin-rulebook R26) — never as a silent default alongside Phases 1-2's automatic read-only checks.

**Phases 1-2 never edit files — not even to fix an obvious REQUIRED violation.** If `plugin-rulebook` or `plugin-validator` surfaces a clear, small, unambiguous fix mid-Validate, record it as a finding for Phase 2's report and Phase 3's `prioritized_next_steps` — do not apply it there. This holds even when another instruction (e.g. a component-authoring rule that says "fix REQUIRED failures before finalizing") would normally justify an immediate fix — that rule governs authoring a component, not running this read-only pipeline against one, and does not override Phases 1-2's read-only contract. Any file edit during this pipeline, at any severity, requires asking the user first, exactly like Phase 3 already does.

**Every written artifact gets a link line.** Whenever this pipeline writes or updates a file (the Audit Report, the Build Handoff Report), present `📄 <Artifact Name> written:`/`updated: \`<path>\`` as its own line before the content summary — see `workflows/run-qa-pipeline.md`'s Phase 2 and Phase 3 for the exact pattern. Shared convention with `plugin-lifecycle-upstream` and `plugin-lifecycle-maintenance` — keep new artifact-producing steps consistent with it.

## Handoff Report: Use and Update

If a build-handoff-writer report exists for this target — passed in directly (`plugin-lifecycle-upstream`'s handover includes the path) or found via `Glob('.claude/output/build-handoff-writer/*.md')`, most recent by timestamp if more than one matches — this pipeline treats it as the running record of the build, not a separate artifact:

- **After Phase 2**, dispatch `build-handoff-writer` (via `Agent`) in **update** mode with the existing report's path, plus `plugin-grader`'s score/gates/weakest-component from the just-written report. This folds the audit result into the same document instead of leaving it siloed in `.claude/output/plugin-grader/`.
- **After Phase 3**, if it ran and produced new commits (see Commit step below), dispatch `build-handoff-writer` again in update mode with those commits and the re-validation result.
- If no existing handoff report is found (this pipeline was invoked standalone against a plugin that wasn't built via `plugin-lifecycle-upstream`), skip this step entirely — do not fabricate one.

## Document

After Phase 3 (Fix) completes **via the normal internal flow (Phases 1-2 ran in this same invocation)** — or after Phase 2 (Audit + Report), if the user declined Phase 3 — invoke `plugin-documentation` (via `Skill`) against the plugin's human-facing docs, passing Phase 3's applied fixes (if any) as the specific list of changed claims. `plugin-documentation` owns its own delta-vs-full `human-doc-reviewer` QA decision internally (see its own Step 4) — do not ask a separate delta/full question here first, or the same choice gets asked twice (plugin-rulebook R26 is already satisfied by `plugin-documentation`'s own gate). "No update needed" is a common, valid outcome, not a failure.

**Skip this step entirely when Phase 3 was entered via the external entry point** (see "When to Use" above) — the external caller (e.g. `plugin-lifecycle-maintenance`'s `improve-a-plugin`/`enhance-a-plugin` workflows) already runs its own Document step after Phase 3 returns control back to it. Running this pipeline's own Document step too would double-author and double-commit the same docs.

Present the authored diff and `plugin-documentation`'s own review findings; ask via `AskUserQuestion` whether to keep the changes as-is, revise, or discard. Stage and commit any kept doc changes **separately** from Phase 3's own commit(s) — state the file list and message first, same discipline as Phase 3's commit above. If a handoff report exists for this target (per "Handoff Report: Use and Update" above), fold a doc-fix commit (if one landed) into its next update the same way Phase 2/3 commits already are.

## Task Tracking

Use `TaskCreate` at the start for the phases that will run (Phase 3 only if the user opts in). Mark each `in_progress` before dispatching, `completed` when its output is ready.

## Handling a Validate Failure

If Phase 1 finds REQUIRED rule violations or Critical structural findings, do not skip Phase 2 — `plugin-grader`'s own hard gates (Gate A: Rule Compliance < 5 caps the score) already account for this, and seeing the full weighted picture (including what's still good) is more useful than stopping early on the first failure.

## Suggested Next Step

After Phase 2, ask with `AskUserQuestion`: "Run Fix (Phase 3) against the prioritized next steps?" — options "Yes — run Fix" / "No — stop here (report is saved)". If yes, proceed to Phase 3 per `workflows/run-qa-pipeline.md`. Never start Phase 3 without asking first.

Also ask, either alongside the Phase 3 offer or as a standalone follow-up at any later point: "Run Deep Test — exhaustive trigger-phrase testing for every agent component and any eval/unit-test suites for skill components? This is expensive (one nested LLM call per trigger phrase, per component) and is separate from Phase 1's structural/rule checks." — options "Yes — run Deep Test" / "No — skip". Never run it as a silent default; see `workflows/run-qa-pipeline.md`'s Deep Test step for the procedure.

## Testing & Validation

1. **Clean plugin** — no findings from Validate or Audit; confirm the pipeline still completes both phases and produces a report showing a clean result, not an early exit
2. **Failing Validate** — REQUIRED rule violations present; confirm Phase 2 still runs (per "Handling a Validate Failure" above) rather than stopping
3. **Fix declined** — user says no to Phase 3; confirm the pipeline stops cleanly with the Phase 2 report as the final artifact
4. **Fix accepted** — confirm `enhancement-suggestor` runs against the actual `prioritized_next_steps` from the just-produced report, not a stale or hypothetical list
5. **Handoff report present** — target was built via `plugin-lifecycle-upstream` and a handoff report exists; confirm Phase 2 updates that same file (not a new one) and Phase 3, if run, appends its own commits to it
6. **Handoff report absent** — target has no handoff report (standalone QA on a plugin not built via `plugin-lifecycle-upstream`); confirm the pipeline skips the update step cleanly rather than erroring or fabricating a report
7. **Fix produces a commit** — Phase 3 applies at least one approved fix; confirm the commit happens only after re-validation succeeds and the user is shown the file list/message first
8. **External Phase 3 entry** — an external caller (e.g. `plugin-lifecycle-maintenance`) invokes Phase 3 directly with its own `prioritized_next_steps`-shaped list, without Phases 1-2 having run in this invocation; confirm `enhancement-suggestor` runs against that supplied list (not a fabricated or re-derived one), that step 4's Phase 1-2 run is treated as a first run, not skipped as "already done", and that this pipeline's own Document step is skipped (the external caller runs its own) — never double-dispatched to `plugin-documentation`
9. **Document step, nothing to update** — confirm "no doc update needed" is presented as a normal outcome, not silently skipped without being stated, whether Document ran after Phase 3 or after Phase 2 (Phase 3 declined)
10. **Phase 1 surfaces a circular or missing dependency** — `dependency-reviewer` finds a Critical (execution-time cycle, or broken target); confirm Phase 2 still runs per "Handling a Validate Failure" and the finding carries through into `prioritized_next_steps`, same as a rulebook or structural Critical would
11. **Deep Test declined (default case)** — confirm Phases 1-2 complete and the pipeline reports its result without ever having run the exhaustive trigger-phrase battery or eval suites, since Deep Test was never opted into
12. **Deep Test accepted** — confirm it runs the full `test-agent-trigger.sh` phrase set per agent component (not the bounded single-phrase check `plugin-lifecycle-upstream` already ran) and any eval suites for skill components, and that any tool-level overhead encountered (a crash, a retry) is disclosed in plain language alongside the results
13. **Document step delegates to plugin-documentation** — confirm the Document step invokes `plugin-documentation` (not `human-doc-reviewer` directly) and does not ask its own separate delta/full question before that call — `plugin-documentation` owns that decision internally; confirm the specific list of changed claims from Phase 3's applied fixes is passed through

**Quality gates:**
- [ ] Phase 2 always runs regardless of Phase 1 findings — never skipped on failure
- [ ] Phase 3 is always opt-in via `AskUserQuestion` — never auto-started, except when an external caller explicitly invokes Phase 3 directly per its documented entry condition
- [ ] Phase 3, when run, always operates against a real `prioritized_next_steps`-shaped list — the current run's own report, or a validly-shaped externally-supplied one — never a cached, hypothetical, or malformed list
- [ ] No phase's substantive work is done by this skill directly — always dispatched via `Skill`/`Agent`
- [ ] Phases 1-2 never edit a file, regardless of how small or clearly-correct the fix looks — findings are recorded, not applied, until Phase 3 is explicitly approved
- [ ] When a handoff report exists, it is updated in place (same path) — never duplicated into a second timestamped file
- [ ] Phase 3's commit (if any) always happens after re-validation, never before, and always states the file list/message first
- [ ] The Document step always runs after Phase 3 (or Phase 2, if Phase 3 was declined) **when Phase 3 was entered via the normal internal flow** — and its own doc-fix commit (if any) is always separate from Phase 3's commit
- [ ] The Document step is always skipped when Phase 3 was entered via the external entry point — never double-dispatched to `plugin-documentation` alongside the external caller's own Document step
- [ ] The Audit Report and any handoff-report update each get the standard `📄 ... written:`/`updated:` link line before the content summary
- [ ] Deep Test is always opt-in via `AskUserQuestion` — never runs as a silent default alongside Phases 1-2's automatic checks
- [ ] Deep Test, when run, always uses the exhaustive per-trigger-phrase/eval-suite check — never the bounded smoke check `plugin-lifecycle-upstream`'s Phase 5 already covers
- [ ] The Document step always delegates to `plugin-documentation` — never calls `human-doc-reviewer` directly or asks its own separate delta/full question

## Reference Guide

| Resource | Purpose |
|---|---|
| `workflows/run-qa-pipeline.md` | Full 3-phase procedure, plus the optional Deep Test step |
| `plugin-rulebook` skill | Phase 1 — rule compliance |
| `plugin-validator` agent | Phase 1 — structural validation |
| `dependency-reviewer` agent | Phase 1 — circular/bidirectional dependency and required-vs-optional analysis |
| `security-reviewer` agent | Phase 1 — permission-risk, prompt-injection surface, PII/credential-leakage audit (deeper than plugin-validator's basic check) |
| `plugin-grader` skill | Phase 2 — weighted score, SWOT, prioritized next steps |
| `build-handoff-writer` agent | Updated (not created) after Phase 2, and after Phase 3 if it runs |
| `enhancement-suggestor` agent | Phase 3 — turns next steps into a WHAT/WHY/HOW plan |
| `agent-development/scripts/test-agent-trigger.sh` | Deep Test (optional) — full trigger-phrase battery per agent component, opt-in per plugin-rulebook R26 |
| `skill-tester` skill | Deep Test (optional) — full baseline-comparison benchmark / eval suite per skill component |
| `plugin-documentation` skill | Document step, after Phase 3 (or Phase 2 if Phase 3 was declined) — authors doc updates and runs its own `human-doc-reviewer` QA internally |
| `skill-improver-loop` skill | Phase 3 — automated fix-review cycles |
| `plugin-lifecycle-upstream` skill | Typical predecessor — produces the plugin this pipeline QAs, and the handoff report this pipeline updates |
| `plugin-lifecycle-maintenance` skill | External Phase 3 caller — supplies its own `prioritized_next_steps`-shaped list from `analyzing-sessions`/`plugin-comparison` findings, entering Phase 3 directly |
