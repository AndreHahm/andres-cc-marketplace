# Step 6.4 (Required CI) for PR #606 and PR #631

This is a simulation. I ran no command, script or skill and posted nothing. Every read below is what I would run through `dependabot_pr_read.py` (`python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/dependabot_pr_read.py" <subcommand>`). I would never fall back to a raw `gh` command. Step 6 handles one PR at a time, so PR #606 goes through 6.4 completely before PR #631 starts at 6.1.

## PR #606

**Reads, in order:**
1. `head-runs 606` comes first, before `pr-checks`. Step 6.4 says: "First run `head-runs <n>`".
   - `head_sha` is `aaaa…a`. That matches the `headRefOid` that 6.1 read, so the head did not move and there is no return to 6.1.
   - `head_incomplete` is not empty. It holds `Validate Plugins` (id 43615085687), with status `queued`.
   - `other_head_incomplete` is empty.
   - `truncated` is false, so there is nothing to say about the 100-run limit.
2. I do **not** read `pr-checks 606` at this point. The skill reads `pr-checks` "only when `head_incomplete` is empty (or the user chose to go on)". The scenario shows four `pass` rows for `Validate Plugins`, but those rows do not count here.

**CI conclusion:** CI on this head is not finished, whatever `pr-checks` says. This is the queued-rerun case. A second run of `Validate Plugins` is queued on the current head. The `pass` rows come from an earlier run of the same workflow, and they hide the queued rerun. Test scenario 69 describes this case.

**What I tell the user:** CI on head `aaaa…a` is not finished. I name the incomplete run:
- name: `Validate Plugins`
- status: `queued`
- link: the `url` field from `head-runs` (the scenario does not give the URL value)

I also explain that the four green `Validate Plugins` checks belong to an earlier run, and a rerun of that workflow is still queued.

**What I ask:** one `AskUserQuestion` with three options:
- **Wait:** I re-run `head-runs 606` afterwards. If `head_sha` has changed by then, I return to 6.1.
- **Skip this PR for now:** I record #606 as skipped, with the reason that CI is not finished, and move to the next PR.
- **Go on anyway:** `merge-pr`'s branch-protection check stays authoritative. This option is only for a run the user knows is not required.

**Whether I go on to `merge-pr`:** not on the current state.
- **Wait or skip:** no `merge-pr`.
- **Go on anyway:** I then read `pr-checks 606`. Every required check reports `pass` and none fails, so step 6.5 (the Codex policy check) has nothing to act on. Step 6.6 then invokes `Skill(merge-pr)` with 606. `merge-pr` runs its own readiness check, merge-rights check and merge confirmation, and I add no merge question of my own. I do not pass `--bypass-codex-review` or `--expected-head-sha`, because `codex-bypass.md` does not apply here.

## PR #631

This PR starts with 6.1 to 6.3 on its own. Step 6.4 then runs as follows.

**Reads, in order:**
1. `head-runs 631` comes first.
   - `head_sha` is `bbbb…b`. That matches 6.1's `headRefOid`, so there is no return to 6.1.
   - `head_incomplete` holds `Validate Plugins` (id 43616403132), with status `pending`.
   - `other_head_incomplete` holds `Validate Plugins` (id 43616392864), with status `in_progress`, on head `cccc…c`.
   - `truncated` is false.
2. I do **not** read `pr-checks 631` yet, for the same reason as #606: `head_incomplete` is not empty.

**CI conclusion:** CI on this head is not finished. This is the pending-run-behind-a-hung-old-head-run case (test scenario 70).
- A `pending` run has no check rows at all. That is why `pr-checks` would list only green checks, with all four `Validate Plugins` checks missing, while the PR can be `BLOCKED`.
- The `in_progress` run on the older head `cccc…c` is the likely blocker. It can hold the workflow's concurrency group, so the new head's run waits behind it.

**What I tell the user:**
- CI on head `bbbb…b` is not finished. I name the head run: `Validate Plugins`, status `pending`, with its `url` from `head-runs`.
- The old-head run is the likely blocker. I name it: `Validate Plugins`, status `in_progress`, id 43616392864, head `cccc…c`, with its `url`. I explain the concurrency-group reason.
- This skill cannot cancel a run. The user can cancel it themselves, with the Cancel workflow button on the run page or with gh run cancel and the run's id (43616392864) in their own shell. After cancelling, they choose wait.
- I cancel nothing myself.

**What I ask:** the same `AskUserQuestion` as for #606: wait (then re-run `head-runs 631`), skip this PR for now, or go on anyway (`merge-pr`'s branch-protection check stays authoritative, and this option is only for a run the user knows is not required).

**Whether I go on to `merge-pr`:** not on the current state.
- **Wait:** I loop back to `head-runs 631`.
- **Skip:** I record #631 as skipped because CI is not finished.
- **Go on anyway:** I read `pr-checks 631`. Its rows all pass, so nothing in 6.4 blocks the PR, and 6.5 has nothing to act on. I then invoke `Skill(merge-pr)` with 631 at 6.6. The skill notes that a required check that has not reported may be missing from `pr-checks`, and that `merge-pr` re-checks against branch protection and is authoritative. Here the four `Validate Plugins` checks are missing because their run is still pending. `merge-pr` would therefore probably stop on missing required checks. If it does, 6.7 records #631 as skipped with the reason `merge-pr` gave.

## Gaps in the skill text

- The skill does not say whether to ask about #606 and #631 together. Step 6's one-PR-at-a-time loop implies a separate question for each PR, asked when that PR reaches 6.4.
- The skill does not say how long to wait or how many times to re-poll on "wait". It only says to re-run `head-runs` afterwards.
- The scenario does not give the runs' URLs. I would show the `url` field that `head-runs` returns.
