# Step 1.6 for PR 913: the edit command waits three minutes at its permission prompt

This is a simulated exercise. I run no `gh` or `git` command and edit no repository file. I follow `merge-pr`'s step 1.6 as written in `references/session-open-items-and-body-check.md`.

## Where the run stands

- I read the body with `gh pr view 913 --json body,commits,number` and built a proposal from it. That read is the proposal's base body.
- The user approved "apply this body update" in `AskUserQuestion`.
- I wrote the whole new body to a scratchpad file with `Write`, for example `<scratchpad>/pr-913-body.md`. Its `## Accepted Review Findings` and `## Known CI Failures (Accepted)` sections are copied unchanged from the base body, because step 1.6 never edits them.

## Tool calls, in order

Each item is a separate tool call, and each runs only after the previous one returns.

1. **Re-read the live body (Bash):** `gh pr view 913 --json body`. This call is pre-approved (`Bash(gh pr view:*)`), so it runs at once, before any prompt. The maintainer has not edited anything yet, so the live body equals the base body and I do not rebuild the proposal.
2. **Check the waiver sections (no tool, a local comparison):** in the scratchpad file and in the body from call 1, each of the two headings occurs the same number of times, and each occurrence matches byte for byte, from its heading to the next `## ` heading or the end of the body. They are identical, so I continue.
3. **Record the wait baseline (Bash):** `gh pr view 913 --json statusCheckRollup`. I note the latest `startedAt` of every entry as step 2's wait baseline.
4. **Apply the edit (Bash):** `gh api -X PATCH repos/{owner}/{repo}/pulls/913 -F body=@<scratchpad>/pr-913-body.md`. This command is not pre-approved, so Claude Code shows a permission prompt here.
   - **The prompt stays open for three minutes.** In that time the maintainer removes one line from `## Accepted Review Findings` on GitHub, which revokes a waiver.
   - When the user approves, the command runs as it was written. Nothing is read between the approval and the PATCH. The checks in calls 1 to 3 ran before the prompt opened, so all three are now three minutes old.
5. **Re-read after the edit (Bash):** `gh pr view 913 --json body`. I compare it with the scratchpad file, and they match.
6. **Check for a lost concurrent edit (no tool, a local comparison):** I compare the two waiver sections of the body from call 5 with those of the body from call 1. They match.

## What happens to the edit and the proposal

- **The edit overwrites the maintainer's change.** The PATCH replaces the whole body with the scratchpad file. That file still has the removed line, because it came from the body as it was before the prompt. So the line comes back on GitHub and the waiver is reinstated, even though the maintainer just revoked it.
- **The proposal is never rebuilt and the user is not asked again.** The only "re-read, rebuild and ask again" check is call 1, and it ran before the maintainer's edit.
- **The checks after the edit do not catch it:**
  - Call 5 matches the file, because the file is what was just written.
  - Call 6 compares against the body read before the prompt, which still had the line. The overwritten body has it too, so the two agree and no "possible lost concurrent edit" is reported. That check only covers an edit made between call 1 and the PATCH that happens to change the waiver sections relative to call 1. Here the PATCH puts back exactly what call 1 read, so the comparison cannot see the change.
- **CI then runs on the edited body.** The `edited` event starts a `marketplace-ci.yml` run that reads the restored line as a valid waiver. Step 2 waits for that run, using the baseline from call 3.

## The gap in this version of the skill

Step 1.6 says "immediately before the edit", but it does not account for the permission prompt. The edit command is not pre-approved, so the prompt can sit open for any length of time between the last read and the write. To close the gap:

- Put the re-read, the byte comparison of the two waiver sections, and the PATCH into one Bash call that runs after the prompt is approved. For example, a single command that runs `gh pr view 913 --json body`, compares the two sections against the scratchpad file, and runs the PATCH only if they match.
- Or, after the user approves, read the body again before the PATCH. If it changed (here, the removed waiver line), stop, send nothing, rebuild the proposal from the live body, and ask the user again.

In either case, the waiver sections must come from the live body at the moment of the write, never from a copy made before the prompt. As written, the baseline does neither, so the maintainer's revocation is silently undone.
