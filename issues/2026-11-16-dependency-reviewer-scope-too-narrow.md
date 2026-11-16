## Summary
`dependency-reviewer` checks only the `Skill()`/`Agent()` call graph between skills, agents and commands. It should cover dependencies between skills, agents, commands, rules, hooks, plugins and external tools/libraries.

## Environment
- **Product/Service**: `plugins/plugin-devkit/agents/dependency-reviewer.md` (exported to `.codex/agents/dependency-reviewer.toml`); a delta-baseline reviewer of the CI `Codex delta review`
- **Region/Version**: `main` at `51fc2b13`

## Reproduction Steps
1. Read `plugins/plugin-devkit/agents/dependency-reviewer.md`, Steps 1, 2 and 5.
2. Step 1 resolves only skills (`skills/*/SKILL.md`), agents (`agents/*.md`) and commands (`commands/*.md`).
3. Step 2 builds edges only from `Skill()`/`Agent()` calls; Step 5 checks missing targets only among those three component types.

## Expected Behavior
The reviewer checks dependencies between skills, agents, commands, rules, hooks, plugins and external tools/libraries. Examples:
- a hook that calls a script;
- a rule that references a skill;
- a plugin that depends on another plugin;
- a skill that needs a CLI (`gh`, `uv`, `node`) or a Python/npm package.

For each of these it reports cycles, bidirectional coupling, required-vs-optional status and missing or unresolvable targets, as it already does for `Skill()`/`Agent()` calls.

## Actual Behavior
Only the `Skill()`/`Agent()` call graph between skills, agents and commands is checked. Dependencies of rules, hooks, plugins and external tools/libraries are not reviewed.

CI result artifacts of 167 reviewing runs (2026-09-19 to 2026-11-16) show what this means in practice:
- `dependency-reviewer` was dispatched in all 167 runs, since it is a delta-baseline reviewer.
- It reported findings in only 17 runs (10%): 18 distinct findings, 16 of them blocking, nearly all on `plugins/*/skills/` paths.
- In the 25 runs whose delta had no skill, agent or command, it found almost nothing.
- The other reviewers had findings far more often: `skill-reviewer` in 69% of its runs, `plugin-rulebook-checker` in 43%, `security-reviewer` in 28%.

Almost every blocking finding in that data came from exactly one reviewer, so the reviewer set stays as it is. This issue is about making `dependency-reviewer` cover its intended scope.

## Impact
**Low**: nothing is broken. A reviewer that costs a Codex call on every CI run covers less than intended.

## Additional Context
Expected work:
1. Compare what the agent reviews today with the intended scope above.
2. Extend its component-set resolution, graph edges and missing-target checks to rules, hooks, plugins and external tools/libraries.
3. Keep the `.codex/agents/` export in sync.
4. Re-check its yield on later CI runs.

Related: #753 (CI review cost), #568 (refactor the reviewers behind the Codex delta review).
