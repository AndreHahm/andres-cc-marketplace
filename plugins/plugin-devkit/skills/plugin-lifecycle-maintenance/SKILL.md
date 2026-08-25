---
name: plugin-lifecycle-maintenance
description: >-
  Orchestrates ongoing maintenance for an already-built plugin through four workflows —
  retro-driven improvement, comparison-driven enhancement, keeping plugin-devkit's own
  rules current, and plugin-devkit's own on-demand self-checks (reflexion, review,
  validation, evaluation, grading, improvement, documentation) — each ending in a
  human-approved, tested, documented, committed change. Use when the user asks to
  "improve this plugin based on the retro", "enhance this plugin compared to X",
  "check plugin-devkit's rules against upstream docs", "run a self-check on plugin-devkit", or wants to act on
  findings from analyzing-sessions, plugin-comparison, or the dev-rules commands rather
  than just reading a report. Never decides what to fix itself — the human always picks.
  Reuses plugin-lifecycle-downstream's Fix phase and the dev-rules commands' own apply
  steps. Not for a single, already-known fix — edit directly or use the matching Design
  skill.
argument-hint: "[workflow: improve|enhance|self-upstream|self-service] [target]"
allowed-tools: Read Glob Grep Skill Agent Edit Write Bash(git:*) Bash(gh pr view:*) Bash(date:*) Bash(*/agent-cost-tracker.py:*) Bash(*/agent-development/scripts/test-agent-trigger.sh:*) Bash(*/hook-development/scripts/test-hook.sh:*) TaskCreate TaskUpdate
---

# Plugin Lifecycle: Maintenance

Guides an already-shipped plugin through four maintenance workflows — each one finds findings via a different source tool, lets the human decide what to act on, then hands off to existing apply/build/commit machinery rather than reimplementing it. This is the third lifecycle leg: `plugin-lifecycle-upstream` creates, `plugin-lifecycle-downstream` QAs what exists, this skill evolves it over time.

## Quick Start

1. **Open-PR check** — before identifying which workflow to run, check for an open PR on the current branch: see "Pre-Flight Checks" below. This runs once per invocation, regardless of which of the 4 workflows the request resolves to.
2. Identify which workflow the request matches and jump to its file:

| Workflow | Purpose |
|---|---|
| [improve-a-plugin.md](workflows/improve-a-plugin.md) | Retro-driven: `analyzing-sessions` finds issues from session behavior, human picks, hand off to Fix |
| [enhance-a-plugin.md](workflows/enhance-a-plugin.md) | Comparison-driven: `plugin-comparison` finds gaps against another target, human picks, hand off to Fix |
| [self-upstream-plugin-devkit.md](workflows/self-upstream-plugin-devkit.md) | Keeps `plugin-devkit`'s own rules current against official Claude Code docs — bulk or single-rule mode |
| [self-service-plugin-devkit.md](workflows/self-service-plugin-devkit.md) | Plugin-devkit's own on-demand self-checks against itself — 7 services: self-reflexion, self-review, self-validation, self-evaluation, self-grading, self-improvement, self-documentation |

## Pre-Flight Checks

Two checks, shared with `plugin-lifecycle-upstream` and `plugin-lifecycle-downstream` — see `plugin-rulebook/references/branch-and-pr-preflight.md` for the exact procedure behind both:

- **Open-PR check** — runs once, centrally, in Quick Start step 1 above, before any of the 4 workflows starts — not duplicated inside each workflow file.
- **Branch-scope check** — runs once per workflow, right before that workflow's own first actual write, since each workflow's write point differs:
  - `improve-a-plugin` / `enhance-a-plugin`: no separate check needed here — both hand off entirely to `plugin-lifecycle-downstream`'s Phase 8 (Consolidated Fix) at their own Step 4 (after the new Step 3 Conceive step, which never writes to the target plugin), and Phase 8 now runs this exact check itself (see `plugin-lifecycle-downstream/SKILL.md`'s own "Mutation and Confirmation", which fires before Phase 8's first write even under External Entry). Adding a second check here would just ask the same question twice.
  - `self-upstream-plugin-devkit`: runs before Bulk mode's Step 6 (`/implement-dev-rules`) and before Single-Rule mode's Step 3 (`/update-dev-rule`) — see that workflow file.
  - `self-service-plugin-devkit`: runs before Service 6's Step 5 (apply approved candidates) and before Service 7's own commit — see that workflow file.

## Open-Item Discipline

Before any workflow step is treated as complete — and again immediately before that workflow's own Commit step — check for that step's own unresolved open, pending, or broken items (e.g. a sub-agent dispatch cancelled by a session limit) and disclose them rather than silently treating the step as complete. See `plugin-rulebook/references/open-item-discipline.md` for the exact procedure, shared with `plugin-lifecycle-upstream` and `plugin-lifecycle-downstream`. Unlike `plugin-lifecycle-downstream`, none of this skill's 4 workflows run the reference file's "Downstream's Proactive Offer" — that step is specific to `plugin-lifecycle-downstream` alone.

## When to Use

- Acting on `analyzing-sessions`' retrospective findings instead of just reading the report and manually applying fixes one at a time
- Acting on `plugin-comparison`'s findings after comparing this plugin to an adjacent one
- Periodically confirming `plugin-devkit`'s own rules (frontmatter fields, tool-scoping syntax, size thresholds) still match current official Claude Code documentation
- Running an on-demand self-check of plugin-devkit against itself (reflection, review, validation, evaluation, grading, improvement, or documentation)
- Wanting one guided, gated path from "here's a report" to "here's a tested, documented, committed fix" — rather than manually chaining `analyzing-sessions`/`plugin-comparison`/the dev-rules commands, `enhancement-suggestor`, a Design skill, and a commit yourself

## When NOT to Use

- A single, already-known fix with no need for a retro or comparison first — edit directly or use the matching Design skill
- Just want the retro or comparison report itself, not the follow-through — use `analyzing-sessions` or `plugin-comparison` directly and stop there
- A routine, single-change "should this update propagate" decision right after finishing other work — use `skill-maintenance` instead; that skill is a lightweight per-change decision/routing aid, not a multi-phase pipeline
- QA on a plugin with no specific finding-source driving the work — use `plugin-lifecycle-downstream` directly (this skill's `improve-a-plugin`/`enhance-a-plugin` workflows hand off to `plugin-lifecycle-downstream`'s own Fix phase rather than duplicating it)
- A general (non-self-referential) audit/QA/grade request for any plugin — including `plugin-devkit` itself when the ask is not explicitly framed as a self-check ("self-review", "self-validate", "self-grade", etc.) — use `plugin-lifecycle-downstream` (or `plugin-grader` for a one-shot score) instead; `self-service-plugin-devkit` is exclusively for plugin-devkit's own on-demand self-check services
- Building a new plugin or component from scratch — use `plugin-lifecycle-upstream`
- Not sure which of the three lifecycle pipelines fits — use `using-plugin-devkit` to confirm first

## Boundaries

**Never decides what to fix.** Every workflow surfaces findings and stops for an explicit `AskUserQuestion` decision before anything is applied — no workflow auto-selects or auto-applies a suggestion, gap, or rule fix on its own judgment.

**Never reimplements a source tool's own logic.** This skill sequences calls to `analyzing-sessions`, `plugin-comparison`, `plugin-conception`, `plugin-lifecycle-downstream`'s Fix phase, the `/report-dev-rules`→`/verify-dev-rules`→`/plan-dev-rules`→`/implement-dev-rules` / `/find-dev-rule`→`/update-dev-rule` command pairs, and (for `self-service-plugin-devkit`) `plugin-grader`/`plugin-documentation`/`skill-tester`/the reviewer agents — it never re-derives a SWOT, re-implements a comparison, a score, a classification, or a doc review. The Document step (below) delegates fully to `plugin-documentation`, which both authors doc content and runs its own `human-doc-reviewer` QA internally — this skill's own role there is limited to the keep/revise/discard decision and the commit, not re-implementing the authoring or review itself.

## The Document Step (Shared Across All 4 Workflows)

After the core workflow's fix/rule-update is applied and committed, invoke `plugin-documentation` (via `Skill`) against the plugin's human-facing docs (README.md, CHANGELOG.md, CONTRIBUTING.md, etc.), passing the specific list of changed claims from the core fix. `plugin-documentation` owns its own delta-vs-full `human-doc-reviewer` QA decision internally (see its own Step 4) — do not ask a separate delta/full question here first, or the same choice gets asked twice (plugin-rulebook R26 is already satisfied by `plugin-documentation`'s own gate). "No update needed" is a common, valid outcome, not a failure. Present the authored diff and `plugin-documentation`'s own review findings; ask via `AskUserQuestion` whether to keep the changes as-is, revise, or discard. Stage and commit any kept doc changes **separately** from the core fix's own commit(s) — state the file list and message first, same discipline as every other commit in this pipeline. Keeping "what changed in the component" and "what changed in the docs" as distinct commits keeps history readable.

## Every Written Artifact Gets a Link Line

Whenever a step in any of the 4 workflows writes a file (Session Analysis Report, Comparison Report, Rules/Gap/Plan/Implementation Reports, Plugin-Grader Report), present `📄 <Artifact Name> written: \`<path>\`` as its own line before the content summary — see `workflows/improve-a-plugin.md` Step 1, `workflows/enhance-a-plugin.md` Step 1, `workflows/self-upstream-plugin-devkit.md`'s Bulk Mode steps, and `workflows/self-service-plugin-devkit.md`'s Service 5 (self-grading) for the exact pattern. Shared convention with `plugin-lifecycle-upstream` and `plugin-lifecycle-downstream`. Single-Rule mode's `find-dev-rule`/`update-dev-rule` steps are the one exception — neither writes a persisted file, so no link line applies there; don't fabricate one.

## Slash Commands Are Not `Skill`-Invocable

`/report-dev-rules`, `/verify-dev-rules`, `/plan-dev-rules`, `/implement-dev-rules`, `/find-dev-rule`, and `/update-dev-rule` each state in their own body: "This command cannot be invoked via `Skill()` — it must be triggered as a slash command or followed manually." `self-upstream-plugin-devkit.md` follows manually — `Read` the command file and execute its documented Steps directly with the given arguments, rather than attempting a tool call that doesn't exist for commands.

## Task Tracking

Use `TaskCreate` at the start of whichever workflow runs, one task per major step (finding-source dispatch, human-decision gate, Conceive — `improve-a-plugin`/`enhance-a-plugin` only — apply/hand-off, Document, Commit). Mark each `in_progress` before dispatching, `completed` when its output is ready.

## Testing & Validation

This is a **manual-review checklist**, not a claim that every item below has eval coverage. Current eval evidence (`evals/plugin-lifecycle-maintenance/`, `skill-tester` Quick Workflow, 9 evals across 3 iterations, 25/25 assertions passing) covers trigger-phrase accuracy and scenarios 1, 2, 4, 5, 6, and 7 for the first 3 workflows (scenario 6's eval-7 record predates the Document step's `plugin-documentation`-delegation rewrite — eval-9 re-verifies it against the current architecture) — scenario 3 (bulk mode) and the 12 quality gates below have not yet been eval-tested; treat them as design-review-verified only until eval coverage is extended. **The `self-service-plugin-devkit` workflow (4th) has zero eval coverage as of this writing** — its own Build/Test pass verified only link resolution and trigger-phrase non-collision (see `workflows/self-service-plugin-devkit.md`'s own Testing & Validation section), not evals; the new "run a self-check on plugin-devkit" trigger phrase is likewise untested by the trigger-accuracy evals above. **The new Step 3 (Conceive) insertion in `improve-a-plugin`/`enhance-a-plugin` (and the resulting Step 4-7 renumbering) is design-review-verified only, not yet eval-tested** — the existing 9-eval/25-assertion evidence above predates this insertion and does not cover scenario 12a or the renumbered steps; treat those as needing eval coverage before relying on the same eval-based confidence the first 3 workflows otherwise have.

1. **improve-a-plugin, findings exist** — confirm `analyzing-sessions` runs, the human is asked which suggestions to act on via `AskUserQuestion`, and the hand-off to `plugin-lifecycle-downstream`'s Fix phase happens rather than a reimplemented apply step
2. **enhance-a-plugin, findings exist** — same shape, confirm `plugin-comparison` is the finding source and the same Fix-phase hand-off happens
3. **self-upstream-plugin-devkit, bulk mode** — confirm the 4 commands run in `report → verify → plan → implement` order (not the order a naive reading of "State→Find→Plan→Implement/Update→Verify" would suggest) and the human is asked which gaps to act on before `/plan-dev-rules` runs
4. **self-upstream-plugin-devkit, single-rule mode** — confirm `/find-dev-rule`'s read-only findings are presented before `/update-dev-rule` runs, and that `/update-dev-rule`'s own built-in pre-flight confirmation is not skipped or duplicated by this skill's own gate
5. **No findings / no gaps** — confirm each workflow stops cleanly and states nothing needed action, rather than forcing a fix
6. **Document step, nothing to update** — confirm "no doc update needed" is presented as a normal outcome, not silently skipped without being stated
7. **Document step delegates to plugin-documentation** — confirm the Document step invokes `plugin-documentation` (not `human-doc-reviewer` directly) and does not ask its own separate delta/full question first — `plugin-documentation` owns that decision internally
8. **Open-PR check, centralized** — confirm it runs exactly once in Quick Start step 1, before workflow routing, regardless of which of the 4 workflows the request resolves to — and confirm `improve-a-plugin`/`enhance-a-plugin` don't run a second copy of it inside their own Step 1
9. **Branch-scope check, improve-a-plugin/enhance-a-plugin** — confirm neither workflow runs its own branch-scope check, and that `plugin-lifecycle-downstream`'s Phase 8 pre-flight check is what actually covers this case when Step 4 hands off
10. **Branch-scope check, self-upstream-plugin-devkit** — confirm it fires before Bulk Step 6 and before Single-Rule Step 3, not earlier (Steps 1-5/1-2 only read/report/plan, no writes) and not later (both steps are the actual write point)
11. **Branch-scope check, self-service-plugin-devkit** — confirm it fires before Service 6 Step 5 and before Service 7's own commit, and does not fire for Services 1-5 (none of which write to the plugin)
12. **improve-a-plugin/enhance-a-plugin, Test and Self-Review reuse** — confirm Step 5 in both workflows doesn't re-invoke or duplicate `plugin-lifecycle-downstream`'s own Phase 8 (Consolidated Fix) re-verification, which already ran automatically as part of Step 4's hand-off once Phase 8 applied a change — and confirm Step 5 is stated as skipped (not silently omitted) when Step 4 applied nothing
12a. **improve-a-plugin/enhance-a-plugin, Conceive step placement** — confirm the new Step 3 (Conceive) always runs after Step 2's human finding-selection pick and before Step 4's hand-off to Fix — never before the pick (which would classify unselected candidates for nothing), and never skipped silently; confirm a narrow, already-known Repair takes `plugin-conception`'s own bypass path straight to Step 4 without a full brief, while every other classification produces one
13. **self-improvement, Test and Self-Review (Service 6, steps 6-7)** — confirm both are scoped to only the component(s) step 5 actually applied a change to, never the whole plugin; confirm step 7's findings are presented unscored; and confirm step 6's `smoke-tester` batch dispatch is used only for a large touched-skill set and only for the skill components in it, with any touched agent/hook/command/rule going through its own per-type tool directly

**Quality gates:**
- [ ] Every workflow's human-decision point uses `AskUserQuestion` — never an automatic selection
- [ ] `improve-a-plugin`/`enhance-a-plugin` always hand off to `plugin-lifecycle-downstream`'s Fix phase for apply/re-validate/commit — never reimplement it
- [ ] `self-upstream-plugin-devkit`'s bulk mode always runs `report → verify → plan → implement`, matching each command's own documented Pipeline order
- [ ] The Document step always runs after the core fix is committed, and its own doc-fix commit (if any) is always separate from the core fix's commit
- [ ] The Document step always delegates to `plugin-documentation` — never calls `human-doc-reviewer` directly or asks its own separate delta/full question
- [ ] The optional Handover offer uses `AskUserQuestion`, never auto-invoked without asking
- [ ] Every written artifact (Retro/Comparison/Rules/Gap/Plan/Implementation Report) gets the standard `📄 ... written:` link line before its content summary — Single-Rule mode's chat-only outputs excepted
- [ ] The Open-PR check runs exactly once per invocation, centrally in Quick Start, before any workflow's own Actions — never duplicated inside a workflow file
- [ ] The Branch-scope check always runs immediately before each workflow's own actual write step, never earlier and never skipped — `improve-a-plugin`/`enhance-a-plugin` rely on `plugin-lifecycle-downstream`'s Phase 8 gate instead of running their own
- [ ] `improve-a-plugin`/`enhance-a-plugin` never re-invoke or duplicate `plugin-lifecycle-downstream`'s Phase 8 (Consolidated Fix) re-verification — Step 5 in both workflows only gives that already-automatic coverage its own place in the step numbering
- [ ] `improve-a-plugin`/`enhance-a-plugin`'s Step 3 (Conceive) always runs after Step 2's human pick and before Step 4's Fix hand-off — never before the pick, never skipped, never reimplementing `plugin-conception`'s own classification logic
- [ ] `self-improvement`'s Test (step 6) and Self-Review (step 7) are always scoped to only the component(s) step 5 touched, and step 7's findings are never scored into anything resembling `plugin-grader`'s output
- [ ] Every workflow's Pre-Commit Disclosure check (`plugin-rulebook/references/open-item-discipline.md`) runs immediately before that workflow's own commit, and its result (including "no open items") is always stated alongside the file list/message

## Reference Guide

| Resource | Purpose |
|---|---|
| `workflows/improve-a-plugin.md` | Retro-driven improvement, full procedure |
| `plugin-rulebook/references/branch-and-pr-preflight.md` | Open-PR check and Branch-scope check procedures, shared with `plugin-lifecycle-upstream` and `plugin-lifecycle-downstream` |
| `plugin-rulebook/references/open-item-discipline.md` | Phase/step-completion check (every workflow step) and Pre-Commit Disclosure (before every workflow's own commit), shared with `plugin-lifecycle-upstream` and `plugin-lifecycle-downstream` |
| `git-kit:starting-work` | Branch-scope check's "create a new branch" option |
| `git-kit:merge-pr` | Open-PR check's "merge it first" option |
| `workflows/enhance-a-plugin.md` | Comparison-driven enhancement, full procedure |
| `workflows/self-upstream-plugin-devkit.md` | Bulk and single-rule modernization against official docs, full procedure |
| `workflows/self-service-plugin-devkit.md` | Plugin-devkit's own 7 on-demand self-checks against itself, full procedure (includes the shared cost-gated dispatch pattern used by self-review/self-evaluation) |
| `analyzing-sessions` skill | Finding source for `improve-a-plugin`; also the SWOT/critique engine `self-reflexion` hands session digests to |
| `plugin-comparison` skill | Finding source for `enhance-a-plugin` |
| `plugin-conception` skill | Step 3 (Conceive) in both `improve-a-plugin`/`enhance-a-plugin` — classifies the human-approved findings and produces a Conception Brief (or takes its own narrow-repair bypass) before the Fix hand-off |
| `enhancement-suggestor` agent | Expands a chosen suggestion/delta into a full WHAT/WHY/HOW plan |
| `plugin-lifecycle-downstream` skill | Reused Phase 8 (Consolidated Fix — apply/re-verify/commit, folding in what the old pipeline ran as separate Test/Self-Review phases) for `improve-a-plugin`/`enhance-a-plugin`; also `self-validation`'s Phase 1 (Scoping) through Phase 5 (Audit) dispatch |
| `plugin-grader/references/rubric.md` | Type-Matched Reviewer Table — `self-improvement`'s Self-Review step (Service 6, step 7, direct dispatch); `improve-a-plugin`/`enhance-a-plugin` get equivalent coverage indirectly, folded into `plugin-lifecycle-downstream`'s own Phase 8 re-verification rather than a separate reviewer dispatch from this skill |
| `plugin-grader` skill | `self-grading`'s standalone dispatch target |
| `plugin-documentation` skill | `self-documentation`'s dispatch target |
| `skill-tester` skill | `self-evaluation`'s dispatch target |
| `plugin-rulebook/scripts/agent-cost-tracker.py` | Cost estimates cited in `self-review`/`self-evaluation`'s scoped-vs-full gate |
| `plugin-documentation` skill | Document step, all 4 workflows — authors doc updates and runs its own `human-doc-reviewer` QA internally |
| `skill-maintenance` skill | Lighter-weight alternative for a single, already-known change — not this skill's job |
| `/report-dev-rules`, `/verify-dev-rules`, `/plan-dev-rules`, `/implement-dev-rules` | `self-upstream-plugin-devkit` bulk mode, in this order |
| `/find-dev-rule`, `/update-dev-rule` | `self-upstream-plugin-devkit` single-rule mode |
