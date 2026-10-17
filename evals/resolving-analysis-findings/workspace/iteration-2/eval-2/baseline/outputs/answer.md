# Codacy finding: Semgrep dangerous-subprocess-use in plugins/example-kit/scripts/run-git.py

## What I could check

- `plugins/example-kit/scripts/run-git.py` does not exist in this worktree. `git ls-files` finds no tracked file named `run-git.py` and no `example-kit` plugin at all. I could not read line 120 or confirm the flagged code.
- I could not query Codacy (no `codacy` or `codacy-analysis` commands were run, per the sandbox rules), so the finding's ID, severity and category are taken from your message only.
- The likely cause is a path or branch mismatch. Check which branch the PR is on and whether the file was renamed or lives in another plugin. Paste the file contents or the Codacy issue ID and I can give a real verdict.

## How to decide whether it is a false positive

Semgrep's `dangerous-subprocess-use` rule flags subprocess calls whose command is built from a non-literal value. It is a true positive when:

- `shell=True` is used with any interpolated or user-influenced string, or
- an argument list is built from external input (CLI args, env vars, file contents) without validation.

It is a likely false positive when the script uses an argument list (no shell), the arguments are fixed or come from a controlled allowlist, and nothing untrusted reaches the call.

## Options

1. **Fix the code (preferred if any input is untrusted).** Pass an argument list without `shell=True`, validate inputs against an allowlist, and keep the subprocess call in one helper. Then confirm the finding is gone with `codacy pull-request ... <prNumber>` or a fresh analysis. Do not assume a change helped without re-checking, because a change can trade one rule for another.
2. **Mark it in Codacy (for a genuine false positive or non-exploitable case).** Use `codacy pull-request <provider> <org> <repo> <prNumber> --ignore-issue <issueId> --ignore-reason FalsePositive` (or `NotExploitable` / `AcceptedUse` if that fits better), with a short reason in the PR.
3. **Do not use `.codacy.yml` `exclude_paths`** for this. It excludes the whole file from the whole engine, which would hide every other finding in a production script.

## Recommendation

Do not change code or ignore the finding until the file is located and read. If the call uses an argument list with fixed or allowlisted input, option 2 is the right fit. If any input can come from outside, option 1.

No repository files were edited. No commands beyond read-only git and file lookups were run, and there was no network access.
