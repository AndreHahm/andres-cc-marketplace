# marketplace-inventory import-grading: target_type Rejection (live test)

Reproduced live in a scratchpad copy (real repo's marketplace-inventory.json never touched).

## Steps
1. Bootstrapped a scratch inventory for the 4 marketplace plugins.
2. Built a synthetic component-mode plugin-grader report: `target: "marketplace-inventory"`, `target_type: "skill"`, `final_score: 8.7`.
3. Ran: `python scripts/marketplace-inventory.py import-grading <scratch>/marketplace-inventory.json <scratch>/skill-report.json plugin-devkit skill`

## Result
```
marketplace-inventory only imports whole-plugin reports (target_type='plugin'); got target_type='skill' -- a component-level report belongs in plugin-inventory's own import-grading instead
EXIT CODE: 1
```
Confirmed: `plugin-devkit`'s record afterward is unchanged (`score: null`, `security_score: null`, `scoring_history_len: 0`) -- zero side effects, rejected before the inventory file is even opened.

## Why (per SKILL.md / reconciliation.md)
- `target_type` is always `plugin` for this inventory; a component-level report belongs in `plugin-inventory`'s own `import-grading` (which has no such guard -- confirmed asymmetric).
- `score`/`security_score` are import-only whole-plugin rollups, never derived from component-level scores (plugin-grader is the sole scoring authority).
- Component-mode and plugin-mode reports have genuinely different field shapes (`final_score`/`dimensions.safety_risk_handling` vs. `plugin_final_score`/`plugin_security_score`) -- accepting the wrong shape risks misreading fields rather than failing cleanly.
- Matches Testing & Validation item 7 and the Quality Gates checklist exactly.
