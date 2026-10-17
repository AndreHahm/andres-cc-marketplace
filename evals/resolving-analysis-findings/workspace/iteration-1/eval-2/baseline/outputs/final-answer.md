# Codacy High finding: Semgrep_dangerous-subprocess-use at run-git.py:120

I could not verify this finding. `plugins/example-kit/scripts/run-git.py` does not exist in this worktree, so I have not seen line 120. Sandbox rules also stopped me from querying Codacy.

## What I can say from the rule itself
`Semgrep_dangerous-subprocess-use` fires when a subprocess call's command or arguments are not a static literal. A common trigger is `subprocess.run(cmd, ...)` where `cmd` comes from a variable or from `sys.argv`. It is a real finding if attacker-influenced data reaches that call. It is a false positive only if all of these hold:
- The executable is a fixed literal, such as `git`.
- The arguments are passed as a list.
- There is no `shell=True`.
- Any variable parts come from validated or allowlisted values, not from user or external input.

## Plan
1. Read the call at line 120 and trace where each argument comes from. Confirm there is no `shell=True`, the executable is fixed, and the arguments are validated.
2. If the data is attacker-reachable, fix the code. Validate against an allowlist of subcommands, reject arguments starting with `-` where that matters, and use a list-form call.
3. If it is a false positive, do not refactor just to quiet the rule. A change aimed at one rule can trip a stricter one on the same line and trade this finding for a worse one.
4. For a genuine false positive, dismiss that single issue in Codacy, either through the UI or the Cloud CLI's `--ignore-issue <id> --ignore-reason FalsePositive` (or `NotExploitable` if it is real but unreachable). Add a short comment at the call site saying why it is safe.
5. Do not use `.codacy.yml` `exclude_paths` for this. It excludes a whole file from a whole engine, which is wrong for a production script. A one-off ignore is the right tool.
6. Re-check that the finding count dropped.

## Questions for you
1. Can you paste lines 105-130 of `run-git.py`? The file is not in this checkout, and this branch (`fix/codacy-subprocess-suppressions`) may not have it. Is it on a different branch?
2. Where do the arguments to that subprocess call come from: hard-coded values, CLI arguments, or file or environment content?
3. If the review confirms a false positive, do you want me to prepare the exact dismissal commands for you to run? I can't run Codacy or `gh` commands in this sandbox.
