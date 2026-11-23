# merge-pr step 1.6 for PR 914: proposing the Open Items line

## The line I would propose

```
- The carry step fails on one self-hosted build runner; the run's logs are kept locally and are not linked here. Deferred by the user in this session.
```

I would not copy the session note into the body as it is. It reads: "The carry step fails on build-03.corp.internal; logs at /home/jdoe/ci-logs/run-4411.txt".

## What I checked before proposing it

1. **Step 1.6 may run.** Step 1.5's checkout check passed, so this session's state can be compared. `--expected-head-sha` was not given. If it had been, step 1.6 would be skipped and reported as skipped.

2. **The item belongs in `## Open Items`.** The user approved leaving it open as an Open Item. That approval came through an `AskUserQuestion` answer in this session, so it counts as explicitly deferred under the reference's closed list. Step 1.5 therefore does not ask about it again or fix it. Step 1.6 comparison (1) says `## Open Items` must list every item this session left open, so the body needs this line. I would also check two things in the body read with `gh pr view <pr-ref> --json body,commits,number`:
   - whether the item is already listed there, in which case the stale wording is replaced rather than a second line added;
   - that no other item this session fixed or filed is still listed.

   Items from earlier sessions or other contributors stay as they are unless their resolution is verified from real state. The item is deferred, not filed, so the line carries no issue number.

3. **The new text passes step 4(a)'s screen.** Step 1.6 says every line of new body text must pass this screen before it is proposed. The session note fails it twice:
   - `build-03.corp.internal` is an internal hostname.
   - `/home/jdoe/ci-logs/run-4411.txt` is an absolute local path. It also exposes a personal username (`jdoe`), which counts as personnel detail.

   The rule is to rewrite flagged text in plain terms, or report it and leave it out. I rewrote it: the host became "one self-hosted build runner" and the log path became "kept locally and not linked". The proposed line has no hostname, path, username, ticket detail, credential-shaped string or bot-trigger mention such as `@codex review`. I would tell the user that the hostname and log path were dropped on purpose, so they can keep them somewhere private.

4. **No waiver section is touched.** The change is only in `## Open Items`. `## Accepted Review Findings` and `## Known CI Failures (Accepted)` are never edited.

5. **The other comparisons are folded into the same proposal.** Comparisons (2) to (4) cover cited SHAs (each must be in `commits` or labelled as on another branch, and no SHA of a commit not yet made), stated test results (only what this session ran, otherwise reported as unverified) and `## Related Issue`. Anything stale there goes into the same single proposal.

## How the edit would then be applied (simulated, nothing run)

- I would save the body the proposal is built on to `<scratchpad>/body-base.txt` (`--jq .body`). Then one `AskUserQuestion` would show every change, with the options "apply this body update" and "leave the body as it is".
- After approval, I would `Write` the whole new body to a scratchpad file, without the final newline that `--jq` adds. Two checks must then pass:
  - `diff --strip-trailing-cr`: only the approved lines may differ.
  - `python3 -I "<plugin root>/scripts/git-pr-body-waiver-check.py" body-base.txt <new-body-file>` must exit `0`. In this repository's own sessions that is the `.claude/scripts/` copy.
- I would record the latest `startedAt` of every `statusCheckRollup` entry as step 2's wait baseline. Then one Bash call does three things in order: re-read the live body (exit 13 on failure), `cmp` it against `body-base.txt` (exit 14 on a difference, meaning re-propose), and run `gh api -X PATCH repos/{owner}/{repo}/pulls/914 -F body=@<file>` (exit 15 on failure, meaning confirm the body and never retry the PATCH). This call is not pre-approved and prompts.
- Last, I would confirm the body with a re-read. Then I would continue to step 1.5's push, if it has one (it supersedes the edit's run), and on to step 2, which waits for the run this skill caused.
