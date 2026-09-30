# Goal Derivation and Measurement

A refinement session states what "done" means up front and checks it at the end. A goal is derived from a pre-analysis finding, never invented, and has three parts:

- **Goal statement** — a verifiable end state, not an aspiration
- **Verification** — a concrete check that returns PASS or FAIL
- **Source finding** — the pre-analysis finding that backs the goal

## Finding → Goal → Verification

Verification uses `Grep`, `Glob` and `Read`, plus `wc -l` through the scoped `Bash(wc:*)` grant. Use the dedicated `Grep` tool for pattern matches, never `grep` through `Bash`. The scans named "the checklist's" below are the pre-analysis checks; SKILL.md step 8 loads the checklist alongside this file at measurement time. Re-run the same scan rather than restating its pattern here.

| Pre-analysis finding | Goal | Verification |
|---|---|---|
| Reference chains (ref→ref) | Zero reference→reference chains | Re-run the checklist's chain scan over `references/*.md` → 0 matches |
| Intake violations | Every intake section the operator agrees to convert uses `AskUserQuestion` with options | Re-run the checklist's intake scan → 0 matches outside sections the operator kept free-form at the Intake question |
| R22 mismatch | `argument-hint`/`arguments` consistent | `Skill(plugin-rulebook)` R22 → OK |
| Tool scoping (undeclared tool) | Every invoked tool is declared in `allowed-tools` | Re-run the checklist's tool-scoping scan → no undeclared tools |
| Dead links / cross-skill references | No dead links; cross-skill paths use the explicit `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/references/` form | `Glob` each linked `references/` path → all exist; re-run the checklist's cross-skill scan → 0 bare paths |
| Oversize files (≥400 lines) | All reference files under 400 lines | `wc -l references/*.md` → no count ≥400 |
| Large low-frequency section (≥50 lines) | No such section stays inline unless the operator chose to keep it | Re-run the checklist's large-section scan → none unapproved |
| SKILL.md above its target R13 tier | SKILL.md within the tier the operator chose | `wc -l SKILL.md` → count within that tier |
| Frontmatter issues (non-standard field, single-line `description`) | Frontmatter passes R5 and R8 | `Skill(plugin-rulebook)` R5 and R8 → OK |
| Missing goal verification | Target skill has a goal-measurement step | `Grep` for a `## Goal Verification` heading or an equivalent step → present |
| Reference clusters (same topic) | One reference file per topic | Re-list `references/`; no two files cover the same topic (operator confirms) |
| Description size outside R21 tiers | `description` and `when_to_use` within the R21 tiers | `Skill(plugin-rulebook)` R21 → OK |
| `when_to_use` split candidate | Frontmatter R21-compliant with `description` + `when_to_use` | `Skill(plugin-rulebook)` R21 → OK |
| Spawn anti-patterns | No spawn anti-patterns | Re-run the checklist's spawn scan → 0 matches |

## Selection

Derive at most 3 goals in this priority order (an ordering for choosing goals, not a severity scale; the severity of each finding comes from its own rule):

1. **First:** reference chains, intake violations, R22 mismatches
2. **Second:** undeclared tools, dead links, oversize files and sections, SKILL.md tier, frontmatter issues
3. **Third:** clusters, `when_to_use` split, spawn anti-patterns, and missing goal verification (an optional candidate: this skill's own convention, never a defect, and never added to an area the operator excluded)

Edge cases:
- **Fewer than 3 findings** — propose fewer goals; never invent one a finding doesn't back
- **More than 3 findings** — propose the 3 highest-priority goals and list the rest as "deferred candidates" in the pre-analysis report
- **Zero findings** — skip goal selection, note "no issues detected", and ask via the normal BATCH 1 questions whether to refine anything specific

## Custom Goals

An operator can type a goal under "Other". A goal with no verification can't be measured, so ask for one in a follow-up `AskUserQuestion`, and reject the goal if none is given.

## Measurement

After the validation phases, before the trigger-regression and compliance steps, for each selected goal:

1. Run its verification
2. Record PASS (result matches) or FAIL (record the actual result)
3. On FAIL, ask via `AskUserQuestion`: "Goal '[goal]' did not pass. Verification: [check]. Actual: [result]. Accept with a recorded reason, or continue refining?" — options "Accept with reason" / "Continue refining"
4. "Accept with reason" → record the operator's reason in the change summary
5. "Continue refining" → return to "Make changes" with the failed goal as the focus

A failed goal is a stop condition, not just a report line. `<skill-improvement-complete>` needs every selected goal at PASS, or each failure accepted with a recorded reason.

## Plan-Only Runs

When the session exits at the plan-only branch, no edits happen, so skip measurement. Record the selected goals and their verification checks in the draft `changes.md` so the session that applies the plan can measure them.
