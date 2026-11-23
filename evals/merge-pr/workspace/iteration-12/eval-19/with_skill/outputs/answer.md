# merge-pr 900 (no flags): simulated walkthrough

Inputs taken as given: PR #900 resolves and is valid; the checkout matches the PR (same origin, branch, HEAD). Three open items were raised this session, all in files the PR changes: A (a reviewer Minor the agent parked under `## Open Items` on its own), B (answered "leave it for later" in an earlier AskUserQuestion), C (an unaddressed security-reviewer Minor in a gate script). The user picks "fix now" for everything asked about.

## Step 1: resolve and validate

- Validate `900` as digits-only. Run `gh pr view 900 --json ...` with the step 1 field list. Validate `headRefName` and `baseRefName` against `^[A-Za-z0-9._/@+=-]+$`. Derive `{owner}/{repo}` from the returned `url`.
- The bare-identity check against `origin` is skipped, because the PR reference is non-empty. Step 1.5's own checkout check still runs.
- No `--expected-head-sha`, no `--bypass-codex-review`, no `--stop-on-review-findings`.

## Step 1.5: session open-items check (the only place questions are asked about A, B and C)

1. **Checkout check.** `isCrossRepository` is false. `origin` (from `git remote get-url origin`, not `gh repo view`) matches. The branch matches `headRefName`. `git rev-parse HEAD` equals `headRefOid`. Proceed.
2. **Classify the three items.**
   - A: not deferred. The agent parked it itself, with no user answer. Per the procedure, a parked item must be asked about at the moment it is parked. That did not happen, so I flag it as a lapse, and now it is asked about like any other touched item.
   - B: explicitly deferred (the user's own AskUserQuestion answer, "leave it for later"). It is never fixed here, never asked about again, and listed in the summary as deferred. It stays listed under `## Open Items`.
   - C: not deferred, touched. Asked about.
   - All three are touched (their files are in the PR's changed-file list from `gh api repos/900/pulls/.../files --paginate`). No untouched item exists, so nothing is filed through `github-issue-lifecycle`.
3. **Question round 1: one AskUserQuestion call with two questions** (A and C, each with "fix now (Recommended)" and "leave deferred"). B is not in it. User answers "fix now" for both.
4. **Apply and verify locally, no push.**
   - Fix A, and verify it per `require-tests-for-behavior-changes.md` (a re-read or the applicable test).
   - Fix C, a gate-script change. `require-security-review-before-new-gate.md` requires a `security-reviewer` pass on the fixed file before it ships. That pass raises one new Minor, D, in the same file.
5. **Question round 2: one AskUserQuestion call with one question** (D). User answers "fix now."
6. **Apply and verify D locally.** If the D fix touches the gate's pass/fail logic, run `security-reviewer` on it again (the same rule applies). If it raises nothing new, stop. If it raises something new, ask again in another batch and repeat. Nothing is pushed during this loop.
7. **Summary to report:** found 4 (A, B, C, D), fixed 3 (A, C, D), deferred 1 (B), filed 0.

## Step 1.6: PR-body currency check (the third question, before the one push)

1. Read the body with `gh pr view 900 --json body,commits,number`, plus `.github/pull_request_template.md` if it exists.
2. Compare the body with the real state:
   - `## Open Items`: remove A, C and D (fixed). Keep B, because it is still deferred and still open.
   - Cited SHAs: cite no SHA of the commit about to be made, since it does not exist yet.
   - Test counts or results: state only what this session actually ran. Mark anything else as unverified.
   - `## Related Issue`: check it names every issue this session worked on.
   - Never touch `## Accepted Review Findings` or `## Known CI Failures (Accepted)`.
3. **Question round 3: one AskUserQuestion call** proposing one combined body edit ("apply this body update" or "leave the body as it is"). User approves.
4. Re-read the live body right before the edit. If it changed since the proposal, rebuild and ask again. Write the new body to a scratchpad file with `Write`. Confirm the two waiver sections are byte-identical to the live body. Record the `statusCheckRollup` `startedAt` baseline.
5. One `gh api -X PATCH repos/{owner}/{repo}/pulls/900 -F body=@<scratchpad-path>`. This is not pre-approved, so it prompts. Re-read the body and compare it with the file.

## The push: exactly one

- Back in step 1.5 item (4): immediately before the push, record the latest `startedAt` of every `statusCheckRollup` entry as the step 2 wait baseline. This replaces the baseline the body edit recorded.
- Run `Skill(commit)` with `--push` once, committing A, C and D together. The commit skill's own tests gate applies here.
- **Total pushes: 1.** The body edit is a PATCH, not a push. It is done before the push, so the push's CI run supersedes the edit's run.

## After the push: do NOT restart from step 1

The next step is step 2 (readiness), continuing the same run. Nothing is restarted from step 1, and A, B, C and D are not re-scanned or re-asked.

1. **Re-fetch** with the step 2 rerun field list: `isDraft,reviews,statusCheckRollup,mergeable,mergeStateStatus,headRefName,baseRefName,isCrossRepository,headRefOid`. Re-validate the refreshed ref names. The head must equal the SHA this skill just pushed, or the run stops.
2. **Wait for this skill's own CI run.** Poll `gh pr view 900 --json headRefOid,statusCheckRollup` every 15 seconds, up to 40 attempts. Wait until every required context has a `COMPLETED` entry whose `startedAt` is later than the baseline, and until two consecutive polls show every required context passing or failing. If the bound runs out, stop and report the contexts still pending, by name.
3. **Classify the six required checks** against the fresh data:
   - not draft;
   - status checks: the required list is the union of `branches/<base>/protection` (`404 Branch not protected` counts as empty) and `rules/branches/<base>`, classified as passing, failing, pending or missing (any non-`COMPLETED` entry keeps a context pending; same-name entries grouped by source);
   - no `CHANGES_REQUESTED` in the latest reviews;
   - `mergeable` is `MERGEABLE` (poll at most 5 times if `UNKNOWN`);
   - not behind base (`compare` `behind_by` must be `0`);
   - review outcomes recorded (`.claude/review-outcomes` at base; if the PR has any review thread, `pr-900.json` must be in its changed files with at least one entry, and the local ledger must hold no entry for PR 900).
   - The bypass exception does not apply, since no bypass flag was given.
4. **Advisory disclosures** (never block without the review-findings flag): `mergeStateStatus` raw value, and the unresolved-thread count from a paginated `reviewThreads` query. A fresh `gh-pr-review` marker goes before each page.
5. **Merge rights** (step 3): the 3-tier check in `references/merge-rights-check.md`, using the step 1 `{owner}/{repo}`.
6. **Step 5 confirmation: AskUserQuestion** showing readiness, both advisory values, and the worktree branch-delete note. Only a yes proceeds.
7. **Step 6 settings** (`pr_merge_type`, `merge_auto_delete_branch`).
8. **Step 7.** (a) Count merge commits in the PR if the strategy is `REBASE`; if there are any, ask which strategy. (b) Re-run the full step 2 readiness check once more, without the bypass exception. Then write the marker and run `gh pr merge 900 --<strategy> --match-head-commit <verified SHA> --delete-branch`. (c) If squash, state the commit count and the granularity loss first. (d) On rejection, ask and re-run the full check before any retry. (e) Verify with `gh pr view 900 --json state,mergeCommit`, and run `git ls-remote --heads origin <headRefName>` before reporting branch deletion.
9. **Step 8:** AskUserQuestion offering `finishing-work` now. It is never auto-invoked.

## Answer to the specific questions

- **Items asked about:** A and C in round 1 (one call, two questions), D in round 2 (one call, one question). B is never asked about, because it is explicitly deferred. Total for the 1.5 items: 2 rounds, 3 questions.
- **Body approval:** one further AskUserQuestion call (step 1.6), before the push.
- **Pushes:** exactly one, via `Skill(commit)` with `--push`, after every fix is decided and verified locally.
- **After the push:** no restart from step 1. Continue at step 2, re-fetch, wait for the run this push started (bounded), classify, then steps 3 to 8.
