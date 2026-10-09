# Eval 2: PR #102 (ty 0.0.71 to 0.0.84), Codex bypass decision

Simulated. I run no command, post nothing, and do not invoke any skill. This describes what I would do.

## 1. Where this sits in the loop

The PR is already past 6.1 (live re-read), 6.2 (recommendation is merge, so no skip or close) and 6.4 (required CI). The only failing required check is `Publish Codex policy result`, and nothing is pending. `Codex delta review` is not a required check, so its failure is ignored. This is step 6.5, so I follow `references/codex-bypass.md` and do not treat it as an ordinary blocker.

Branch freshness (6.3): I assume the 6.1 read showed `mergeStateStatus` is not `BEHIND` or `DIRTY`. If it had been, the PR would go to a `@dependabot rebase` path first, asked separately, and the bypass would wait for the new head. The classifier output also gives no sign of a stale uv branch (see condition 4).

## 2. Evaluating every bypass condition

I evaluate these just before asking. The approved head SHA is the `headRefOid` from the 6.1 read, `0123456789abcdef0123456789abcdef01234567`. I validate that it is 40 lowercase hex characters.

- **0. Values.** The title matches `\bbump (\S+) from (\S+) to (\S+)`:
  - package `ty`, old `0.0.71`, new `0.0.84`.
  - `ty` fits the package pattern. Both versions fit the version pattern.
  - `{owner}/{repo}` from the PR url matches its pattern.
  - Pass.
- **1. Only failing required check.** `Publish Codex policy result` is the only failing required check and nothing required is pending. Pass.
- **2. Branch name.** `dependabot/uv/ty-0.0.84` equals `dependabot/uv/<package>-<new>`, compared lowercase with `_` read as `-`. Pass. A grouped update would not match, so this also confirms it is not one.
- **3. Files.** Exactly one file: `uv.lock` at the repo root, status `modified`, no `previous_filename`. The `files` list from the same 6.1 read that produced the SHA must also be exactly `uv.lock`, so the list and the SHA describe the same head. `truncated` is not true. There is no `pyproject.toml` change. Pass.
- **4. Lockfile content.** I fetched the base and head `uv.lock` into the session scratchpad through `dependabot_pr_read.py uv-lock` (role base at `baseRefName`, role head at the approved SHA). `check_uv_lock_bump.py --base ... --head ... --package ty --old 0.0.71 --new 0.0.84` printed `"ok": true` with exit code 0. I read the JSON, not just the exit code. Pass.
- **5. Commits.** Every commit is `verified`, author `dependabot[bot]`, committer `web-flow`, and the last commit's `sha` equals the approved head SHA. `truncated` is not true. Pass.
- **6. Reason values.** Pass validation (condition 0).

All conditions hold, so the bypass is offered. If any had failed, I would report the unexplained failure and skip the PR. The one exception is a stale uv branch, which returns to 6.3 for a rebase.

## 3. What the user is shown and asked

One `AskUserQuestion`. It is separate from, and earlier than, `merge-pr`'s merge confirmation. It shows:

- PR #102, head SHA `0123456789abcdef0123456789abcdef01234567`.
- Package `ty`, `0.0.71` to `0.0.84`, a dev dependency (`chore(deps-dev)`).
- The classifier summary: `uv.lock` is the only file, a single package entry replaced, file entries checked, `"ok": true`.
- The full reason text, filled from the template:

> Dependency-only update by dependabot (uv: ty 0.0.71 to 0.0.84). Codex delta review refuses to dispatch on dependency-spec paths by design; lockfile change verified by parsing base and head to touch only this package's version and its PyPI file entries, commits report GitHub-verified signatures with author dependabot[bot], other required checks passing; approved by the maintainer through triaging-dependabot-prs.

It also tells the user plainly:

- Approving makes `merge-pr` post a public, permanent attestation comment and apply a label before `merge-pr`'s own merge confirmation. Declining that merge confirmation does not undo the comment or label.
- The `s: codex review bypassed` label must already exist in the repo. Otherwise `merge-pr` stops after the comment is posted.
- The checks do not prove authorship. Commit verification does not rule out a spoofed `dependabot[bot]` author from someone with write access. The lockfile check bounds the change to this package's version bump and file entries, but it cannot say whether `0.0.84` is the version the maintainer wants. 0.0.x tool versions can be breaking, so the maintainer's own judgment is the backstop.
- `merge-pr` asks for the merge itself, separately.

Options: attest the bypass and hand to `merge-pr` / skip this PR / stop. I add no merge question of my own.

## 4. After approval: how the merge is handled

1. **Void check.** I record the approved SHA, then re-read `headRefOid` right before invoking `merge-pr`. If it differs from `0123...4567`, the approval is void and I return to 6.1 (at most three such returns per PR, then skip it with the reason). A rebase would also void it.
2. **Invoke `Skill(merge-pr)`** with PR 102, `--bypass-codex-review "<the reason above>"` and `--expected-head-sha 0123456789abcdef0123456789abcdef01234567`.
3. **What `merge-pr` does.** It runs its merge-rights check and confirms `Publish Codex policy result` is the only non-passing required check. At its step 4(b) it resolves the head itself and compares it with `--expected-head-sha` and with the head it classified in its step 2. If either differs, it stops before writing anything and reports both SHAs. Otherwise it screens the reason, writes the `gh-pr-review` marker, posts the SHA-bound attestation comment, applies the label, and polls `statusCheckRollup` for up to about five minutes for the replacement check. It then re-runs every readiness check and asks the user for the merge confirmation. It binds its merge to the attested SHA (step 7(b)), so a later push voids the attestation.
4. **My part.** I do none of the following:
   - post the attestation or the label;
   - add a Bash call between its marker write and its comment;
   - add my own checkpoint;
   - run a raw `gh` merge, comment or label command.
5. **Nested prompts I warn about up front.** The `finishing-work` offer after the merge (answer "No - skip" until the end, because it switches the checkout to `main`), the open-issues advice to check out the PR branch (ignored, I never check out a dependabot branch), the CODEOWNERS and merge-method and branch-delete prompts, and the merge confirmation with its disclosures.
6. **Confirm (6.7).** `gh pr view 102 --json state` must say `MERGED`.
   - If it does not, I record the PR as skipped with the reason `merge-pr` gave (declined confirmation, failing check, merge-rights failure, and so on). If `merge-pr` actually posted them, I add that the public attestation comment and label remain on the PR even though it was not merged.
   - If `merge-pr` stopped at 4(b) on a SHA mismatch, nothing was posted. I say so, return to 6.1 (counts toward the three returns), and re-run conditions 3 to 5 on the new head.
   - If it stopped as behind or conflicted, I ignore its `git-sync-branch` advice and go to 6.3 for a `@dependabot rebase` (asked separately, through `dependabot_pr_action.py`, capped at two posted rebases).
7. Then I go on to the next PR. The remaining PRs are now behind or conflicted because the base moved, especially other uv PRs sharing `uv.lock`. Their lockfiles are regenerated by `@dependabot rebase`, never resolved by hand. The wrap-up (step 7) reports the result and offers `Skill(finishing-work)` once, bound to the last merged PR number.
