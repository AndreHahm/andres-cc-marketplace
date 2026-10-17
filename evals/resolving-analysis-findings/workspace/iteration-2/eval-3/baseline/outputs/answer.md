# Codacy Bandit B603 finding on run-git.py

## First: the file named in the finding is not in this checkout

I looked for `plugins/example-kit/scripts/run-git.py` in the worktree at
`<repo>`.
There is no `example-kit` plugin under `plugins/` (the directory list is analysis-kit, antigravity-kit,
codex-kit, context-kit, example-plugin, github-actions-kit, git-kit, plugin-devkit, promptlibrary-kit,
quality-kit, session-kit, workledger-kit, workmanagement-kit), and no file named `run-git*` exists anywhere
outside `.git/`. So I could not read line 120 and cannot confirm what the flagged call looks like.

Possible explanations, to check before changing anything:

- The finding is on a different branch or PR than the one checked out here (this worktree is on
  `fix/codacy-subprocess-suppressions`).
- The path in the Codacy report is stale, or the file was renamed or removed on the PR branch.
- The plugin name in the report is a typo for another plugin.

Confirm the real path and line from the Codacy issue itself (the Codacy Cloud issue list for the PR), not
from memory.

## What to do once the call is in front of you

Bandit B603 means "subprocess call without shell=True" and is a low-risk pattern by itself. Whether the
Medium-severity finding is real depends on what goes into the argument list:

1. **Arguments are fixed or built from trusted values only** (for example, a literal `git` subcommand
   list). This is a false positive or accepted use. Record it in Codacy's own issue management, not with a
   code change. Use `codacy pull-request <provider> <org> <repo> <prNumber> --ignore-issue <id>
   --ignore-reason <FalsePositive|AcceptedUse|NotExploitable>` (the reason that fits best). Do not add an
   exclude to `.codacy.yml` for this: it excludes a whole file from a whole engine, which is too broad for
   one finding on production code.

2. **Arguments include values from outside the script** (a CLI argument, a PR title or branch name, a
   config value, or any other input). B603 itself is still only a warning, but the real risk is argument
   injection: `git` accepts options such as `--upload-pack` or `--output=` that can run commands or write
   files if a user-controlled value starts with `-`. Fix that in the code: validate the values against an
   allowlist or a strict pattern, and put `--` before user-supplied positional arguments. Then re-check.

3. **Any code change made to clear this finding**: verify it actually reduces Codacy's count before
   assuming it helped. A change aimed at B603 can trip a stricter rule on the same line (for example, a
   "non-static subprocess command" rule that rates variable-based commands as worse than literal ones). Re-run
   the analysis (`codacy-analysis analyze --pr` locally, or a push and a fresh Codacy check) and compare the
   issue list. Do not rely on a local Bandit run alone.

Other points:

- Do not replace the call with `shell=True` or a shell string to avoid the rule. That removes the B603 warning
  and adds a real injection risk.
- A `# nosec B603` comment in the code may or may not suppress Codacy's copy of the finding. I have not
  verified that for this Codacy setup. The Codacy issue-management step is the reliable way to record the
  decision.
- I did not run any `codacy`, `codacy-analysis` or `gh` command, did not use the network, and did not edit
  any repository file, as instructed.

## Recommended next step

Get the real file path, line and argument list for the finding from Codacy. Then decide between option 1
(ignore with a reason in Codacy) and option 2 (validate inputs in code, re-analyze, and confirm the count
drops). Without the file, the recommendation stays conditional.
