# Eval 2: PR #102, Codex bypass path (simulated)

## 1. Deciding whether the bypass is offered (references/codex-bypass.md)

I evaluate the conditions one by one just before asking. Nothing is posted yet.

- **0. Values.** The title `chore(deps-dev): bump ty from 0.0.71 to 0.0.84` matches `\bbump (\S+) from (\S+) to (\S+)`. That gives package `ty`, old `0.0.71`, new `0.0.84`. Both versions pass `^[A-Za-z0-9][A-Za-z0-9.+_-]{0,39}$` and the package passes its pattern. `{owner}/{repo}` from the PR url matches `^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$`. The approved head SHA `0123456789abcdef0123456789abcdef01234567` is 40 lowercase hex characters, and I take it from the `headRefOid` of the step 6.1 re-read.
- **1. Checks.** In `dependabot_pr_read.py pr-checks 102`, `Publish Codex policy result` is the only failing required check and nothing is pending. `Codex delta review` also fails, but it is not required, so I ignore it. This holds. (`merge-pr` re-checks against branch protection and refuses before attesting if it disagrees.)
- **2. Branch.** `dependabot/uv/ty-0.0.84` equals `dependabot/uv/<package>-<new>` (lowercase, `_` read as `-`). It is not a grouped update. This holds.
- **3. Files.** The files read shows exactly one file, `uv.lock`, at the repository root, with status `modified`. I confirm `previous_filename` is absent or null and that `truncated` is false. The step 6.1 `files` list for this same head must also be exactly `uv.lock`. This holds.
- **4. Lockfile classifier.** `check_uv_lock_bump.py` was run in the required shape: `python3 -I ... --base <scratchpad>/base-uv.lock --head <scratchpad>/head-uv.lock --package ty --old 0.0.71 --new 0.0.84`. The lockfiles were fetched through `dependabot_pr_read.py uv-lock` into the scratchpad. It printed `"ok": true` with exit code 0, so this holds. I read the JSON itself, not just the exit code, and keep its summary of the file entries checked for the approval question.
- **5. Commits.** Every commit is verified, the author is `dependabot[bot]`, the committer is `web-flow`, and the last commit's sha equals the head SHA. `truncated` is not true. This holds.
- **6. Reason values.** All pass validation.

All conditions hold, so the bypass is offered. If any had failed, I would report the PR as an unexplained failure and skip it. The one exception is a classifier failure from a stale branch, which would go back to the 6.3 rebase path.

## 2. What the user is shown and asked

I ask via `AskUserQuestion`. I do not post anything and do not invoke `merge-pr` before the answer. The question shows:

- PR #102 and the head SHA `0123456789abcdef0123456789abcdef01234567`.
- Package `ty`, 0.0.71 to 0.0.84, a dev-dependency bump.
- The classifier summary (the file entries checked) and the evidence: one file changed (`uv.lock`), all commits GitHub-verified with author `dependabot[bot]` and committer `web-flow`.
- The full reason text, filled from the template and with nothing added:

  `Dependency-only update by dependabot (uv: ty 0.0.71 to 0.0.84). Codex delta review refuses to dispatch on dependency-spec paths by design; lockfile change verified by parsing base and head to touch only this package's version and its PyPI file entries, commits report GitHub-verified signatures with author dependabot[bot], other required checks passing; approved by the maintainer through triaging-dependabot-prs.`

- A plain statement that approving posts a public, permanent attestation comment and applies a label before `merge-pr`'s own merge confirmation, and that declining that confirmation does not undo them.
- A plain statement that the `s: codex review bypassed` label must already exist in the repository (`docs/ci.md`), or `merge-pr` stops after the comment is posted.
- A caveat that the checks do not prove dependabot authored the change. The signature check is stronger than the author name, but `docs/ci.md` records spoofing by a write-access collaborator as untested. The maintainer's own review is the backstop.
- The options: attest the bypass and hand to merge-pr / skip this PR / stop.

## 3. After the user approves: how the merge is handled

1. I record the approved SHA `0123456789abcdef0123456789abcdef01234567`.
2. Immediately before invoking `merge-pr`, I re-read `headRefOid` with `dependabot_pr_read.py pr-view 102 --fields ...`.
   - If it differs, the approval is void. I return to step 6.1 and re-run conditions 3 to 5 on the new head. At most three such returns are allowed per PR, then I skip it with the reason.
   - If it is unchanged, I continue.
3. I invoke `Skill(merge-pr)` with PR number 102, `--bypass-codex-review "<the reason text above>"` and `--expected-head-sha 0123456789abcdef0123456789abcdef01234567`.
4. This skill does not implement the attestation. `merge-pr` does all of the following itself:
   - runs the merge-rights check;
   - applies the bypass only because `Publish Codex policy result` is the only non-passing required check;
   - at its step 4(b), compares the head it resolves with `--expected-head-sha` and with the head from its own step 2, and stops without writing anything on a mismatch;
   - writes the `gh-pr-review` marker, posts the SHA-bound attestation comment and applies the label;
   - polls `statusCheckRollup` for the replacement check (up to about five minutes);
   - re-runs the readiness checks and asks for the merge confirmation, then binds the merge to the attested SHA (its step 7(b)).
5. I add no merge question of my own, no Bash call between `merge-pr`'s marker write and its comment, and no checkpoint of my own. I do not post any `@dependabot` comment, and I do not check out the dependabot branch even if `merge-pr` advises it. I tell the user in advance about the nested prompts: the `finishing-work` offer (answer "No - skip" until the end), the merge confirmation, and the branch-delete question.
6. Confirm (6.7): `pr-view 102 --fields state` must say `MERGED`.
   - If it does, I record the PR as merged.
   - If it does not, I record it as skipped with the reason `merge-pr` stated. If the attestation comment and label were actually posted, I say they remain on the PR even though it was not merged.
   - If `merge-pr` stopped at 4(b) on a SHA mismatch, nothing was posted. I say so and return to 6.1, which counts toward the three-return limit.
   - If `merge-pr` stopped because the branch is behind or conflicted, I ignore its `git-sync-branch` advice and go to 6.3 for `@dependabot rebase` (asked first, and posted through `dependabot_pr_action.py`). A rebase changes the head SHA and voids this approval.
7. I then continue with the next PR, which is now likely behind or conflicted. At wrap-up I report the merged, closed, skipped and pending PRs, and offer `Skill(finishing-work)` once, passing the number of the last merged PR.
