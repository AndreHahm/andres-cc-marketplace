# PR #102 (ty 0.0.71 -> 0.0.84): what happens next (simulated, nothing executed)

Position in the skill: step 6.5 (Codex policy check). Step 6.4 found `Publish Codex policy result` as the only failing required check with nothing pending, so I follow `references/codex-bypass.md` to decide whether a bypass is offered. The skill itself posts no bypass comment and no label; `merge-pr` does all of that. The skill only decides whether to pass the flag, and asks first.

## 1. Evaluate the bypass conditions (all must hold; fail closed)

| # | Condition | PR #102 |
|---|---|---|
| 0 | Title matches `\bbump (\S+) from (\S+) to (\S+)` (case-insensitive) | package `ty`, old `0.0.71`, new `0.0.84`. Package regex `^[A-Za-z0-9]([A-Za-z0-9._-]{0,98}[A-Za-z0-9])?$` ok; versions match `^[A-Za-z0-9][A-Za-z0-9.+_-]{0,39}$`. `{owner}/{repo}` (from the PR `url`) must match `^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$` per step 1; if not, stop. |
| 1 | Only `Publish Codex policy result` fails among required checks, none pending | Yes. `Codex delta review` also fails but is not required, so it is ignored. |
| 2 | Branch is exactly `dependabot/uv/<package>-<new>` (lowercase, `_` read as `-`) | `dependabot/uv/ty-0.0.84` = `ty` + `0.0.84`. Yes; also excludes grouped updates. |
| 3 | Files API returns exactly one file: root `uv.lock`, `status` `modified`, `previous_filename` absent/null | One file `uv.lock`, `modified`. I confirm `previous_filename` is absent/null in the same response. No `pyproject.toml`, so no manifest change. |
| 4 | Classifier says `"ok": true`, exit 0 | Yes. The lockfiles were fetched into the session scratchpad (base tip and the approved head SHA, not the branch name) and checked with `python3 -I .../check_uv_lock_bump.py --base ... --head ... --package ty --old 0.0.71 --new 0.0.84`. I read the JSON, not only the exit code. |
| 5 | Commits: all verified, author `dependabot[bot]`, committer `web-flow`, last commit sha == approved head SHA, page not full (100 = truncated) | Yes: all verified, correct author and committer, last sha equals `0123456789abcdef0123456789abcdef01234567`. I also check the commit count is under 100. |
| 6 | Reason values pass validation | Yes (see 2). |

Preconditions I also carry through: the approved head SHA is the `headRefOid` from the step 6.1 re-read made just before conditions 3 to 5. I assume the freshly read `mergeStateStatus` is not `BEHIND`/`DIRTY`; if it were, I would take the step 6.3 rebase path (ask, marker then `@dependabot rebase`, cap of two) and re-run all conditions on the new head. The classifier passing on a stale-branch lockfile is not expected, and a classifier failure of the "exactly one package entry replaced" kind would also route to that rebase path once.

All conditions hold, so the bypass is offered. I do not post anything or run any marker script at this point.

## 2. What the user is shown and told (one `AskUserQuestion`)

The question shows:

- PR number 102 and head SHA `0123456789abcdef0123456789abcdef01234567`.
- Package `ty`, `0.0.71` to `0.0.84` (dev dependency, `chore(deps-dev)`).
- The classifier's summary (file entries checked) and the facts that only `uv.lock` changed and commits are GitHub-verified from `dependabot[bot]` via `web-flow`.
- The full reason text that would be posted verbatim:

  > Dependency-only update by dependabot (uv: ty 0.0.71 to 0.0.84). Codex delta review refuses to dispatch on dependency-spec paths by design; lockfile change verified by parsing base and head to touch only this package's version and its PyPI file entries, commits report GitHub-verified signatures with author dependabot[bot], other required checks passing; approved by the maintainer through triaging-dependabot-prs.

It states plainly that:

- Approving makes `merge-pr` post a **public, permanent attestation comment** and apply the `s: codex review bypassed` label **before** `merge-pr`'s own merge confirmation, and **declining that later merge confirmation does not undo the comment or label**.
- That label must **already exist** in the repository (`docs/ci.md`); if it does not, `merge-pr` stops after the comment is already posted.
- The checks do not prove dependabot authored the change (`docs/ci.md` records the `web-flow`/spoofed-author question as untested); they bound the change to this package's version bump. The maintainer's own review is the backstop.
- `merge-pr` asks for the merge itself, separately.

Options: attest the bypass and hand to merge-pr / skip this PR / stop. Skip records the PR as skipped; stop ends the run to wrap-up.

## 3. On "attest": the SHA checkpoint, then `merge-pr`

1. Record the approved SHA. Immediately before invoking the skill, re-read `headRefOid` (`gh pr view 102 --json headRefOid`). If it differs, the approval is void: back to step 6.1 (max three returns per PR, then skip with the reason).
2. Invoke `Skill(merge-pr)` with `102` and `--bypass-codex-review "<the reason above>"`. I add no merge question of my own.
3. `merge-pr` then does, in its own steps: resolves and validates the PR (step 1); the session open-issues check (1.5), whose "check out the PR branch" advice I ignore and I do not check out a dependabot branch; readiness (step 2), applying its bypass exception because `Publish Codex policy result` is the only non-passing required context; the merge-rights check (step 3, always before any attestation); then step 4:
   - 4(a) screens the reason text.
   - **Required checkpoint (step 4(b))**: take the `headRefOid` that `merge-pr` resolves in its first Bash call, which comes before the marker write, and compare it with the approved SHA `0123456789abcdef0123456789abcdef01234567`. On mismatch: stop without the marker or the comment, return to step 6.1 and re-run conditions 3 to 5 on the new head. I never add a Bash call of my own between `merge-pr`'s marker write and its comment, since that would consume the marker and the comment would be denied.
   - If it matches, `merge-pr` writes the `gh-pr-review` marker, posts the SHA-bound attestation comment, captures the policy-check baseline, checks the label exists and applies it, polls `statusCheckRollup` (up to 20 times, 15 s apart) for the replacement `Publish Codex policy result`, then re-runs every readiness check without the bypass exception.
4. Prompts the user will see mid-run (also announced in the step 5 plan): the merge confirmation (with `mergeStateStatus` and unresolved-thread disclosures, noting Codex review was bypassed and why), possibly merge-vs-squash / branch-delete questions, a wait of up to about five minutes during polling, and the post-merge `finishing-work` offer, which I answer "No - skip" because it would switch the checkout to `main` mid-loop.

## 4. How the merge is handled

- Only `merge-pr` asks for and executes the merge (its step 7(b): final recheck without the bypass exception, then the `gh-pr-merge` marker and `gh pr merge --match-head-commit <verified SHA>`; it binds the merge to the attested SHA, so a later push voids the attestation). The skill itself runs no merge, PR edit, label change or push.
- Afterward I run `gh pr view 102 --json state`. If it says `MERGED`, record PR #102 as merged.
- If it does not (declined confirmation, draft, requested changes, failing or missing required check, merge-rights failure, label missing, replacement check never completing, head SHA changed), record PR #102 as skipped with the reason `merge-pr` stated. After a bypass I also tell the user the public attestation comment and the label remain on the PR even though it was not merged. If `merge-pr` stopped because the branch is behind or conflicted, I ignore its `git-sync-branch` advice and go back to the 6.3 rebase path (ask, marker then `@dependabot rebase`; a rebase voids any bypass approval since the head SHA changes, so approval is re-sought after the final rebase).
- Then continue to the next PR (the remaining ones are now behind or conflicted, since uv PRs share `uv.lock`; never resolve that by hand). At wrap-up, report merged/closed/skipped/pending, and offer `Skill(finishing-work)` once via `AskUserQuestion`, passing PR 102 (or the last merged PR's number).

## Files read

- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/SKILL.md
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/references/codex-bypass.md
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/references/ordering-and-checks.md
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/references/test-scenarios.md
- <repo-root>/plugins/git-kit/skills/merge-pr/SKILL.md (lines 1-325 of 430 only)
