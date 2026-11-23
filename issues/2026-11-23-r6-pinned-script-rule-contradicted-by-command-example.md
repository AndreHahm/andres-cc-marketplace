## Summary
A `command-development` example still shows a wildcard `bash` script grant, which plugin-rulebook's R6 text now says only passes for one pinned script path.

## Environment
- **Product/Service**: plugin-devkit: `plugin-rulebook` R6 (`references/compact-rule-checklist.md`, `references/frontmatter-corrections.md`) and `command-development` (`examples/plugin-commands.md`), plus their `.claude/` mirror copies
- **Region/Version**: `main` at `809c6931`
- **Browser/OS**: not applicable

## Reproduction Steps
1. Read the R6 row in `plugins/plugin-devkit/skills/plugin-rulebook/references/compact-rule-checklist.md` (line 29). After listing bare interpreter grants as violations, it says "(bare interpreter only; an interpreter followed by one pinned script path passes; ...)".
2. Read the `commands/run-checks.md` example in `plugins/plugin-devkit/skills/command-development/examples/plugin-commands.md` (line 403). Its frontmatter is `allowed-tools: Bash(echo:*), Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/*.sh:*), Read`.
3. Compare the two.

## Expected Behavior
The example and R6 agree. An author who copies the example gets a grant that R6 accepts.

## Actual Behavior
The example grants `bash` on a wildcard set of scripts (`scripts/*.sh`), not one pinned script path. Its body runs six different scripts: `test-full.sh`, `security-scan.sh`, `perf-check.sh`, `compliance.sh`, `test-basic.sh` and `lint.sh`. Under R6's current wording the example teaches a grant that R6 would flag.

The pinned-path wording came from PR #524 (commit `660892b0`, "fix(git-kit): launch marker script through bash"). The example predates it: it is already on `bce78f7b`, the base of that change.

## Error Details
~~~
plugin-rulebook-checker, Major, R20 duplicate fact sweep,
plugins/plugin-devkit/skills/plugin-rulebook/references/compact-rule-checklist.md:29:
"The changed R6 checklist now permits an interpreter grant only when it pins one script
path. The sibling command example still grants Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/*.sh:*),
which covers a wildcard set rather than one pinned script, and presents it as a valid example."
~~~

## Visual Evidence
None. The finding came from a local replay of PR #524's Codex delta review with today's reviewer briefing, done while working on #525.

## Impact
**Low** - documentation inconsistency, and a workaround exists. Authors who copy the example get a grant the rulebook flags. The contradiction also lets `plugin-rulebook-checker` raise a blocking R20 finding on any PR that edits the R6 line.

## Additional Context
- Two ways to fix it, not decided:
  - (a) Change the example to six pinned grants, one per script its body runs.
  - (b) If a wildcard under a plugin's own `scripts/` directory is meant to pass, say so in R6.
- R20 sweep: update the `.claude/` mirrors too (`.claude/skills/command-development/examples/plugin-commands.md`, `.claude/skills/plugin-rulebook/references/compact-rule-checklist.md`, `.claude/skills/plugin-rulebook/references/frontmatter-corrections.md`), and check every other R6 restatement, such as plugin-rulebook's `SKILL.md`.
- Related: #564 (audit of interpreter-wide grants in component frontmatter; this issue is about a documentation example, not a component grant), #525, PR #524.
