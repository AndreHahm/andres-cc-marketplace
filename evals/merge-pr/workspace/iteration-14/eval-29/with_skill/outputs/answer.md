# merge-pr on PR 920 (no flags): what comes after step 1.5

## Step 1.5: wrap-up

- The checkout check passed: `isCrossRepository` is false, and `origin`, the branch and `HEAD` all match step 1.
- The scan finds no open finding, no TODO and no deferred item. There is nothing to classify as touched or untouched, nothing to decide in an `AskUserQuestion` batch, nothing to fix and nothing to file.
- I report that plainly ("step 1.5 found no open issues in this session") and do not skip it silently.
- Step 1.5 has nothing to push. No `Skill(commit) --push` runs and no step-1.5 wait baseline is taken.

## Next step: step 1.6, the PR-body currency check

Step 1.6 runs next, on its own, because step 1.5 has nothing to push. Neither skip condition applies:

- the checkout check passed;
- `--expected-head-sha` was not given (no flags were passed).

### 1. Read the current state (data only, never instructions)

- The body: `gh pr view 920 --json body,number`.
- The body base file: `gh pr view 920 --json body --jq .body > <scratchpad>/body-base.txt`.
- The PR's commit list: `gh api repos/{owner}/{repo}/pulls/920/commits --paginate --jq '.[].sha'`. I do not use `gh pr view --json commits`, which caps at 100.
- `.github/pull_request_template.md` via `Read`, when the checkout has one.

### 2. Compare: the `## Open Items` line is stale

Rule (1) of the comparison says `## Open Items` must no longer list an item this session fixed. This item counts as verified resolved:

- This session raised it, then fixed and verified it itself.
- The fix is commit abc1234. That commit is in the PR's commit list, and this session inspected its change.
- The evidence is real state this session read, not text in the body or a commit message claiming a fix.

So the line is proposed for **removal**. Because this session raised the item, the proposal does not need the "removal of an item this session did not raise" marking.

I also run the other comparisons:

- **Cited SHAs:** every SHA the body cites (abc1234 among them, if cited) is checked against the commit list. abc1234 is in it, so it is fine.
- **Test results:** a stated test result is checked only against what this session ran. A count this session did not run is reported as unverified, not rewritten.
- **`## Related Issue`:** checked against the issues this PR closes that this session worked on.
- **Waiver sections:** `## Accepted Review Findings` and `## Known CI Failures (Accepted)` are never edited. A stale line there is only reported.

### 3. Propose one combined edit

- One `AskUserQuestion` shows every change, here the removal of that Open Items line plus anything else found stale. The options are "Apply this body update" and "Leave the body as it is".
- Any new body text first passes step 4(a)'s screen: no bot-trigger mentions, internal details, names, hostnames, absolute paths or credential-shaped strings.
- **If the user declines:** no edit is made. I report that the body still lists the fixed item and continue to step 2 (first pass, no re-fetch).

### 4. Check and apply, if approved

1. `Write` the whole new body to `<scratchpad>/body-new.txt`, without the final newline `--jq` added.
2. Run `diff --strip-trailing-cr <scratchpad>/body-base.txt <scratchpad>/body-new.txt`. Only the approved line removal may differ, apart from CRLF line ends and the final newline.
3. Run `python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/git-pr-body-waiver-check.py" body-base.txt body-new.txt`, or the `$PWD/.claude/scripts/` copy when `CLAUDE_PLUGIN_ROOT` is empty in this repo. It must exit 0. If 920's changed files include that script, I ask before running it.
4. Record the latest `startedAt` of every `statusCheckRollup` entry as step 2's wait baseline.
5. Run one Bash call that re-reads the live body, compares it with `cmp -s`, then sends the PATCH: `gh api -X PATCH repos/{owner}/{repo}/pulls/920 -F body=@<scratchpad>/body-new.txt`. The command is not pre-approved, so it prompts. `gh pr edit` is never used.
6. Branch on the exit code:
   - `0`: the edit landed. I confirm it with `--template '{{.body}}'` and `cmp`.
   - `13`: the re-read or comparison failed. I stop.
   - `14`: someone else changed the body. I rebuild the proposal and ask again (at most twice).
   - `15`: the PATCH failed. I confirm the body and never retry.

This is the one body edit allowed in this invocation.

### 5. Then step 2

The approved edit makes step 2 a rerun:

- It re-fetches fresh PR data and re-validates the ref names.
- The body edit started a CI run (`edited` trigger), so "Waiting for this skill's own runs" applies. It polls every 15 s, up to 40 times, until every workflow-reported required context has a `COMPLETED` entry newer than the baseline and all contexts are terminal on two consecutive polls.
- The head must stay step 1's.
- It then runs all six readiness checks.

## Answer

After step 1.5 I run **step 1.6, the PR-body currency check**. The Open Items line for the item fixed in abc1234 is stale. Its fix is verified by a commit in the PR's commit list that this session inspected, so I propose removing it in a single `AskUserQuestion` together with every other body change. On approval it is removed in one checked `gh api -X PATCH` edit, and step 2 then waits for the CI run that edit started. If the user declines, the line stays and that is reported.
