# Codex bypass decision for PR #103 and PR #104 (simulated)

This is a simulated run. I ran no `gh`, `git`, shell command or script, posted nothing and invoked no other skill. The steps below are what I would do under `triaging-dependabot-prs` (SKILL.md step 6.5 and `references/codex-bypass.md`).

Both PRs reach step 6.5 the same way. After the step 6.1 live re-read and the step 6.4 `pr-checks` read, `Publish Codex policy result` is the only failing required check and no required check is pending. That failure is expected for every Dependabot PR, because `Codex delta review` never runs without Actions secrets. `codex-bypass.md` picks the path from the changed-file list:
- a PR whose only changed file is `uv.lock` takes **path A** (scripted);
- any other `uv` or `npm_and_yarn` PR takes **path B** (maintainer review).

A PR that fails path A for a given head SHA is never moved to path B for that head.

---

## PR #103 (`pyproject.toml` + `uv.lock`): bypass offered, path B

**Path:** B (maintainer review). The files are not exactly `uv.lock`. Under path A, condition 3 would refuse it outright: "Any other file, including `pyproject.toml`, means no bypass: a manifest change needs a human reviewer". Path B is the route for exactly this case.

**Checking path B's conditions, evaluated just before the approval question:**
0. **Values.** I parse `<package>`, `<old>` and `<new>` from the title with `\bbump (\S+) from (\S+) to (\S+)`. Each is validated against the reason-template patterns:
   - package: `^[A-Za-z0-9]([A-Za-z0-9._-]{0,98}[A-Za-z0-9])?$`, and it must equal the branch's package segment;
   - each version: `^[A-Za-z0-9][A-Za-z0-9.+_-]{0,39}$`;
   - `{owner}/{repo}`: `^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$`.

   If any value fails, there is no bypass and I report the PR as suspicious.
1. **Checks.** `Publish Codex policy result` is the only failing required check and nothing required is pending. Given, so this passes.
2. **Branch.** It is `dependabot/uv/<package>-<suffix>`. Names are compared lowercase with `_` read as `-`, and the suffix must match `^[0-9]+(\.[0-9A-Za-z+_-]+)*$` and be at most 40 characters. Given that it matches the title's package, this passes. The version itself is checked by the maintainer's review.
3. **Files.** `dependabot_pr_read.py files 103` must show:
   - `truncated` false;
   - only root `pyproject.toml` and `uv.lock`, both inside the `uv` expected paths;
   - each with `status` `modified` and `previous_filename` absent or null;
   - the same set as the `files` from the step 6.1 read that gave the approved head SHA.

   The prompt gives the two paths. I would still confirm `status` and `previous_filename` from the real output.
4. **Commits.** These are path A's condition 5. `dependabot_pr_read.py commits 103` must show every commit with `verified` true, author `dependabot[bot]` and committer `web-flow`, the last `sha` equal to the approved head SHA, and `truncated` false. Given, so this passes.
5. **uv lockfile sources.** I fetch base and head `uv.lock` into the session scratchpad with `dependabot_pr_read.py uv-lock`:
   - `--role base --ref <baseRefName>`;
   - `--role head --ref <approved-head-sha>`.

   Then I run `python3 -I ".../check_uv_lock_bump.py" --sources-only --base "<scratchpad>/base-uv.lock" --head "<scratchpad>/head-uv.lock"` in exactly that shape. It printed `"ok": true` with exit code 0, so this passes. It shows that every changed locked package comes from PyPI (`files.pythonhosted.org`, named for its own name and version) or is the root project. It does **not** prove a single-package bump, or why the packages changed.
6. **Maintainer confirmation.** This happens in the approval question below.
7. **Reason.** The reason values pass validation, as in condition 0.

**Approval question (`AskUserQuestion`).** It shows:
- path B, PR #103, the approved head SHA, and the package with its old and new versions;
- the changed files (`pyproject.toml`, `uv.lock`) and the summary of the `--sources-only` check;
- the pinned diff link `https://github.com/{owner}/{repo}/compare/<baseRefName>...<approved-head-sha>`.

It also gives the review guidance:
- GitHub collapses large lockfile diffs ("Load diff"), so the lockfile must be expanded and read;
- look for a dependency other than `<package>` changing;
- look for any URL outside `files.pythonhosted.org` or `registry.npmjs.org`;
- look for any unexpected change in `pyproject.toml`.

It states plainly that:
- `<old>` and `<new>` come from the PR title, which is not machine-verified, and path B is not a verified check;
- approving posts a public, permanent attestation comment and applies the `s: codex review bypassed` label before `merge-pr`'s own merge confirmation;
- declining that confirmation does not undo the comment or the label;
- the label must already exist in the repository, or `merge-pr` stops after the comment is posted.

Options: **"I read the diff at this SHA; attest the bypass and hand to merge-pr"** / skip this PR / stop. Any answer other than the first means no bypass.

**Reason text (path B template, uv, sources check ran):**

```
Dependabot PR (from title, not machine-verified: uv <package> <old> to <new>). Codex delta review does not run for Dependabot PRs (no Actions secrets); changed files limited to the ecosystem's root manifest and lockfile; uv.lock package sources checked against PyPI by parsing base and head; commits report GitHub-verified signatures with author dependabot[bot]; other required checks passing; diff read and approved by the maintainer through triaging-dependabot-prs.
```

There is no "Python quality skipped" clause, because that clause is only for `npm_and_yarn`.

**After approval:**
1. I record the approved SHA and re-read `headRefOid` immediately before `merge-pr`. If it changed, the approval is void and I return to 6.1, at most three times per PR.
2. I invoke `Skill(merge-pr)` with `103 --bypass-codex-review "<reason>" --expected-head-sha <approved SHA>`. `merge-pr` does the rest:
   - it runs its readiness and merge-rights checks;
   - at its step 4(b) it compares the head SHA with the approved SHA;
   - it posts the attestation and the label;
   - it polls for the re-run check;
   - it asks for the merge itself, so I add no merge question of my own, and I run no Bash call between its marker write and its comment.
3. At step 6.7 I confirm the state is `MERGED`. If it is not, I record why. If `merge-pr` posted the comment and label but did not merge, I say they remain on the PR.

---

## PR #104 (only `uv.lock`, classifier exit 1): no bypass offered

**Path:** A (scripted uv lockfile check), because the only changed file is `uv.lock`. Path A fails at condition 4. `check_uv_lock_bump.py` (default mode, `--package/--old/--new`) exited 1 with `entry key 'dependencies' changed`. That is a new dependency edge, and path A requires the bumped package's dependency edges to stay unchanged. Path A requires `"ok": true` with exit 0, so this means **no bypass**.

**No rebase detour.** The stale-branch rule in condition 4 applies only to the reasons `expected exactly one package entry replaced` and `top-level key ... changed`. This reason is neither, and the branch is already current with its base. So I do not take step 6.3's rebase path and post no `@dependabot rebase`.

**No fallback to path B.** A PR that fails path A for a head SHA is reported and never moved to path B for that head. The `--sources-only` mode is not run for #104.

**What I do instead:**
- I record PR #104 as **skipped: Codex policy failure not explained by a qualifying bypass; report for manual review**.
- I include the classifier's printed reason (`entry key 'dependencies' changed`) and the JSON reasons in the report.
- I ask no bypass question, call no `merge-pr` with the flag, and post no comment or label.
- I continue with the next PR.

The wrap-up table lists #104 as skipped with that reason. A maintainer can review the new dependency edge and handle it manually, outside this skill's bypass. A later rebase that produces a new head would be classified again from its own file list.

---

## Summary

| PR | Files | Path | Bypass offered? | Action |
|---|---|---|---|---|
| #103 | `pyproject.toml`, `uv.lock` | B (maintainer review) | Yes, if every path B condition holds and the maintainer picks "I read the diff at this SHA" | `AskUserQuestion` with the pinned diff link and review guidance, then `Skill(merge-pr)` with `--bypass-codex-review "<path B reason>" --expected-head-sha <SHA>` |
| #104 | `uv.lock` only | A (scripted) | No: the classifier exited 1 (`entry key 'dependencies' changed`) | No rebase (the reason is not stale-branch and the branch is current), no path B fallback; report for manual review, skip, continue |
