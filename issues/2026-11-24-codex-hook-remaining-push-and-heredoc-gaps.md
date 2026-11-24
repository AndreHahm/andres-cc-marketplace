## Summary
Codex command hook: four remaining ways past the push and git checks (quoted shell strings, `push --prune`, a quote or backtick after `main`, heredocs)

## Environment
- **Product/Service**: `.codex/hooks/block-dangerous-command.sh` (Codex PreToolUse hook for Bash)
- **Region/Version**: branch `fix/codex-hook-autosetuprebase` at 4908d01b (the PR for #863)
- **Browser/OS**: Linux, mawk and busybox awk; not OS-specific

## Reproduction Steps
1. Feed the hook each command below as `tool_input.command` and check the exit code (2 = blocked, 0 = allowed).
2. A redirection inside a quoted shell string:
   - `bash -c 'git push 2>&1 -f origin x'`
   - `bash -c 'git push 2>&1 --mirror'`
3. `git push --prune origin` (with a wildcard refspec it is already blocked).
4. A quote or backtick written against the word:
   - `bash -c 'git push origin main'`
   - ``x=`git push origin main` ``
5. A command after a real heredoc:
   ~~~
   cat <<E >/dev/null
   E
   git $'reb\x61se' main
   ~~~

## Expected Behavior
All are blocked (exit 2). The plain forms already are: `git push 2>&1 -f origin x`, `git push origin main`, `git rebase main` after the same heredoc.

## Actual Behavior
All are allowed (exit 0).
- Step 2: the copies that drop the `&` of a redirection come from the normalized text, where a quoted string is one word.
- Step 3: no pattern for `--prune`.
- Step 4: the push-to-main check does not end its word at a quote or backtick.
- Step 5: a real heredoc ends the normalized copy, so decoded or escaped spellings after it are not read.

## Error Details
~~~
exit 0 (allowed) for every command in steps 2 to 5
~~~

## Visual Evidence
None.

## Impact
**Medium** - bypasses of a command gate that need an unusual spelling; the exec-policy rules still prompt for a plain `git push`.

## Additional Context
- Found by `security-reviewer` passes while working on #863; left out of that PR by the maintainer's decision. Related: #863, #860.
- `--prune` deletes remote branches that have no local one; this was not run against a real remote.
- Steps 4 and 5 risk new false blocks in commit messages and PR bodies, where quotes and backticks around commands are common. Measure a fix with the repository's own commit messages, old hook against new.
- Any extra copy of the text should be additive, as the arithmetic and redirection copies are: changing the normalized copy itself removed a line end that the push-to-main check needed.
