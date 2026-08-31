# Test Scenarios

Detailed verification scenarios for `merge-pr`'s Testing & Validation section (R30 extraction —
R29's own three required inline subsections, the trigger-phrase lists and `Quality gates:`, stay in
`SKILL.md` itself; the scenario walkthroughs below live here).

1. **Post-merge sync accepted** — after a successful merge, confirm step 8's `AskUserQuestion` fires and, on "Yes", `Skill(git-kit:finishing-work)` is invoked with the just-merged PR's number/URL, not a re-resolved current-branch PR
2. **Post-merge sync declined** — confirm the skill still reports the merge result cleanly on "No — skip", without invoking `finishing-work`
3. **Merge fails or is never reached** (readiness/rights check fails, user declines the step-5 confirmation) — confirm step 8 never fires; it's conditioned on a successful merge, not on the skill having run at all

**Verify step 7's remote-branch-deletion fallback (`merge_auto_delete_branch: true`) -- `git ls-remote` always runs on a `MERGED` state, regardless of the merge command's own exit code:**
- `gh pr merge --delete-branch` exits 0 → `git ls-remote --heads origin <headRefName>` returns empty; step 7 proceeds straight to reporting, no `gh api -X DELETE` call
- `gh pr merge --delete-branch` exits 0, but `git ls-remote --heads origin <headRefName>` returns non-empty (a silent server-side deletion failure with no local error to signal it) → step 7 still catches this, since the check runs regardless of exit code, and completes the deletion via `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>`
- `gh pr merge --delete-branch` exits non-zero, `state` is `MERGED`, `git ls-remote --heads origin <headRefName>` returns non-empty (the worktree-checkout-conflict case) → step 7 completes the deletion via `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>` (`headRefName` already validated at step 1, before this or any other use), and reports that the fallback ran
- Same non-zero-exit/`MERGED` case, but `git ls-remote --heads origin <headRefName>` returns empty (the local error was cosmetic; deletion actually completed) → step 7 does not attempt a redundant `gh api -X DELETE` call
- `gh pr merge --delete-branch` exits non-zero, `state` is still `OPEN` → reported as an actual merge failure; the `git ls-remote` fallback never runs
- `gh pr merge --delete-branch` exits non-zero, `state` is `MERGED`, `isCrossRepository` is `true` (a fork PR) → the `git ls-remote`/`gh api -X DELETE` fallback never runs regardless of local error; reports that the branch lives in the contributor's fork and isn't this skill's to delete
- `merge_auto_delete_branch: false`, `isCrossRepository` is `true` → the manual-delete `AskUserQuestion` is never asked; skips straight to reporting

**Verify step 5's worktree branch-delete note:** the note about a possible `fatal: '<default>' is already used by worktree ...` error is present in step 5's confirmation prompt unconditionally — never gated on `merge_auto_delete_branch`, since that setting isn't read until step 6

**Verify `--bypass-codex-review` behavior:**
- `Publish Codex policy result` is the *sole* failing required check, flag given with a non-empty reason, actor has merge rights → step 4 attests, waits for the re-triggered check, reruns step 2, and (if now fully green) proceeds to step 5's normal confirmation
- Flag given, but another required check (e.g. `Python quality`) is *also* failing → the step-2 exception does not apply; normal "not ready" reporting and stop, same as no flag were given
- Flag given, but `Publish Codex policy result` is already passing → nothing to bypass; normal flow, no attestation step runs
- Flag given with an empty or missing reason → treated as if the flag were absent entirely
- Step 3 (merge-rights) fails even though step 2's bypass exception applied → stop at step 3, exactly like the non-bypass path; a bypass never grants merge rights
- Step 4's re-triggered check comes back failing (bad attestation, actor/SHA mismatch server-side) → step 4(e)'s rerun of step 2 reports not-ready and stops; never proceeds to step 5 on an assumption that the bypass "should" have worked
- `codex-review-bypassed` label missing from the repo → step 4(c) stops and reports failure; the skill never creates the label itself

**Verify step 2's four-state CI classification never collapses a state into another:**
- A required context has no entry anywhere in `statusCheckRollup` (never ran for the current head SHA) → classified **missing**, reported distinctly from "pending" (e.g. "1 required context missing: Fork PR (unsupported) — never ran for the current head commit"), never silently folded into a "still running" message
- A required `StatusContext` entry has `state: EXPECTED` → classified **missing**, same as an absent entry
- A required `CheckRun` entry has `status: COMPLETED`, `conclusion: SKIPPED` → classified **passing**, not failing (a required check can legitimately resolve to an intentional no-op, e.g. this repo's own "Fork PR (unsupported)" context on a non-fork PR)
- A required `CheckRun` entry has `status: IN_PROGRESS` → classified **pending**, never reported as failing or missing
- The branch-protection required-check list and `statusCheckRollup` disagree in count (a context required by branch protection has zero matching rollup entries) → the context is still individually classified **missing**, not silently dropped from the readiness report
- The branch-protection REST call itself fails (no protection configured, insufficient permission, transient API error) → stop and report that the required-check list could not be resolved; never fall back to `gh pr checks`'s bare output to satisfy the gate

**Verify step 2's no-merge-conflicts and not-behind-base checks are required, blocking gates:**
- `mergeable` resolves to `MERGEABLE` → the check passes silently, no interruption
- `mergeable` resolves to `CONFLICTING` → step 2 stops, reports the PR has merge conflicts with
  `<baseRefName>`, and points at `resolving-merge-conflicts` — never proceeds to the rights check
- `mergeable` resolves to `UNKNOWN` → step 2 polls `gh pr view $ARGUMENTS --json mergeable` until it
  reaches a terminal value; if it's still `UNKNOWN` after polling, step 2 stops and reports mergeability
  could not be determined — never silently treated as `MERGEABLE`
- A re-run (step 4(e) or step 7(d)) re-fetches `mergeable` fresh rather than reusing step 1's original
  fetch — a conflict that appeared after step 1 (e.g. a new commit landed on the base branch) is caught
  before merging
- Branch is 0 commits behind base, `isCrossRepository` is `false` → `behind_by` resolves to `0`; the
  check passes silently, no interruption
- Branch is N commits behind base (N > 0), `isCrossRepository` is `false` → step 2 computes the real
  count via the compare endpoint, stops, reports the exact count, and points at `/sync-branch` — never
  proceeds to the rights check on a stale branch
- `isCrossRepository` is `true` → the compare-endpoint call never runs at all; the check is treated as
  passing and step 5 states explicitly that it was skipped for that reason, not silently omitted
- The compare-endpoint call fails for any reason → step 2 stops and reports the in-sync state could not
  be confirmed — never treated as passing

**Verify step 2's two advisory disclosures never block readiness and are always surfaced at step 5:**
- `mergeStateStatus` resolves to `CLEAN` → step 5 still states the raw value explicitly, never omitted
  just because it's clean
- `mergeStateStatus` resolves to `BLOCKED`, `DIRTY`, `BEHIND`, `UNSTABLE`, or `HAS_HOOKS` while this
  skill's own required checks above all pass → the disclosure surfaces the disagreement; readiness is
  unaffected (no stop, no bypass needed) — this value is informational only, never a gate on its own
- PR has zero review threads, or every thread is resolved → the `reviewThreads` count resolves to `0`;
  step 5 still states "0 unresolved review threads" explicitly
- PR has N unresolved review threads across more than one GraphQL page (> 100 total threads) → the loop
  continues while `pageInfo.hasNextPage` is `true`, summing `isResolved: false` nodes across every page,
  not just the first
- Either disclosure is non-zero/non-clean → readiness still reaches step 5's confirmation normally;
  neither disclosure ever causes step 2 to stop the way a failing required check does
- The `reviewThreads` query's own marker write (`gh-pr-review`) is immediately followed by the `gh api
  graphql` call on every page, including the second and later pages of a paginated result — never reused
  from an earlier page's marker
- The `reviewThreads` query fails on any page → step 5 states the disclosure as "could not be
  determined," never silently as `0`

**Verify step 7's rebase-compatibility pre-check, squash-tradeoff disclosure, and rejection fallback:**
- `pr_merge_type` is `REBASE`, the PR's commit history contains zero merge commits → step 7(a)'s pre-check finds a zero count and proceeds straight to `gh pr merge --rebase` with no `AskUserQuestion` interruption
- `pr_merge_type` is `REBASE`, the PR's commit history contains one or more merge commits → step 7(a) reports the count, asks via `AskUserQuestion` for an alternate strategy, and never attempts `gh pr merge --rebase` at all
- Squash chosen at step 7(a) → step 7(c)'s tradeoff disclosure (commit count that will collapse, granularity lost) always fires before the `--squash` merge command runs
- `pr_merge_type` is already `SQUASH` (no rebase pre-check involved) → step 7(c)'s disclosure still fires; it is never conditioned on having reached squash via (a) or (d)
- `pr_merge_type` is `REBASE`, step 7(a)'s pre-check finds zero merge commits, but `gh pr merge --rebase` fails live anyway (history changed after the pre-check) → step 7(d) asks for an alternate strategy, never silently retries with a different flag
- Step 7(d)'s fallback fires → the *full* step-2 readiness check re-runs before retrying, not just a bare re-attempt of the merge command; if the re-check now fails (e.g. a required check regressed while the user was being asked), report why and stop rather than retrying
