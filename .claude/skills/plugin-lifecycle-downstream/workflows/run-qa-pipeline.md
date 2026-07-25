# Run the QA Pipeline: Full Downstream Procedure

The complete Validate → Audit+Report → Fix procedure. Phases 1-2 run automatically; Phase 3 is opt-in.

## Phase 1: Validate

**Entry:** A plugin path is given or resolved from context.

**Actions:**
1. Invoke `Skill(plugin-rulebook)` in batch mode against every component in the plugin (per `plugin-rulebook-enforcement.md`'s Batch mode — one invocation, per-component PASS/ADVISORY/FAIL lines).
2. Invoke the `plugin-validator` agent (via `Agent`) against the plugin root for structural/manifest validation.
3. Invoke the `dependency-reviewer` agent (via `Agent`) against the plugin's full component set for circular/bidirectional dependency and required-vs-optional analysis.
4. Invoke the `security-reviewer` agent (via `Agent`) against the plugin's full component set for the deeper permission-risk/prompt-injection/PII audit `plugin-validator`'s own Security Checks item doesn't attempt.
5. Collect all four reports.

**Exit criteria:** All four reports are complete — do not proceed to Phase 2 with a partial rulebook sweep (e.g. only some components checked) or a partial reviewer dispatch.

## Phase 2: Audit + Report

**Entry:** Phase 1 complete (regardless of findings — see SKILL.md's "Handling a Validate Failure").

**Actions:**
1. Invoke `plugin-grader` (via `Skill`) in whole-plugin rollup mode against the plugin path.
2. Pass Phase 1's rulebook findings as context if `plugin-grader`'s own Rule Compliance dimension dispatch would otherwise redundantly re-run `Skill(plugin-rulebook)` — reuse the Phase 1 result rather than invoking it twice.
3. Wait for the written report at `.claude/output/plugin-grader/<target>-<timestamp>.json`.

**Exit criteria:** The `plugin-grader` report exists with a `plugin_final_score`, `weakest_component`, and `prioritized_next_steps` (rollup mode) or `final_score`/`prioritized_next_steps` (component mode, if the plugin has only one component).

Present the artifact link first, then the summary:

```
📄 Audit Report written: `.claude/output/plugin-grader/<target>-<timestamp>.json`
```

Present a narrative summary to the user: overall score, any triggered gates, weakest component, top 3 prioritized next steps.

**Handoff report update:** if a build-handoff-writer report exists for this target (per SKILL.md's "Handoff Report: Use and Update"), dispatch `build-handoff-writer` (via `Agent`) in **update** mode with the report's path and this phase's score/gates/weakest-component. Skip silently if no report exists. If dispatched, present the link line once it returns:

```
📄 Build Handoff Report updated: `<report path>`
```

## Phase 3: Fix (Optional)

**Entry:** User opted in via the SKILL.md's "Suggested Next Step" prompt (the normal case — Phases 1-2 of *this* run produced the list), **or** an external caller invokes this skill directly at Phase 3 with an already-produced `prioritized_next_steps`-shaped list (each entry: `rank`, `action`, `dimension`, `points_gain_estimate`, `lifts_gate` — the exact shape `plugin-grader` writes, per `plugin-grader/references/output-schema.md`). The external-entry case exists for callers that already ran their own audit-equivalent step and don't need Phases 1-2 re-run — e.g. `plugin-lifecycle-maintenance`'s `improve-a-plugin`/`enhance-a-plugin` workflows, which derive their list from `analyzing-sessions`/`plugin-comparison` findings rather than a fresh `plugin-grader` audit.

**Actions:**
1. Invoke the `enhancement-suggestor` agent (via `Agent`) against the findings list — Phase 2's own `prioritized_next_steps`/`swot.weaknesses` in the normal case, or the externally-supplied list in the external-entry case (pass an empty `swot.weaknesses` if the caller didn't supply one; `enhancement-suggestor` tolerates this).
2. Present the classified WHAT/WHY/HOW plan to the user.
3. For each Quick Win the user approves: apply via the matching development skill (`skill-development`/`agent-development`/etc.) or `skill-improver-loop` for automated structural fix-review cycles, per `enhancement-suggestor`'s own "Implementing any of these is a separate step" closing note.
4. After fixes are applied, run Phase 1-2 against the target to confirm improvement — in the normal case this is a re-run; in the external-entry case it's Phase 1-2's first run against this target within the current invocation. Either way, do not assume the fix worked without validating it through Phase 1-2's own checks.
5. Once re-validation confirms the fixes, state the exact file list and commit message, then stage and commit per this repo's standard git-commit conventions (message ends with the `Co-Authored-By` line; never `--no-verify`). This requires its own confirmation — do not fold it into the Quick Win approval from step 2, since the user approved the *content* of the fix there, not yet the *commit*.
6. Run `git log -1`/`git show --stat` to capture the resulting commit SHA, message, and touched files, then dispatch `build-handoff-writer` (via `Agent`) in **update** mode with those commits and the re-validation result — same skip-if-no-report rule as Phase 2. If dispatched, present the link line once it returns:

```
📄 Build Handoff Report updated: `<report path>`
```

**Exit criteria:** All user-approved fixes applied, re-validated, and committed, or the user stops mid-list (partial application is fine — report which items were applied vs. deferred, and commit only what was actually applied).

## Deep Test (Optional)

**Entry:** The user opted in via the SKILL.md's "Suggested Next Step" prompt, at any point after Phase 1 has run (alongside the Phase 3 offer, or as a standalone follow-up later). Independent of Phases 1-3 — does not require Phase 2 or Phase 3 to have run first, and does not block them from running.

This is where the exhaustive testing `plugin-lifecycle-upstream`'s own Phase 5 deliberately does NOT run belongs — Phase 5 only smoke-checks that a new component doesn't crash the harness (at most 3 bounded checks); this step is the full, expensive pass, opt-in only (plugin-rulebook R26).

**Actions:**
1. For each agent component in scope: dispatch a `general-purpose` agent (via `Agent`, since this orchestrator's own `allowed-tools` intentionally has no general `Bash` — only the scoped `Bash(git:*)` used by Phase 3's commit step) with the instruction to run `agent-development/scripts/test-agent-trigger.sh` against the component's complete "When to invoke" phrase set (not the single-phrase bounded check upstream already ran) — every phrase, both should-trigger and should-not-trigger.
2. For each skill component in scope with an `evals/` directory: run its full eval suite, or invoke `skill-tester` (via `Skill`) in full baseline-comparison benchmark mode (not fast pass/fail).
3. Collect a detailed per-component, per-phrase (or per-eval) result — not just an aggregate pass/fail.
4. **Disclose unplanned overhead:** if any component's run required a debugging detour, a tool-level crash-and-retry, or otherwise deviated from a single clean pass, state this in plain language alongside the results — do not fold it silently into an aggregate summary (plugin-rulebook R25).

**Exit criteria:** Every in-scope component has a detailed test result recorded, or the user declined this step entirely (a valid, common outcome — state it plainly rather than treating Deep Test as mandatory).

Present a summary: per-component pass/fail counts, any specific failing phrases or eval cases, and any tool-level overhead disclosed per Action 4. This does not gate progress on its own — Phases 2/3 run (or already ran) independently of whether Deep Test was accepted.

## Document

**Entry:** Phase 3 just completed via the normal internal flow (per its exit criteria above), or the user declined Phase 3 at the "Suggested Next Step" prompt. **Skip this step entirely if Phase 3 was entered via the external entry point** — see `SKILL.md`'s "Document" section for why (the external caller already runs its own Document step).

See `SKILL.md`'s "Document" section for the full procedure — identical here. Locally: after `plugin-documentation` returns and any kept doc changes are committed (separately from Phase 3's own commit), if a handoff report exists for this target dispatch `build-handoff-writer` (via `Agent`) in **update** mode with the doc-fix commit, if one landed — same skip-if-no-report rule as Phase 2/3. This can be folded into the same update call as Phase 3's, if Phase 3 also ran and hasn't been reported yet; otherwise it's its own update call.

**Exit criteria:** `plugin-documentation` ran and its findings were presented; either no doc changes were needed (stated plainly) or kept doc changes were applied and committed. Or: this step was skipped because Phase 3 was entered externally.

## Fix Confirmation Discipline

This orchestrator never applies a fix itself without going through the matching development skill or `skill-improver-loop` — both already carry their own confirmation/review requirements (e.g. `skill-improver-loop`'s fix-review cycles, `plugin-rulebook`-before-finalizing discipline). Do not shortcut those by editing files directly from this workflow.

The one exception is the commit in step 5 above — this orchestrator does run `git add`/`git commit` itself (via its own scoped `Bash(git:*)`), since committing isn't "applying a fix," it's recording ones the user already approved. That still requires its own explicit confirmation of the file list and message before running, per this repo's standing git norms — approval of the fix content in step 2 does not carry forward as approval to commit it.
