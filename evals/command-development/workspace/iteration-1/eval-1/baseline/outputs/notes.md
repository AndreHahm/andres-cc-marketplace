# Design notes: /deploy

- **Argument validation first.** `$0` is validated against a strict pattern before anything else. The skill's guidance is that a command argument is substituted into shell text, so an unvalidated value could escape quoting or traverse paths. Validation runs before the config is read, so a value like `../x` never reaches a file read.
- **Config is read with the Read tool, not an `@` reference.** An `@${CLAUDE_PLUGIN_ROOT}/config/$0-deploy.json` reference resolves when the command loads, which is before the validation step can run. A Read call in step 2 keeps the order: validate, then read.
- **Narrow tool grants.** `allowed-tools` is `Read` plus one scoped `Bash` grant for `scripts/deploy.sh` only, using `${CLAUDE_PLUGIN_ROOT}`, so the command stays portable across installs.
- **Production confirmation.** A deploy is consequential and the skill calls for confirmation before irreversible actions, so `prod` and `production` get an AskUserQuestion gate. Other environments run without a prompt.
- **Argument hint.** `argument-hint: [environment]` matches the single positional argument the body consumes as `$0`.
- **Assumptions.** The config file's fields are not specified, so the command only summarizes them and leaves their use to `deploy.sh`. The script is assumed to read the same config file itself and to exit non-zero on failure. The `prod`/`production` names are assumed; adjust if the plugin uses different names. `deploy.sh` is not visible to this command, so its own argument validation is not verified here.
- **Not verified.** The command was not run against a real plugin layout. The validation pattern and the Bash grant form should be checked with a live `/deploy` invocation.
