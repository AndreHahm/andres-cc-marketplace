# development-to-pr — simulated run

**Task:** Push new local commits onto already-open PR #412 (Linear issue linked to this branch, same repo/branch as this checkout).

Following `plugins/workmanagement-kit/skills/development-to-pr/SKILL.md` in order.

---

## Step 1 — Resolve context

- `Skill(linear-work-management)` → read the active Linear Issue's outcome/title (needed later for step 8's PR summary, though step 8 is skipped on this path — read anyway per step 1's instruction, kept for the evidence trail).
- `Skill(linear-github-linking)` → read the Issue's existing `git-github-evidence` entries.
- `Skill(repository-gates)` → read this repository's policy profile (branch protection / required checks configuration).

Result: Issue found, no blocking data quality issues. Repository profile loaded.

## Step 2 — Search for an existing PR, before committing

`Skill(linear-github-linking)` searches for an existing PR by **repository, branch, head SHA, and Linear ID**.

Result: **PR #412** found, classified **`Exact`** (per the task's stated assumption).

Per the skill's own table: `Exact` is already unambiguous — no `AskUserQuestion` confirmation step needed beyond this read. PR #412 is treated as "the existing PR" for everything downstream. This also means the branch this session is about to commit and push has to route through the **existing-PR path**, not `git-kit:create-pr`.

## Step 2.5 — Existing-PR path only: verify checkout, then the cross-model-review gate

Two ordered sub-checks, cheap-then-expensive, **both before `git-kit:commit` is invoked at all**.

### (a) First — verify the checkout is actually PR #412's own repository and branch

This runs *before* anything else in step 2.5, and before any diff is handed to a review gate.

- `Bash(git remote get-url origin)` → returns the checkout's actual push target (not `gh`'s resolved context — `gh repo view` is explicitly not used here, since `gh` can be redirected by `GH_REPO`/`GH_HOST` env overrides and would silently agree with step 2's read even if `origin` itself pointed elsewhere; `git-kit:commit`'s own push step pushes to `origin`, so `origin` is the only check that actually binds to the real push target).
- Compare that URL against the repository step 2 read back from `linear-github-linking` for PR #412.
- `Bash(git branch --show-current)` → returns the checkout's current branch.
- Compare that against PR #412's own head branch (as read by `linear-github-linking` in step 2).

**Result (per the task's stated assumption): both match.** Repository matches PR #412's repository; branch matches PR #412's head branch. No mismatch, so this is not a structured-handoff case — proceed to (b).

(If either check had failed — wrong `origin`, wrong branch, or the session's cwd landed on an unrelated checkout — this would stop here with a structured handoff naming the mismatch. `git-kit:commit` would never be invoked, and sub-check (b) would never run against an unconfirmed diff. That branch does not apply in this run.)

### (b) Only now — run the cross-model-review gate

Since (a) passed, invoke `Skill(git-kit:cross-model-review)` against the current diff:
- `BASE=main`
- no `SCOPE` (full diff)

This reviews the working tree exactly as it stands right now — `cross-model-review`'s own diff mechanic already folds in uncommitted working-tree changes on top of the merge-base, so this is reviewing precisely what step 3's commit is about to capture and push, before anything is committed.

Mirroring `create-pr`'s own step-4 behavior:
- Claude runs its own native review pass over the diff.
- The nested Codex dispatch (via `codex-kit`) triggers its **mandatory First-Send Confirmation** — this is not skipped or assumed; an `AskUserQuestion` fires here asking to confirm sending the diff to the external Codex review bridge before it goes out. Confirmed by the user.
- Both reviewers run independently (Phase 1, fresh-eyes) and then cross-examine each other's findings (Phase 2, challenger persona: confirms/refutes/adds novel findings).
- `cross-model-review` reports a ranked, confidence-scored findings table and stops — report-only, it never edits code itself.

Findings surfaced this run (illustrative):

| # | Finding | Confidence | Source |
|---|---|---|---|
| 1 | A newly-added helper function has no guard for an empty input list, which would raise on the caller's next line | High | Both (confirmed cross-model) |
| 2 | A renamed local variable is now shadowing an outer-scope name of the same name a few lines down | Low | Codex only, Claude did not confirm |

`cross-model-review` asks which findings, if any, to fix. Decision: fix #1 (real bug, cheap, high-confidence), decline #2 (low-confidence, cosmetic, not worth the churn right now).

Fixing #1 produces an edit to the working tree. Per the skill's own re-review discipline: since this edit is now part of the uncommitted diff and nothing has been committed yet on this path, **re-invoke `Skill(git-kit:cross-model-review)` again** against the new current diff (still `BASE=main`, no `SCOPE`) before proceeding.

Second pass: clean read — no new findings requiring action. Gate clears. Proceed to step 3.

*(Both sub-checks of step 2.5 are now satisfied, in order: (a) repo/branch match confirmed first, (b) cross-model-review gate cleared second — and only now does the procedure move to invoking `git-kit:commit`.)*

## Step 3 — Commit

Invoke `Skill(git-kit:commit)`. This skill never stages or commits directly itself.

Explicit instruction given to `commit` for this invocation (existing-PR path): **skip only its own step 17 (Auto-PR)** — a PR already exists (#412), so none should be created. Its own **step 16 (push) is left to run normally** — it asks its own push confirmation (or follows `commit_auto_push` if configured), exactly as it would standalone.

`commit`'s own procedure runs:
- Staging review (`git status`) — shows the fix from step 2.5(b) plus the originally-intended changes.
- Sensitive-file scan — clean, nothing flagged.
- Commit message drafted and confirmed via `commit`'s own `AskUserQuestion` step.
- `git commit` executes.
- Step 16 push confirmation: confirmed → `git push` to `origin` on the current branch succeeds. (Since this is a plain push of new commits to the branch PR #412 already tracks, this is exactly what updates PR #412 on GitHub — no separate PR-mutation action exists or is needed.)
- Step 17 (Auto-PR) is skipped per this invocation's explicit instruction — and would have independently no-op'd anyway on seeing a PR already open, so this is doubly safe against a duplicate.

## Step 4 — Read back the commit

From `git-kit:commit`'s own output: new commit SHA `<sha>` on branch `<branch>` (matching PR #412's head branch), and confirmation that step 3's push actually happened (not declined).

## Step 5 — Record `commit-linked`

`Skill(linear-github-linking)` appends a `git-github-evidence` entry: `stage: "commit-linked"`, `commits: [{sha: "<sha>", recorded_at: "<now>"}]`, per `FOUNDATION_CONTRACTS.md`'s Git/GitHub Evidence Record.

## Step 6 — Discover pre-push gate configuration

`Skill(repository-gates)` — discovery only, no execution. Confirms this repository enforces a required-status-check-style gate (e.g. a required CI workflow check) against PRs targeting `main`. Gate identity carried forward to step 12.

## Step 7 / 8 / 9 — New-PR path only

Skipped entirely — this is the existing-PR path. There is no new PR description to draft (step 7), no separate publication confirmation needed since step 3's own commit-time push confirmation already covered it (step 8), and nothing to delegate to `git-kit:create-pr` since step 3's push already updated PR #412 (step 9).

## Step 10 — Read back

Existing-PR path: read directly via
`Bash(gh pr view 412 --json headRefName,headRefOid,number,url,baseRefName,isDraft)`.

Result: `headRefName` matches the pushed branch, `headRefOid` matches step 4's new commit SHA (confirming the push landed on PR #412's actual head), `number: 412`, `url` present, `baseRefName: main`, `isDraft` reflects PR #412's current draft state. This is a read-only confirmation of what step 3 already did.

## Step 11 — Verify no native status change

Check the Linear Issue's workflow status before vs. after this push. GitHub's native Linear integration (if configured on this repo) attaches informational evidence (a link/reference to the new commit) without changing the Issue's workflow status. Confirmed: status unchanged. (Had it changed, this would be reported as drift, not treated as expected.)

## Step 12 — Confirm the pre-push gate's outcome

Only now, after the actual push, invoke `Skill(repository-gates)` again to read back the real gate result — using the gate identity discovered in step 6, bound to the exact head SHA confirmed in step 10 (`headRefOid`).

Result (illustrative): required check `pass`. (Not assumed — this is the actual read-back.)

## Step 13 — Record `pr-published`

`Skill(linear-github-linking)` appends a `git-github-evidence` entry: `stage: "pr-published"`, using the PR identity read back in step 10 (`number: 412`, `headRefOid`, `url`, `baseRefName`), with step 12's gate result carried into this same entry's `gates[]` array as `pass`. No separate `stage: "ci-gates-passed"` entry is minted — that stage is reserved for a later, dedicated confirmation if a gate had instead resolved from `pending`/`fail` to `pass` after this point, which didn't happen here since it read `pass` on the first read-back.

---

## Outcome summary

- Existing PR #412 confirmed `Exact` — no adoption confirmation needed.
- Step 2.5(a) (repo/branch verification) ran and passed **before** step 2.5(b) (cross-model-review gate), and both ran **before** `git-kit:commit` was invoked — per the skill's mandatory ordering.
- Cross-model-review gate ran against the pre-commit working-tree diff (`BASE=main`, no `SCOPE`), including its mandatory First-Send Confirmation for the nested Codex dispatch; one accepted finding was fixed and the gate was re-run clean before committing.
- `git-kit:commit` was instructed to skip only its own step 17 (Auto-PR); its own step 16 push ran normally and updated PR #412 directly — no `git-kit:create-pr` or `git-kit:collaborating-on-a-pr` call was made or needed.
- Evidence recorded on both `commit-linked` (step 5) and `pr-published` (step 13), the latter carrying the real gate outcome (`pass`) in its `gates[]` array.
- No native Linear workflow-status drift observed.
