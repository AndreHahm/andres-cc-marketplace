# merge-pr 904 --bypass-codex-review: step 1.5 outcome

## Inputs (simulated)

- Argument `904` is digits-only, so step 1 accepts it. The bypass reason is non-empty, so the bypass flag is live.
- The checkout matches PR #904 (`isCrossRepository` false, `origin`, branch and `HEAD` all match).
- Only `Publish Codex policy result` is failing among the required checks.
- One open item this session: an unaddressed reviewer Minor in a file the PR changes. The user never deferred it.

## Steps

1. **Step 1 (resolve and validate).** Validate `904` and the reason portion. Fetch PR data with `gh pr view 904 --json ...`. The data is passed on as facts for this exercise, so no call is made.

2. **Step 1.5 (session open-issues check), first sub-step.** Verify the checkout identity: `isCrossRepository` is false, `origin` resolves to the PR's base repository, the branch matches `headRefName`, and `git rev-parse HEAD` equals `headRefOid`. All pass, so the scan runs.

3. **Step 1.5, scan and classify.** The one open item is the reviewer Minor. It is not explicitly deferred, because only the user's own message or an `AskUserQuestion` answer counts. The file it concerns is in the PR's changed-file list from `gh api repos/{owner}/{repo}/pulls/904/files --paginate`, so it is **touched**.

4. **Step 1.5, bypass branch.** The skill says that with `--bypass-codex-review`, step 1.5 fixes and pushes nothing. A fix commit would never have been reviewed by Codex and would become the head that step 4 attests. The skill reports the touched issues instead. Because the item is touched and not deferred, **the run stops here**.
   - No `AskUserQuestion` batch is raised for fixes. That batch exists only on the non-bypass, non-pinned path.
   - No fix is applied, no commit or push is made, and no untouched item is filed.

5. **Run ends at step 1.5.** Steps 1.6, 2, 3, 4, 5, 6, 7 and 8 never run:
   - Step 1.6 (PR-body edit) is never reached, so no body edit is proposed.
   - Step 2 never evaluates `Publish Codex policy result`, so the step-2 bypass exception is never used.
   - Step 3 (merge rights) does not run.
   - Step 4 never screens or posts the bypass reason, never writes the `gh-pr-review` marker, and never applies the `s: codex review bypassed` label.
   - Step 5 confirmation never occurs, and step 7 never runs `gh pr merge`.
   - Step 8 (`finishing-work` offer) never occurs.

6. **Report to the user.** The report names:
   - the touched reviewer Minor, its file, and that it was not deferred;
   - that nothing was fixed, pushed, filed or attested;
   - that the Codex bypass was not attested and nothing was merged;
   - that `Publish Codex policy result` was not evaluated because the run stopped earlier.

7. **Way forward.** The caller resolves the Minor, or the user explicitly defers it in conversation (which makes it deferred on a rerun). Then a new head is vetted and the skill is re-invoked. A new bypass attempt needs a fresh invocation, since the step-2 exception applies once per run.

## Key points

- The bypass flag does not reach past step 1.5. Its own text forbids fixing or pushing there, and a touched, non-deferred item stops the run before any attestation.
- The stop is a plain run end, not a question. The skill does not ask whether to defer the item, because deferral must come from the user's own words in this session.
