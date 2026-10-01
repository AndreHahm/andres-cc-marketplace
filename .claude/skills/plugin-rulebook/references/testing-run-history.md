# Plugin Rulebook — Testing Run History

Full dated run records for this skill. SKILL.md keeps only the latest summary.

Iterations 1-2 (2026-08-15), `evals/plugin-rulebook/` — eval-1: 4/4 assertions passed;
eval-2: 2/2 assertions passed (both `with_skill`, via `skill-tester`'s blind-comparison harness).
Iteration-3 (2026-09-24, `skill-tester` Quick Workflow, `with_skill`-only): eval-3 (R27 applies
verb-first to the filename portion after an R33-registered prefix) 3/3 assertions passed; eval-4 (R27
still checks the full basename when no prefix is registered) 3/3 assertions passed.
Iteration-4 (2026-09-30, same harness, `with_skill`-only, PR 11's R33 wording change): evals 3-4 re-run as regressions
(3/3, 3/3), plus new eval-5 (explicit `prefix: null` is an inert opt-out) 3/3, eval-6 (registered `pdk` still flags a
mis-prefixed file; `__init__.py` exempt) 3/3, eval-7 (an absent `prefix` key is a finding, not silently inert) 3/3.
Iteration-5 (2026-09-30, after a cross-model-review fix round reworded R33's null/absent-key text and eval 4's premise):
evals 4, 5, 7 re-run against the reworded files, 3/3 each.
See `evals/plugin-rulebook/evals.json` for the scenario definitions. R33's own `test-against-example-
plugin.md` dry-run record: `.claude/output/plugin-rulebook/example-plugin-20260923T204026Z.md`.
Iteration-6 (2026-10-01, same harness, `with_skill`-only, R34/R35 added): eval-8 (R34: a `..` link into plugin-root `references/` passes, a link into `docs/` and a dead link are Critical) 4/4; eval-9 (R35: `When to Use This Skill` satisfies `When to Use`, `Reference Guide` only required with a `references/` directory, Testing & Validation left to R29) 4/4. Agents were pointed at the worktree files directly, since a by-name skill dispatch resolves to the main checkout's copy.
