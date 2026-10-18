| Date | Event | Summary |
|---|---|---|
| 2026-06-29 | Merged from skill-development-ok, skill-creator-pro-todo | Combined plugin-scoped procedural guide with five-phase eval/benchmark methodology into one canonical skill-development skill |
| 2026-06-30 | Merged from test-skill-todo | Added Phase 3.5 Compliance Testing (TDD RED-GREEN-REFACTOR for skills) as a SKILL.md subsection + full methodology in references/compliance-testing.md |
| 2026-10-05 | Moved compliance-testing.md to plugin-root | `references/compliance-testing.md` moved to plugin-devkit's root `references/pdk-compliance-testing.md` so `skill-tester` shares one copy instead of reaching into this skill's folder (R34) |
| 2026-10-13 | Moved size-limits.md to plugin-root | `references/size-limits.md` moved to plugin-devkit's root `references/pdk-size-limits.md` (R33 prefix) so `skill-reviewer` and `skill-refiner-interactive` share one copy instead of reaching into this skill's folder (R34) |
| 2026-10-14 | Moved design-patterns.md to plugin-root | `references/design-patterns.md` moved to plugin-devkit's root `references/pdk-design-patterns.md` (R33 prefix) so `skill-reviewer` and `skill-refiner-interactive` share one copy (R34) |
| 2026-10-18 | Pinned every interpreter grant to one script | Replaced `Bash(python:*)` with one `Bash(python ${CLAUDE_SKILL_DIR}/scripts/<script>.py *)` grant per bundled script; `run_loop.py` and `aggregate_benchmark.py` now run by path instead of `python -m scripts.<name>` (`run_loop.py` adds its skill directory to `sys.path`). Description reworded to third person |
