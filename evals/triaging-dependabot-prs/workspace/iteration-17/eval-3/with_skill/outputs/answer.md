# Codex bypass decision for PR #103 and PR #104 (simulated)

This is a simulation, so I ran no commands, scripts or skills. Every step below is what I would do under `triaging-dependabot-prs` step 6.5 and `references/codex-bypass.md`.

For both PRs, `Publish Codex policy result` is the only failing required check and no required check is pending. That meets condition 1 on both paths. The check fails because the `Codex delta review` job never runs for Dependabot: Dependabot runs get no Actions secrets. The skill does not attest anything itself. It only decides whether to pass `--bypass-codex-review` to `merge-pr`, and it asks the user first.

`codex-bypass.md` decides the path by the changed files:
- **Path A (scripted check):** the PR's only changed file is `uv.lock`.
- **Path B (maintainer review):** every other `uv` or `npm_and_yarn` PR.
- A PR that fails path A's conditions is reported. It is **never moved to path B**.

---

## PR #103: `pyproject.toml` and `uv.lock` changed. Bypass offered through path B.

**Why path B:** the changed files are not exactly `uv.lock`. Path A's condition 3 fails because a `pyproject.toml` change needs a human reviewer. Path B covers this case: a `uv` PR whose files are all in the ecosystem's expected paths. For `uv` those are the root `pyproject.toml` and `uv.lock`.

**Checks, done just before asking.** The approved head SHA is the `headRefOid` from the step 6.1 re-read: `pr-view 103 --fields state,mergeStateStatus,headRefOid,baseRefName,files,commits`.
- **B0, values:** parse `<package>`, `<old>` and `<new>` from the title with `\bbump (\S+) from (\S+) to (\S+)` (case-insensitive).
  - Package must match `^[A-Za-z0-9]([A-Za-z0-9._-]{0,98}[A-Za-z0-9])?$` and equal the branch's package segment.
  - Each version must match `^[A-Za-z0-9][A-Za-z0-9.+_-]{0,39}$`.
  - `{owner}/{repo}` must match `^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$`.
  - If any value fails, the PR is suspicious and no bypass is offered.
- **B1, required checks:** `dependabot_pr_read.py pr-checks 103` shows `Publish Codex policy result` as the only failure and nothing pending.
- **B2, branch:** `dependabot/uv/<package>-<suffix>`. Names are compared lowercase, with `_` read as `-`. The suffix is at most 40 characters and matches `^[0-9]+(\.[0-9A-Za-z+_-]+)*$`. The scenario says the branch matches.
- **B3, files:** `dependabot_pr_read.py files 103` must show:
  - `truncated` false;
  - exactly `pyproject.toml` and `uv.lock` at the root;
  - each with `status` `modified` and `previous_filename` absent or null;
  - the same set as the 6.1 `files` list that produced the approved SHA.
- **B4, commits:** `dependabot_pr_read.py commits 103` must show:
  - `truncated` false;
  - every commit with `verified` true, author `dependabot[bot]` and committer `web-flow`;
  - the last commit's `sha` equal to the approved head SHA.

  The scenario says all of this holds.
- **B5, maintainer review:** nothing checks what changed inside the files. A manifest edit, a new dependency or a changed registry would show only in the diff. The maintainer's own reading of the diff is the review, and I do not describe path B as a verified check.
- **B6:** the reason values pass validation.

**Approval:** one `AskUserQuestion` that shows:
- path B, PR #103, the approved head SHA, and the package with its old and new version;
- the changed files (`pyproject.toml`, `uv.lock`) and the link `https://github.com/{owner}/{repo}/pull/103/files`;
- the full path B reason text:
  > Dependency-only update by dependabot (uv: `<package>` `<old>` to `<new>`). Codex delta review does not run for Dependabot PRs (no Actions secrets); changed files limited to the ecosystem's manifest and lockfile, commits report GitHub-verified signatures with author dependabot[bot], other required checks passing; diff read and approved by the maintainer through triaging-dependabot-prs.
- a plain warning on three points:
  - Approving posts a public, permanent attestation comment and applies a label before `merge-pr`'s own merge confirmation. Declining that confirmation does not undo them.
  - The `s: codex review bypassed` label must already exist, or `merge-pr` stops after the comment is posted.
  - `merge-pr` may wait up to about five minutes for the replacement check.

The options are:
1. "I read the diff at this SHA; attest the bypass and hand to merge-pr"
2. "Skip this PR"
3. "Stop"

Any answer other than option 1 means no bypass, and the PR is recorded as skipped.

**If approved:**
1. Re-read `headRefOid` right before the handoff. If it changed, the approval is void and I return to 6.1. A PR gets at most three returns, then it is skipped.
2. Invoke `Skill(merge-pr)` with `103 --bypass-codex-review "<reason above>" --expected-head-sha <approved SHA>`.
   - `merge-pr` checks merge rights and branch protection, and compares SHAs at its step 4(b). It then posts the comment and label, polls for the replacement check, and asks for the merge itself. I add no merge question of my own.
   - I add no Bash call of my own between its marker write and its comment.
3. Confirm with `pr-view 103 --fields state` that the state is `MERGED`.
   - If `merge-pr` stopped on a SHA mismatch, nothing was posted, and I return to 6.1.
   - If it did not merge after posting, I say that the comment and label stay on the PR.

---

## PR #104: only `uv.lock` changed. No bypass. The PR is reported for manual review and skipped.

**Why path A:** the only changed file is `uv.lock`. Conditions A0 to A3 pass: the values are valid, the only failing check is the Codex one, the branch matches, and `files 104` shows exactly root `uv.lock`, `modified`, not renamed.

**Condition A4 fails.** I would fetch the base and head lockfiles into the session scratchpad:
- `dependabot_pr_read.py uv-lock --role base --ref <baseRefName> --dir "<scratchpad>"`
- `dependabot_pr_read.py uv-lock --role head --ref <approved-head-sha> --dir "<scratchpad>"`

Then I would run `python3 -I .../check_uv_lock_bump.py --base ... --head ... --package <package> --old <old> --new <new>`. It exits 1, not `"ok": true`, with the reason `entry key 'dependencies' changed`. The package's dependency edges changed: the update added a new dependency. The script's job is to pass only a pure version bump with unchanged edges, so any result other than ok with exit 0 means no bypass. Condition A5 (commits) passing does not help.

**Not a rebase case.** The stale-branch path back to 6.3 is only for the reasons `expected exactly one package entry replaced` or `top-level key ... changed`. `entry key 'dependencies' changed` is neither. The scenario also says the branch is current with its base. So I post no `@dependabot rebase`, and no rebase would remove the new edge anyway.

**Not moved to path B.** A PR that fails path A's conditions is reported, never re-routed to the maintainer-review path. That holds even though path B would accept a `uv.lock`-only file list, and even if the maintainer offers to read the diff.

**What I do:**
- Report PR #104 as a Codex policy failure with no bypass, for manual review.
- Quote the script's JSON reason (`entry key 'dependencies' changed`) as data in the report.
- Say plainly that the bump pulls in a new dependency edge, which needs a human or a real Codex review, not an attestation.
- Record the PR as **skipped**, with that reason, in the step 7 wrap-up table. Then move on to the next PR.

I do not invoke `merge-pr` with `--bypass-codex-review`, and I do not invoke it without the flag either: the required check would block the merge, and there is no override path. I post no comment and do not close the PR unless the user separately asks for one; each would need its own `AskUserQuestion`, a `--dry-run` first, and `dependabot_pr_action.py`.

---

## Summary

| PR | Files | Path | Bypass offered? | Action |
|---|---|---|---|---|
| #103 | `pyproject.toml`, `uv.lock` | B (maintainer review) | Yes, only if B0 to B6 hold and the maintainer picks "I read the diff at this SHA; attest the bypass" | Re-read the head SHA, then `Skill(merge-pr)` with `--bypass-codex-review "<path B reason>" --expected-head-sha <SHA>`, then confirm `MERGED` |
| #104 | `uv.lock` only | A (scripted), fails condition 4 | No | Report for manual review with the script's reason, skip. No rebase (not a stale-branch reason, and the branch is current), not moved to path B, no merge |
