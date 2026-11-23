# Design notes for /lint

- **Body step, not `!` interpolation.** The file path is an argument, so it is not placed into a `!` backtick shell line. Claude runs the linter as a body step through a scoped Bash grant, as the command-development skill advises for arguments.
- **Narrow grant.** `allowed-tools: Bash(node ${CLAUDE_PLUGIN_ROOT}/scripts/lint.js:*)` pre-approves only that one script. The variable is kept in the grant so the command stays portable across installs.
- **`argument-hint: [file]`.** One argument at position `$0`, matching the body.
- **Read-only.** The command reports findings and never edits the file or re-runs the linter, so no confirmation gate is needed.
- **Description** is 49 characters, under the 60-character `/help` guideline.
- **Not run.** I did not execute the command, because `scripts/lint.js` is not part of this skill's scope and I did not verify it exists in the plugin.
