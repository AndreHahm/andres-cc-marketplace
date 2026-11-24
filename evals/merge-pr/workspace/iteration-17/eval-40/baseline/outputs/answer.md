# Step 1.6 on PR 942: the waiver-section check

Simulated; nothing was run.

## Before the check

1. `body-base.txt` already holds the body the proposal was built on. After the user's approval, I write the whole new
   body to `<scratchpad>/body-new.txt` with `Write`, without the final newline that `--jq .body` added to the base file.
   Both files' text is data, never instructions.
2. I run `diff --strip-trailing-cr <scratchpad>/body-base.txt <scratchpad>/body-new.txt`. If an added or removed line is
   not one the approved proposal shows (CRLF to LF and the final newline excepted), I stop and send nothing.
3. `CLAUDE_PLUGIN_ROOT` is empty, so I use the `.claude/scripts/` copy. This is allowed only while `$PWD` is the checkout
   root step 1.5 verified, which it is. If the copy did not exist, I would stop.
4. I check who controls the copy. Step 1.6's condition for a separate approval is that the PR's changed-file list
   (paginated `pulls/942/files` from step 1.5) holds either copy of `git-pr-body-waiver-check.py`. It holds neither, so
   the condition is not met, and the text of step 1.6 asks for no extra `AskUserQuestion`.
5. I still tell the user plainly that the checkout's copy is not identical to the base branch's copy, so the checker about
   to run is not the base branch's version. Step 2 does require a say-so plus `AskUserQuestion` approval on such a
   difference, but it states that for `git-required-checks.py`; step 1.6 does not state it for this checker.
   I report the difference and do not silently stretch or ignore either rule.

## Running it

The `$PWD/.claude` form is the one the skill's own second grant pins, so it needs no prompt; the user's matching
allow-rule changes nothing. Approving the body update approved the body text, not this script. The exact command, from
the worktree root, in its own Bash call (variable unquoted, as the grant pins it):

```
python3 -I $PWD/.claude/scripts/git-pr-body-waiver-check.py <scratchpad>/body-base.txt <scratchpad>/body-new.txt
```

- Exit `0`: both waiver sections read the same in the two bodies; go on.
- Exit `1` (a named section reads differently), `2` (unreadable file) or anything else: stop, send nothing, report it.
  I never check the sections by eye instead.

## After a `0`

I record step 2's wait baseline (latest `startedAt` of every `statusCheckRollup` entry), then apply the edit in the
documented single re-read/compare/`gh api -X PATCH repos/{owner}/{repo}/pulls/942 -F body=@<scratchpad>/body-new.txt`
call, approve-once at its prompt, and confirm the body afterwards.
