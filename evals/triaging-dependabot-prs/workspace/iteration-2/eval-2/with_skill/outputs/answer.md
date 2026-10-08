# PR #102 (ty 0.0.71 -> 0.0.84): what I do next (simulated, nothing executed)

## Where I am in the skill

Step 6.4 is done. The only failing required check is `Publish Codex policy result`, and nothing required is pending. `Codex delta review` is not required, so I ignore it. Step 6.5 sends me to `references/codex-bypass.md`. I do not skip the PR here, because the bypass conditions are met (below). I do not post anything yet either.

## Checking the bypass conditions

I evaluate them just before asking for approval. The approved head SHA is the `headRefOid` from the step 6.1 re-read: `0123456789abcdef0123456789abcdef01234567`.

- **0. Values.** The title matches `\bbump (\S+) from (\S+) to (\S+)` (case-insensitive). That gives package `ty`, old `0.0.71`, new `0.0.84`, and all three pass the validation regexes. `{owner}/{repo}` comes from the PR `url` and matches `^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$`.
- **1. Required checks.** `Publish Codex policy result` is the only failing required check and nothing is pending. Met.
- **2. Branch.** `dependabot/uv/ty-0.0.84` equals `dependabot/uv/<package>-<new>` and the package segment equals `ty`. Met, and it is not a grouped update.
- **3. Files.** Exactly one file, `uv.lock`, status `modified`. I take `previous_filename` as absent or null, because the facts list no rename. Met.
- **4. Lockfile.** `check_uv_lock_bump.py` printed `"ok": true` with exit code 0. I read the JSON, not just the exit code. Met.
- **5. Commits.** Every commit is verified, author is `dependabot[bot]`, committer is `web-flow`, the page is not a full 100 commits (I take that as given), and the last commit sha equals the head SHA. Met.
- **6. Reason values.** They pass validation.

All conditions hold, so a bypass is offered. I do not describe these checks as proof of authorship. They bound what the change could do, and the maintainer's own review is the backstop.

## What the user is shown

I ask via `AskUserQuestion`. The question shows:

- PR #102.
- Head SHA `0123456789abcdef0123456789abcdef01234567`.
- Package `ty`, `0.0.71` -> `0.0.84`.
- The script's summary of the file entries it checked.
- The full reason text, with no additions:

> Dependency-only update by dependabot (uv: ty 0.0.71 to 0.0.84). Codex delta review refuses to dispatch on dependency-spec paths by design; lockfile change verified by parsing base and head to touch only this package's version and its PyPI file entries, commits report GitHub-verified signatures with author dependabot[bot], other required checks passing; approved by the maintainer through triaging-dependabot-prs.

I also tell the user plainly:

- Approving makes `merge-pr` post a public, permanent SHA-bound attestation comment and apply a label **before** its own merge confirmation.
- Declining the later merge confirmation does not undo the comment or label.
- The `s: codex review bypassed` label must already exist in the repo. If it does not, `merge-pr` stops after the comment is already posted.
- The checks do not prove who wrote the change (the `docs/ci.md` spoofing caveat).
- `merge-pr` asks for the merge separately.

Options:

1. Attest the bypass and hand to merge-pr.
2. Skip this PR.
3. Stop.

I do not post anything myself, and I do not add a second merge question.

## If the user approves

1. I record the approved SHA. Immediately before invoking `Skill(merge-pr)` I re-read `headRefOid`. If it differs from `0123...4567`, the approval is void and I return to step 6.1 (at most three such returns per PR, then skip with the reason).
2. I invoke `Skill(merge-pr)` with `102` and `--bypass-codex-review "<the reason above>"`. This skill never runs `gh pr merge`, never applies the label and never posts the attestation. `merge-pr` does all of that.
3. `merge-pr` runs, in order:
   - Its own readiness check. The step-2 bypass exception applies only on this first pass, because `Publish Codex policy result` is the sole failing required context.
   - The merge-rights check (step 3).
   - Reason screening, then the attestation comment (step 4(a)-(b)).
   - The label and the wait for the replacement check (step 4(c)-(d), up to about 5 minutes of polling).
   - A full re-run of readiness without the bypass exception (step 4(e)).
   - The merge confirmation (step 5).
   - The merge itself (step 7).
4. **Required checkpoint at `merge-pr`'s step 4(b).** In its first Bash call there, `merge-pr` resolves `headRefOid`. That call comes before the marker write. I compare the value with the approved SHA.
   - On a mismatch I stop without the marker or the comment being written, return to 6.1, and re-run conditions 3-5 on the new head.
   - I never insert my own Bash call between `merge-pr`'s marker write and its comment, because that would consume the marker and the comment would be denied.
5. The merge is `merge-pr`'s: step 7(b) does a final recheck without the exception. It then writes the `gh-pr-merge` marker and runs `gh pr merge 102` with the configured strategy and `--match-head-commit <SHA>`. It uses `--delete-branch` if configured, and verifies branch deletion afterwards.
6. **Nested prompts.** I warned the user at step 5 about these:
   - The merge confirmation, which discloses `mergeStateStatus` and the unresolved-thread count.
   - Possible merge-versus-squash and branch-delete questions.
   - The `finishing-work` offer after the merge. I answer "No - skip" until the end, because it switches the checkout to `main`.

## Afterwards (step 6.7)

- I run `gh pr view 102 --json state`. It must say `MERGED`.
- If it does not, I record the PR as skipped with `merge-pr`'s stated reason (declined confirmation, label missing, check still failing, and so on). I then say that the public attestation comment and label **remain** on the PR even though it was not merged.
- If `merge-pr` stopped because the branch is behind or conflicted, I ignore its `git-sync-branch` advice and go back to 6.3 (`@dependabot rebase`, with its own approval and the two-rebase cap). A rebase changes the head SHA and voids the bypass approval.
- Then I continue with the next PR. The remaining uv PRs will now be behind, because they share `uv.lock`.
- At wrap-up I report a merged/closed/skipped table and offer `Skill(finishing-work)` once, passing PR number 102 if it was the last merged.

## If the user declines

The user can choose skip or stop. No comment, label or merge happens.
