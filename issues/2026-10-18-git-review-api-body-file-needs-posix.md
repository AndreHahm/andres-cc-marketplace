## Summary
`git-review-api.py` cannot read a reply body on Windows, so `handling-review-findings`' reply and resolve path cannot run there.

## Environment
- **Product/Service**: git-kit, `plugins/git-kit/scripts/git-review-api.py` (used by `handling-review-findings`)
- **Region/Version**: Windows 11, Python 3.13 (`sys.platform` is `win32`), script as of the 2026-10-16 wrapper commits (`fe8d2996` through `0d0c1a82`, issues #580/#582)

## Reproduction Steps
1. On Windows, work a PR with `handling-review-findings` and reach Workflow step 4 (reply to an inline thread).
2. Write the reply text to a scratchpad file and run the `reply` subcommand with `--owner`, `--repo`, `--pr`, `--comment-id` and `--body-file` pointing at that file.
3. Observe the exit code and message.
4. Try the documented fallback, a raw `gh api` call to the replies endpoint.

## Expected Behavior
The reply is posted to the thread, then the thread can be resolved, as on Linux.

## Actual Behavior
`reply` exits 2 before reading the file:

```
git-review-api.py: --body-file needs a POSIX platform (owner and no-follow checks)
```

The raw `gh api` fallback is blocked by git-kit's reviewer-action guard (`git-guard-raw-pr-review.sh`), which tells the caller to use a skill that writes the marker. No sanctioned path remains.

Probe on the affected machine: `hasattr(os, "getuid")` is `False` and `hasattr(os, "O_NOFOLLOW")` is `False`. Temp dir is `[LOCAL_PATH]`.

## Impact
**Medium** - Blocks every `handling-review-findings` step that posts text on Windows: reply to a thread (step 4), the resolve that must follow a reply, and the next-round trigger comment (step 8). The script's own `issue-create` is blocked the same way. `threads`, `resolve`, `list-comments`, `whoami` and `push-destinations` take no body file and are not affected by this error.

Observed on PR #566 on 2026-10-18: a CodeRabbit inline thread could not be replied to or resolved after its fix was pushed and CI was green.

## Additional Context
- The limitation is documented, not accidental: the script header and `handling-review-findings/references/github-api-mechanics.md` say it "needs a POSIX platform and refuses elsewhere". The gap is that no alternative exists for a Windows user.
- The affected subcommands are the ones that call `read_body`: `reply`, `trigger-comment`, `issue-create`.
- Claude Code's scratchpad on Windows is `<temp>\claude\<project>\<session>\scratchpad`, so the directory is named `claude` with no uid suffix. The `claude-<uid>` location check would not match even without the `getuid` guard.
- The skills' `allowed-tools` grants of the form `Edit(//tmp/claude-*/*/*/scratchpad/**)` assume the same Linux layout.
- Suggested priority: `p: medium`. A root-cause analysis follows as a comment.
