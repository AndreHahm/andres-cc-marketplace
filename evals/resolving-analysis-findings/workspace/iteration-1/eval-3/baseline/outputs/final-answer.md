# Codacy Bandit_B603 (Medium) on plugins/example-kit/scripts/run-git.py:120

I could not inspect the code. `plugins/example-kit/scripts/run-git.py` does not exist in this worktree (branch `fix/codacy-subprocess-suppressions`). So the plan below is conditional on what line 120 actually does.

## What the finding means
Bandit B603 (`subprocess_without_shell_equals_true`) fires on almost every `subprocess.run/Popen/call` that does not use `shell=True`. It asks you to confirm that the argument list is not built from untrusted input. It is a "please review" flag, not a proven vulnerability. It is usually a false positive or accepted use when:
- the argv is a list (never a shell string),
- `shell=False` (the default),
- the executable is fixed (`git`),
- and any variable parts (branch name, path, ref) are validated or passed after `--`.

## Plan
1. Read line 120 and its callers. Check three things: is the argv a list, is `shell=True` absent, and can any element come from outside the script (CLI args, env, file contents, PR or branch names)?
2. Decide:
   - **Inputs are fixed or validated:** this is a genuine false positive or accepted use. Dismiss it in Codacy's own issue management with a reason (FalsePositive or AcceptedUse) and a short justification. Do not change code to satisfy the rule.
   - **Inputs are untrusted and unvalidated:** it is a real finding. Fix it by validating or allow-listing the inputs, using `--` before user-supplied refs, and not building strings. Then re-check that Codacy's count actually drops.
3. Do not use a blanket `.codacy.yml` `exclude_paths` entry or an inline `# nosec` workaround for a single production-code finding. Per project guidance, `exclude_paths` is only for structurally false-positive-prone code such as test harnesses. Do not switch to a variable-based command to dodge B603, because that can trade a Medium finding for a stricter Critical one.
4. Use the Codacy Cloud CLI to get the authoritative issue ID and details, and the local analysis CLI to re-check before pushing. I did not run either, per the sandbox constraints.

## Question I would send before acting
(Not answered by me.)

"Bandit B603 on `run-git.py:120` is probably a review-me flag on a `git` subprocess call. Which do you want?
1. Dismiss it in Codacy as a false positive or accepted use, with a justification (no code change), if the argv is fixed or validated.
2. Harden the code (validate inputs, add `--`) and re-check that the count drops.
3. Let me inspect line 120 and its inputs first, then recommend one."

I would also confirm that the file path is right, since it is missing from this worktree.
