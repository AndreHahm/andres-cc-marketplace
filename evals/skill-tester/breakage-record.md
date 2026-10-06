# skill-tester smoke test: breakage record

Run date: 2026-10-06 (supersedes the 2026-10-05 run of 9 breakages). Smoke test under test: `plugins/plugin-devkit/skills/skill-tester/scripts/smoke_test.py` (7 checks, with the `Edit` check anchored to Step 7.2's own instruction).

Method: for each breakage, a copy of the skill folder (plus the plugin-root `references/` folder, so `${CLAUDE_SKILL_DIR}/../../references/` still resolves) was made in a temporary directory,
one deliberate defect was applied to the copy, and `scripts/smoke_test.py` was run inside it. A breakage counts as caught when the run exits 1 and at least one check prints FAIL.
The real skill folder was never modified by these runs.

| # | Deliberate breakage | Result | Check that caught it | First FAIL message (truncated) |
|---|---|---|---|---|
| 1 | restore unused Glob/Grep | CAUGHT | `check_declared_tools_used` | declared but never used in the body: Glob, Grep |
| 2 | dead references/ path | CAUGHT | `check_referenced_files` | referenced file(s) do not exist: SKILL.md: references/nope.md |
| 3 | banker's rounding in ruby_round | CAUGHT | `check_aggregate_fixture` | ruby_round no longer rounds half away from zero |
| 4 | ungranted command in bash block | CAUGHT | `check_bash_grants` | body invokes command(s) not covered by any granted Bash scope: node |
| 5 | orphan reference file | CAUGHT | `check_no_orphans` | files not referenced from SKILL.md: references/extra.md |
| 6 | lexicographic eval sort | CAUGHT | `check_aggregate_fixture` | eval order [10, 2] (want numeric [2, 10]); eval-2 delta {'pass_rate': 0.5, 'tokens': 200, 'duration_ms': 3000} |
| 7 | dead shared ../../references path | CAUGHT | `check_referenced_files` | referenced file(s) do not exist: SKILL.md: ${CLAUDE_SKILL_DIR}/../../references/pdk-compliance-missing.md |
| 8 | unsigned negative improvement print | CAUGHT | `check_negative_improvement_output` | negative improvement not printed as '-50.0': 'ry:\n  Evals processed: 1\n  With Skill pass rate: 25.0%\n  Bas |
| 9 | python3 invoked under a python grant | CAUGHT | `check_bash_grants` | body invokes command(s) not covered by any granted Bash scope: python3 |
| 10 | remove Step 7.2 direct-edit instruction (Edit unused) | CAUGHT | `check_declared_tools_used` | declared but never used in the body: Edit |

Result: 10 of 10 breakages caught.
