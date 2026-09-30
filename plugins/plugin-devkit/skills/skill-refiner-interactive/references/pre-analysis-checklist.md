# Pre-Analysis Checklist

Run immediately after locating the target skill, before any interview. Emit the report at the end so the operator can scope findings into the refinement interview.

## Checks

- Check for `plugin-rulebook` skill (Glob `**/plugin-rulebook/SKILL.md`); if found, read its `assets/settings.json` and load BOTH R13 (SKILL.md line-count) and R18 (inline code-block size) tiered thresholds — these supersede the flat limits below for the rest of pre-analysis. If not found, fall back to `${CLAUDE_PLUGIN_ROOT}/skills/skill-development/references/size-limits.md`'s flat 500-line / 10-line limits.
- Read SKILL.md; count body lines (exclude frontmatter); classify against the resolved R13 tiers (OK / Weak Warning / Soft Warning / Warning / Critical) — don't treat 500 as the only threshold worth reporting; a Soft Warning at, say, 350 lines is worth surfacing even though it's non-blocking
- Scan frontmatter: flag non-standard fields per `plugin-rulebook`'s R5 (if found in the check above — currently just `version`; treat R5's own text as authoritative rather than restating its list here, since it's the source of truth this file would otherwise drift from), single-line `description` (needs `>-`) — `allowed-tools` may be space-separated, comma-separated, or a YAML list (space-separated is preferred style, not a requirement), and `argument-hint` is an allowed skill field, not a violation. If `plugin-rulebook` wasn't found, fall back to: `version` is the only forbidden field; `AskUserQuestion` in `allowed-tools` is a harmless no-op, not a violation.
- Identify sections ≥50 lines; classify core (80%+ usage) vs. low-frequency (<20%)
- List reference files; note topically related clusters (≥2 files, same domain); flag any `references/*.md` ≥400 lines
- Check all `workflows/*.md`; flag any ≥300 lines; scan each for links to `references/` files used as action steps (workflow→reference chain violation); also scan each `references/*.md` for imperative directives to read another `references/` file (reference→reference chain violation)
- Scan SKILL.md and all `references/*.md` for spawn anti-patterns: Cartesian product spawning (subagents spawned for every combination of two or more independent lists), unbounded agent spawning (spawn inside a loop with no explicit count cap where the list is user-controlled), vague subagent prompts (dispatch instructions with no file paths, no goal statement, no output spec)
- Scan SKILL.md for sections that handle user intake: grep for `ask the user`, `prompt the user`, free-form `questions:` blocks (i.e., `questions:` key present but no `options:` key in the same block). Flag each as a behavioral intake violation — sections that collect input without `AskUserQuestion` should be converted to use it
- Check R22 argument-hint/arguments consistency: if `plugin-rulebook` was found above, read `${CLAUDE_PLUGIN_ROOT}/skills/plugin-rulebook/references/argument-consistency.md` for the detection procedure; otherwise scan the body directly for `$ARGUMENTS`, `$ARGUMENTS[N]`, a bare unescaped `$0`/`$1`/`$2`/..., or `$name` for a name declared in `arguments`. Compare against frontmatter `argument-hint`/`arguments`: flag a missing declaration (body accepts arguments but frontmatter is empty), an orphaned declaration (frontmatter declares a slot never referenced in the body), or a wrong-position mismatch (declared order doesn't match consumption order). Catching this in pre-analysis lets the operator fix it as part of BATCH 2 instead of only via the mandatory `plugin-rulebook` gate at the end of the workflow.
- Check for a `when_to_use`-split candidate: if no `when_to_use` field is present, scan `description` for an embedded trigger-condition clause (e.g., a `Use when` / `use when` phrase mid-description). If found and `description` alone exceeds roughly 400 characters, flag it — the trigger conditions could move to `when_to_use`, tightening `description` to the "what" per `skill-development`'s What+When formula (see `${CLAUDE_PLUGIN_ROOT}/skills/skill-development/references/content-guidelines.md`).
- Tool scoping (both directions): scan SKILL.md body and all `references/*.md` for tool names used as actual invocations (Read, Write, Edit, Glob, Grep, Agent, Skill, Bash, Task, TodoRead, TodoWrite). Compare against `allowed-tools`: flag any tool used but not declared as Major (R6 violation — the agent will be blocked at runtime), and any tool declared but not used as Minor (over-permissioning). Exclude `AskUserQuestion` from the undeclared-tool flag — it is always callable, so listing it is an ADVISORY no-op per `plugin-rulebook`'s `references/frontmatter-corrections.md` (R5). Tool names appearing only in descriptive prose (e.g., an example table recommending tools for *other* skills) are not invocations — distinguish actual instructions to the operator from descriptive references.
- Dead links and cross-skill references: scan all `references/` paths in SKILL.md and all `references/*.md` files. Flag (a) dead links — paths to files that don't exist locally, and (b) cross-skill references — paths into another skill's internal `references/` directory (e.g., `skill-development/references/X.md`). Cross-skill references are fragile: if the target skill moves or renames the file, the reference breaks silently. Recommend making cross-skill paths explicit using `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/references/X.md` form, or moving shared content to a plugin-root `references/` file.
- Missing standard sections: verify all 5 standard body sections are present: `## When to Use`, `## When NOT to Use`, `## Quick Start` (or equivalent entry workflow), `## Testing & Validation`, `## Reference Guide`. Flag any missing section as Minor — these are auto-addable per the standard-section policy in the refinement workflow.
- Goal verification: check whether the target skill has a `## Goal Verification` section or equivalent per-session goal-measurement step at the end of its workflow. If absent, flag as Missing — AGENTS.md §4 requires "Define success criteria. Loop until verified." The target skill's quality gates may check generic correctness, but per-session goal measurement ties the output back to the operator's specific intent.

## Report Template

```
📋 Pre-Analysis: <skill-name>
Lines: X — [OK | Weak Warning | Soft Warning | Warning | Critical] (R13)
Frontmatter issues: [list or "none"]
Large sections (≥50 lines): [name — X lines | "none"]
Reference files: N [clusters: list | "none"] [oversize ≥400 lines: list | "none"]
Workflow files: N [oversize ≥300 lines: list | "none"] [workflow→ref chain violations: list | "none"]
Reference chain violations (ref→ref): [list | "none"]
Spawn anti-patterns: [list | "none"]
Intake pattern violations: [section name — reason | "none"]
Argument consistency (R22): [mismatch description | "none"]
when_to_use split candidate: [description length + embedded trigger clause | "no"]
Tool scoping (R6): [undeclared tools list | "none"] / [unused declared tools list | "none"]
Dead links: [list | "none"] / Cross-skill references: [list | "none"]
Missing standard sections: [list | "all 5 present"]
Goal verification: [present | "absent — flag as Missing"]
R13/R18 threshold source: [plugin-rulebook/assets/settings.json | skill-development fallback]
```
