# Goal Measurement (SKILL.md step 8)

Selected goals (all three offered, all selected): measured after the step 7 validation phases, using goal-derivation.md verifications.

| # | Goal | Source finding | Verification | Result |
|---|---|---|---|---|
| 1 | No large low-frequency section stays inline unless the operator chose to keep it | Large low-frequency section: "Troubleshooting (Edge Cases)", 60 lines, est. <20% usage | Re-run the checklist's large-section scan (sections >=50 lines) over target/SKILL.md; Grep `^- Failure mode` in SKILL.md | PASS. Longest section is now Workflow Step N at 33 lines; Troubleshooting is a 3-line pointer; 0 `Failure mode` bullets remain inline (55 live in references/troubleshooting.md). |
| 2 | SKILL.md within the target R13 tier (operator-chosen target: below Soft Warning, i.e. <300 lines) | SKILL.md above its target R13 tier (307 lines, Soft Warning) | `wc -l target/SKILL.md` -> count within tier | PASS. 271 lines (was 307; net -36), tier Weak Warning (100-299). |
| 3 | Target skill has a goal-measurement step (optional, low-priority candidate) | Missing goal verification | Grep for a `## Goal Verification` heading -> present | PASS. `## Goal Verification` heading present (added, 3 lines). |

Outcome: 3/3 PASS, no failures, so no "Accept with reason / Continue refining" question was needed.

Not measured / caveat: step 10 (`Skill(plugin-rulebook)` and `skill-reviewer`) cannot be run in this dry run, so `<skill-improvement-complete>` is NOT emitted even though every selected goal passed.
