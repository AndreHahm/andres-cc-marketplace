# Design a Plugin: Full Upstream Procedure

The complete Conceive → Ideate → Plan → Design → Build → Self-Review → Test procedure, one phase at a time. Follow this exactly — do not skip a gate.

## Pre-Flight Check: Open PR

Before Phase 1's own Actions — the very first thing this procedure does: run the Open-PR check from `plugin-rulebook/references/branch-and-pr-preflight.md`. If an open PR is found for the current branch, ask (merge-first / continue-anyway) before proceeding to Phase 1. If none is found, proceed straight into Phase 1 with no ask.

## Phase 1: Conceive

**Entry:** `$ARGUMENTS` is a rough idea, session evidence, or no Conception Brief/Concept Card/Plan was found by Auto-Detection.

**Actions:**
1. Invoke `plugin-conception` (via `Skill`) with the rough idea or evidence source.
2. Wait for the Conception Brief to be written.

**Exit criteria:** A Conception Brief exists at `.claude/output/plugin-conception/<concept-slug>-<timestamp>.md`.

**GATE 1:** Present the artifact link first, then the summary:

```
📄 Conception Brief written: `.claude/output/plugin-conception/<concept-slug>-<timestamp>.md`
```

Present the brief's classification and rationale.

- **If the classification is Create:** ask via `AskUserQuestion`: proceed to Ideate / revise the concept / stop. Do not proceed until approved. On approval, the light brief becomes Phase 2's input.
- **If the classification is anything else** (Enhance, Repair, Consolidate, Reposition, Retain, Reject/Defer): this pipeline is creation-only and stops here — state `plugin-conception`'s own hand-off target plainly (`plugin-planning` directly, `plugin-lifecycle-downstream`'s Phase 8 Consolidated Fix, or a clean stop with rationale) and point the user there. Do not proceed to Phase 2.

## Phase 2: Ideate

**Entry:** Phase 1's gate passed with a Create classification, or a Conception Brief was found by Auto-Detection and confirmed with the user (which also implies Phase 1 is skipped, per Auto-Detection Logic).

**Actions:**
1. Invoke `plugin-ideation` (via `Skill`) with the rough idea, or with Phase 1's light Conception Brief as input if Phase 1 ran.
2. Wait for the Concept Card to be written.

**Exit criteria:** A Concept Card exists at `.claude/output/plugin-ideation/<slug>-<timestamp>.md`, and its overlap classification is None or Partial (not Full — a Full-overlap concept stops here per `plugin-ideation`'s own Step 3).

**GATE 2:** Present the artifact link first, then the summary:

```
📄 Concept Card written: `.claude/output/plugin-ideation/<slug>-<timestamp>.md`
```

Present the Concept Card's problem statement, name candidates, and complexity tier. Ask via `AskUserQuestion`: proceed to Plan / revise the concept / stop. Do not proceed until approved.

## Phase 3: Plan

**Entry:** Phase 2's gate passed, or a Concept Card was found by Auto-Detection and confirmed with the user (which also implies Phases 1-2 are skipped, per Auto-Detection Logic).

**Actions:**
1. Invoke `plugin-planning` (via `Skill`) with the Concept Card path.
2. Wait for the Plan to be written.

**Exit criteria:** A Plan exists at `.claude/output/plugin-planning/<slug>-<timestamp>.md` with a component inventory, depth allocation, and functional groups.

**GATE 3:** Present the artifact link first, then the summary:

```
📄 Plan written: `.claude/output/plugin-planning/<slug>-<timestamp>.md`
```

Present the component inventory and functional groups. Ask via `AskUserQuestion`: proceed to Design / revise the plan / stop. Do not proceed until approved.

## Phase 4: Design

**No filesystem writes in this phase.** Every action below produces drafted content to hold in the conversation and present at Gate 4 — do not call `Write` or `Edit` against any real component path here, even to "show the actual file" more concretely. The first disk write this pipeline permits is Phase 5 (Build), after Gate 4 is explicitly approved. This is what makes Gate 4's "stop"/"revise" answer free to take: nothing exists on disk yet to walk back.

**Entry:** Phase 3's gate passed, or a Plan was found by Auto-Detection and confirmed with the user (which also implies Phases 1-3 are skipped, per Auto-Detection Logic).

**Actions:**
1. For each functional group in the Plan (in the order listed), for each component in that group:
   - Skill → invoke `skill-development`
   - Agent → invoke `agent-development`
   - Command → invoke `command-development`
   - Hook → invoke `hook-development`
   - Rule → invoke `rule-development`
2. Pass the component's plan entry (name, purpose, trigger phrases, depth tier if a skill) as context to each invocation.
3. Groups may be designed sequentially or, if fully independent (no shared naming/trigger concerns), the user may choose to parallelize — ask if the Plan has 2+ independent groups.
4. **After a functional group's components are all drafted, check whether any two of them gained a new `Skill()` call to each other in this same pass** (not a pre-existing call from before this build — a *new* one on both sides). If so, trace at least one full round-trip invocation scenario before Gate 4: "what happens if A calls B, and B's own trigger condition for calling A back is also true in that same invocation?" This check exists because it's exactly the kind of cross-component interaction a single-component-at-a-time Design invocation (step 1 above) cannot see on its own — in a real build, two components each gained a new mutual `Skill()` call in the same Design pass, were both approved at Gate 4, and shipped a Critical circular-dependency bug (nested/duplicate execution risk) that was only caught later by a dedicated `dependency-reviewer` pass. If a round-trip risk is found, resolve it in the drafted content (e.g. an explicit "skip this step when invoked as a nested dependency of the other" contract) before presenting at Gate 4, not after. **Scope boundary:** this check only covers a cycle assembled within the same Design pass — it does not catch a cycle assembled across two separate, unrelated builds (e.g. build A adds a call from X to Y; a later build B adds a call from Y back to X). `dependency-reviewer`'s full-plugin cycle detection (run during downstream QA) is the backstop for that broader case, not this step.

**Exit criteria:** Every planned component has designed content ready to write (the Design skill's own output — not yet written to disk), and step 4's mutual-invocation check has been performed for any functional group where it applies.

**GATE 4:** Present a summary of designed components (one line each: name, type, one-line purpose) — as prose/code blocks in the response, never as files already written to disk. Ask via `AskUserQuestion`: proceed to Build / revise specific components / stop. Do not proceed until approved.

## Phase 5: Build

**Entry:** Phase 4's gate passed.

**Actions:**
0. **Pre-flight: branch-scope check.** This is the first actual disk write in the whole pipeline (Phases 1-4 only ever write drafted content into the conversation or artifacts under `.claude/output/`) — before Action 1, run the Branch-scope check from `plugin-rulebook/references/branch-and-pr-preflight.md`. If the current branch isn't scoped (on `main`/`master`, or doesn't match `<type>/<description>`), ask (new-branch / continue-anyway) before proceeding. If already scoped, proceed with no ask.
1. Invoke `plugin-development` (via `Skill`) to scaffold the plugin directory and write all designed component content from Phase 4.
2. If the plugin directory already exists (resuming a partial build), confirm with the user before any overwrite — per `plugin-development`'s own confirm-before-overwrite discipline.

For a single-component addition to an already-existing plugin (this pipeline's most common Phase 5 case when adding to `plugin-devkit` itself), route through `plugin-development`'s own "Adding a Component to an Existing Plugin" path (its Quick Routing option 2) rather than writing the designed file(s) directly — that path already includes a post-addition validation step (`claude plugin validate`/`scripts/validate_plugin.py`, confirming the whole plugin's structure and manifest are still valid, not just the new file's own formatting) that writing files directly would skip.

**Exit criteria:** All planned components exist on disk in the correct plugin structure.

**GATE 5:** Present the build summary (files created, directory tree). Ask via `AskUserQuestion`: proceed to Self-Review / revise specific components / stop. Do not proceed until approved.

## Phase 6: Self-Review

**Entry:** Phase 5's gate passed.

**Actions:**
1. For each component Phase 5 (Build) actually wrote in this run — not the whole plugin, and not any pre-existing sibling component this run didn't touch — dispatch the type-matched `*-reviewer` agent(s) (via `Agent`), per `plugin-grader/references/rubric.md`'s Type-Matched Reviewer Table:
   - Skill → `skill-reviewer` (SKILL.md) + `skilldir-reviewer` (everything else in the skill's directory)
   - Agent → `subagent-reviewer`
   - Command → `command-reviewer`
   - Hook → `hook-reviewer`
   - Rule → `rule-reviewer`
2. Collect each reviewer's findings as-is — Critical/Major/Minor or FAIL/ADVISORY, whatever that reviewer's own report format is. **Do not score, weight, or roll these findings up into anything resembling `plugin-grader`'s output** — no `dimensions`, no `plugin_final_score`, no `prioritized_next_steps`. See SKILL.md's "Self-Review is deliberately lighter than `plugin-lifecycle-downstream`'s Audit phase" section for the full rationale behind keeping this pass unscored and narrowly scoped.
3. **Phase-completion check:** before presenting GATE 6, check whether any of this phase's own reviewer dispatches were cancelled, errored, or left incomplete (e.g. a session-limit interruption mid-dispatch) — see `plugin-rulebook/references/open-item-discipline.md`'s Phase-Completion Check. Disclose any such gap plainly rather than presenting GATE 6 as if every dispatched reviewer actually completed.

**Exit criteria:** Every component Phase 5 wrote in this run has a recorded reviewer result (a findings list, however short), or a disclosed gap per step 3 above.

**GATE 6:** Present the findings, grouped by component. Ask via `AskUserQuestion`: proceed to Test / fix findings first (returns to Phase 4/5 for the affected component) / stop. A component with an unresolved Critical/FAIL-equivalent finding should normally route back for a fix, not proceed as-is — same spirit as GATE 7 (Test)'s failing-component guidance below. Do not proceed until approved.

## Phase 7: Test

**Entry:** Phase 6's gate passed.

**Actions:**
1. For each built component, dispatch a bounded smoke check by type — see SKILL.md's "Phase 7 is a bounded smoke check, not exhaustive correctness testing" section for the full rationale (why this is bounded, and where exhaustive testing actually lives):
   - Skill → invoke `skill-tester` (via `Skill`) in its fast pass/fail mode — not the full baseline-comparison benchmark
   - Agent → run `agent-development/scripts/test-agent-trigger.sh <agent-file>` directly via the scoped `Bash(*/agent-development/scripts/test-agent-trigger.sh:*)` tool — no subagent dispatch. The script is a deterministic, offline check with no LLM step inside it, so there is nothing here that benefits from `general-purpose`'s isolation or justifies paying its full tool-schema cost. Call it with **no second argument** (auto-derive mode) against a single representative "should trigger" phrase from the new agent's own "When to invoke" section — the second positional argument is a path to a phrases FILE, not an inline phrase string; passing an inline phrase there is a real, previously-hit usage mistake, not a valid form. If that single check passes cleanly, stop there. If it fails or crashes, run the same script (at most 2 more times, for a 3-check cap total) against 1-2 already-existing, known-good peer agents, same no-second-argument form, to isolate whether the failure is the new component's own issue or a bug in the shared tool — the diagnostic pattern that surfaced a real encoding bug in the tool itself during this plugin's own `permission-reviewer` build. The script only reads the agent file and simulates trigger phrases offline — it does not invoke the live harness, so it isn't blocked by the "new agent needs a session restart before the harness registers it" limitation
   - Hook → run `hook-development/scripts/test-hook.sh <hook-script> <sample-input.json>` directly via the scoped `Bash(*/hook-development/scripts/test-hook.sh:*)` tool — no subagent dispatch, same reasoning as the agent-component check (deterministic, offline, no LLM step). Use representative sample input matching the hook's actual event type; confirm it runs without crashing and returns a plausible exit code (0/2, not an unexpected crash).
   - Command → no dispatchable quick-test tool exists (commands aren't `Skill()`-invocable) — instead, `Read` the command file and manually follow its documented Steps once against one small, representative real input, not a fabricated one. Confirm it runs without crashing and produces plausible output; do not exhaustively cover every flag/branch. See SKILL.md's Phase 7 section for why this manual live-trial exists (a real gap it closes). **Safety boundary:** before executing any Step that would commit, delete, push, or otherwise mutate state beyond the local working tree, stop and confirm with the user first — or skip that specific step, note it was skipped, and continue the trial for the remaining non-mutating steps. The live-trial's purpose is confirming the command runs without crashing and produces plausible output, not exercising every mutating side effect unsupervised.
   - Rule → no dedicated quick-test tool exists yet; record as "skipped — no quick-test tool available", do not silently omit
2. Collect one pass/fail/skipped result per component, with a one-line reason for any fail or skip.
3. **Disclose unplanned overhead:** if reaching a result required more than the single representative check — a tool crash, a peer-comparison detour, an unplanned retry — state this to the user in plain language as part of presenting GATE 7, not folded silently into a clean-looking pass/fail line (plugin-rulebook R25).

**Exit criteria:** Every built component has a recorded test result (pass, fail, or skipped-with-reason).

**GATE 7:** Present the per-component test results. Ask via `AskUserQuestion`: proceed to Commit + Handoff / revise a specific component / stop. A failing component should normally route back to Phase 4/5 for that component, not be committed as-is. Do not proceed until approved.

## Commit

After GATE 7 is approved, run the Pre-Commit Disclosure check from `plugin-rulebook/references/open-item-discipline.md` — surface any open item from Phases 1-7 (including any Self-Review finding the user chose not to act on at GATE 6) alongside the file list and message below, not silently folded into the commit. Then stage exactly the files this pipeline run created or changed and commit them, per this repo's standard git-commit conventions (message ends with the `Co-Authored-By` line; never `--no-verify`; never bundle in unrelated unstaged changes). State the file list and commit message as part of presenting GATE 7 so the one approval covers both proceeding and committing — do not treat this as a second silent step after the gate. After committing, run `git log -1`/`git show --stat` to capture the commit SHA, message, and touched-file list for the handoff report.

## Document

After the Commit step, invoke `plugin-documentation` (via `Skill`) against the plugin's human-facing docs (README.md, CHANGELOG.md, CONTRIBUTING.md, etc.) to draft whatever update the newly built components require — it reads the plugin's actual current state and runs its own built-in `human-doc-reviewer` QA pass on what it writes, so this step no longer needs to invoke `human-doc-reviewer` separately or hand-apply its findings. "No update needed" is a common, valid outcome, not a failure, and does not block progress to the handoff report below. Present the authored diff and `plugin-documentation`'s own review findings; ask via `AskUserQuestion` whether to keep the changes as-is, revise, or discard. Stage and commit any kept doc changes **separately** from the build commit above — state the file list and message first. This step produces no persisted report of its own (only direct doc edits plus an optional commit), so no `📄 ... written:` line applies here.

**Post-Commit handoff report:** invoke `build-handoff-writer` (via `Agent`) in **create** mode with the Conception Brief (if Phase 1 ran), Concept Card, Plan (if any), Design gate summaries, the Build summary, Phase 6's Self-Review findings, Phase 7's test results, and the commit info gathered above — including a doc-fix commit if Document produced one. This runs automatically — no separate gate, since GATE 7's approval already covers it. The agent has no `Write` tool and returns the full report as text — get a timestamp (`Bash(date -u +%Y-%m-%dT%H-%M-%SZ)`) and `Write` its returned content to `.claude/output/build-handoff-writer/<slug>-<timestamp>.md` yourself before presenting GATE 8.

**GATE 8:** Present the artifact link first, then the summary:

```
📄 Build Handoff Report written: `.claude/output/build-handoff-writer/<slug>-<timestamp>.md`
```

Present the handoff report's summary. Ask via `AskUserQuestion`: hand off to `plugin-lifecycle-downstream` for QA / stop here. This is the SKILL.md's own "Handover to Downstream" step — see there for the exact prompt. Pass the handoff report's path along so downstream updates it instead of creating a new one.

## If a Gate Fails

Return to the phase that produced the rejected output. Apply the user's feedback, re-run that phase's Actions, and re-present the gate. There is no retry limit — keep revising until the user approves or chooses to stop.
