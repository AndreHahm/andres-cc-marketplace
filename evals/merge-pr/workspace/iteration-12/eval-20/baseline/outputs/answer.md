# Baseline answer: `merge-pr 901` with stale PR body (simulated, no gh/git calls)

## What the baseline skill says

The baseline `plugins/git-kit/skills/merge-pr/SKILL.md` has no procedure for editing a PR body. Its only
body-related grant is `Bash(gh pr edit:*)`, and its own step 1.5 covers fixes and filed issues, not body
text. Its `allowed-tools` also does not grant a `gh api repos/*/pulls/*` PATCH. So the body edit below is
my own addition, not a documented step. I am disclosing that rather than presenting it as the skill's
procedure.

## Steps

1. **Resolve PR 901.** The argument is digits-only, so it passes validation. Run the step 1 fetch
   (`gh pr view 901 --json number,isDraft,headRefName,baseRefName,isCrossRepository,headRefOid,reviews,statusCheckRollup,mergeable,mergeStateStatus,url`).
   Derive `{owner}/{repo}` from `url`. The PR-reference portion was non-empty, so the origin-identity check is
   skipped. Validate `headRefName` and `baseRefName` against `^[A-Za-z0-9._/@+=-]+$`.

2. **Step 1.5 result.** Given: nothing to fix. Confirm that the checkout matches the PR (repository, branch,
   `git rev-parse HEAD` equal to `headRefOid`, `isCrossRepository` false), then state "no open issues" in the
   report. This is not a reason to skip the body check below.

3. **Step 2 readiness checks**, re-fetched on the first pass only if step 1.5 pushed (it did not). Check
   not-draft, the required-check list from the branch-protection endpoint, change requests, merge
   conflicts, and not-behind-base. Report the advisory disclosures (`mergeStateStatus` and the unresolved
   thread count, both stated even if zero). Step 3 merge rights and step 5 confirmation still come after
   this.

4. **Body audit (not a skill step; a proposal).** Read the live body once with
   `gh pr view 901 --json body --jq .body` and save it to a scratchpad file. Check the four points below
   against the PR's own commit list (`gh api repos/{owner}/{repo}/pulls/901/commits --paginate`, an allowed
   grant). Compose the proposal as a diff against the live text.

5. **Present the proposal** via `AskUserQuestion`, showing the full before/after diff of the body and the
   reason for each change. Do not edit anything until the user approves.

## The four stale points

1. **`## Open Items` lists item X, which this session fixed in an already-pushed commit.** Propose marking X
   done and citing the real fixing SHA, but only after confirming that SHA is in the PR's commit list from
   step 4. If it is not, cite nothing and only mark X as "fixed in this branch" without a SHA. Do not remove
   X silently; a reader should still see it was an open item.

2. **The body cites `abc1234`, which is not in the PR's commit list.** Propose removing that citation. It
   is a wrong reference, and the body should not carry a SHA that no commit in the PR has. Replace it with
   the verified SHA from point 1, or drop it. Do not guess a replacement.

3. **`## Accepted Review Findings` has a line whose issue was closed yesterday.** Propose removing that line,
   since a closed issue is no longer an accepted open finding. If the user wants a record of it, keep it
   with "closed <date>" instead of deleting it. This is a judgement about the body's own history, so it
   goes to the user; the skill does not decide it.

4. **The body states "5317 tests passed," and this session never ran them.** Propose removing the number
   entirely. Do not replace it with another count. If the user wants a test claim in the body, the honest
   form is "tests not run in this session," and that needs their say-so. Running the suite would be a
   separate step with its own approval, and this exercise does not allow it.

## Body edit: count, command, and checks

- **Number of body edits: one.** All approved changes go in a single new body, so the PR history has one
  edit event rather than several. Writing the body in pieces would also widen the window for a race like
  the one below.
- **Command:** `gh pr edit 901 --body-file <scratchpad path>`, with the new body in a file written by
  `Write`, never interpolated into the shell. This is the form `allowed-tools` grants. My memory notes say
  `gh pr edit` errors on this machine (Projects classic) and that `gh api .../pulls/<n> -X PATCH -F body=@file`
  works instead. That PATCH is not in the baseline grant, so if `gh pr edit` fails I stop and ask the user to
  approve widening the grant. I do not switch commands silently.

## Checks right before the edit

Immediately before the edit, re-run `gh pr view 901 --json body,headRefOid,state`.

- `headRefOid` must still equal step 1's value. If not, stop and re-run step 1 and step 2.
- `state` must still be `OPEN`.
- Re-read the live body and compare it with the snapshot the user approved (the saved scratchpad copy).

## When the maintainer's change is found

The maintainer deleted the `Accepted Review Findings` line from the live body after my proposal was made.
So the live body no longer matches the approved snapshot. I do not write my proposed body over it: that would
rebuild from a stale copy and could undo other maintainer edits.

- Re-derive the new body from the **live** text, applying only the changes that still apply: points 1, 2 and 4.
  Point 3 is already done by the maintainer, so drop that edit.
- Because the approved change set shrank to a strict subset of what the user approved, and the deletion is
  the same line the user already accepted for removal, I can proceed with the three remaining edits on the
  live text. I disclose the change in the report.
- If any other live text differs from the approved snapshot, the approval no longer covers what I would
  write. Stop and re-ask via `AskUserQuestion` with the new diff before editing.
- Then write the one edit as above and re-read the body afterward to confirm all changes are present and no
  other text moved.

## How each stale point is handled, in summary

| Point | Proposed handling | Verification before editing |
|---|---|---|
| Open Item X fixed in pushed commit | Mark done, cite real SHA | SHA is in PR commit list; else no SHA |
| `abc1234` not in PR commits | Remove the citation | Not in commit list (confirmed) |
| Closed-issue accepted finding | Remove the line (maintainer already did) | Live body no longer has it; no edit needed |
| "5317 tests passed" unverified | Remove the number | Session never ran the suite |

## Not done in this exercise

No `gh`/`git` command was run, no repository file was edited, and nothing was posted. Every command above is
the plan for the live run, not a result.
