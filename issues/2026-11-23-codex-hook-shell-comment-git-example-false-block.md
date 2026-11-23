## Summary
Codex command hook: a Git example after a semicolon inside a shell comment in a `bash -c` string is read as a command and blocked

## Environment
- **Product/Service**: `.codex/hooks/block-dangerous-command.sh` (Codex PreToolUse hook for Bash)
- **Region/Version**: `main` at 0458e271; also PR #854 head 0c0c5428
- **Browser/OS**: Windows 11, Git Bash (not OS-specific)

## Reproduction Steps
1. Feed the hook `bash -c 'echo ok # note; git rebase main'` as `tool_input.command`.
2. Check the exit code.

## Expected Behavior
Allowed (exit 0). Everything after `#` is a comment inside the string, so no `git rebase` runs.

## Actual Behavior
Blocked (exit 2). The recursive shell-string check (`INNER_GIT_RE` and the shell-string patterns) reads the raw string text, where the comment is still present, so `; git rebase main` inside the comment looks like a second command. `split_words` strips the comment from the normalized copy, but the raw copies keep it.

On PR #854's branch, where `git stash` is also forbidden inside a shell string, `bash -c 'echo ok # see; git stash'` is blocked the same way; on `main` that command is allowed only because `main` does not check `git stash` in a shell string at all. `bash -c 'echo ok # see git stash'` (no semicolon) is allowed on both.

## Error Details
~~~
BLOCKED: Do not rebase; propose a follow-up commit or a fresh branch instead.
~~~

## Visual Evidence
None.

## Impact
Low: a false block (the safe direction) that only appears with a comment holding a semicolon followed by a forbidden git command. A fix must not let a real command after a `#` that is not a comment through (for example `echo a#b; git rebase`, or a `#` inside quotes), so it needs bash's own comment rules, not a regex cut at `#`.

## Additional Context
- Found in PR #854 (https://github.com/AndreHahm/andres-cc-marketplace/pull/854) by Devin (devin-ai-integration), round 1, analysis comment https://github.com/AndreHahm/andres-cc-marketplace/pull/854#discussion_r4664784944, at head SHA bd59c1c6e20f2cbe0ac0b261701ffb068d347dee.
- Severity: Low (reviewer label: analysis).
- Filed instead of fixed in PR #854 because the behavior predates that PR (reproduced on `main`), so it is out of the PR's scope.
