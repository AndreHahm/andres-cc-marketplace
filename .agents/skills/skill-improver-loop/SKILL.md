---
name: skill-improver-loop
description: >-
  Iteratively reviews and improves Codex skills by running automated
  fix-review cycles until no critical or major issues remain. Use when fixing
  multiple skill quality issues, running automated improvement loops, iterating
  a skill until it passes skill-reviewer, or enforcing consistent quality
  without manual editing. NOT for one-time reviews — use /skill-reviewer
  directly. For manual, conversational refinement with a user checkpoint
  at each step, use skill-refiner-interactive instead — this skill runs
  unattended automated cycles with no interactive checkpoints.
allowed-tools: Read Edit Write Glob Grep Task Skill
---

# Skill Improvement Methodology

Iteratively improve a Codex skill using the `skill-reviewer` agent until it meets quality standards.

## Prerequisites

Requires the `plugin-devkit` plugin, which provides the `skill-reviewer` agent.

Verify it's enabled: run `/plugins` — `plugin-devkit` should appear in the list.

## Skill Location

Search in this order:

1. **Project paths (preferred):** `skills/skill-name/` or `.Codex/skills/skill-name/` in current project
2. **User-space (fallback):** `~/.Codex/skills/skill-name/` — only if not in project
3. **Cache paths (forbidden):** `~/.Codex/plugins/cache/*` — REFUSE; read-only installed copies

Use Glob `**/SKILL.md` to find all skills in the project.

### Scope Rules

| Path type | Action |
|---|---|
| `skills/*/` or `.Codex/skills/*/` in project | ✅ Edit freely |
| `~/.Codex/skills/*/` | ⚠️ Only if not in project |
| `~/.Codex/plugins/cache/*` or any `/cache/` path | ❌ REFUSE immediately |

## Quick Start

1. **Locate** — Find the skill directory using the Skill Location rules above
2. **Review** — Call `skill-reviewer` on the target skill in Structured output mode (see "Invoking skill-reviewer" below)
3. **Categorize** — Read `counts` and `findings[].severity` directly from the returned YAML — no prose-parsing needed. See `${CLAUDE_SKILL_DIR}/references/issue-categorization.md` for what Critical / Major / Minor mean when deciding fixes
4. **Fix** — Address critical and major issues. For structural changes (moving, reorganizing content), follow `${CLAUDE_SKILL_DIR}/references/structural-changes.md`
5. **Validate** — Run post-fix validation phases before the next review cycle. See `${CLAUDE_SKILL_DIR}/references/post-fix-validation.md`. For plugin-rule compliance (naming, language, tool-scoping, formatting), invoke `plugin-rulebook` via the `Skill` tool and treat any violations as Major issues.
6. **Evaluate** — Check each minor issue individually before fixing. See `${CLAUDE_SKILL_DIR}/references/issue-categorization.md` for evaluation criteria
7. **Repeat** — Continue until `counts.critical == 0` and `counts.major == 0`. Abort after 3 cycles: if either count is still nonzero, report the remaining findings and stop — do not loop indefinitely.

## When to Use

- Improving a skill with multiple quality issues
- Iterating on a new skill until it meets standards
- Automated fix-review cycles instead of manual editing
- Consistent quality enforcement across skills

## When NOT to Use

- **One-time review**: Use `/skill-reviewer` directly instead
- **Quick single fixes**: Edit the file directly
- **Non-skill files**: Only works on SKILL.md files
- **Experimental skills**: Manual iteration gives more control
- **Creating a new skill from scratch**: Use `skill-development` instead
- **Empirical benchmarking/eval-driven testing with baseline comparison**: Use `skill-tester` instead

## Invoking skill-reviewer

```
Review the skill at [SKILL_PATH] using the plugin-devkit:skill-reviewer agent in Structured output mode. Return YAML only, per skill-reviewer's own Structured Output Mode schema.
```

Replace `[SKILL_PATH]` with the absolute path to the skill directory. Invoke via the `Task` tool with `subagent_type='plugin-devkit:skill-reviewer'`. Parse the returned YAML directly: `counts.critical`/`counts.major` drive the loop-termination check (steps 3/7 above), `verdict` drives the Completion Criteria check below, and `findings[]` (each with `severity`/`location`/`finding`/`fix`) is the issue list to work through in step 4. If the response isn't valid YAML with `counts`/`verdict` present, treat `skill-reviewer` as unavailable — see Testing & Validation gate 4.

## Completion Criteria

**CRITICAL**: The stop hook checks for this exact marker only — no other signal terminates the loop.

```
<skill-improvement-complete>
```

Output when: (1) skill-reviewer's structured output has `verdict: Pass` or `S-Tier` with `counts.critical: 0` and `counts.major: 0`, (2) all critical and major issues are fixed and verified by re-running skill-reviewer, or (3) remaining issues are only minor and evaluated individually as false positives or not worth fixing.

Do NOT output while any critical or major issue remains unfixed.

## Testing & Validation

After invoking the skill, verify:

1. **Trigger phrases** — confirm skill activates on: "fix my skill", "improve skill quality", "run the improvement loop", "iterate until it passes skill-reviewer"
2. **Non-triggers** — confirm skill does NOT activate on: "review my skill once", "create a new skill", "check plugin structure"
3. **Loop termination** — skill emits `<skill-improvement-complete>` on its own line when done; stop hook detects via whole-line match
4. **skill-reviewer reachable** — `Task` tool with `subagent_type='plugin-devkit:skill-reviewer'` succeeds; stop hook surfaces the error and halts if unavailable
5. **Structured output parses** — the response is valid YAML with `counts`/`verdict`/`findings` present; if not, treat skill-reviewer as unavailable rather than falling back to prose-parsing

**Quality gates:**
- [ ] `Task` and `Skill` are in `allowed-tools` before activating the loop
- [ ] `plugin-devkit` plugin is installed (run `/plugins` to verify)
- [ ] Loop does not emit `<skill-improvement-complete>` while `counts.critical` or `counts.major` is nonzero
- [ ] Every `skill-reviewer` call requests Structured output mode — never parsed from the narrative report format

## Gotchas

- **Marking complete without re-running skill-reviewer.** After applying fixes, always re-run skill-reviewer to verify — a fix can introduce new issues that invalidate the earlier pass.
- **Skipping minor issue evaluation.** Evaluate each minor issue individually. Some are false positives; some are genuine improvements. Blanket skip or blanket accept both lead to wrong outcomes.
- **Editing cache-path skills.** `~/.Codex/plugins/cache/*` contains read-only installed copies. REFUSE edits immediately and report the correct editable path to the user.

## Rationalizations to Reject

- "I'll mark it complete and come back later" — Fix issues now
- "This minor issue seems wrong, skip all of them" — Evaluate each one individually
- "The reviewer is being too strict" — The quality bar exists for a reason
- "It's good enough" — If there are major issues, it's not good enough

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/issue-categorization.md` | Critical / Major / Minor definitions and minor issue evaluation criteria |
| `references/structural-changes.md` | Pre-change gates and movement pattern for reorganizing content |
| `references/post-fix-validation.md` | Seven-phase validation to run after fixes, before next review cycle |
| `plugin-rulebook` skill | Active rule configuration for naming, language, tool-scoping, and formatting compliance |
