# Notes: /lint command design

## What the command does

`/lint <file>` runs the plugin's `scripts/lint.js` with `node` on one file and shows the output for review. It never edits the file.

## Choices

- **Body step, not a `!` backtick preprocessing line.** The command-development skill warns that `$0` is substituted into shell text before anything runs, so a path with quotes or metacharacters could alter the command. The skill recommends a body step that calls the script through a scoped Bash grant for untrusted input. A file path given by a user is that kind of input, so the command has Claude make one quoted `node` call.
- **Scoped grant.** `allowed-tools` is `Bash(node ${CLAUDE_PLUGIN_ROOT}/scripts/lint.js *)`, which pre-approves only that script. No `Read`, `Edit`, or `Write` is needed because the command never edits files.
- **`argument-hint: [file]`** matches the single positional argument, which is `$0` (0-based), per the skill's frontmatter guidance and plugin-rulebook R22.
- **`${CLAUDE_PLUGIN_ROOT}`** is used for the script path so the command works from any installation.
- **Early exits.** An empty argument prints the usage line. A missing file stops before the linter runs, so the user sees a clear "not found" instead of a linter error.
- **Output shown verbatim, no fixes.** The command is for review. Fixing is a separate request, which keeps the command single-purpose.
- **Non-zero exit is reported, not treated as a failure of the command.** Lint findings are expected output.
- **Invocation note** is included, as the skill's quality gates require for commands that take a typed argument.

## Assumptions

- `scripts/lint.js` exists in the plugin, accepts one file path as its only argument, and writes its result to stdout or stderr. I did not verify this, since no plugin was provided. If the script takes flags or a different argument shape, the body's step 3 needs to change.
- `node` is on `PATH`.

## Not done

- The script was not run and the command was not invoked, since no plugin or `lint.js` exists in this workspace.
