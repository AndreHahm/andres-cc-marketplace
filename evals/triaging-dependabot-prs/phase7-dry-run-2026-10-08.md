# triaging-dependabot-prs — Phase 7 test record, 2026-10-08

Run during `plugin-lifecycle-upstream` Phase 7 (Test) for the new skill
`plugins/git-kit/skills/triaging-dependabot-prs/`. Everything below was read-only against GitHub: no
comment, label, rebase, close or merge was posted, and the bypass flow was never run end to end.

## 1. Read-only dry run of steps 1-5 and the bypass conditions (live repository)

The exact documented commands (`gh pr list`, `gh pr view`, `gh pr checks --required`, the pulls files and
commits APIs, the `contents/uv.lock` fetch, `check_uv_lock_bump.py`) were run against the 11 open dependabot
PRs, using a throwaway harness outside the repository.

| PR | Ecosystem | `mergeStateStatus` | Required checks failing | Bypass |
|---|---|---|---|---|
| 489 | uv | BLOCKED | Publish Codex policy result | offered (all conditions met) |
| 488 | uv | BLOCKED | Publish Codex policy result | offered |
| 487 | uv | BLOCKED | Publish Codex policy result | no: classifier, `entry key 'dependencies' changed` (new dependency `packaging`) |
| 486 | npm_and_yarn | BEHIND | Hygiene (PR contract), Publish Codex policy result | n/a (rebase first) |
| 485 | github_actions | BEHIND | Hygiene (PR contract), Publish Codex policy result | n/a (rebase first; no bypass for this ecosystem) |
| 484 | uv | BLOCKED | Publish Codex policy result | offered |
| 483 | npm_and_yarn | BEHIND | Hygiene (PR contract), Publish Codex policy result | n/a (rebase first) |
| 482 | github_actions | BEHIND | Hygiene (PR contract), Publish Codex policy result | n/a (rebase first; no bypass for this ecosystem) |
| 473 | uv | BEHIND | Hygiene (PR contract), Publish Codex policy result | n/a (rebase first) |
| 472 | uv | BEHIND | Hygiene (PR contract), Publish Codex policy result | n/a (rebase first) |
| 470 | uv | BEHIND | Hygiene (PR contract), Publish Codex policy result | n/a (rebase first) |

Confirmed on real data: collection and the owner/repo, branch-name and file-list checks all work; commit
authors come back as `dependabot[bot]`; `gh pr checks --required` works on `gh` 2.45.0 and prints
tab-separated name, bucket, elapsed and link; `gh pr checks --json` is rejected by that `gh` (`unknown flag`);
the commits API reports `verified: true` with committer `web-flow`.

Observation, not proven: the seven BEHIND PRs also fail `Hygiene (PR contract)`. That is probably stale CI
from before the dependabot CI fixes already on `main`, in which case a rebase clears it; the two
`github_actions` PRs may still fail it afterwards, as `docs/ci.md` predicts. Only a posted rebase would show
which, and none was posted.

## 2. Lockfile classifier (`scripts/check_uv_lock_bump.py`)

- Live: merge-base vs head of the seven open uv PRs. Accepted 489, 488, 484, 472, 470. Rejected 487
  (`entry key 'dependencies' changed`) and 473 (`expected exactly one package entry replaced, found 2 removed
  and 2 added`).
  The skill itself compares the base branch's tip with the head, which is the same thing once a branch is
  current. For the BEHIND PRs (473, 472, 470) that comparison would first report an `expected exactly one
  package entry replaced` or `top-level key ... changed` mismatch and send the PR down the rebase route
  before any bypass is offered; the merge-base comparison above shows what each PR's own change is.
- `scripts/test_check_uv_lock_bump.py`: 50 fixture tests, all pass (49 at the time of the live check; one
  case added after the final review).
- Mutation check (scratchpad, not committed): 23 deliberate weakenings of the script, 23 caught by the tests.

## 3. Structural checks

- `scripts/smoke_test.py`: 11 checks pass on the real files. A negative harness (scratchpad) applied 21
  deliberate breakages to copies; every one failed the expected checks.
- Smoke tests of the changed skills `merge-pr` (35 checks), `create-pr` (5) and `commit` (4) pass.
- `plugin-development`'s `validate_plugin.py` on `git-kit`: passed, 0 errors, 0 warnings.

## 4. `skill-tester` Quick Workflow (with_skill only, no baseline)

Seven simulated-exercise evals (`evals.json`), 37 pre-written assertions, graded per `grading.json`.
Subject agents were told to run no command, post nothing and invoke no other skill; none did.

| Iteration | Condition | Result |
|---|---|---|
| 1 | Agents could read `references/test-scenarios.md`, which documents the expected behavior; evals 4, 5, 6 cite its scenario numbers. Eval 4's agent also ran one read-only `ls` against the Read/Write-only rule (disclosed in its answer). | 37/37 |
| 2 | Blind: agents read only `SKILL.md`, `ordering-and-checks.md`, `codex-bypass.md` (and optionally `merge-pr/SKILL.md`); forbidden from `test-scenarios.md`, `evals/`, `scripts/` and the Bash tool. | 37/37 |

Coverage of the skill's own scenario list (`references/test-scenarios.md`, 42 entries): 12 exercised by
these evals (`testing_validation_coverage` in `evals.json`). The collection and planning scenarios, CI-state
handling, the close path, wrap-up, and most bypass-denial conditions are not covered by an eval.

Limits of this evidence (superseded in part by section 7, which adds a blind baseline): Quick Workflow has no baseline, so it shows the text can be followed, not that it
beats an agent without it; all 37 passed in both rounds, so it does not discriminate between weaker and
stronger versions of the skill; and the evals read the skill as a procedure, they do not run it.

## 5. `plugin-rulebook` batch check (before finalizing)

Run as an executed `Skill(plugin-rulebook)` call over every changed component, with the mechanical checks run
as scripts or greps. Findings fixed in this session:

- R35 (FAIL): the new `SKILL.md` had no `## Quick Start`; added.
- R9 (FAIL): nine committed eval answer files contained the author's OS username in `/home/...` paths;
  redacted to `<repo-root>`.
- R31 (FAIL): `evals.json` coverage arithmetic did not add up (12 covered + 6 grouped notes != 42); now lists
  the 30 uncovered scenarios individually (12 + 30 = 42). Registry check (every `workspace/iteration-*/eval-N`
  has an `evals.json` entry): clean.
- R6: `check_tool_grants.py` flagged three prose lines in the new skill and one added line in `merge-pr`, all
  prose descriptions rather than commands; reworded. The 26 other `merge-pr` findings exist in the committed
  original and are unchanged (identical flagged-command sets before and after).

Remaining, not fixed here: R13 weak warning on the new skill (118 lines, over 100); `merge-pr` at 429 lines
(soft warning tier), 8 bare URLs and one code block over 10 lines, all pre-existing; R36 advisory, because
`dependency-updater` and `merge-pr` do not name this skill back in their "When NOT to Use" sections.
R19 mirror parity (plugin copies vs `.claude/` copies) identical for every changed file; R20 sweep of the
`gh-pr-review` marker-caller list (guard header and denial text, marker-script header, README, shared
protocol) consistent; R37 passes (the directly-run marker and guard scripts are mode 100755; the Python
scripts are run through `python3`).

## 6. Not run

- The Codex bypass end to end: it posts a real attestation comment and applies a real label.
- Any `@dependabot rebase` / `@dependabot close` comment through the real `gh-pr-review` marker handshake and
  guard, and `merge-pr`'s and `commit`'s/`create-pr`'s attestation comments through the same guard. The
  guard's behavior was established by reading it and by hitting it with an incidental mention of the command,
  not by a posting run.
- Whether Claude Code's permission matching accepts the pre-approved `python3 -I ${CLAUDE_PLUGIN_ROOT}/...`
  and `gh api repos/*/contents/uv.lock` grants as written; at worst the first live run shows a permission
  prompt.
- A `skill-tester` eval of the changes to `merge-pr`, `create-pr` and `commit`; they are covered by their
  smoke tests, updated written scenarios and the shared-protocol check only.

## 7. Later rounds on this branch (downstream QA, same date)

Sections 1-6 above record the build-time test. These later rounds ran after the guard hooks, `merge-pr` and
the CI bypass code changed (`plugin-lifecycle-downstream`, run `qa-20261008-triaging-dependabot-prs`).

- **`skill-tester` Full Pipeline, iteration 3** (`workspace/iteration-3/`): the same 7 evals, one with-skill
  and one blind baseline agent each (the baseline prompt does not name the skill and forbids reading plugin
  files). With skill 37/37; baseline 15/37 (mean per-eval pass rate 100% against 44.8%, +55.2 points). No
  baseline answer quoted the skill. Eval 2's expected output had been rewritten for the `--expected-head-sha`
  contract after iterations 1-2, so iteration 3 is the first round that re-ran it; its assertions 6-7 were
  rewritten for that contract after the run and re-graded from the existing answers (scores unchanged: 8/8
  with skill, 0/8 baseline). The baseline separates from the skill on the marker-then-comment sequence,
  the bypass offer and hand-off, the rebase cap and out-of-bound comment requests; evals 3 and 5 are
  largely passed by general judgment alone. The evals still read the skill as a procedure; they do not run it.
- **Smoke tests** (`smoke-tester`): `triaging-dependabot-prs` 11 checks, `merge-pr` 37 checks, `create-pr`
  and `commit` pass; 4/4 skills, no failures. (`merge-pr` was 35 checks at section 3's time.)
- **Final verification reviewers**: `plugin-validator` Pass; `security-reviewer` Pass (no Critical or Major;
  five minors, three fixed); `plugin-rulebook-checker` one R6 FAIL (an unused `Bash(gh repo view:*)` grant in
  `merge-pr`, present in the baseline commit; removed); Codex-routed `activation-`, `authority-` and
  `consistency-reviewer` Pass. Two Codex findings were verified false and not acted on: five "critical"
  oversized-marker-timestamp claims (all five guards deny a 25-digit timestamp, run live) and a request to
  add `AskUserQuestion` to `allowed-tools` (the rulebook treats it as a no-op).
- **Resolved since section 5**: the R36 advisory is closed (`dependency-updater` and `merge-pr` now name this
  skill back). `merge-pr` is 456 lines (soft warning tier), up from the 429 recorded above.
- **Still not run**: everything in section 6 (bypass flow and posting run live, grant matching), plus a
  `skill-tester` eval of the `merge-pr`/`create-pr`/`commit` changes. `merge-pr`'s evals 10 and 14 still
  owe a re-grade from 2026-08-31 (pre-existing, deferred).
