---
name: plugin-lifecycle-maintenance
description: >-
  Orchestrates ongoing maintenance for an already-built plugin through four workflows —
  retro-driven improvement, comparison-driven enhancement, keeping plugin-devkit's own
  rules current, and plugin-devkit's own on-demand self-checks (reflexion, review,
  validation, evaluation, grading, improvement, documentation) — each ending in a
  human-approved, tested, documented, committed change. Use when the user asks to
  "improve this plugin based on the retro", "enhance this plugin compared to X",
  "modernize plugin-devkit's rules", "run a self-check on plugin-devkit", or wants to act on
  findings from analyzing-sessions, plugin-comparison, or the dev-rules commands rather
  than just reading a report. Never decides what to fix itself — the human always picks.
  Reuses plugin-lifecycle-downstream's Fix phase and the dev-rules commands' own apply
  steps. Not for a single, already-known fix — edit directly or use the matching Design
  skill.
argument-hint: "[workflow: improve|enhance|self-upstream|self-service] [target]"
allowed-tools: Read Skill Agent Edit Write Bash(git:*) TaskCreate TaskUpdate
---

# Plugin Lifecycle: Maintenance

Guides an already-shipped plugin through four maintenance workflows — each one finds findings via a different source tool, lets the human decide what to act on, then hands off to existing apply/build/commit machinery rather than reimplementing it. This is the third lifecycle leg: `plugin-lifecycle-upstream` creates, `plugin-lifecycle-downstream` QAs what exists, this skill evolves it over time.

## Quick Start

Identify which workflow the request matches and jump to its file:

| Workflow | Purpose |
|---|---|
| [improve-a-plugin.md](workflows/improve-a-plugin.md) | Retro-driven: `analyzing-sessions` finds issues from session behavior, human picks, hand off to Fix |
| [enhance-a-plugin.md](workflows/enhance-a-plugin.md) | Comparison-driven: `plugin-comparison` finds gaps against another target, human picks, hand off to Fix |
| [self-upstream-plugin-devkit.md](workflows/self-upstream-plugin-devkit.md) | Keeps `plugin-devkit`'s own rules current against official Claude Code docs — bulk or single-rule mode |
| [self-service-plugin-devkit.md](workflows/self-service-plugin-devkit.md) | Plugin-devkit's own on-demand self-checks against itself — 7 services: self-reflexion, self-review, self-validation, self-evaluation, self-grading, self-improvement, self-documentation |

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
- Building a new plugin or component from scratch — use `plugin-lifecycle-upstream`

## Boundaries

**Never decides what to fix.** Every workflow surfaces findings and stops for an explicit `AskUserQuestion` decision before anything is applied — no workflow auto-selects or auto-applies a suggestion, gap, or rule fix on its own judgment.

**Never reimplements a source tool's own logic.** This skill sequences calls to `analyzing-sessions`, `plugin-comparison`, `plugin-lifecycle-downstream`'s Fix phase, the `/report-dev-rules`→`/verify-dev-rules`→`/plan-dev-rules`→`/implement-dev-rules` / `/find-dev-rule`→`/update-dev-rule` command pairs, and (for `self-service-plugin-devkit`) `plugin-grader`/`plugin-documentation`/`skill-tester`/the reviewer agents — it never re-derives a SWOT, re-implements a comparison, a score, or a doc review. The Document step (below) delegates fully to `plugin-documentation`, which both authors doc content and runs its own `human-doc-reviewer` QA internally — this skill's own role there is limited to the keep/revise/discard decision and the commit, not re-implementing the authoring or review itself.

## The Document Step (Shared Across All 4 Workflows)

After the core workflow's fix/rule-update is applied and committed, invoke `plugin-documentation` (via `Skill`) against the plugin's human-facing docs (README.md, CHANGELOG.md, CONTRIBUTING.md, etc.), passing the specific list of changed claims from the core fix. `plugin-documentation` owns its own delta-vs-full `human-doc-reviewer` QA decision internally (see its own Step 4) — do not ask a separate delta/full question here first, or the same choice gets asked twice (plugin-rulebook R26 is already satisfied by `plugin-documentation`'s own gate). "No update needed" is a common, valid outcome, not a failure. Present the authored diff and `plugin-documentation`'s own review findings; ask via `AskUserQuestion` whether to keep the changes as-is, revise, or discard. Stage and commit any kept doc changes **separately** from the core fix's own commit(s) — state the file list and message first, same discipline as every other commit in this pipeline. Keeping "what changed in the component" and "what changed in the docs" as distinct commits keeps history readable.

## Every Written Artifact Gets a Link Line

Whenever a step in any of the 4 workflows writes a file (Session Analysis Report, Comparison Report, Rules/Gap/Plan/Implementation Reports, Plugin-Grader Report), present `📄 <Artifact Name> written: \`<path>\`` as its own line before the content summary — see `workflows/improve-a-plugin.md` Step 1, `workflows/enhance-a-plugin.md` Step 1, `workflows/self-upstream-plugin-devkit.md`'s Bulk Mode steps, and `workflows/self-service-plugin-devkit.md`'s Service 5 (self-grading) for the exact pattern. Shared convention with `plugin-lifecycle-upstream` and `plugin-lifecycle-downstream`. Single-Rule mode's `find-dev-rule`/`update-dev-rule` steps are the one exception — neither writes a persisted file, so no link line applies there; don't fabricate one.

## Slash Commands Are Not `Skill`-Invocable

`/report-dev-rules`, `/verify-dev-rules`, `/plan-dev-rules`, `/implement-dev-rules`, `/find-dev-rule`, and `/update-dev-rule` each state in their own body: "This command cannot be invoked via `Skill()` — it must be triggered as a slash command or followed manually." `self-upstream-plugin-devkit.md` follows manually — `Read` the command file and execute its documented Steps directly with the given arguments, rather than attempting a tool call that doesn't exist for commands.

## Task Tracking

Use `TaskCreate` at the start of whichever workflow runs, one task per major step (finding-source dispatch, human-decision gate, apply/hand-off, Document, Commit). Mark each `in_progress` before dispatching, `completed` when its output is ready.

## Testing & Validation

This is a **manual-review checklist**, not a claim that every item below has eval coverage. Current eval evidence (`evals/plugin-lifecycle-maintenance/`, `skill-tester` Quick Workflow, 9 evals across 3 iterations, 25/25 assertions passing) covers trigger-phrase accuracy and scenarios 1, 2, 4, 5, 6, and 7 for the first 3 workflows (scenario 6's eval-7 record predates the Document step's `plugin-documentation`-delegation rewrite — eval-9 re-verifies it against the current architecture) — scenario 3 (bulk mode) and the 5 quality gates below have not yet been eval-tested; treat them as design-review-verified only until eval coverage is extended. **The `self-service-plugin-devkit` workflow (4th) has zero eval coverage as of this writing** — its own Build/Test pass verified only link resolution and trigger-phrase non-collision (see `workflows/self-service-plugin-devkit.md`'s own Testing & Validation section), not evals; the new "run a self-check on plugin-devkit" trigger phrase is likewise untested by the trigger-accuracy evals above.

1. **improve-a-plugin, findings exist** — confirm `analyzing-sessions` runs, the human is asked which suggestions to act on via `AskUserQuestion`, and the hand-off to `plugin-lifecycle-downstream`'s Fix phase happens rather than a reimplemented apply step
2. **enhance-a-plugin, findings exist** — same shape, confirm `plugin-comparison` is the finding source and the same Fix-phase hand-off happens
3. **self-upstream-plugin-devkit, bulk mode** — confirm the 4 commands run in `report → verify → plan → implement` order (not the order a naive reading of "State→Find→Plan→Implement/Update→Verify" would suggest) and the human is asked which gaps to act on before `/plan-dev-rules` runs
4. **self-upstream-plugin-devkit, single-rule mode** — confirm `/find-dev-rule`'s read-only findings are presented before `/update-dev-rule` runs, and that `/update-dev-rule`'s own built-in pre-flight confirmation is not skipped or duplicated by this skill's own gate
5. **No findings / no gaps** — confirm each workflow stops cleanly and states nothing needed action, rather than forcing a fix
6. **Document step, nothing to update** — confirm "no doc update needed" is presented as a normal outcome, not silently skipped without being stated
7. **Document step delegates to plugin-documentation** — confirm the Document step invokes `plugin-documentation` (not `human-doc-reviewer` directly) and does not ask its own separate delta/full question first — `plugin-documentation` owns that decision internally

**Quality gates:**
- [ ] Every workflow's human-decision point uses `AskUserQuestion` — never an automatic selection
- [ ] `improve-a-plugin`/`enhance-a-plugin` always hand off to `plugin-lifecycle-downstream`'s Fix phase for apply/re-validate/commit — never reimplement it
- [ ] `self-upstream-plugin-devkit`'s bulk mode always runs `report → verify → plan → implement`, matching each command's own documented Pipeline order
- [ ] The Document step always runs after the core fix is committed, and its own doc-fix commit (if any) is always separate from the core fix's commit
- [ ] The Document step always delegates to `plugin-documentation` — never calls `human-doc-reviewer` directly or asks its own separate delta/full question
- [ ] The optional Handover offer uses `AskUserQuestion`, never auto-invoked without asking
- [ ] Every written artifact (Retro/Comparison/Rules/Gap/Plan/Implementation Report) gets the standard `📄 ... written:` link line before its content summary — Single-Rule mode's chat-only outputs excepted

## Reference Guide

| Resource | Purpose |
|---|---|
| `workflows/improve-a-plugin.md` | Retro-driven improvement, full procedure |
| `workflows/enhance-a-plugin.md` | Comparison-driven enhancement, full procedure |
| `workflows/self-upstream-plugin-devkit.md` | Bulk and single-rule modernization against official docs, full procedure |
| `workflows/self-service-plugin-devkit.md` | Plugin-devkit's own 7 on-demand self-checks against itself, full procedure (includes the shared cost-gated dispatch pattern used by self-review/self-evaluation) |
| `analyzing-sessions` skill | Finding source for `improve-a-plugin`; also the SWOT/critique engine `self-reflexion` hands session digests to |
| `plugin-comparison` skill | Finding source for `enhance-a-plugin` |
| `enhancement-suggestor` agent | Expands a chosen suggestion/delta into a full WHAT/WHY/HOW plan |
| `plugin-lifecycle-downstream` skill | Reused Fix phase (apply/re-validate/commit) for `improve-a-plugin`/`enhance-a-plugin`; also `self-validation`'s Phase 1+2 dispatch |
| `plugin-grader` skill | `self-grading`'s standalone dispatch target |
| `plugin-documentation` skill | `self-documentation`'s dispatch target |
| `skill-tester` skill | `self-evaluation`'s dispatch target |
| `plugin-rulebook/scripts/agent-cost-tracker.py` | Cost estimates cited in `self-review`/`self-evaluation`'s scoped-vs-full gate |
| `plugin-documentation` skill | Document step, all 4 workflows — authors doc updates and runs its own `human-doc-reviewer` QA internally |
| `skill-maintenance` skill | Lighter-weight alternative for a single, already-known change — not this skill's job |
| `/report-dev-rules`, `/verify-dev-rules`, `/plan-dev-rules`, `/implement-dev-rules` | `self-upstream-plugin-devkit` bulk mode, in this order |
| `/find-dev-rule`, `/update-dev-rule` | `self-upstream-plugin-devkit` single-rule mode |
