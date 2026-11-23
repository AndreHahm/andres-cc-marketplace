# Design notes: /deploy command

- **Argument:** `$0` is the environment (0-based, first argument). `argument-hint: [environment]` matches it (R22).
- **No `!` shell injection on `$0`:** the skill warns that arguments are substituted into shell text before anything runs. A `!` backtick line would execute before Claude can validate, so the script is run as a body step after validation.
- **Validation:** `$0` must match `^[a-z][a-z0-9-]{0,31}$`. No environment allowlist was added because the task names none; the user can add one if the set of environments is fixed.
- **Config:** loaded with the Read tool after validation, so an invalid name never reaches a file path, and the file contents are treated as data.
- **Confirmation:** a deploy changes a live environment, so the command asks via AskUserQuestion before running the script (the skill's "confirm before destructive actions" gate).
- **Tool scoping:** `allowed-tools: Read, Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/deploy.sh:*)`. Only the reader and the one script are pre-approved.
- **Invocation note:** included because the command depends on a typed argument.
- **Not included:** no `model` field (inherits), no `disable-model-invocation` (not requested). The command writes no output files, so no update policy is needed.
- **Verification:** the bundled `validate-command.sh` and `validate-frontmatter.sh` both pass. plugin-rulebook was not run because the Skill tool was out of scope for this task.
