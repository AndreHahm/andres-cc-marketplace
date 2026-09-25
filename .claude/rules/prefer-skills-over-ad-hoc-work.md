# Prefer Skills Over Ad Hoc Work

## When this applies

Any point in a session where a task is about to be solved freehand (reimplementing behavior from
scratch) while a skill already listed in this session's available-skills listing covers the same task.

## Rule

Before solving a task ad hoc, check whether a listed skill already covers it, and dispatch that skill
instead of reimplementing the same behavior freehand. This is a strong default, not an absolute: if no
skill actually fits the task, proceed ad hoc as normal — don't force a mismatched skill onto a task it
doesn't cover.

## Incorrect

A session needs to create a git branch for new work and just runs `git checkout -b feature/x` directly,
or names a new plugin rule file without first checking the rulebook's naming conventions, even though
`starting-work` and the naming-conventions reference exist for exactly these tasks.

## Correct

The session dispatches `Skill(starting-work)` to create the branch — syncing main, validating the name,
asking worktree vs. plain branch first — and reads `plugin-rulebook/references/naming-conventions.md`
before naming a new rule file, using the skill's own instructions instead of reimplementing its logic
from scratch.

## Why

This is the general default that this repo's own domain-specific routing rules already assume — e.g.
[[route-through-git-kit-lifecycle-skills]] for git/GitHub operations,
`.claude/rules/plugin-rulebook-enforcement.md` for plugin-component compliance, and
`.claude/rules/consult-naming-conventions-first.md` for naming. Skills exist specifically so behavior
stays consistent and rule-compliant across sessions; solving the same problem freehand skips whatever the
skill's own instructions (rule loading, gating, formatting, required checks) would otherwise have
enforced. Stated here as a standalone, repo-wide general principle rather than leaving it implicit in
each domain-specific rule.

## Enforcement

Policy gate, no backing hook — the same disclosed-limitation model most process rules in this repo use.
Whether a listed skill actually "covers" a given task is a semantic judgment, not something a mechanical
hook can verify; compliance depends on author/reviewer attention in the moment.
