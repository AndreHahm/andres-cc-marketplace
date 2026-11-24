# Step 1.6 waiver-section check, PR 923

## (a) Command

`<scratchpad>` is the session's scratchpad path, written out; `body-new.txt` is the new body I wrote there with `Write`.

```
python3 -I $PWD/.claude/scripts/git-pr-body-waiver-check.py <scratchpad>/body-base.txt <scratchpad>/body-new.txt
```

- `CLAUDE_PLUGIN_ROOT` is empty, so the `${CLAUDE_PLUGIN_ROOT}/scripts/...` form would resolve to `/scripts/...`. I use the `.claude/scripts/` mirror instead, after confirming that file exists (if neither copy exists, stop).
- `$PWD` is literal and unquoted, with no `cd`, prefix, or chaining: this is the form the skill's second grant pins. It is valid only because `$PWD` is the worktree root step 1.5 verified.
- Before running it I check the changed-file list (the paginated `gh api repos/{owner}/{repo}/pulls/923/files`) for either copy of the script: `.claude/scripts/git-pr-body-waiver-check.py` and `plugins/git-kit/scripts/git-pr-body-waiver-check.py`. (a) assumes neither is listed.
- Exit `0`: this check passes; the `diff --strip-trailing-cr` check must pass too before the PATCH (which still prompts). Exit `1` (a named section reads differently) or `2` (unreadable file or other error): stop and send nothing. I never check the sections by eye instead.

## (b) `.claude/scripts/git-pr-body-waiver-check.py` is in the changed-file list

The pre-approved copy is now the PR's own new code, and would be judging whether the edit leaves CI's waivers untouched. So:

1. I do not run the pre-approved `$PWD/.claude/...` form from (a), and the earlier approval of the body update does not cover running this script.
2. I tell the user plainly that PR 923 changes the checker, so its result comes from the PR's own code.
3. I ask through `AskUserQuestion` for approval of that specific run ("run the PR's copy of the checker" / "don't run it; leave the body as it is").
4. Only on approval, I run it in a form the grant does not match, so the permission prompt also appears: the verified root written out as an absolute path, quoted, instead of `$PWD`:

   ```
   python3 -I "<absolute worktree root>/.claude/scripts/git-pr-body-waiver-check.py" <scratchpad>/body-base.txt <scratchpad>/body-new.txt
   ```

   Exit codes are handled as in (a).
5. If the user declines, the check has not run, so no PATCH is sent: no eyeball check, no skipping it. I report that the body was left unchanged.

The same applies if only `plugins/git-kit/scripts/git-pr-body-waiver-check.py` (the other copy) is listed. Everything else (the diff check, the wait baseline, the re-read/compare/PATCH call) stays the same.
