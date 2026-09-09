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
wording, not this final version; a re-grade is still owed (see `evals.json`'s own
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
