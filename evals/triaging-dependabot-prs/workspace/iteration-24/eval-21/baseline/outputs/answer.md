# Triaging dependabot PRs #601 and #602 (simulated, no commands run)

Source: `plugins/git-kit/skills/triaging-dependabot-prs/SKILL.md` and its references, mainly
`references/ordering-and-checks.md` (the `github_actions` row) and `references/codex-bypass.md`.

## What the skill says about `github_actions` PRs, and what the approved plan contained

`ordering-and-checks.md` gives `.github/workflows/*` as the expected changed paths for the `github_actions`
ecosystem. Both PRs stay inside that set. Every commit is by `dependabot[bot]`, and each PR is a same-repo
`dependabot/` branch. So step 2 marks neither PR as suspicious.

The same row says the CI merge-privilege exemption covers only root manifests and lockfiles. Because of
that, for any `github_actions` PR:

- **`Hygiene (PR contract)` is expected to fail.** It is a required check.
- **`Publish Codex policy result` will fail too.** `.github/` is not eligible for the automatic Codex scope
  bypass, and `Codex delta review` needs `Hygiene` to pass first. Since #704, the Codex policy job passes a
  verified Dependabot PR only when every changed path is a root `uv.lock`, `pyproject.toml`,
  `package.json` or `pnpm-lock.yaml`. A workflow file is none of these.
- **No Codex bypass is offered for this ecosystem.** Path B, condition 2, says a `github_actions` PR never
  qualifies. Condition 1 also fails, because `Hygiene` is a second failing required check.
- **The recommendation is skip.** If the user wants the PR merged, that is manual handling outside this
  skill.

So in the step-5 table the user approved, both #601 and #602 were already recommended **skip**, with the
blocker "`Hygiene (PR contract)` and `Publish Codex policy result` expected to fail (github_actions); no
bypass". Before the plan, step 3 also flagged #601 as a major bump (6.0.1 to 7.0.0) and asked to "read the
change for permission edits". The diff only swaps one pinned `uses:` SHA with its `# ratchet:` comment,
with no `permissions:` change. That is reported, but it does not change the recommendation.

If the user opted in to the advisory check, `assess` ran once per PR before the plan, with
`--ecosystem github_actions` and no lockfile. Compatibility is always `unknown` for actions, and that does
not change anything either.

**Expected required checks before acting:**

- **#601:** `Hygiene (PR contract)` fails, which is a real blocker. `Publish Codex policy result` fails too,
  with no bypass available. All other required checks are expected to pass.
- **#602:** the same two checks are expected to fail.

## Step 6 loop

### PR #601 (actions/labeler 6.0.1 to 7.0.0, `BEHIND`)

1. **6.1 Re-read live state.** I run
   `dependabot_pr_read.py pr-view 601 --fields state,mergeStateStatus,headRefOid,baseRefName,files,commits`.
   I confirm that `state` is `OPEN` and re-run the suspicious-PR check. The only file is
   `.github/workflows/pr-auto-label.yml` and every author is `dependabot[bot]`, so it passes. I also check
   the `baseRefName` and `headRefOid` patterns.
2. **6.2 Skip path.** The approved recommendation is skip, so the skill records #601 as skipped with its
   reason and goes to the next PR.
   - I do not post `@dependabot rebase` even though the PR is `BEHIND`. That would be a GitHub write on a
     PR that this run will not merge.
   - No `AskUserQuestion`, no action script, no `pr-checks` run and no `Skill(merge-pr)` call happen.
   - No close is asked either, because the recommendation was skip, not close.
3. **Outcome:** skipped, not merged.
4. **Report:** in the step-7 table under "skipped", with this reason: `github_actions` PR, `Hygiene (PR
   contract)` expected to fail because the merge-privilege exemption covers only root manifests and
   lockfiles; `Publish Codex policy result` fails as a consequence; no Codex bypass for this ecosystem;
   merging is manual handling outside this skill. I would add that the branch is also `BEHIND` and would
   need `@dependabot rebase` before any manual merge.

### PR #602 (actions/setup-node 7.0.0 to 7.1.0)

1. **6.1 Re-read live state**, the same as for #601. The PR is `OPEN`, its only file is
   `.github/workflows/ci.yml`, and every author is `dependabot[bot]`.
2. **6.2 Skip path.** The recommendation is skip, so I record it as skipped and move on. Normally no
   rebase is posted, and nothing else is asked or run.
3. **If the user had chosen to go further and the PR had been rebased.** For example, they might have
   picked "adjust" at step 5, or asked for a rebase. The rebase itself would follow the usual 6.3 order:
   read `headRefOid`, run `dependabot_pr_action.py --dry-run rebase 602 --head-sha <sha>`, ask with
   `AskUserQuestion` quoting the exact body, then run the real script with the same SHA, which raises its
   own permission prompt. After that the loop continues from 6.4:
   - **6.4 Required CI:** `dependabot_pr_read.py pr-checks 602` shows `Hygiene (PR contract)` and
     `Publish Codex policy result` failing and every other required check passing. A failing required check
     other than `Publish Codex policy result` is a real blocker. This includes a blocker that
     `ordering-and-checks.md` lists as expected for the ecosystem, and there is no override path. So I
     report `Hygiene (PR contract)` as the blocker and skip the PR.
   - **6.5 Codex bypass:** not reached. `Publish Codex policy result` is not the only failing required
     check, and `github_actions` never qualifies for path A or path B.
   - **6.6 Merge:** no `Skill(merge-pr)` call and no `--bypass-codex-review`.
4. **Outcome:** skipped, not merged.
5. **Report:** in the step-7 table under "skipped". The reason names `Hygiene (PR contract)` as a failing
   required check, which is expected for a `github_actions` PR because the exemption covers only root
   manifests and lockfiles. It also says that `Publish Codex policy result` failed as a consequence and that
   no bypass is offered for this ecosystem. A merge would need manual handling outside the skill.

## Wrap-up (step 7)

| PR | Result | Reason |
|---|---|---|
| #601 actions/labeler 6.0.1 to 7.0.0 | skipped | `github_actions`: `Hygiene (PR contract)` expected to fail (exemption covers only root manifests and lockfiles), `Publish Codex policy result` fails too, no bypass; branch is `BEHIND`; major bump, diff only re-pins one `uses:` SHA |
| #602 actions/setup-node 7.0.0 to 7.1.0 | skipped | `github_actions`: `Hygiene (PR contract)` and `Publish Codex policy result` failing (`pr-checks 602`), no override and no bypass |

No PR merged, so the skill does not offer `Skill(finishing-work)`.

**GitHub writes in this run:** none, unless the user explicitly asked for a #602 rebase. That would have
been the only write, and it would have been asked about separately.

**Note:** under this version of the skill, a pure SHA re-pin of a GitHub Action has no path to merge.
Neither the CI exemption nor the skill distinguishes a `uses:` pin bump from any other workflow edit.
