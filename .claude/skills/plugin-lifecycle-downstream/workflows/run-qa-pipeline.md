# Run the QA Pipeline: Full Downstream Procedure

The complete Validate → Audit+Report → Fix procedure. Phases 1-2 run automatically; Phase 3 is opt-in.

## Pre-Flight: Token Cost Notice

Before Phase 1's own Actions — the very first thing this procedure does, on every invocation: state plainly that this pipeline's reviewer/grader fan-out (`plugin-rulebook`, `plugin-validator`, `dependency-reviewer`, `security-reviewer`, then `plugin-grader`'s own per-component dispatch) can use enough tokens to meaningfully affect a 5-hour usage window, and ask via `AskUserQuestion`: "Continue" / "Stop — let me check usage first". Only proceed to Phase 1 on "Continue". See SKILL.md's "Token Cost Notice" for the full rationale — this step is that notice's actual procedure.

## Phase 1: Validate

**Entry:** A plugin path is given or resolved from context.

**Dependency/security check mode:** `dependency-reviewer` and `security-reviewer` (Actions 3-4) each support a Delta mode scoped to a named new/changed component, instead of re-verifying the whole plugin's call graph and permission surface every time (`plugin-validator`, Action 2, has no such mode and always runs full). Before Actions 3-4, check whether this Phase 1 run's own entry names a small, specific set of new or changed components (e.g. "QA following the addition of new agent X", "check the just-built skill Y") rather than a general, periodic, or pre-release audit with no such named focus.

- If it names a narrow scope: ask via `AskUserQuestion` — "Scoped" (each agent's own Delta mode, checking only the named component(s)' edges/permissions) or "Full" (the whole-plugin sweep)? State plainly that Scoped won't catch a pre-existing cycle or permission issue elsewhere in the plugin, while Full re-verifies everything but costs substantially more on a large plugin. Recommend Scoped as the default option here, matching the same never-silently-default-to-expensive discipline this plugin already applies elsewhere (`plugin-documentation`'s delta/full gate, `plugin-lifecycle-maintenance`'s self-service "Shared: Cost-Gated Dispatch" procedure) — plugin-rulebook R26. **Caveat for a genuinely new (not modified) component:** `dependency-reviewer`'s Delta mode still saves real cost (it only needs to check the new component's own edges against the existing graph). `security-reviewer`'s Delta mode is scoped to changed lines/sections within a component — a brand-new component has no prior version to diff against, so its Delta mode degenerates to checking the whole new component anyway, buying little over Full for that specific agent. State this when recommending Scoped for a new-component run, so the user knows the savings are asymmetric between the two agents.
- If the run's own framing is already a general/periodic/pre-release audit (no named narrow scope): skip this question entirely and run Full — asking would be noise when Full is already the only sensible answer.

**Actions:**
1. Invoke `Skill(plugin-rulebook)` in batch mode against every component in the plugin (per `plugin-rulebook-enforcement.md`'s Batch mode — one invocation, per-component PASS/ADVISORY/FAIL lines).
2. Invoke the `plugin-validator` agent (via `Agent`) against the plugin root for structural/manifest validation. **For a plugin with more than 6 skills** (the threshold above which a single whole-plugin dispatch has previously run long enough to hit a session-limit error mid-run), split into multiple smaller dispatches instead of one big one, so a mid-run failure only costs re-running one batch:
   a. One dispatch covering manifest/directory-structure/MCP/file-organization/security only (its own Steps 1-3, 8-10) — always a single call, cheap regardless of plugin size.
   b. Skills split into batches of ~5-6 per dispatch, each in Batch mode (per the agent's own "Invocation Modes").
   c. Commands + agents + hooks together in one more dispatch, unless any single type's count alone exceeds ~6, in which case batch that type the same way as skills.
   d. Merge all batch reports into one combined result before presenting: union the Critical/Warning counts, concatenate Component Summary rows, state plainly that the result was compiled from N batched dispatches — never present a merged report as if it came from one dispatch.
   For 6 or fewer skills, one whole-plugin dispatch (no batching) is fine — the blast-radius problem batching solves doesn't materialize at that size.
3. Invoke the `dependency-reviewer` agent (via `Agent`) — Full component set, or Scoped (Delta mode) against the named component(s), per the gate above.
4. Invoke the `security-reviewer` agent (via `Agent`) — Full component set, or Scoped (Delta mode) against the named component(s), per the gate above.
5. Collect all four reports. If Scoped mode was used for 3-4, state this plainly alongside the collected results — a Scoped report must never be presented as if it were a Full sweep.

**Exit criteria:** All four reports are complete — do not proceed to Phase 2 with a partial rulebook sweep (e.g. only some components checked) or a partial reviewer dispatch. A Scoped dependency/security report is still "complete" for its own declared scope, per the gate above — it is not a partial dispatch.

## Phase 2: Audit + Report

**Entry:** Phase 1 complete (regardless of findings — see SKILL.md's "Handling a Validate Failure").

**Actions:**
1. Invoke `plugin-grader` (via `Skill`) in whole-plugin rollup mode against the plugin path.
2. Pass Phase 1's rulebook findings, and Phase 1's `security-reviewer` findings, as context to `plugin-grader` — reuse both rather than letting `plugin-grader` re-dispatch `Skill(plugin-rulebook)` or `security-reviewer` itself for the same components. `security-reviewer` is the higher-cost case: `plugin-grader`'s own default (per `references/rubric.md`'s dispatch table) is one fresh `security-reviewer` call *per component* in plugin mode, which would run the same check `1 + N` times across a single full downstream pass without this reuse. Phase 1's report already attributes each finding to the specific file(s)/component(s) it names — extract each component's findings from that one report to feed its `safety_risk_handling` dimension. **If Phase 1 ran Scoped mode** (a named narrow target, per Phase 1's own gate above — not a whole-plugin sweep), its `security-reviewer` coverage doesn't extend past that target: only reuse findings for the component(s) Phase 1 actually covered, and let `plugin-grader` dispatch fresh `security-reviewer` calls for every other component in scope.
3. Wait for the written report at `.claude/output/plugin-grader/<target>-<timestamp>.json`.

**Exit criteria:** The `plugin-grader` report exists with a `plugin_final_score`, `weakest_component`, and `prioritized_next_steps` (rollup mode) or `final_score`/`prioritized_next_steps` (component mode, if the plugin has only one component).

Present the artifact link first, then the summary:

```
📄 Audit Report written: `.claude/output/plugin-grader/<target>-<timestamp>.json`
```

Present a narrative summary to the user: overall score, any triggered gates, weakest component, top 3 prioritized next steps.

**Handoff report update:** if a build-handoff-writer report exists for this target (per SKILL.md's "Handoff Report: Use and Update"), dispatch `build-handoff-writer` (via `Agent`) in **update** mode with the report's path and this phase's score/gates/weakest-component. Skip silently if no report exists. The agent has no `Write` tool and returns the full updated report as text — `Write` its returned content back to the same report path before presenting the link line:

```
📄 Build Handoff Report updated: `<report path>`
```

## Phase 3: Fix (Optional)

**Entry:** User opted in via the SKILL.md's "Suggested Next Step" prompt (the normal case — Phases 1-2 of *this* run produced the list), **or** an external caller invokes this skill directly at Phase 3 with an already-produced `prioritized_next_steps`-shaped list (each entry: `rank`, `action`, `dimension`, `points_gain_estimate`, `lifts_gate` — the exact shape `plugin-grader` writes, per `plugin-grader/references/output-schema.md`). The external-entry case exists for callers that already ran their own audit-equivalent step and don't need Phases 1-2 re-run — e.g. `plugin-lifecycle-maintenance`'s `improve-a-plugin`/`enhance-a-plugin` workflows, which derive their list from `analyzing-sessions`/`plugin-comparison` findings rather than a fresh `plugin-grader` audit. **Provenance caveat:** the only validation applied here is that the supplied list has the shape `plugin-grader` writes (`rank`/`action`/`dimension`/`points_gain_estimate`/`lifts_gate`) — this pipeline trusts the caller to have sourced the list legitimately and cannot itself verify where it actually came from.

**Actions:**
0. **Pre-flight: Open-PR and Branch-scope checks.** Phase 3 is the only phase that writes to the target plugin — before Action 1, run both checks from `plugin-rulebook/references/branch-and-pr-preflight.md`. Open-PR check: if the current branch already has an open PR, ask (merge-first / continue-anyway). Branch-scope check: if the current branch isn't scoped (`main`/`master`, or doesn't match `<type>/<description>`), ask (new-branch / continue-anyway). Both checks apply to whichever branch/repo the target plugin actually lives in — for the normal case this is the current working branch; run each independently, since a branch can fail one check without failing the other (see the reference file's "Why Two Separate Checks" section).
1. Invoke the `enhancement-suggestor` agent (via `Agent`) against the findings list — Phase 2's own `prioritized_next_steps`/`swot.weaknesses` in the normal case, or the externally-supplied list in the external-entry case (pass an empty `swot.weaknesses` if the caller didn't supply one; `enhancement-suggestor` tolerates this).
2. Present the classified WHAT/WHY/HOW plan to the user, then use `AskUserQuestion` (multi-select) — question: "Which Quick Wins should be applied?", one option per Quick Win — to get per-item approval.
3. For each Quick Win the user approved: apply via the matching development skill (`skill-development`/`agent-development`/etc.) or `skill-improver-loop` for automated structural fix-review cycles, per `enhancement-suggestor`'s own "Implementing any of these is a separate step" closing note.
4. After fixes are applied, run Phase 1-2 against the target to confirm improvement — in the normal case this is a re-run; in the external-entry case it's Phase 1-2's first run against this target within the current invocation. Either way, do not assume the fix worked without validating it through Phase 1-2's own checks. **This re-run must independently re-read the actual current file content — never accept the applied-fix list itself as evidence the fix landed correctly.** Re-dispatch the same reviewer type(s) that originally found each fixed finding, against the live post-fix files, not against a description of what was changed. A real instance from this plugin's own use: a re-validation pass that did this caught 3 fixes that had landed incompletely (a glob-narrowing pattern applied to 2 of 3 required sites, documentation left describing a script's pre-fix behavior after the script itself changed, a reciprocal cross-reference fix that reached a skill's `SKILL.md` but not its own `references/` file) and 2 new regressions the fix pass itself introduced — none of which a self-report from the fix step would have surfaced. **A cheaper substitute (a `compute_score.py` recomputation against known fixes instead of a fresh reviewer dispatch, or a targeted re-check of only the specific reviewer(s) that found each fix instead of the full Phase 1-2 set) is a legitimate choice when cost warrants it — but it must be stated plainly as a substitution, not silently presented as equivalent to a fresh Phase 1-2 run.** Two independent post-Fix reports in this plugin's own history skipped a fresh re-dispatch entirely (one used a recomputation, the other ran only 2 targeted reviewer re-checks) without either one ever completing a full Phase 1-2 re-run afterward — both disclosed the gap in their own text, which is the right instinct, but neither treated "get a real updated score" as a still-open follow-up action, so the gap stayed open indefinitely rather than being closed later.
5. Once re-validation confirms the fixes, state the exact file list and commit message, then use `AskUserQuestion` — question: "Commit these changes?", options: "Commit" / "Don't commit yet" — before staging and committing per this repo's standard git-commit conventions (message ends with the `Co-Authored-By` line; never `--no-verify`). This requires its own confirmation — do not fold it into the Quick Win approval from step 2, since the user approved the *content* of the fix there, not yet the *commit*.
6. Run `git log -1`/`git show --stat` to capture the resulting commit SHA, message, and touched files, then dispatch `build-handoff-writer` (via `Agent`) in **update** mode with those commits and the re-validation result — same skip-if-no-report rule as Phase 2. The agent returns the full updated report as text (no `Write` tool) — `Write` it back to the same report path before presenting the link line:

```
📄 Build Handoff Report updated: `<report path>`
```

**Exit criteria:** All user-approved fixes applied, re-validated, and committed, or the user stops mid-list (partial application is fine — report which items were applied vs. deferred, and commit only what was actually applied). **Re-validated means one of:** a fresh Phase 1-2 re-run against the live post-fix files (the default expectation), or an explicitly-disclosed cheaper substitute per step 4 above, recorded as a named open item (not just a footnote) so a later reader — or a later `improve-a-plugin` retro — treats "get a real updated score" as still-outstanding work rather than assuming the substitute already closed it.

## Deep Test (Optional)

**Entry:** The user opted in via the SKILL.md's "Suggested Next Step" prompt, at any point after Phase 1 has run (alongside the Phase 3 offer, or as a standalone follow-up later). Independent of Phases 1-3 — does not require Phase 2 or Phase 3 to have run first, and does not block them from running.

This is where the exhaustive testing `plugin-lifecycle-upstream`'s own Phase 5 deliberately does NOT run belongs — Phase 5 only smoke-checks that a new component doesn't crash the harness (at most 3 bounded checks); this step is the full, expensive pass, opt-in only (plugin-rulebook R26).

**Actions:**
1. For each agent component in scope: run `agent-development/scripts/test-agent-trigger.sh` directly via the scoped `Bash(*/agent-development/scripts/test-agent-trigger.sh:*)` tool — no subagent dispatch. The script is a deterministic, offline check with no LLM step inside it, so there is nothing here that benefits from `general-purpose`'s isolation or justifies paying its full tool-schema cost. Run it against the component's complete "When to invoke" phrase set (not the single-phrase bounded check upstream already ran) — every phrase, both should-trigger and should-not-trigger.
2. For each skill component in scope with an `evals/` directory: run its full eval suite, or invoke `skill-tester` (via `Skill`) in full baseline-comparison benchmark mode (not fast pass/fail).
3. Collect a detailed per-component, per-phrase (or per-eval) result — not just an aggregate pass/fail.
4. **Disclose unplanned overhead:** if any component's run required a debugging detour, a tool-level crash-and-retry, or otherwise deviated from a single clean pass, state this in plain language alongside the results — do not fold it silently into an aggregate summary (plugin-rulebook R25).

**Coverage scope:** Deep Test currently covers agent and skill components only, per Actions 1-2 above. Hook and command components have no Deep Test coverage yet — always report them as "skipped — no Deep Test coverage for this type yet" (the same skipped-component convention Phase 1/the bounded-smoke-check level already uses), never silently omit them from the summary.

**Exit criteria:** Every in-scope agent/skill component has a detailed test result recorded, and every hook/command component is explicitly reported as skipped (per the coverage-scope note above) — or the user declined this step entirely (a valid, common outcome — state it plainly rather than treating Deep Test as mandatory).

Present a summary: per-component pass/fail counts, any specific failing phrases or eval cases, and any tool-level overhead disclosed per Action 4. This does not gate progress on its own — Phases 2/3 run (or already ran) independently of whether Deep Test was accepted.

## Document

**Entry:** Phase 3 just completed via the normal internal flow (per its exit criteria above), or the user declined Phase 3 at the "Suggested Next Step" prompt. **Skip this step entirely if Phase 3 was entered via the external entry point** — see `SKILL.md`'s "Document" section for why (the external caller already runs its own Document step).

See `SKILL.md`'s "Document" section for the full procedure — identical here. Locally: after `plugin-documentation` returns and any kept doc changes are committed (separately from Phase 3's own commit), if a handoff report exists for this target dispatch `build-handoff-writer` (via `Agent`) in **update** mode with the doc-fix commit, if one landed — same skip-if-no-report rule as Phase 2/3. This can be folded into the same update call as Phase 3's, if Phase 3 also ran and hasn't been reported yet; otherwise it's its own update call.

**Exit criteria:** `plugin-documentation` ran and its findings were presented; either no doc changes were needed (stated plainly) or kept doc changes were applied and committed. Or: this step was skipped because Phase 3 was entered externally.

## Fix Confirmation Discipline

This orchestrator never applies a fix itself without going through the matching development skill or `skill-improver-loop` — both already carry their own confirmation/review requirements (e.g. `skill-improver-loop`'s fix-review cycles, `plugin-rulebook`-before-finalizing discipline). Do not shortcut those by editing files directly from this workflow.

The one exception is the commit in step 5 above — this orchestrator does run `git add`/`git commit` itself (via its own scoped `Bash(git add:*)`/`Bash(git commit:*)`), since committing isn't "applying a fix," it's recording ones the user already approved. That still requires its own explicit confirmation of the file list and message before running, per this repo's standing git norms — approval of the fix content in step 2 does not carry forward as approval to commit it.
