---
description: Lint one file with lint.js and show the result
argument-hint: [file]
allowed-tools: Bash(node ${CLAUDE_PLUGIN_ROOT}/scripts/lint.js *)
---

> **Invocation:** Run as /lint <file> in the Claude Code prompt.

The file path to lint is `$0`. Treat it as a plain path, not as shell syntax.

1. If `$0` is empty, stop and reply with the usage line `Usage: /lint <file>`. Do not run anything else.
2. If `$0` does not name an existing regular file, stop and report that the file was not found. Do not run the linter.
3. Otherwise, run exactly one command, passing the path as a single quoted argument:

   `node "${CLAUDE_PLUGIN_ROOT}/scripts/lint.js" "$0"`

   Do not add pipes, redirects, or any other command around it.
4. Show the linter's output to the user, unchanged. Do not summarize it away. Keep the original order and any severity labels.
5. A non-zero exit status means the linter reported findings or failed. Report the exit status with the output. Do not treat it as a crash in this command.
6. Do not edit `$0` or any other file. Do not apply fixes. If the user wants fixes, they will ask for them separately.
