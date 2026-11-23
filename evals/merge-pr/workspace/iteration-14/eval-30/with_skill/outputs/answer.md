# merge-pr on PR 921: commit declined after step 1.6's body edit

## Short answer

No, I do not go on to step 2's readiness checks. The push never landed, so the rule in step 1.5 (4) of `references/session-open-items-and-body-check.md` applies: "If that push does not land (the commit is declined or the push fails), the body step 1.6 just applied no longer lists items whose fixes never shipped: run step 1.6 again against the real state, so `## Open Items` lists them again ... Then stop the run before step 2."

The "fix now" finding is still open on the PR. It is touched and not deferred, and a run never merges over such an item. I also do not restart the skill from step 1.

## What I do next, in order

### 1. Record the real state
- The fix exists only as an uncommitted change in the local working tree. No commit was made and nothing was pushed, so the PR head is still step 1's `headRefOid`.
- The PR body that step 1.6 just edited is now wrong. It no longer lists the finding under `## Open Items`, but the fix never reached the PR.
- The commit was declined at commit's confirmation. That was the user's decision, so I do not retry `Skill(commit)` and I do not push by any other route.

### 2. Re-run step 1.6 against the real state (the one permitted second edit)
"One edit per invocation" allows this second edit, because step 1.5's push did not land.
1. **Read** the current body with `gh pr view <pr-ref> --json body,number` and the PR's commit list with `gh api repos/{owner}/{repo}/pulls/<number>/commits --paginate --jq '.[].sha'`. Read `.github/pull_request_template.md` too if it exists. Save the body exactly as GitHub returns it: `gh pr view <pr-ref> --json body --jq .body > <scratchpad>/body-base.txt`. This is the body my first edit produced, unless someone has changed it since.
2. **Compare** against the real state:
   - `## Open Items` must list the "fix now" finding again, because its fix never shipped.
   - Every other item stays as it is, including items from other sessions.
   - No SHA of the declined commit is cited, because that commit does not exist.
   - Any test result the body states must not claim the unshipped fix as part of the PR.
   - `## Related Issue` must still be right.
   - I never touch `## Accepted Review Findings` or `## Known CI Failures (Accepted)`.
3. **Screen** the new lines (step 4(a)'s screen): no bot-trigger mentions, ticket details, personal names, internal hostnames, absolute local paths or credential-shaped strings.
4. **Propose** the change in one `AskUserQuestion`: "apply this body update" or "leave the body as it is". The proposal shows the finding being put back under `## Open Items`.
5. **If approved:**
   - `Write` the whole new body to a scratchpad file, without the final newline that `--jq` added.
   - Run `diff --strip-trailing-cr <scratchpad>/body-base.txt <new-body-file>`. The only changed lines may be the approved ones.
   - Run `python3 -I $PWD/.claude/scripts/git-pr-body-waiver-check.py <scratchpad>/body-base.txt <new-body-file>`. This is the mirror form, because `CLAUDE_PLUGIN_ROOT` is empty in this repository's sessions and `$PWD` is the checkout root that step 1.5 verified. It must exit 0. If either check fails, I stop and send nothing.
   - Record the latest `startedAt` of every `statusCheckRollup` entry. That is the baseline step 1.6 normally takes.
   - Apply the edit in one Bash call: re-read the live body into `body-live.txt` (any failure exits 13), then `cmp -s` it against `body-base.txt` (exits 14 if they differ, 13 if a file cannot be read), then `gh api -X PATCH repos/{owner}/{repo}/pulls/<number> -F body=@<new-body-file>` (exits 15 on failure). The call is not pre-approved, so it prompts.
   - Branch on the exit code:
     - **0:** confirm with `gh pr view <pr-ref> --json body --template '{{.body}}' > body-after.txt` and `cmp`.
     - **13:** report it and stop.
     - **14:** someone edited the body in the meantime. Rebuild the proposal from `body-live.txt`, redo the checks, and ask again, up to a second such round. After that, stop and report.
     - **15 or any other code:** confirm the body. Never retry the PATCH.
6. **If declined:** I report that the PR body still shows the finding as fixed, even though its fix was never pushed.

### 3. Stop the run before step 2 and report
I give the step 1.5 summary:
- **Found:** the touched finding.
- **Fixed locally and verified, but not committed or pushed:** the user declined the commit, so the change is still in the working tree.
- **Still open on the PR:** the same finding, so the PR is not mergeable in this run.
- **Body:** either restored to list the finding under `## Open Items` again, or the edit was declined and the body still wrongly shows it as fixed.
- **Untouched items and their drafting or filing outcomes**, if there were any.

Then I stop. I run no step 2 readiness checks, no step 2 wait on CI runs, no merge-rights check, no confirmation and no merge. The run never merges over a "fix now" item that is still open, touched and not deferred.

To continue later, the user commits and pushes the fix, or decides otherwise about the finding, and then runs merge-pr again in a new invocation.
