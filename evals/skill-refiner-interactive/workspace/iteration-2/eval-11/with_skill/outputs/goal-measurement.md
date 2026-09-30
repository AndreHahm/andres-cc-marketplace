# Goal measurement (step 8)

R13 thresholds (plugin-rulebook settings.json): >100 Weak, >300 Soft, >490 Warning, >500 Critical.

| Goal | Verification | Result |
|---|---|---|
| G1: Troubleshooting (60 lines, <20% usage) no longer inline | Large-section scan: no section >=50 lines left inline unapproved. Sections now: Workflow Steps 33 lines each, Troubleshooting 4 lines (pointer only); `Grep "Failure mode" SKILL.md` -> 0 matches | PASS |
| G2: SKILL.md within a better R13 tier (<=300 lines, i.e. out of Soft Warning) | `wc -l SKILL.md` -> 283 (was 307, Soft Warning); now Weak Warning | PASS |
| G3: Target skill has a goal-measurement step | `Grep "## Goal Verification" SKILL.md` -> line 274, present | PASS |

Notes: 283 lines includes the auto-added standard sections (When to Use, When NOT to Use, Testing & Validation, Reference Guide) and the Goal Verification section. Line count 307 -> 283 (-24). Troubleshooting content moved verbatim (55 failure modes, verified identical by diff) to references/troubleshooting.md (60 lines, under the 400 limit).
All goals PASS, so no failed-goal ask was needed.
