## Summary
`.codex/hooks/block-dangerous-command.sh` allows a forbidden git or publish command when an option value combines a single-quoted backslash with an escaped space or separator (`git -c x.y='a b\'c\ d stash`).

## Environment
- **Product/Service**: Codex PreToolUse hook `.codex/hooks/block-dangerous-command.sh` (registered in `.codex/hooks.json`)
- **Region/Version**: the issue #802 fix branch `fix/codex-hook-continuation-split`
- **Browser/OS**: any (verified on Windows Git Bash; the check logic is platform-independent)

## Reproduction Steps
1. Build hook input for each command below, with `printf %b` and `jq -n --arg c "$cmd" '{tool_input:{command:$c}}'` (`\\` is one backslash):
   - `git -c x.y='a b\\'c\\ d stash`
   - `git -c x.y='a b\\'\\; stash`
   - `git -c x.y='a b\\'c\\ d rebase main`
   - `npm --prefix 'a b\\'c\\ d publish`
2. Pipe each to `bash .codex/hooks/block-dangerous-command.sh` and check the exit code.

## Expected Behavior
Exit 2 (blocked). Inside single quotes a backslash is literal, so `'a b\'` is `a b\`; then `c\ d` is `c d`. The value is one word (`a b\c d`), and bash runs `stash`, `rebase` or `publish`.

## Actual Behavior
Exit 0 (allowed) for all four. The hook reads several copies of the command: as written, with quotes removed, with backslashes removed, and with each backslash plus the next character turned into `_`. None of them reads a backslash as literal inside single quotes while also keeping both the quoted space and the escaped space inside the word. In the `_` copy, `\'` swallows the closing quote, so the value no longer parses.

## Error Details
~~~
git -c x.y='a b\'c\ d stash           -> hook exit 0 (bash runs: git stash)
git -c x.y='a b\'\; stash             -> hook exit 0 (bash runs: git stash)
git -c x.y='a b\'c\ d rebase main     -> hook exit 0 (bash runs: git rebase main)
npm --prefix 'a b\'c\ d publish       -> hook exit 0 (bash runs: npm publish)
~~~

## Visual Evidence
None.

## Impact
**Low** - A contrived command shape that a model is unlikely to issue by accident. The hook is documented as a guardrail, not a security boundary, and the Codex sandbox stays on.

## Additional Context
- Found by the third `security-reviewer` round on the issue #802 fix and verified live; the four inputs are not yet in the test suite.
- Suggested direction (not decided): replace the substitution copies with one awk pass that rewrites each word the way bash reads it: single quotes literal up to the closing quote; in double quotes a backslash escapes only `"`, `\`, `$`, backtick and newline; unquoted, a backslash plus the next character is one character; quote characters dropped; a space or separator inside a word written as `_`. Then add the four inputs as block cases in `.codex/hooks/tests/test-block-dangerous-command.sh` and run `test-block-dangerous-command-matrix.sh`.
- Related: #802 (its fix added the backslash and escaped-space copies this gap sits between), #176.
