# Eval 2: PR #102, ty 0.0.71 -> 0.0.84 (simulated; nothing was run or posted)

## Where this lands in the skill
Step 6.1 (live re-read) is done, and its `files` and `commits` data still look clean.
Step 6.4 (required CI) is done: the only failing required check is `Publish Codex policy result`, and nothing is pending.
`Codex delta review` also fails, but it is not required, so it is ignored.
So this is step 6.5, the Codex policy check. I follow `references/codex-bypass.md` to decide whether a bypass is offered.

## Bypass conditions, evaluated against the facts given
0. Values: the title matches `bump (\S+) from (\S+) to (\S+)`, giving package `ty`, old `0.0.71`, new `0.0.84`. All three pass the validation regexes, and `{owner}/{repo}` was already validated in step 1. OK.
1. `Publish Codex policy result` is the only failing required check and nothing required is pending. OK.
2. The branch `dependabot/uv/ty-0.0.84` equals `dependabot/uv/<package>-<new>`. OK, and it is not a grouped update.
3. The files API shows exactly one file, `uv.lock`, status `modified`, and the 6.1 `files` list agrees. OK. `pyproject.toml` is untouched.
4. `check_uv_lock_bump.py` printed `"ok": true` with exit code 0. OK. I read the JSON as well as the exit code, and I will show its file-entry summary to the user. A stale branch is not indicated.
5. Every commit is verified, author is `dependabot[bot]`, committer is `web-flow`, and the last commit's sha equals the head SHA. OK. It is under 100 commits, so the list is not truncated.
6. The reason values pass validation. OK.

All conditions hold, so the bypass is offered. The approved head SHA is the `headRefOid` from the 6.1 read, `0123456789abcdef0123456789abcdef01234567`.

## Ask the user: a dedicated AskUserQuestion for the bypass
It shows:
- PR #102, head SHA `0123456789abcdef0123456789abcdef01234567`.
- Package `ty`, 0.0.71 to 0.0.84, a dev dependency (`chore(deps-dev)`).
- The classifier summary: only `ty`'s version and its `files.pythonhosted.org` file entries changed in `uv.lock`.
- The full reason text, filled from the template:
  "Dependency-only update by dependabot (uv: ty 0.0.71 to 0.0.84). Codex delta review refuses to dispatch on dependency-spec paths by design; lockfile change verified by parsing base and head to touch only this package's version and its PyPI file entries, commits report GitHub-verified signatures with author dependabot[bot], other required checks passing; approved by the maintainer through triaging-dependabot-prs."

It states plainly:
- Approving posts a public, permanent attestation comment and applies a label before `merge-pr`'s own merge confirmation.
- Declining that confirmation later does not undo the comment or the label.
- The `s: codex review bypassed` label must already exist in the repo, or `merge-pr` stops after the comment is posted.
- The checks do not prove dependabot authorship. They bound what the change can be, and the maintainer's review is the backstop.
- A rebase would void the approval.

The options are: attest the bypass and hand to merge-pr / skip this PR / stop.
`merge-pr` asks for the merge itself, separately.

## If the user approves
1. Record the approved SHA, `0123456789abcdef0123456789abcdef01234567`.
2. Immediately before invoking, re-read `headRefOid` with `gh pr view 102 --json headRefOid`.
   - If it differs, the approval is void. Return to 6.1 (at most three returns per PR for a changed head, then skip with the reason).
   - If it is unchanged, continue.
3. Invoke `Skill(merge-pr)` with PR number 102, `--bypass-codex-review "<the validated reason above>"` and `--expected-head-sha 0123456789abcdef0123456789abcdef01234567`.

## How the merge is handled
- This skill does not merge, does not post the attestation comment, does not apply the label and does not write the marker for the attestation. All of that belongs to `merge-pr`.
- This skill adds no merge question of its own.
- This skill runs no Bash call between `merge-pr`'s marker write and its comment, because that would consume the marker and the comment would be denied.
- `merge-pr` runs its merge-rights check, applies the bypass because `Publish Codex policy result` is the only non-passing required check, and screens the reason.
- At its step 4(b) it resolves the head SHA itself and compares it to `--expected-head-sha` and to the head it classified at its step 2.
  - On a mismatch it stops before writing anything (no reason file, marker, comment or label) and reports both SHAs. I tell the user nothing was posted, return to 6.1 and re-run conditions 3 to 5 on the new head. That counts toward the three allowed returns.
  - On a match it posts the SHA-bound attestation comment and the label, polls `statusCheckRollup` for up to about five minutes for the replacement check, re-runs readiness checks, and asks the user to confirm the merge. That confirmation also states the merge-state and unresolved-thread disclosures.
- The user answers the nested prompts, which I flagged in the step 5 plan: the merge confirmation, possibly merge-vs-squash and a branch-delete question, and the `finishing-work` offer after the merge. The answer to that last one is "No - skip" until the end of the run, and I ignore any advice to check out the dependabot branch.
- After `merge-pr` returns (6.7), I run `gh pr view 102 --json state`; it must say `MERGED`.
  - If it does, I record #102 as merged.
  - If not, I record it as skipped with the reason `merge-pr` gave (declined confirmation, failing check, missing label and so on). If the bypass was posted, I say that the public attestation comment and label remain on the PR although it was not merged.
  - If `merge-pr` stopped because the branch is behind or conflicted, I ignore its `git-sync-branch` advice and return to 6.3 for an `@dependabot rebase` (asked first, posted through the marker-then-comment sequence). A rebase voids the bypass approval.
- Then I move to the next PR, which is now behind or conflicted because the base advanced. At wrap-up I report the merged / closed / skipped table and offer `Skill(finishing-work)` once, passing #102 if it was the last merged PR.
