# Decision: python:S5443 at scripts/tool.py:12 (PR 42, example-org/example-repo)

## Short answer

Do not dismiss this as a false positive just because the path is a constant. S5443 is about the location, not whether the value varies. A hardcoded path under a publicly writable directory (`/tmp`, `/var/tmp`, `/dev/shm`, or similar) is exactly what it flags. A constant path there is still exposed to symlink and pre-creation attacks by other local users. My default action is a code fix, not a suppression.

## Things I could not verify

- `scripts/tool.py` does not exist in this worktree (``). The finding belongs to `example-org/example-repo` PR 42, which is a different repository. So I have not seen line 12 and cannot confirm the path it uses.
- The record says category VULNERABILITY. In SonarQube, S5443 is normally a Security Hotspot (review-required), not a vulnerability. That affects which Sonar action applies (mark as safe vs. fix), so confirm the category in the Sonar UI.

## What I would do

1. Read `scripts/tool.py` in the PR 42 branch and check what line 12 actually is.
2. If the path is a fixed directory under `/tmp` or another shared location, change the code. Use `tempfile.mkdtemp()` (or `TemporaryDirectory()`) so the directory is private and unpredictable. If a fixed location is really needed, create it with mode 0700 and verify ownership before use. Do not suppress.
3. If the path is not in a shared directory (for example, a path under the user's home or the project's own gitignored output directory), the finding is a rule misfire. Then mark it as safe in Sonar with a written reason, not a silent change.
4. Re-run the Sonar analysis on the PR after the change and confirm the issue is closed, not just moved.

## Questions I would ask (not asked, sandbox)

- AskUserQuestion: "Line 12 of scripts/tool.py uses a constant path. Which path is it?" Options: (a) a shared temp directory such as `/tmp` or `/var/tmp`; (b) a private or project-owned directory; (c) not sure, I need to read the file first. Recommended: read the file first, then choose.
- AskUserQuestion: "Fix the code (use a private temp directory), or mark the hotspot as safe in SonarQube Cloud with a reason?" Recommended: fix the code if the path is in a shared directory; mark as safe only if the path is verifiably private.

## Commands I would show (not run)

- Read the file in the PR branch: `git show <pr-42-head-sha>:scripts/tool.py | sed -n '8,16p'`
- Fix (if shared path): replace the constant with `tempfile.mkdtemp()` and add a test for the path's ownership and mode.
- Suppression (only if mark-as-safe is chosen): an inline `# NOSONAR(python:S5443)` comment with a stated reason, or the "Mark as Safe" action in the SonarQube Cloud UI with the same reason, so the decision is recorded in Sonar.

## Not changed

No Sonar, Codacy, or `gh` command was run. No repository file was changed. Only this answer file was created.
