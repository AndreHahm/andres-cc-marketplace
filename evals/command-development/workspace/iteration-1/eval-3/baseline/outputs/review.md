# Review of draft `build-env.md` (command-development skill, baseline run)

## Problems found and fixes

1. **The build runs unconditionally at load time (critical logic bug).**
   The `Build:` line uses `` !`bash ${CLAUDE_PLUGIN_ROOT}/scripts/build.sh $0` ``. A `!` backtick executes when the command loads, before Claude reads the "If the validation passed" condition. An invalid environment still runs the build. Fix: remove the `!` build and run the build as a body step (step 3) that Claude performs only after validation passes. The skill's Bash Execution and Validation Patterns guidance says to stop when validation fails. This draft has no stop branch at all.

2. **Configuration is loaded before validation (path traversal risk).**
   `@${CLAUDE_PLUGIN_ROOT}/config/$0.json` injects the file at load time, whatever `$0` is. A value such as `../../something` reads an arbitrary `.json` file from outside the config directory. Fix: load the config with the Read tool in step 2, only after step 1 has accepted one of the three fixed names.

3. **Validation runs through the shell with the raw argument (command-injection risk).**
   `` !`echo "$0" | grep ...` `` substitutes `$0` into shell text before it runs. Inside double quotes, `$(...)` and backticks still execute, so an argument like `$(touch x)` runs code. Quoting does not stop this. The skill says to have the script validate an argument, or to keep untrusted input out of `!` lines and use a scoped Bash grant in a body step. Fix: validate by plain-text comparison in the prompt (step 1), with no shell involved.

4. **Validation output is ambiguous and the failure branch is missing.**
   On success, `grep` prints the matched name. On failure, `echo` prints `INVALID`. The body's "If the validation passed:" does not define what a pass looks like, and it never tells Claude to stop and report on `INVALID`. Fix: a literal, explicit stop-and-report branch for invalid input (step 1).

5. **`allowed-tools` does not cover the validation pipeline.**
   `Bash(echo:*)` pre-approves `echo` only. The pipeline's `grep` has no grant, so it would prompt. Fix: the shell validation is gone, so `Bash(echo:*)` is removed. `Read` is kept for the config step. The Bash grant is narrowed to the one build script, with the same `${CLAUDE_PLUGIN_ROOT}` form the skill's own examples use.

6. **Unquoted `$0` in the build line.**
   `bash build.sh $0` is unquoted, so word splitting and globbing apply. This is moot after fix 1, since the build now receives the validated name, not the raw argument.

7. **Missing invocation note.**
   The skill's Best Practices and Quality Gates require a multi-step command that depends on typed arguments to state how it is run. Fix: added `> **Invocation:** Run as /build-env <environment> ...`.

8. **Vague report step.**
   "Report the build status" does not say what to report or what counts as success. Fix: report the exit code and the last lines of output, and do not claim success unless the exit code is 0.

9. **Description could name the object more precisely.**
   "Build for an environment" is short and verb-led, so the fix is small: "Build the project for an environment" (under 60 characters, verb first). This is a minor wording change, not a rule violation.

## Checked and left unchanged

- `argument-hint: [environment]` matches the single argument, `$0`, which is 0-based and first (plugin-rulebook R22). It is correct.
- The `Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/build.sh:*)` grant follows the skill's own plugin-features examples. The skill does not test whether a grant that contains the variable matches at runtime, so that stays unverified here.
- `Read` is needed for the config step.

## Open points (not verified in this run)

- Whether `${CLAUDE_PLUGIN_ROOT}` expands in plain body text, not only inside `!` and `@` lines. The skill's examples use it only in those, and the fixed command relies on body text for the Read path and build call. A quick live check is the next step.
- The skill gives no guidance on prod confirmation. A build for `prod` may deserve an `AskUserQuestion` confirmation, but the draft did not ask for one, so none was added.
- The skill's validator scripts were not run against the output. They check only structure, `model`, and description length, and the output has no `model` field.
