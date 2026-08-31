## Summary
Run a fresh `skill-tester` Full Pipeline against all 7 `workmanagement-kit` skills, closing the R28 eval-scenario-count gap first — needed to remove the "qualified" status on the plugin's current 9.9/10 `plugin-grader` score.

## Context
- **Product/Service**: `workmanagement-kit` plugin (`plugins/workmanagement-kit/`), all 7 skills: `notion-knowledge-management`, `linear-work-management`, `idea-to-implementation`, `status-and-learning`, `work-linking`, `open-item-management`, `plugin-integration-intake`
- **Related work**: `plugin-lifecycle-downstream` QA run, 2026-08-30/31

## Scoped Work

1. **Before the pipeline run**: add a 3rd eval scenario to each of the 7 `evals/<skill>/evals.json` files (each currently has 2, below `plugin-rulebook`'s advisory `min_eval_scenarios: 3`), and populate the `testing_validation_coverage` field in each (currently absent from all 7 entirely). Do this as part of the same `skill-tester` pass per that skill's own Step 2.1b cross-check, not a separate pass beforehand.
2. **Run a fresh `skill-tester` Full Pipeline** against all 7 skills. The existing eval evidence under `evals/<skill>/workspace/iteration-1/` was produced *before* this session's `plugin-lifecycle-downstream` Phase 5/6 fixes changed substantial skill behavior: approval-gate logic (all 7 skills gained `AskUserQuestion`), allowed-tools grants (narrowed `Skill(...)` scoping), activation triggers (several exclusion/trigger fixes), data-only boundary scope (broadened in 4 skills), and the Decision Propose approval requirement (`notion-knowledge-management`). This staleness is the sole reason `plugin-grader`'s Testing dimension currently scores 10/10 from a file-existence heuristic without actually certifying current behavior.

## Impact
**Low** (no functional gap — the plugin behaves correctly per 2 rounds of independent reviewer re-verification) but **blocks** an unqualified grading result, and leaves the plugin's own Testing evidence not reflective of its current code.

## Additional Context
**Caution for whoever runs this**: a prior Full Pipeline run in this same session had baseline eval dispatches with unscoped live Linear/Notion MCP tool access create real, unintended artifacts in the user's live workspaces (a real Linear issue and a real Notion page, both left in place per the user's own instruction to handle them personally). Scope or sandbox that MCP access before re-running this pipeline.
