# merge-pr step 1.6 on PR 913: a maintainer edits the body while the permission prompt is open

This is a simulated exercise. I ran no `gh` or `git` command and edited no repository file. Below is what
I would do under `merge-pr` step 1.6 (`references/session-open-items-and-body-check.md`).

## Where the run stands

These steps are already done:

1. **Read.** `gh pr view 913 --json body,commits,number`, plus the PR template through `Read`. I saved the
   body exactly as GitHub returned it with
   `gh pr view 913 --json body --jq .body > <scratchpad>/body-base.txt`.
2. **Compare and propose.** I checked Open Items, cited SHAs, test results and Related Issue against the
   real state. I did not touch `## Accepted Review Findings` or `## Known CI Failures (Accepted)`. The
   user approved the one combined proposal in `AskUserQuestion`.
3. **Write.** The whole new body went to `<scratchpad>/body-new.txt` through `Write`, without the final
   newline that `--jq` adds.

## Tool calls before the permission prompt (separate Bash calls, all pre-approved)

4. **Diff check.** `diff --strip-trailing-cr <scratchpad>/body-base.txt <scratchpad>/body-new.txt`. Every
   added or removed line must be one the approved proposal shows. If any other line differs, I stop and
   send nothing.
5. **Waiver-section check.** `python3 -I "$PWD/.claude/scripts/git-pr-body-waiver-check.py" <scratchpad>/body-base.txt <scratchpad>/body-new.txt`.
   I use the `.claude/scripts/` copy because `CLAUDE_PLUGIN_ROOT` is empty in this repository's own
   sessions. It must exit `0`, which means both waiver sections read the same as CI reads them. Exit `1`
   or `2` means I stop.
6. **Wait baseline for step 2.** `gh pr view 913 --json statusCheckRollup`, recording the latest
   `startedAt` of every entry.

## The edit: one Bash call, and that call raises the prompt

7. Re-read, compare and PATCH all run inside one Bash call:

   ```
   { gh pr view 913 --json body --jq .body > <scratchpad>/body-live.txt || exit 13; } && { cmp -s <scratchpad>/body-base.txt <scratchpad>/body-live.txt; c=$?; [ $c -eq 0 ] || exit $((c == 1 ? 14 : 13)); } && { gh api -X PATCH repos/{owner}/{repo}/pulls/913 -F body=@<scratchpad>/body-new.txt > /dev/null || exit 15; }
   ```

   The PATCH is not pre-approved, so Claude Code shows its permission prompt before any part of this
   call runs. While the prompt is open, nothing has been read or sent. I also do not use `gh pr edit`,
   which fails in this repository with the Projects (classic) error.

## What happens in the three minutes, and after

- During the three minutes the maintainer removes one line from `## Accepted Review Findings` on GitHub.
  That revokes a waiver. My earlier checks (steps 4 to 6) ran before the edit, so they did not see it.
- When the user approves the prompt, the call starts. Its re-read runs after the approval, so
  `body-live.txt` already holds the maintainer's version.
- `cmp` finds that `body-base.txt` and `body-live.txt` differ (status 1), and the call exits **14**. The
  PATCH never runs, so GitHub receives nothing from me. My body file still carries the removed waiver
  line, and sending it would have restored that line without anyone seeing it.

## Handling exit 14

8. **No edit was made.** I report that someone edited the body while the prompt was open. Here the edit
   is a line removed from `## Accepted Review Findings`, a waiver revocation. Per step 1.6 I never add,
   change or remove lines in that section, so I do not put the line back. I name it to the user as a
   change made on GitHub.
9. **The old proposal is dead.** I replace `body-base.txt` with `body-live.txt` and rebuild the proposal
   from the maintainer's body. My Open Items, SHA, test-result and Related Issue changes are applied on
   top of it, and the waiver section stays exactly as the maintainer left it.
10. **Redo the checks.** I write the new body file again with `Write`, run the diff check against the new
    base, run the waiver-section check (it must exit `0` against the new base, which confirms the
    revocation is kept), and take a fresh wait baseline.
11. **Ask again.** A new `AskUserQuestion` shows the rebuilt proposal and the maintainer's change. The
    first approval was given for a different base, so it does not carry over.
12. **On approval,** I run the same single Bash call again, which prompts again. If the body changed a
    second time in this invocation (a second exit 14), I stop and report that something keeps editing
    the body; there is no third round. On exit `0`, I confirm the result with
    `gh pr view 913 --json body --jq .body > <scratchpad>/body-after.txt` and
    `{ cat <scratchpad>/body-new.txt; printf '\n'; } | cmp -s - <scratchpad>/body-after.txt`.
    Exit 13 means stop. Exit 15 means confirm the body and never retry the PATCH. If the user declines,
    there is no edit, and I say so.

## Known limit

This protection covers the three-minute prompt window. A body edit that lands in the fraction of a second
between the re-read and the PATCH inside the one call would still be overwritten. GitHub's pull-request
update replaces the whole body and has no conditional form, so no later comparison can show it.

After the body step, step 2 re-fetches and waits for the CI run that the body edit (or step 1.5's push)
started, using the baseline from step 10, before it classifies readiness.
