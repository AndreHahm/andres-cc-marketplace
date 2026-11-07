# Tool-scoping scans miss an ungranted command behind a broad Bash grant

## Summary
`skill-reviewer` and `skill-refiner-interactive` compare tool names with `allowed-tools`, so a broad grant such as `Bash(git:*)` hides a Bash command that no grant reaches.

## Environment
- **Product/Service**: plugin-devkit, `skill-reviewer` agent and `skill-refiner-interactive` skill
- **Region/Version**: PR #665 head `ef8789c0`
- **Browser/OS**: not relevant

## Reproduction Steps
1. Give a skill `allowed-tools: Read, Bash(git:*)`, and have its body run an undocumented `codacy pull-request` command.
2. Run a plan-only `skill-refiner-interactive` pass, or `skill-reviewer`, against it.
3. Read the tool-scoping result.

## Expected Behavior
Each Bash command is compared with the scoped grants before R6's deliberately-ungranted exceptions are applied, so the command is flagged.

## Actual Behavior
The scan sees `Bash` declared and flags nothing. A plan-only refinement exits before the `plugin-rulebook` check, so the plan can omit the R6 finding.

## Error Details
~~~
No error. The finding is absent.
~~~

## Visual Evidence
None.

## Impact
Severity: Low. `plugin-rulebook`'s `check_tool_grants.py` compares commands and still catches this in a full compliance check. The gap predates PR #665, so it was left out of that PR's scope.

## Additional Context
Found in PR #665, not fixed there.

## Review Finding Source

- PR: https://github.com/AndreHahm/andres-cc-marketplace/pull/665
- Head SHA: `ef8789c0de8efc22ea4010f7d783b179a58f3889`
- Review comment: https://github.com/AndreHahm/andres-cc-marketplace/pull/665#discussion_r4503222913
- Reviewer: CodeRabbit
- Severity: Minor (reviewer's label)
- Files: `plugins/plugin-devkit/agents/skill-reviewer.md:143`, `plugins/plugin-devkit/skills/skill-refiner-interactive/references/pre-analysis-checklist.md:18`
