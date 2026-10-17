# Decision: Bandit_B603 on plugins/example-kit/scripts/run-git.py:77

**Verdict: false positive. Make no code change. Dismiss the finding in Codacy.**

## Why
- B603 is a generic "subprocess call, check for untrusted input" warning. Bandit raises it for any `subprocess.run` that does not use `shell=True`.
- The flagged call is `subprocess.run(["git", "status"], cwd=root, capture_output=True)`.
  - The argv list is a literal.
  - There is no shell.
  - No user-controlled value reaches the command. `root` is only the working directory.
- The `"git"` PATH lookup is a separate rule (B607). It is not part of this finding.
- A code change would not help and could make things worse:
  - Building the command from a variable, or resolving the git path, can trip Codacy's stricter "non-static subprocess command" rule. That would trade a Warning for a Critical.
  - A blanket `exclude_paths` entry in `.codacy.yml` is the wrong tool for one finding on production code.
  - An inline `# nosec` hides the rule in the source. The repo's guidance prefers Codacy's own issue management.

## Exactly what I would do
1. Change no files. Nothing in the repo changes.
2. Dismiss the issue in Codacy with the Cloud CLI. This needs your approval, because it changes remote state, and I have not run it here:
   `codacy pull-request <provider> <org> <repo> 7 --ignore-issue aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --ignore-reason FalsePositive`
   - I chose `FalsePositive` over `AcceptedUse` because the call is literal and there is nothing to accept.
   - I would also pass a short ignore comment if the CLI supports one, such as "literal argv, no shell, no external input".
3. Re-read the PR's issue list to confirm the finding shows as ignored and the check goes green. Analysis is current for the PR head, so no push or re-analysis is needed.

## Question for you (not answered here)
Dismiss issue aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa on PR 7 in Codacy as `FalsePositive`?
- Yes: dismiss as FalsePositive (recommended).
- Use AcceptedUse instead.
- No: leave it open.
