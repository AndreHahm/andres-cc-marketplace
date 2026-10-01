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
Iteration-7 (2026-10-01, same harness, `with_skill`-only, R36/R37 added): eval-10 (R36: an overlapping one-way exclusion is an ADVISORY finding against the other component, pure delegation is not) 4/4; eval-11 (R37: a bare-path hook script at committed mode 100644 fails even with `shell: bash` set, the committed mode not the on-disk bit counts, an interpreter grant is not a direct invocation) 4/4. Same worktree-file pointing as iteration 6.
Iteration-8 (2026-10-01, same harness, `with_skill`-only, R9/R14/R21/R31 extensions): eval-12 (R9: a real username in a committed eval output fails; a placeholder name and a redaction-test example do not) 4/4; eval-13 (R14: a reference file that requires loading another is an ADVISORY chain; a see-also and SKILL.md pointers are not) 4/4; eval-14 (R21: ADVISORY only above 900 chars with a trigger clause and no `when_to_use`) 4/4; eval-15 (R31: a workspace eval with no registry entry is a gap, `eval_id` is an accepted form) 4/4. The eval-15 agent had no write tool, so its answer file was saved by the coordinator from the returned report.
