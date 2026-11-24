# Development History

Extracted from `SKILL.md`'s Testing & Validation section to keep that file under its own R13
line-budget threshold — the "why does the design look like this" story, kept out of the main procedure
a reader follows on every merge-readiness pass. Nothing here is needed to execute a live run; see
`SKILL.md`'s own "Last dated run record:" line for the current state pointer.

**2026-08-31 run record.** Added step 2's no-merge-conflicts and not-behind-base required
checks (the latter promoted from an advisory disclosure) and the mergeStateStatus advisory disclosure.
Both new GraphQL enums were live-verified via `gh api graphql` introspection (`__type(name: "...")`,
`includeDeprecated: true`) against this repository: `MergeableState` is
`MERGEABLE`/`CONFLICTING`/`UNKNOWN`; `MergeStateStatus` has 7 active values
(`CLEAN`/`DIRTY`/`BLOCKED`/`BEHIND`/`UNSTABLE`/`HAS_HOOKS`/`UNKNOWN`) plus a `DRAFT` member GitHub's
schema still carries but marks `isDeprecated: true` (superseded by `isDraft`, which this skill already
checks separately). Two review passes followed, each finding real gaps, all fixed in this same commit
history: a `skill-reviewer` pass (score 84) found `references/merge-rights-check.md` re-deriving
`{owner}/{repo}` via a fresh `gh repo view` instead of reusing step 1's resolved value (the exact bug
issue #216 had fixed only at step 1/2, never in this reference file), and the no-merge-conflicts stop
message pointing bare at `resolving-merge-conflicts` with no local-reproduction guidance. A subsequent
`cross-model-review` pass (Claude + Codex, re-run repeatedly against the growing diff — this skill's
own `create-pr` gate requires a fresh pass after every accepted fix, until one comes back clean) found,
across its rounds: neither new check branched on `isCrossRepository` (a fork PR's `headRefName` isn't
fetchable from `origin` by name; a fork PR was silently exempted from the not-behind-base blocking gate
entirely) — fixed using GitHub's `pull/<number>/head` ref and the already-fetched `mergeStateStatus`
field respectively; an overstated "no `DRAFT` value" claim and a stale pre-fix scenario left in
`references/test-scenarios.md`; both new `UNKNOWN`-polling paths having no bound on how many times to
retry; step 2's rerun re-fetch omitting `headRefName`/`baseRefName`/`isCrossRepository`, so a PR's base
branch being retargeted mid-run would silently validate against a stale base; and — found only after the
fork-PR fix above shipped — the reproduction guidance still fetching from a bare `origin`, which is only
correct when the current local checkout happens to be a clone of the PR's own repository, not when
`$ARGUMENTS` names a PR step 1 explicitly supports checking without one (now fetches from an explicit
`https://github.com/{owner}/{repo}.git` URL instead, for both the same-repository and fork-PR cases).
`scripts/smoke_test.py` has 29 checks, all passing on both the canonical and `.claude/` mirror copies.
Verified with two `skill-tester` Quick Workflow evals — 6 new scenarios (ids 10-15,
`evals/merge-pr/evals.json`, `workspace/iteration-6/` and `iteration-7/`): 23/23 assertions passed, but
evals 10 and 14's own prompt/expected_output text were subsequently updated to match the
explicit-URL fix above *after* that grading ran — their recorded PASS results reflect the pre-fix
wording, not this final version; re-graded 2026-10-08 against the current SKILL.md
(`workspace/iteration-8/`, 5/5 assertions each for evals 10 and 14; see `evals.json`'s own
`testing_validation_coverage` note). No open PR existed in this repository at any point to exercise any
of this end-to-end; see `references/test-scenarios.md` for further walkthroughs and `evals.json`'s own
`testing_validation_coverage` field for what else remains uncovered (mostly the bypass-attestation
flow).

Once PR #269 was open, three automated reviewers (CodeRabbit, Devin, Codex) posted 10 findings across
9 threads; `handling-review-findings` triaged them. Four were real and fixed: `smoke_test.py`'s
code-fence regex missed `sh`/`shell` fences (CodeRabbit); its enum-value assertions were incomplete —
no explicit `MERGEABLE` check, `UNKNOWN` missing from the `MergeStateStatus` loop (CodeRabbit); the
fixed `pr-head`/`pr-base` local branch names in the conflict-reproduction guidance risked colliding
with a branch the user already had checked out, now `<number>`-suffixed (Devin); and step 2's
status-checks/not-behind-base bullets still literally said "from step 1" even on a rerun, contradicting
this step's own intro paragraph — reworded to name both the original and re-fetched cases explicitly
(Codex). One was fixed by explicit user decision despite being pre-existing, out-of-diff-scope
behavior: the normal (non-bypass) merge path never rechecked readiness immediately before the actual
`gh pr merge` call — only step 4(e)'s bypass rerun and step 7(d)'s rejection-fallback retry did — step
7(b) now reruns the full step-2 check unconditionally right before writing the marker (Devin). One was
verified as a false positive: a claimed "branch names can inject Git options" finding, refuted live —
`git branch -- '-weird'` fails with `fatal: '-weird' is not a valid branch name`, so a real PR's
`headRefName` can never start with `-` (Devin). Two were declined as already-disclosed, pre-existing
characteristics not introduced by this PR (`smoke_test.py`'s phrase-matching-not-control-flow
limitation; the eval-10/14 stale-grading-artifact disclosure already in the PR body). One — the
fork-PR `mergeStateStatus` fallback treating any non-`BEHIND`/`UNKNOWN` value as "not stale," which
can't distinguish a genuinely-clean fork from one that's behind *and* separately `BLOCKED`/`UNSTABLE`
— was independently raised by both Devin and Codex; filed as its own tracked issue by explicit user
choice rather than fixed in this already-long review chain. `scripts/smoke_test.py` now has 30 checks.

A second automated-review round followed (Codex only, triggered manually — a separate, still-open issue
tracks the discovery that a shared multi-reviewer trigger comment silently prevented Devin's own trigger
from firing). Codex found one real, security-relevant gap (P1): step 2's bypass exception was keyed only
on whether `--bypass-codex-review` was present in `$ARGUMENTS`, with no tracking of whether a genuine
attested pass had already been achieved — so step 7(b)'s and step 7(d)'s reruns of "the full step-2
readiness check" could silently re-apply the exception to a new, never-attested commit that landed
during step 5's confirmation wait or steps 6-7(a), if that commit's own `Publish Codex policy result`
was the only non-passing context. Fixed by making the exception explicitly single-use per invocation and
having every rerun point state it suppresses the exception. Per
`.claude/rules/require-security-review-before-new-gate.md` (a structural change to an existing security
gate's pass/fail logic), a `security-reviewer` dispatch followed and returned Reject with one further
Critical and two Major findings, all fixed in the same round: (Critical) step 2's own "when this step is
being re-run" enumeration never named step 7(b) — added in this same session as an unconditional
pre-merge recheck — so 7(b)'s recheck would have silently reclassified step 1's stale snapshot instead
of re-fetching, which would have made both Devin's original fix and Codex's bypass-exception fix no-ops
on the normal path; fixed by adding step 7(b) to that enumeration. (Major) step 4(d)'s poll for the
Codex-policy check to reach "terminal state" couldn't distinguish the pre-label run's own already-failing
result — the common case, since the bypass path is only entered when that check is already non-passing —
from the label-triggered re-run; fixed by capturing a `startedAt` baseline immediately before the label
write (step 4(c)) and requiring the poll to observe a strictly-later `startedAt` plus a terminal `bucket`
before accepting the result, bounded to 20 attempts. (Major) `gh pr merge` was never bound to the exact
SHA the immediately-preceding recheck validated, leaving the same TOCTOU gap the recheck exists to close
open at the one irreversible call itself; fixed by adding `headRefOid` to step 2's rerun re-fetch and
passing it to every `gh pr merge` call (step 7(b), step 7(d)) via `--match-head-commit`, live-verified
against `gh pr merge --help` ("Commit SHA that the pull request head must match to allow merge").
`scripts/smoke_test.py` now has 34 checks, all passing on both the canonical and `.claude/` mirror
copies. No fresh `skill-tester` eval re-run for this round — the changes are readiness-gate control-flow
fixes verified directly against the skill's own text and against `gh`'s live `--help` output, not
re-tested end-to-end behaviorally; the bypass-attestation flow remains without eval coverage (see
`evals.json`'s own `testing_validation_coverage` field, unchanged by this round).

**Step 1.5 (session open-issues check) — added 2026-09-08, PR #301.** Built as a `create-pr`/`merge-pr`
pair; see `create-pr`'s own Testing & Validation for the shared narrative of what the feature is.
`merge-pr`'s own step 1.5 went through 3 rounds of real, automated Codex review on the live PR before
merging, each round fixing genuine gaps in the checkout-match guard and the touched/untouched
classification: round 1 found the fix-and-push path had no guard at all for a fork/cross-repo PR, plus
(via Codex's own challenger pass) that a user-explicitly-deferred item would be silently auto-fixed;
round 2 found the round-1 guard's `isCrossRepository`-only check still let a same-repo-shaped-but-
different-repository mismatch through, and separately found `gh pr view --json files` caps at 100
entries with no pagination reachable from this skill, silently misclassifying a touched file past that
boundary as untouched, and that the guard never compared local `HEAD` against `headRefOid` at all
(a checkout could be the right repo and branch while still being ahead of, behind, or diverged from the
actual PR head); round 3 found the round-2-fixed guard still relied on `gh repo view`, whose output can
be overridden by `GH_REPO`/`gh repo set-default` — a real fork-contributor setup — decoupling it from
what `git push origin HEAD` actually targets, fixed by comparing the real `origin` remote URL instead.
No fresh `skill-tester` eval re-run for any of these — each was verified directly (a live reproduction,
or a check against `git`'s/`gh`'s own documented behavior) rather than end-to-end blind comparison.

**Bypass attestation fixes (2026-10-08, found while building `triaging-dependabot-prs`):** two defects
stopped the bypass path from completing. (Critical) step 4(b)'s attestation `gh pr comment` was posted
with no `gh-pr-review` marker written first; `git-guard-raw-pr-review.sh` hard-blocks every raw
`gh pr comment` and has no exemption for the attestation comment (its denial text listed `merge-pr` for
the step-2 thread check only), so the comment was denied after the user had approved the bypass. The
same gap existed in `create-pr` step 5 and `commit` step 16.5, which follow the shared protocol; fixed
once in `../../references/git-bypass-attestation-protocol.md` step 3(c) and here in step 4(b). (Major)
steps 4(c) and 4(d) polled `gh pr checks --json name,startedAt[,bucket]`, which `gh` 2.45.0 rejects
(unknown flag), so the flow would have died after the attestation comment was posted; fixed by reading
the `Publish Codex policy result` `CheckRun` from `statusCheckRollup` (the source step 2 already
classifies from), keeping the `startedAt` baseline and the strictly-later requirement, and waiting for
`status` `COMPLETED`; the now-unused `Bash(gh pr checks:*)` grant was removed. Verified by reading the
guard and the skill text, by running `gh pr checks 489 --json name,bucket` on `gh` 2.45.0 (result:
`unknown flag: --json`; `gh pr checks 489 --required` runs and prints tab-separated name, bucket, elapsed
and link), and by reading live `statusCheckRollup` data (one `CheckRun` entry named
`Publish Codex policy result` with `status`, `conclusion` and `startedAt`); the bypass flow itself was
not run live, because it posts real comments and applies a real label.

**Expected-SHA flag and resolved PR number (2026-10-08, downstream QA of `triaging-dependabot-prs`):**
four independent reviewers noted that `triaging-dependabot-prs` could only keep the SHA it vetted equal to
the SHA `merge-pr` attests by interrupting `merge-pr` between two Bash calls inside step 4(b), a contract
`merge-pr` never stated. Step 4(b) now accepts an optional `--expected-head-sha <40 lowercase hex>`
(validated in step 1) and compares it with the freshly resolved head SHA before the reason file, marker,
comment or label exist; a mismatch attests nothing. Two reviewers also found that step 4(b)-(d) used
`$ARGUMENTS`, which is empty when no PR was named, turning the attestation comment into the argument-less
`gh pr comment` form the shared protocol forbids (the wording dates from commit `90e844cf`, not from this
branch). A first version used a bare step-1 `number`; the security review of that change found it
regressed a PR URL naming another repository (a bare number resolves against the checkout's repository or
`GH_REPO`, so the attestation and label could land on an unrelated same-numbered PR). The shipped form
addresses steps 4(b)-(d) by `<pr-ref>`: the validated PR-reference portion of `$ARGUMENTS` when one was
given (number or URL), otherwise step 1's `number`; step 4(b) also compares its resolved head SHA with
step 2's most recent `headRefOid` whether or not the flag was given. `scripts/smoke_test.py` has 37
checks: two added (`check_step4_addresses_pr_explicitly`,
`check_expected_head_sha_validated_and_compared_before_attesting`) and one updated for the new comment
form. Structural verification only; not run live.

**Earlier run records** (moved from `SKILL.md`, newest first): 2026-11-24 (iteration 17) — issues #608 and #864 and leftovers of PR #868: evals 32 and 38-42 (origin read by hand, commit count, the waiver check's copies and approval), with_skill 12 of 12 against a baseline (the pre-change skill at c7b078e3) of 7 of 12, graded by the author, the with_skill arm's model not recorded; evals 39, 41 and 42 did not separate the arms; evals 39 and 41 re-run after the last edits to steps 1.6 and 7(b); the text on reporting a credential-free origin came after all runs. A first run of evals 32 and 38-40, before the `security-reviewer` fixes, was not graded or kept. `security-reviewer`: two Majors in the first draft, both fixed and re-checked. `scripts/smoke_test.py`: 45 checks pass; ten deliberate weakenings of the new rules were each caught. Previous record: 2026-11-24 (iteration 16) — PR #868 review fixes: evals 36 (4(c)'s wait for unfinished `Marketplace CI` runs) and 37 (step 2's wait for its own runs), Quick Workflow, with_skill only, 6 of 6, graded by the author. Iteration 15 — issues #858 and #861: step 2 takes every required context's state from `git-required-checks.py` (per server-set source, with the named app), and the marker is built by `git-bypass-attestation-marker.py` instead of `jq`. Evals 33-35 in `evals/merge-pr/workspace/iteration-15/`, Quick Workflow, with_skill only, 8 of 8, no baseline arm; unit tests in `tests/marketplace_ci/test_git_required_checks.py` and `test_git_bypass_attestation_marker.py`; the script was run live against the heads of two merged PRs (12 of 12 contexts passing). Several `security-reviewer` passes ran: the first three found six Majors in the first draft and one introduced by its fixes, all fixed or documented as limits before commit; later ones covered the PR #868 review fixes. Previous record: 2026-11-23 (iteration 14) — PR #859 review fixes to steps 1.5 and 1.6 (continue to 1.6 when nothing is open, re-list Open Items and stop after a push that did not land, opt-in before issue drafting, the mirror-path waiver check): evals 29-32 in `evals/merge-pr/workspace/iteration-14/`, Quick Workflow, with_skill only, 10 of 10, no baseline arm. Iteration 13 — review fixes to steps 2, 4(c) and 1.6 (missing policy check not waited for, CheckRun-only pending rule, Open Items kept unless verified, same-call re-read, `scripts/git-pr-body-waiver-check.py` for the waiver sections): evals 24-28 in `evals/merge-pr/workspace/iteration-13/`, with_skill 15 of 15, baseline (this branch's HEAD) 9 of 15; evals 25, 26 and 28 did not discriminate. Previous record: 2026-11-23 — issues #850, #748 and #640: step 1.5 decides every touched item in one batch and pushes once, then continues at step 2 with a bounded wait for its own run; the new step 1.6 brings the PR body up to date in one approved edit; step 2's required-check list adds ruleset contexts, groups same-name entries by source, and gains a sixth required check (review outcomes recorded); step 4(c) waits for in-flight runs. Steps 1.5 and 1.6 moved to `references/session-open-items-and-body-check.md` (R13). The new API shapes were live-verified (ruleset endpoint, `404 Branch not protected`, contents `-X GET -f ref=`, `@base64d` on an outcomes file, `workflowName` in `statusCheckRollup`). A `security-reviewer` pass found eight Major gaps in the first draft (stale-success selection, same-name masking, a broad PATCH pre-approval, write-capable GET grants, waiver restoration, a removed outcomes file passing, the bypass attesting an agent-pushed fix, PR-body text read as deferral), all fixed before commit. Smoke test: 41 checks. Evals 19-23 in `evals/merge-pr/workspace/iteration-12/` were each run once by a simulated subagent (`skill-tester` Full Pipeline, baseline = the pre-change skill on `main`) and graded by the author: with_skill 18 of 18 assertions, baseline 2 of 18 (mean per-eval pass rate 100% vs 10.7%). Previous record: 2026-11-18 — for issue #741, `--expected-head-sha` is no longer bypass-only: step 1 stops when the PR's head differs from it, step 7(b) and a 7(d) retry merge only that SHA, and step 1.5 pushes no fix while it is set, so `triaging-dependabot-prs` can pin the merge to the head its step 6.4 checked. A `security-reviewer` pass found the 7(d) retry unpinned in the first draft (Major), fixed before commit. Eval 18 in `evals/merge-pr/workspace/iteration-11/` was run once by a simulated subagent and graded by the author, with a baseline on the pre-change skill. Previous record: 2026-11-14 — issue #732 added the opt-in `--stop-on-review-findings` flag
(step 2's "Review findings" bullet, applied on every pass including 7(b)'s final recheck). New evals 16
and 17 in `evals/merge-pr/workspace/iteration-9/` were each run once by a simulated subagent and graded by
the author: with the flag, a late finding stops the merge before the marker (with_skill 5 of 5, baseline 1
of 5; eval 16 re-run in `iteration-10/` with a concrete comment author and time: 5 of 5 vs. 1 of 5); without it, behavior is unchanged (4 of 4 in both configurations). The smoke test now has 38 checks.
Previous record: 2026-10-08 — step 4(b) now writes the review marker before the attestation
comment, and steps 4(c)/(d) poll `gh pr view --json statusCheckRollup` instead of `gh pr checks --json`
(narrative above). Verified by structural smoke tests only
(`scripts/smoke_test.py`) and updated scenarios in `references/test-scenarios.md`; the marker
sequence was not run live and has no `skill-tester` eval. The same day, step 4 gained the optional
`--expected-head-sha` flag (compared before anything is attested), now addresses the PR by `<pr-ref>`
instead of a possibly empty `$ARGUMENTS`, and compares its resolved head SHA with step 2's last fetch;
the smoke test is now 37 checks, with two added for this change and six added scenarios, all structural
only. Previous record: 2026-09-08, PR #301 — step 1.5 (session open-issues check) went through 3
rounds of real automated Codex review before merging, each fixing a genuine gap in the checkout-match
guard or the touched/untouched classification (fork/cross-repo push safety, local-HEAD-vs.-`headRefOid`
drift, `gh pr view --json files`'s 100-entry cap, and `gh repo view`'s `GH_REPO`/default-repo
override risk) — documentation-only Testing & Validation coverage, not a fresh `skill-tester` eval run.
