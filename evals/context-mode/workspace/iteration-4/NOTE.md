# Iteration 4 (2026-11-20): Quick Workflow re-run

`skill-tester` Quick Workflow, `with_skill` only, no baseline and no timing. All 10 evals were re-run
plan-only against branch `docs/context-kit-rulebook-gaps` (issue #461) at commit `4b03923c`, whose only
change to this skill rewords a dead `references/dev.md` pointer in `references/design-history.md`. A later
commit on the same branch also added a note to that file's header; it is documentation-only and these
runs predate it. The assertions are copied unchanged from the latest iteration of each eval (iteration 1
for evals 1-8, iteration 2 for eval 9, iteration 3 for eval 10). Grading was done by the session that
dispatched the agents, not blind to the scenario.

Result: 25/26 assertions passed. First graded 26/26; a cross-model review then found that eval 8's second
assertion (report the mode from the script's answer) is not supported by the response, which takes the
mode from the scenario and never says it would relay a different script answer, so it was regraded as
failed.
