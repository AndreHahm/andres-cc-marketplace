# Review of draft `build-env` command

Skill used: `command-development` (worktree copy, `plugins/plugin-devkit/skills/command-development/`).
Bundled validators (`validate-command.sh`, `validate-frontmatter.sh`) pass on the corrected file, but they
check structure and frontmatter only. They do not catch any of the problems below, so the fixes rest on the
skill's guidance (`SKILL.md` Dynamic Arguments / Bash Execution / Quality gates, `examples/plugin-commands.md`
examples 9 and 10 and "Common Mistakes", `references/frontmatter-reference.md`).

## Problems found and fixes

1. **The build runs before the validation gate (critical).**
   The `Build:` line is a `!` preload that runs `bash build.sh $0` when the command loads. The `Validate:` line
   is also a `!` preload, so it cannot stop anything. The text "If the validation passed:" only tells Claude what
   to do afterwards; the build has already run for `INVALID` input.
   Fix: validation moves into the body. The build is a Bash tool step that runs only after the environment is
   accepted. (Skill guidance: `examples/plugin-commands.md` example 9 and the "Not validating inputs" mistake.)

2. **Unquoted, unvalidated `$0` is substituted into shell text (injection).**
   `$0` is substituted into the shell string as raw text. `bash build.sh $0` with a value such as
   `dev; rm -rf ~` or `$(...)` reaches the shell. The `echo "$0"` validator is also inside shell quotes, so a
   value containing `"` breaks out of it.
   Fix: the Bash step uses the validated name only, quoted (`"<environment>"`), and no `$0` appears in any shell text.
   (Skill guidance: `examples/plugin-commands.md` "Pattern: Input Validation" and the note that arguments are
   substituted into shell text as-is.)

3. **Unvalidated `$0` is used as a path in an `@` include (path traversal).**
   `@${CLAUDE_PLUGIN_ROOT}/config/$0.json` expands at load time, before any check. A value such as `../../x` reads
   an arbitrary file, and that happens even when the validation line would later say `INVALID`.
   Fix: no `@` include. The config is read with the Read tool after validation, using the validated name. The
   `Read` grant is scoped to `config/*.json`. (Skill guidance: `plugin-features-reference.md` "Multi-Step
   Plugin Workflows" and example 9's config step.)

4. **`grep` is used by the validator but is not pre-approved.**
   `allowed-tools` lists only `Bash(echo:*)` and the build script. The validation pipeline
   `echo ... | grep -E ...` would prompt or fail. Fix: the grep is removed (validation is now in the body), so
   `Bash(echo:*)` is removed too, because nothing uses it. (Skill guidance: "allowed-tools ... contains only what
   the command actually uses", SKILL.md Testing & Validation step 5.)

5. **Unscoped `Read` grant.**
   Plain `Read` allows any file. The command only needs the plugin's config files.
   Fix: `Read(${CLAUDE_PLUGIN_ROOT}/config/*.json)`, as in example 9. Note: the variable inside a grant pattern is
   copied from the skill's own examples, not verified against this environment. If a grant with the variable is
   not honored, Claude Code will prompt for it. The skill does not claim that it works.

6. **Vague `description`.**
   "Build for an environment" does not say what it does. Fix: "Build the plugin for a dev, staging or prod
   environment" (56 chars, under the 60-character `/help` guideline). Frontmatter reference: start with a verb,
   be specific.

7. **Missing invocation note.**
   The command is multi-step and depends on a typed argument, so the SKILL.md quality gate requires an invocation
   note. Fix: `> **Invocation:** Run as /build-env <environment> in the Claude Code prompt.`

8. **No defined stop path for an invalid or missing environment.**
   The draft emits `INVALID` and then continues. Fix: the body says to stop, report the problem and ask for one of
   the three valid values, and not to read config or run any script. Config-file-missing also stops and reports.

9. **Final step was too thin.**
   "Report the build status." does not say what counts as success or what to show on failure. Fix: report whether
   the build step succeeded and any errors it printed.

## Considered and not changed

- `disable-model-invocation: true`: not added. A build is not destructive or irreversible, and the skill says to use
  this sparingly. If the build ever deploys or publishes, revisit it.
- An existence check for `build.sh` (example 9's `test -x`): not added, to keep the command minimal. Bash will report
  a missing script at the build step anyway.
- `Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/build.sh:*)` keeps the `:*` suffix so the environment argument is allowed.
  The argument is validated in the body first, so the grant does not widen what runs.
- `model`: not set. Nothing here needs a different model.
- Whether `build.sh` itself checks its argument: not in scope (the script was not provided). Defense in depth would
  have the script reject any value other than dev, staging or prod.

## Not verified

- The `plugin-rulebook` check the skill asks for before finalizing was not run, because the user prohibited the Skill
  tool for this task. The compliance check (R22 argument-hint order, R1-R37 in general) is therefore still open.
- The behavior of the variable-based `Read(...)` grant and the `bash ${CLAUDE_PLUGIN_ROOT}/...` grant at runtime was
  not tested. No live invocation of the command was run.
