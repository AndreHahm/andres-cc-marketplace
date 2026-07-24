---
name: plugin-lifecycle-upstream
description: >-
  Orchestrates the full upstream plugin-creation lifecycle — Ideate, Plan, Design, Build,
  and Test — as one guided, gated pipeline, dispatching to plugin-ideation, plugin-planning,
  the matching Design skill per component (skill-development, agent-development,
  command-development, hook-development, rule-development), plugin-development for
  scaffolding, and skill-tester/agent-development's trigger-test script for a quick
  post-Build check. Use when the user asks to "build a plugin from scratch", "run the full
  plugin creation pipeline", "guide me through creating a plugin", or "start the upstream
  workflow". Commits the build, writes a handoff report, and hands off to
  plugin-lifecycle-downstream for QA once Test completes. For a single already-designed
  component, use the matching Design skill directly instead of this pipeline.
argument-hint: "[rough idea, or path to an existing Concept Card/Plan]"
allowed-tools: Read Glob Grep Skill Agent Edit Write Bash(git:*) Bash(*/test-agent-trigger.sh:*) TaskCreate TaskUpdate
---

# Plugin Lifecycle: Upstream

Guides plugin creation through five gated phases — Ideate, Plan, Design, Build, Test — each phase producing the artifact the next phase consumes. This orchestrator dispatches to existing skills for the substantive work; it does not design or write components itself.

## Quick Start

For the common case (a rough idea, nothing built yet): run all five phases in order, stopping for approval between each, then commit and write the handoff report. See [design-a-plugin.md](workflows/design-a-plugin.md) for the full phase-by-phase procedure.

## Workflow Selection

| Workflow | Purpose |
|---|---|
| [design-a-plugin.md](workflows/design-a-plugin.md) | Full 5-phase pipeline: Ideate → Plan → Design → Build → Test |

### Auto-Detection Logic

Before starting, check what already exists to avoid redundant work:

| Condition | Action |
|---|---|
| No Concept Card or Plan found, and `$ARGUMENTS` is a rough idea | Run the full pipeline from Phase 1 |
| A Concept Card path is given or found in `.claude/output/plugin-ideation/` | Skip Phase 1; confirm the card with the user, then start at Phase 2 |
| A Plan path is given or found in `.claude/output/plugin-planning/` | Skip Phases 1-2; confirm the plan with the user, then start at Phase 3 |
| Some components already exist on disk matching the plan | Ask the user: design the remaining components only, or re-design everything? |

## When to Use

- Building a new plugin from a rough idea, wanting guided help through the whole creation process
- Resuming plugin creation from an existing Concept Card or Plan (auto-detection picks up where a prior session left off)
- Preparing for `plugin-lifecycle-downstream` — this is the pipeline that produces what downstream QAs

## When NOT to Use

- A single, already-well-understood component — use the matching Design skill directly (`skill-development`, `agent-development`, `command-development`, `hook-development`, `rule-development`); this pipeline's overhead isn't worth it for one obvious skill
- QA on an already-built plugin — use `plugin-lifecycle-downstream` (or `plugin-grader` directly for a one-shot score)
- Just scaffolding files with a manifest already decided — use `plugin-development` directly, skipping Ideate/Plan/Design

## The Five Phases

| Phase | Dispatches to | Produces |
|---|---|---|
| 1. Ideate | `plugin-ideation` | Concept Card |
| 2. Plan | `plugin-planning` | Component inventory + depth plan |
| 3. Design | `skill-development` / `agent-development` / `command-development` / `hook-development` / `rule-development` (one per planned component, grouped by the plan's functional groups) | Designed component content, ready to write |
| 4. Build | `plugin-development` | Scaffolded plugin directory on disk |
| 5. Test | `skill-tester` (fast pass/fail mode, per skill component) / `agent-development`'s `scripts/test-agent-trigger.sh` (bounded smoke check, per agent component) | Per-component pass/fail/skipped smoke-check results |

There is no separate "Specify" phase — each Design skill listed above already produces complete, ready-to-write component content (full `SKILL.md`/agent `.md`/command `.md` text), so a distinct specification step would just be a redundant hop for this plugin's own skill set.

Phase 5 covers skill and agent components only — command, hook, and rule components have no dedicated quick-test tool in this plugin yet. Those component types are listed in the Test results as "skipped — no quick-test tool available" rather than silently omitted, so the gap stays visible in both the gate and the handoff report.

**Phase 5 is a bounded smoke check, not exhaustive correctness testing.** At most 3 checks run: confirm the new component doesn't crash the harness and the test tooling itself works in this session — not that every declared trigger phrase fires correctly, and not a full eval/unit-test suite. Exhaustive per-trigger-phrase testing and eval suites are `plugin-lifecycle-downstream`'s optional Deep Test step, gated behind an explicit user decision (plugin-rulebook R26) since they run a nested LLM call per trigger phrase — real cost that a "quick" gate must not spend by default. If reaching a Phase 5 result took more than the bounded check — a tool crash, a debugging detour, an unplanned retry — state this to the user in plain language before Gate 5, not folded silently into a clean pass/fail line (plugin-rulebook R25).

**Gate between every phase:** present the phase's output to the user and get explicit approval (`AskUserQuestion`: proceed / revise / stop) before starting the next phase. Never advance silently.

**Design never touches disk.** Phase 3's own output — the matching Design skill's drafted `SKILL.md`/agent/command/hook content — stays in the conversation, never written via `Write`/`Edit` to a real component path, no matter how tempting it is to "just show the actual file" at Gate 3. The first phase permitted to write is Phase 4 (Build), and only after Gate 3 is explicitly approved. This is the whole point of gating by phase: a "stop" or "revise" answer at Gate 3 costs nothing to walk back only if nothing was written yet.

**Every written artifact gets a link line.** Whenever a phase writes a file (Concept Card, Plan, Build Handoff Report), the gate that follows opens with `📄 <Artifact Name> written: \`<path>\`` as its own line, before the content summary — see `workflows/design-a-plugin.md`'s Gates 1, 2, and 6 for the exact pattern. This is a standing convention shared with `plugin-lifecycle-downstream` and `plugin-lifecycle-maintenance` — keep new artifact-producing steps consistent with it rather than inventing a different confirmation style.

## Task Tracking

Use `TaskCreate` at the start to create one task per phase actually running (per Auto-Detection Logic, above — skipped phases don't get a task). Mark each `in_progress` before dispatching, `completed` immediately after the phase's gate is approved.

## Commit

After Phase 5 (Test)'s gate is approved, stage and commit the built files per this repo's standard git-commit conventions (message ends with the `Co-Authored-By` line; never `--no-verify`). This is the one destructive action in this pipeline, so state the exact file list and commit message before running it — Phase 5's gate approval covers "proceed to Commit + Handoff," it is not a separate silent step. After committing, run `git log`/`git show --stat` to gather the resulting commit SHA(s), one-line message(s), and touched-file list(s) for the handoff report below.

## Document

After the Commit step, invoke `plugin-documentation` (via `Skill`) against the plugin's human-facing docs (README.md, CHANGELOG.md, CONTRIBUTING.md, etc.) to draft whatever update the newly built components require — it reads the plugin's actual current state and runs its own built-in `human-doc-reviewer` QA pass on what it writes, so this step no longer needs to invoke `human-doc-reviewer` separately or hand-apply its findings. "No update needed" is a common, valid outcome, not a failure. Present the authored diff and `plugin-documentation`'s own review findings; ask via `AskUserQuestion` whether to keep the changes as-is, revise, or discard. Stage and commit any kept doc changes **separately** from the build's own commit — state the file list and message first, same discipline as the Commit step above. This runs before the Post-Commit Handoff Report below, so the report can fold in whichever commit(s) actually happened (build commit, plus a doc-fix commit if one landed).

## Post-Commit Handoff Report

Immediately after the Commit and Document steps — before the downstream-QA offer below — invoke the `build-handoff-writer` agent (via `Agent`) with the Concept Card path, Plan path (if Phase 2 ran), a summary of each Design-phase gate outcome, the Build summary, Phase 5's test results, and the commit list gathered above (the build commit, plus a doc-fix commit if Document produced one). This is a **create** call (first report for this build). It produces one narrative-and-open-items report at `.claude/output/build-handoff-writer/` for a cold-context reader — it does not gate progress and does not require separate user approval to run, since it only synthesizes what already happened and was already approved at Phase 5's gate.

## Handover to Downstream

After the handoff report is written, ask with `AskUserQuestion`: "Run `plugin-lifecycle-downstream` now for QA (Validate → Audit → Report)?" — options "Yes — run downstream QA" / "No — stop here". If yes, invoke `plugin-lifecycle-downstream` (via `Skill`) with the newly built plugin's path **and the handoff report's path**, so downstream updates the same report instead of starting a new one. Never invoke it without asking first.

## Testing & Validation

1. **Cold start** — a rough idea with no existing artifacts; confirm all 5 phases run in order with a gate between each
2. **Resume from Plan** — pre-existing plan file; confirm Phases 1-2 are skipped and the user is shown the loaded plan for confirmation before Phase 3 starts
3. **Partial build detected** — some but not all planned components exist on disk; confirm the skill asks rather than silently overwriting or silently skipping
4. **Gate rejection** — user rejects a phase's output; confirm the pipeline returns to that phase for revision rather than advancing anyway
5. **Test phase, mixed component types** — a plan with a skill, an agent, and a command; confirm the skill and agent get real bounded smoke-check results (not exhaustive trigger-by-trigger testing) while the command is explicitly listed as skipped, not silently dropped
5a. **Test phase, unplanned overhead** — construct a case where the test tool crashes or needs a debugging retry before producing a result; confirm this is disclosed to the user in plain language before Gate 5, not silently absorbed into a clean-looking pass/fail line
6. **Commit and handoff** — confirm the Commit step never runs before Phase 5's gate is approved, and the handoff report (create call) always includes the resulting commit SHA(s)
7. **Document step, nothing to update** — confirm "no doc update needed" is presented as a normal outcome, not silently skipped without being stated, and that the handoff report still runs even when Document made no changes
8. **Design produces no disk writes** — confirm no `Write`/`Edit` tool call targets a real component path during Phase 3, regardless of how the designed content is presented at Gate 3; the component's files exist on disk only once Phase 4 (Build) has run following Gate 3 approval

**Quality gates:**
- [ ] Every phase transition is gated by explicit `AskUserQuestion` approval — never silent
- [ ] Auto-detection always runs before Phase 1 starts — never assumes a cold start
- [ ] No phase's substantive work is done by this skill directly — always dispatched via `Skill`/`Agent` (Phase 5's agent-component check is a narrow, named exception: it calls `test-agent-trigger.sh` directly via the scoped `Bash(*/test-agent-trigger.sh:*)` tool, since the script is a deterministic offline check with no LLM step — not substantive delegated work)
- [ ] Phase 3 (Design) never calls `Write`/`Edit` against a real component path — designed content stays in the conversation until Gate 3 is approved and Phase 4 (Build) begins
- [ ] Phase 5's per-component results always distinguish pass / fail / skipped — a skipped component type is never presented as if it passed
- [ ] Phase 5 never runs a component's full trigger-phrase battery or an eval suite — that's `plugin-lifecycle-downstream`'s optional, user-gated Deep Test step
- [ ] Any unplanned overhead reaching a Phase 5 result (a tool crash, a debugging detour, a retry) is disclosed to the user in plain language before Gate 5
- [ ] The Commit step always states the file list and message before running, and never runs before Phase 5's gate is approved
- [ ] The Document step always runs after the Commit step, and its own doc-fix commit (if any) is always separate from the build's own commit
- [ ] The downstream handoff offer uses `AskUserQuestion`, never auto-invoked without asking
- [ ] Every gate that follows a written artifact opens with the standard `📄 ... written:` link line, before the content summary

## Reference Guide

| Resource | Purpose |
|---|---|
| `workflows/design-a-plugin.md` | Full 5-phase procedure with gate criteria per phase |
| `plugin-ideation` skill | Phase 1 |
| `plugin-planning` skill | Phase 2 |
| `skill-development` / `agent-development` / `command-development` / `hook-development` / `rule-development` | Phase 3, one per component type |
| `plugin-development` skill | Phase 4 |
| `skill-tester` skill | Phase 5, fast pass/fail mode, skill components |
| `agent-development/scripts/test-agent-trigger.sh` | Phase 5, agent components — bounded smoke check only, called directly via the scoped `Bash(*/test-agent-trigger.sh:*)` tool (no subagent dispatch); full battery moved to `plugin-lifecycle-downstream`'s optional Deep Test step |
| `plugin-documentation` skill | Document step, after Commit and before the handoff report — authors doc updates and runs its own `human-doc-reviewer` QA internally |
| `build-handoff-writer` agent | Post-Commit handoff report (create), before the downstream offer |
| `plugin-lifecycle-downstream` skill | Handover target after Test; also updates the handoff report |
