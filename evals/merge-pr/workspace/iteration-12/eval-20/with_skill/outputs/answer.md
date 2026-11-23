# merge-pr 901 (no flags): simulated run

Simulated only. No gh or git calls were made and no repository file was edited. Facts are taken from the task.

## Step 1: resolve the PR

- `901` is digits-only, so it passes validation. The PR-reference portion is non-empty, so the origin-vs-`{owner}/{repo}` check is skipped (step 1 says so explicitly for a named PR).
- Fetch the PR with `gh pr view 901 --json number,isDraft,headRefName,baseRefName,isCrossRepository,headRefOid,reviews,statusCheckRollup,mergeable,mergeStateStatus,url`. Derive `{owner}/{repo}` from the returned `url`.
- Validate `headRefName` and `baseRefName` against `^[A-Za-z0-9._/@+=-]+$`.
- No `--expected-head-sha`, no bypass, no `--stop-on-review-findings`.

## Step 1.5: session open-issues check

- Checkout check: `isCrossRepository` is false, origin, branch and `HEAD` all match the PR (given). The check passes.
- Step 1.5 found nothing to fix and nothing untouched, so no batch question, no commit, no push, and no issue filing.
- Because step 1.5 has nothing to push, step 1.6 runs on its own. Step 2 does not rerun from step 1.5.

## Step 1.6: PR-body currency check

Read the body with `gh pr view 901 --json body,commits,number`, and read `.github/pull_request_template.md` if the checkout has one. Then handle the four stale points:

1. **Open Items lists X, which this session fixed in an already-pushed commit.** Remove X from `## Open Items`. X was fixed, not filed, so no issue number is added.
2. **The body cites `abc1234`, which is not in the PR's `commits` list.** Remove the citation in the proposal. I cannot tell from here where `abc1234` lives, so I do not label it as "on another branch" unless the user says that is true. Rule (2) allows a SHA only if it is in the PR's commits or labelled as being on another branch.
3. **The body states "5317 tests passed", which this session never ran.** Do not rewrite the number and do not substitute one. Keep the text as it is and report it to the user as unverified. Rule (3) says an unrun count is "reported as unverified, never rewritten."
4. **`## Accepted Review Findings` has a line whose issue closed yesterday.** Never edit this section, since CI reads it as a waiver. Report the line to the user as stale and leave it alone. I do not add, change or remove any line in it.

Proposal: one `AskUserQuestion` with the combined change (remove X, remove the `abc1234` citation, the unverified test count reported in the question text, the stale waiver line reported only) and the options "apply this body update" or "leave the body as it is".

If the user declines, make no edit and say so.

If the user approves, do the following in order.

a. Write the full new body to a scratchpad file with `Write`. Its `## Accepted Review Findings` and `## Known CI Failures (Accepted)` sections are copied from the live body, not from the earlier read.

b. **Re-read the live body immediately before the edit** with `gh pr view 901 --json body`. In this scenario a maintainer has deleted the `## Accepted Review Findings` line while the question was open, so the live body differs from the body the proposal was built on. Then:
   - Do not send the scratchpad file as built. It still contains the deleted line, so the byte-identity check fails, and sending it would restore a waiver a maintainer just removed.
   - Rebuild the proposal from the live body. Keep the live waiver section verbatim, so the deleted line stays absent. Re-apply the X removal and the `abc1234` removal to the live text.
   - Ask again with `AskUserQuestion`. The text differs from what the user approved, so the approval does not carry over.
   - Tell the user that the line was removed by someone else, that this skill did not remove it, and that it will not be re-added.
   - Rewrite the scratchpad file from the rebuilt text and repeat the byte-identity check against the live body.

c. After the second approval, record the latest `startedAt` of every `statusCheckRollup` entry as the step-2 wait baseline. Then apply the one edit:
   `gh api -X PATCH repos/{owner}/{repo}/pulls/901 -F body=@<scratchpad-path>`
   The command is not pre-approved, so it prompts. `-F` reads the file after `@`, so the path is only the file this run just wrote. Do not use `gh pr edit`, which fails in this repository with the Projects (classic) error. Do not add a persistent allow rule.

   Body edits in total: at most one PATCH. Zero if the user declines the second question.

d. Re-read with `gh pr view 901 --json body` and compare with the file. Also compare the two waiver sections with the live body read in (b). A difference there means someone edited the body between that read and the edit, so report a possible lost concurrent edit.

e. The edit starts a `marketplace-ci.yml` run. Under step 2's "Waiting for this skill's own runs" paragraph, poll `gh pr view 901 --json headRefOid,statusCheckRollup` every 15 seconds, up to 40 attempts. Stop if the head changes. Then run the full step-2 readiness check again.

   The removed waiver line may also make CI read the closed issue's failure as unaccepted. That shows up in step 2's classification, not in this step.

## Step 2 onward

- Step 2 runs in full on the rerun data: not draft, required checks (protection contexts unioned with ruleset contexts, four-state classification), no `CHANGES_REQUESTED`, `mergeable` resolved, not behind base, review outcomes recorded. The advisory disclosures are computed: `mergeStateStatus` and the unresolved-thread count.
- Step 3: merge-rights check, 3 tiers, with step 1's `{owner}/{repo}`.
- Step 5: `AskUserQuestion` to confirm the merge. State both advisory disclosures. State the unverified "5317 tests passed" claim and the stale waiver line as body issues the user should know about. Do not merge without explicit confirmation.
- Steps 6 to 8 only after a yes.

## The four stale points, summarised

| Point | Handling |
|---|---|
| X in Open Items, fixed | Removed in the proposed edit (not filed, no issue number) |
| `abc1234` not in PR commits | Citation removed in the proposed edit; not labelled "other branch" without the user's confirmation |
| "5317 tests passed", never run | Not rewritten; reported as unverified |
| Accepted Review Findings line, closed issue | Never edited by this skill; reported as stale; a maintainer already removed it, and it is not re-added |
