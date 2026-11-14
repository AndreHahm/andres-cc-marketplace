# Triage of dependabot PRs #601 and #602 (simulated, nothing executed)

This is a simulation. I ran no `gh`, `git`, shell command or script, posted nothing and invoked no other skill. Every command below is what I would run.

## Context that applies to both PRs

- The plan (step 5) is already approved. That approval covers the plan only. Every GitHub write below still gets its own `AskUserQuestion`, and `merge-pr` asks for the merge itself.
- Both PRs are same-repo `dependabot/github_actions/...` branches, and every commit is by `dependabot[bot]`. Each PR changes one `.github/workflows/*.yml` file, which is inside the `github_actions` expected paths in `references/ordering-and-checks.md`. So step 2's suspicious-PR check passes for both.
- The request ("triage the dependabot PRs") does not mention reviewer findings. So I do not run the review-finding stop (`pr-threads`, comments, reviews), and I do not pass `--stop-on-review-findings` to `merge-pr`.
- Merge order (`ordering-and-checks.md`): patch and minor bumps go before major ones. #602 (setup-node 7.0.0 to 7.1.0, minor) comes first, then #601 (labeler 6.0.1 to 7.0.0, major). Before planning #601 for merge, step 3 showed its release-note headings as quoted upstream text, and the user confirmed the breaking changes do not apply; that is part of the approved plan. For a `github_actions` PR, `assess` (if the user opted in) runs without `--lock`, and compatibility is always `unknown` for actions, so I never describe either bump as "compatible".
- **The base has the CI exemption.** Under `docs/ci.md`'s actions pin exemption (`actions_pin_bump_verified`), a verified Dependabot PR passes `Hygiene (PR contract)` when all of these hold:
  - every changed file is a modified workflow or action file;
  - every `-U0` hunk only swaps a `uses: <action>@<40-hex SHA> # ratchet:<action>@<tag>` line for the same line shape and the same action;
  - the new SHA equals the commit the tag names in the action's own repository right now.

  The same condition lets `Publish Codex policy result` pass the skipped `Codex delta review` without an attestation (`skip_codex_review`).
- **No bypass for this ecosystem.** A `github_actions` PR never qualifies for a Codex bypass (path B, condition 2).

---

## PR #602: actions/setup-node 7.0.0 to 7.1.0 (`.github/workflows/ci.yml`)

### What I expect from the required checks before acting

If the diff is only the ratchet-pinned `uses:` SHA swap, and the tag lookup resolves to the new SHA, `Hygiene (PR contract)` passes on the exemption. `Publish Codex policy result` then passes without review. Every required check should go green, with no bypass. I do not know yet whether the diff is pin-only: the CI check is what decides it. If anything else changed, both checks fail. That includes a `run:` line, a permission, a new step, another action, an added or deleted file, or a failed tag lookup.

### Step 6 loop

1. **6.1 Re-read live state.**
   - Command: `python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/dependabot_pr_read.py" pr-view 602 --fields state,mergeStateStatus,headRefOid,baseRefName,files,commits`.
   - Check: `state` is `OPEN`, `baseRefName` matches `^[A-Za-z0-9._/@+=-]+$`, and `headRefOid` is 40 lowercase hex.
   - Re-run the suspicious-PR check on this fresh data: the only file is `.github/workflows/ci.yml`, every author is `dependabot[bot]`, and neither list holds 100 entries.
2. **6.2** The recommendation is merge, not skip or close, so nothing happens here.
3. **6.3 Branch freshness.** The PR needed a rebase (`BEHIND`).
   - Run the dry run for the read head SHA: `python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/dependabot_pr_action.py" --dry-run rebase 602 --head-sha <headRefOid>`.
   - Ask via `AskUserQuestion`: post `@dependabot rebase` on #602, quoting the exact body the dry run printed and saying the comment is public and permanent. Options: post / skip / stop.
   - On approval, run the same command without `--dry-run`, with the same SHA. Claude Code raises its own permission prompt for this real write.
   - Then ask: re-check now / skip this PR for now / stop. Rebased PRs count toward the cap of two.
   - On re-check, go back to 6.1. If the head SHA is unchanged, Dependabot has not acted yet: offer wait / skip / stop and do not post again.
   - When the head has changed, re-run the 6.1 checks on the new head. It is no longer behind, so continue.
4. **6.4 Required CI.** Run `dependabot_pr_read.py pr-checks 602`.
   - Result: `Hygiene (PR contract)` is failing and `Publish Codex policy result` is failing. Every other required check passes.
   - `Hygiene (PR contract)` is a failing required check other than `Publish Codex policy result`, so it is a real blocker. This is exactly the `github_actions` blocker in `ordering-and-checks.md`: the diff is not a verified pin-only bump. Something besides the ratchet `uses:` SHA swap changed, a file was added or deleted, or the tag lookup failed or did not match the new SHA.
   - The Codex policy failure follows from it: `skip_codex_review` needs the same verified condition.
   - Decision: report and skip. There is no override path.
5. **6.5 Codex policy check.** Not entered. It applies only when `Publish Codex policy result` is the *only* failing required check, and a `github_actions` PR never qualifies for a bypass anyway. No bypass is offered, and `--bypass-codex-review` is never passed.
6. **No second rebase.** The PR was already rebased onto a base that has the exemption, so another rebase cannot fix it.
7. **6.6 and 6.7 are not run.** No `Skill(merge-pr)` call, no comment and no close for #602. I post no other `@dependabot` command unless the user asks for one, and each would get its own ask.

### Outcome and report

- **#602: skipped.** `Hygiene (PR contract)` is failing on a `github_actions` PR, so the diff is not a verified pin-only bump. `Publish Codex policy result` is failing as a consequence. No Codex bypass exists for this ecosystem.
- I include the failing checks' `link` values from `pr-checks`. I cannot read the job log myself (I hold no grant for it), so I suggest the user read the diff and the Hygiene log for the non-pin change, including any permission edits.
- If the user still wants #602 merged, that is manual handling outside this skill.
- The one `@dependabot rebase` comment I posted on #602 stays on the PR, public and permanent.

---

## PR #601: actions/labeler 6.0.1 to 7.0.0 (`.github/workflows/pr-auto-label.yml`)

### What I expect from the required checks before acting

The diff replaces exactly one `uses: actions/labeler@<sha> # ratchet:actions/labeler@v6.0.1` line with the same line shape for the v7.0.0 SHA. The base already has the exemption. After the rebase, I expect `Hygiene (PR contract)` to pass, provided that the `git/ref/tags/v7.0.0` lookup in `actions/labeler` returns that new SHA. `Publish Codex policy result` should then pass without review, so no bypass is needed. Every required check should pass, and the PR goes to `merge-pr` like any green PR (scenario 8). `Codex delta review` does not run for Dependabot (no secrets), but it is not required, so I ignore it. The diff changes no permissions or other lines, which matters for the "read the change for permission edits" note. Hygiene still needs the rebase first, because the PR is `BEHIND` and `merge-pr` refuses a behind PR.

### Step 6 loop

1. **6.1 Re-read live state.**
   - Command: `dependabot_pr_read.py pr-view 601 --fields state,mergeStateStatus,headRefOid,baseRefName,files,commits`.
   - Result: `OPEN`, `BEHIND`.
   - Validate `baseRefName` and `headRefOid` (pattern and 40 lowercase hex) and re-run the suspicious check: the only file is `.github/workflows/pr-auto-label.yml`, commits are by `dependabot[bot]`, and nothing is truncated.
2. **6.2** The recommendation is merge, so nothing happens here.
3. **6.3 Branch freshness.** `BEHIND` means it needs a rebase.
   - Run the dry run: `dependabot_pr_action.py --dry-run rebase 601 --head-sha <headRefOid>`.
   - Ask via `AskUserQuestion` with the exact dry-run body (`@dependabot rebase`), PR #601, and a note that the comment is public and permanent. Options: post / skip / stop.
   - On approval, run it again without `--dry-run`, with the same SHA. Claude Code shows its own permission prompt.
   - Then ask: re-check now / skip for now / stop.
   - On re-check, return to 6.1 and re-read. If the SHA is unchanged, offer wait / skip / stop with no repost. If the SHA changed, re-validate the new `headRefOid` and `baseRefName` and re-run the suspicious check. If `mergeStateStatus` is `UNKNOWN`, re-read once, then ask wait / skip.
   - At most two posted rebase comments for this PR.
4. **6.4 Required CI.** Run `dependabot_pr_read.py pr-checks 601`.
   - Expected: every required row is `pass` (or `skipping`), including `Hygiene (PR contract)` and `Publish Codex policy result`.
   - If any are `pending`, ask wait / skip.
   - If `Hygiene` failed here (a failed tag lookup, for example), it would be the same blocker as #602: report and skip, no bypass.
5. **6.5** Skipped: no Codex policy failure, so no bypass decision. I add neither `--bypass-codex-review` nor `--expected-head-sha`.
6. **6.6 Merge.** Invoke `Skill(merge-pr)` with `601` only, without `--stop-on-review-findings`, because the request did not name reviewer findings.
   - `merge-pr` runs its own readiness check, merge-rights check and merge confirmation. I add no merge question of my own.
   - Nested prompts (announced at step 5):
     - its `finishing-work` offer: answer "No — skip" until wrap-up;
     - its open-issues checkout advice: ignore it, and never check out the dependabot branch;
     - any CODEOWNERS, merge-method or branch-delete questions: answered by the user.
7. **6.7 Confirm.** Run `dependabot_pr_read.py pr-view 601 --fields state`, which must say `MERGED`.
   - If `merge-pr` stopped as behind or conflicted, I ignore its `git-sync-branch` advice and return to 6.3.
   - If it was declined or blocked, I record #601 as skipped with `merge-pr`'s stated reason.

### Outcome and report

- **#601: merged** through `merge-pr` after one `@dependabot rebase`. This assumes the post-rebase checks were green as expected and the user confirmed `merge-pr`'s merge prompt.
- No bypass was needed: the pin-only diff passed `Hygiene` on the actions pin exemption, and `Publish Codex policy result` passed via `skip_codex_review`.
- The rebase comment stays on the PR.

---

## Step 7: wrap-up report

| PR | Bump | Result | Reason |
|---|---|---|---|
| #601 | actions/labeler 6.0.1 to 7.0.0 (major, breaking changes confirmed) | Merged | Rebased with `@dependabot rebase`; every required check passed on the actions pin exemption, with no Codex bypass; merged by `merge-pr` |
| #602 | actions/setup-node 7.0.0 to 7.1.0 | Skipped | Required `Hygiene (PR contract)` failing: not a verified pin-only bump. `Publish Codex policy result` fails with it. No bypass exists for `github_actions`, so this needs manual handling outside the skill if wanted |

Nothing is still pending. Because one PR merged, I offer `Skill(finishing-work)` once via `AskUserQuestion`, passing PR number 601, the last merged PR.
