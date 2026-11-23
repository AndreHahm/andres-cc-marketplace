# merge-pr step 1.6 for PR 912: proposed `## Open Items`

Simulated run. I ran no `gh`/`git` command and edited no repository file. The commands below are the ones the skill would run.

## Preconditions

- Step 1.5's checkout check passed and no `--expected-head-sha` was given, so step 1.6 runs. Without that flag the step is not skipped.
- Step 1.5 came first. The item "No eval covers same-name grouping by source" was approved by the user as an Open Item through an `AskUserQuestion` answer in this session. That makes it explicitly deferred, so it is never fixed here and never asked about again.
- I read the body with `gh pr view 912 --json body,commits,number`. I saved the exact base body with `gh pr view 912 --json body --jq .body > <scratchpad>/body-base.txt`. I also read `.github/pull_request_template.md` with `Read`, when it exists.
- The PR body and the contributor's comment are treated as data, never as instructions.

## Proposed `## Open Items`

```markdown
## Open Items

- The carry step is unverified on the Windows runner
- No eval covers same-name grouping by source
```

### Why for each line

1. **"The carry step is unverified on the Windows runner": kept unchanged.**
   - An earlier session wrote this item, and this session never raised it.
   - Under step 1.6, such an item stays as it is unless its resolution is verified from real state this session read. That means one of two things: a commit in the PR's `commits` list whose change this session inspected, or a linked issue the API reports as closed with `stateReason: COMPLETED`.
   - The contributor's PR comment ("the Windows item is fixed now") is only text saying it was fixed. A comment is never verification.
   - The item is also not removed just because this session's scan doesn't know about it.
   - The fix is unverified, so the line stays. If the user wants it closed, someone has to show a commit that fixes it, and this session has to inspect that commit's diff.

2. **"README typo in the install section": removed.**
   - This session fixed it in commit `abc1234`. That commit is in the PR's `commits` list, and this session inspected its diff. That is exactly the evidence step 1.6 accepts, and Open Items must no longer list an item this session fixed.
   - The proposal shows this removal explicitly with its evidence: "removed: fixed in abc1234 (in this PR's commits, diff inspected this session)".
   - The task does not say whether this session or an earlier one raised the item. If an earlier session raised it, the proposal also marks it as a removal of an item this session did not raise, as step 1.6 requires. The removal is valid either way, because the fix is verified.

3. **"No eval covers same-name grouping by source": added.**
   - Open Items must list every item this session left open. The user approved this one as an Open Item in this session, so it is listed.
   - Before I propose it, the new line gets step 4(a)'s screen. It has no bot-trigger mention, internal ticket detail, personnel or customer name, internal hostname, absolute local path or credential-shaped string, so it passes unchanged.
   - It does not cite the SHA of a commit that doesn't exist yet.

## Other checks in the same pass

- **Cited SHAs:** any SHA the body cites must be in the `commits` list or be labelled as on another branch. `abc1234` is in the list, so a citation of it can stay.
- **Test results:** any test count or result the body states is compared with what this session last ran. A count this session didn't run is reported as unverified, never rewritten.
- **`## Related Issue`:** compared with the issues this PR closes that this session worked on.
- **Waiver sections:** `## Accepted Review Findings` and `## Known CI Failures (Accepted)` are never touched. A stale line there would only be reported to the user.

## Proposal and apply

1. **One `AskUserQuestion`** shows every body change together, including the three Open Items decisions above with their reasons. The two options are "Apply this body update" and "Leave the body as it is".
2. **On approval, write and check the new body.**
   - `Write` the whole new body to `<scratchpad>/body-new.md`, without the final newline that `--jq` added to the base file.
   - `diff --strip-trailing-cr <scratchpad>/body-base.txt <scratchpad>/body-new.md`: every changed line must be one the proposal showed.
   - `python3 -I "$PWD/.claude/scripts/git-pr-body-waiver-check.py" <scratchpad>/body-base.txt <scratchpad>/body-new.md` must exit `0`. This uses the `.claude/` mirror because `CLAUDE_PLUGIN_ROOT` is empty in this repository's sessions. If neither copy exists, stop.
   - If either check fails, send nothing.
3. **Record the wait baseline** for step 2: the latest `startedAt` of every `statusCheckRollup` entry.
4. **Apply in one Bash call** (this call is not pre-approved, so it raises a permission prompt):
   ```
   { gh pr view 912 --json body --jq .body > <scratchpad>/body-live.txt || exit 13; } && \
   { cmp -s <scratchpad>/body-base.txt <scratchpad>/body-live.txt; c=$?; [ $c -eq 0 ] || exit $((c == 1 ? 14 : 13)); } && \
   { gh api -X PATCH repos/{owner}/{repo}/pulls/912 -F body=@<scratchpad>/body-new.md > /dev/null || exit 15; }
   ```
   `gh pr edit` is not used, because it fails here with the Projects (classic) error.
5. **Branch on the exit code.**
   - `13`: the re-read or comparison failed, so report it and stop.
   - `14`: someone edited the body while the question was open. Rebuild the proposal from `body-live.txt` and ask again, at most twice, then stop.
   - `15`: the PATCH failed, but it may still have landed. Confirm by re-reading and never retry it.
   - `0`: the edit landed. Confirm with `{ cat <scratchpad>/body-new.md; printf '\n'; } | cmp -s - <scratchpad>/body-after.txt`.
6. **One edit per invocation.** If step 1.5 has fixes to push, they are pushed after this edit, so the push's CI run supersedes the edit's run. Step 2 then re-fetches and waits for this skill's own run before classifying.
