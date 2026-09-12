# development-to-pr — existing-PR path (PR #412)

Following `plugins/workmanagement-kit/skills/development-to-pr/SKILL.md`'s Procedure in order. This is
the existing-PR path (an already-open PR for the Linear issue linked to this branch), so the new-PR-only
steps (7-9) are skipped as documented.

## Step 1 — Resolve context

- `Skill(linear-work-management)`: read the active Linear Issue's outcome/title. This supplies the
  concise summary that would back a new PR description (not needed on this path, but the read still
  happens here since step 1 is unconditional) and confirms which issue this branch is linked to.
- `Skill(linear-github-linking)`: read the Issue's existing `git-github-evidence` entries — prior
  `commit-linked`/`pr-published` stages already recorded for this issue, establishing that PR #412 is the
  PR of record.
- `Skill(repository-gates)`: read the repository policy profile (branch protection, required checks,
  merge policy) for this repo. Carried forward for step 6/12's gate discovery/confirmation.

## Step 2 — Search for an existing PR, before committing

Invoke `Skill(linear-github-linking)`'s search: by repository, branch, SHA, and Linear ID.

Given: PR #412 already open, `linear-github-linking` classifies it **`Exact`** for this repo/branch/
Linear-ID combination.

Per the skill's own classification table, `Exact` is already unambiguous — no `AskUserQuestion`
confirmation is needed beyond this read (unlike `Adoptable`, which would require one). PR #412 is treated
as the confirmed existing PR for the rest of this run.

This search runs before any commit, per the skill's own reasoning: `git-kit:commit` must be told which
path it's on (skip only step 17 here, vs. skip 16+17 on a no-existing-PR path) before it's invoked, so
the classification has to be resolved first.

## Step 2.5 — Existing-PR path only: verify checkout, then the cross-model-review gate

Two ordered sub-checks, cheap-then-expensive, both completed before `git-kit:commit` is invoked at all.

### (a) Verify the current checkout matches PR #412's repository and branch

- `Bash(git remote get-url origin)` → returns this checkout's actual `origin` URL.
- Compare against the repository `linear-github-linking` read back for PR #412 in step 2 → **match**.
- `Bash(git branch --show-current)` → returns this checkout's current branch name.
- Compare against PR #412's own `headRefName` (from the step-2 read) → **match**.

Per the prompt's stated assumptions, both match — no mismatch. Note per the skill: this check
deliberately uses `git remote get-url origin`, not `gh repo view` alone, because `gh` can resolve its
repository context from `GH_REPO`/`GH_HOST` environment overrides before falling back to the local git
remote — `gh repo view` could report agreement with PR #412's repo even if this checkout's actual
`origin` pointed elsewhere. `commit`'s own step 16 pushes to `origin`, not to whatever `gh` reports, so
`origin` itself is the only check that actually binds to the real push target. Both checks pass, so we
proceed to (b). (Had either failed, this would stop here with a structured handoff naming the mismatch —
`commit` would never be invoked, and (b) would never run against an unconfirmed checkout.)

### (b) Run the cross-model-review gate — mandatory unless declined

Only now that the checkout is confirmed correct: invoke `Skill(git-kit:cross-model-review)` against the
current diff with **`BASE=HEAD`** — explicitly, not the tool's own default `BASE=main`.

**Why `BASE=HEAD` here, not the default:** on this existing-PR path, HEAD already sits on a commit history
that includes everything already pushed to and reviewed on PR #412. If this gate ran with the tool's
default `BASE=main`, its merge-base would resolve to `merge-base(main, HEAD)` — an ancestor commit far
back on the branch — and its diff mechanic would re-review this branch's *entire* already-committed,
already-reviewed PR diff every single time this skill runs, not just the new uncommitted change about to
be committed. Passing `BASE=HEAD` instead makes `merge-base(HEAD, HEAD)` resolve to `HEAD` itself, so the
gate's diff mechanic — which already layers in uncommitted working-tree changes on top of its resolved
merge-base — reviews exactly and only the pending uncommitted change step 3's commit is about to capture
and push, nothing already committed and reviewed on this branch. This is deliberately different from
`create-pr`'s own Pre-flight step 4, which correctly uses the tool's default `BASE=main` there because a
brand-new PR's entire diff is genuinely new and unreviewed — `BASE=HEAD` is this existing-PR path's own
narrower equivalent for a PR that's already been reviewed once and is only gaining new commits.

Invoking: `Skill(git-kit:cross-model-review)` with `BASE=HEAD`.

- Claude reviews the diff natively.
- Codex reviews independently through `codex-kit` (`codex-review-bridge`, falling back to
  `codex-windows-guardrails` if no sandboxed profile is available). Per the skill's own note, mirroring
  `create-pr`'s step 4 behavior: the **mandatory First-Send Confirmation** for this nested Codex dispatch
  fires normally here too — before the diff/instructions are actually sent to the Codex bridge for the
  first time this session, `cross-model-review` pauses and asks for explicit confirmation to proceed
  with that first send. Confirming here (as the user's task requires) lets the dispatch continue.
- Both personas cross-examine each other's findings (fresh-eyes Phase 1, challenger Phase 2).
- `cross-model-review` is report-only: it surfaces a ranked, confidence-scored findings table and asks
  which findings, if any, to fix — it never edits code itself.

Simulated outcome for this run: the gate returns a clean read (no Critical/Major findings on the pending
diff; a couple of low-confidence style notes are surfaced and declined). Per the skill: **if the gate
produces no edit** (clean read, or the user declines every finding), proceed directly to step 3. (Had an
accepted finding produced an edit, that edit would become part of the uncommitted working tree, and
`Skill(git-kit:cross-model-review)` would be re-invoked again — still with `BASE=HEAD` — against the new
diff, repeating until a pass produces no newly-accepted edit, before proceeding to step 3.)

Gate cleared. Proceeding to step 3.

## Step 3 — Commit

Invoke `Skill(git-kit:commit)`. Never staging or committing directly.

Since this is the existing-PR path (`Exact` match, confirmed at step 2, checkout verified and
cross-model-review gate cleared at step 2.5): instruct `commit`, as part of this invocation, to skip
**only its own step 17 (Auto-PR)** — a PR already exists (#412), so none should be created. Explicitly
*not* skipping step 16 (push): let `commit`'s own step 16 push proceed normally — it will ask its own
push confirmation (or follow `commit_auto_push` if configured), exactly as it would standalone. Pushing
new commits to the same branch is exactly what updates PR #412 on GitHub; no separate PR-mutation skill
exists or is needed for that.

`git-kit:commit` runs its own procedure:
- Reviews staging (`git status`/`git diff --staged`), presents what will be committed.
- Scans for sensitive files.
- Drafts and confirms the commit message via its own confirmation step.
- Runs `git commit`.
- Step 16: push confirmation — confirmed; pushes `HEAD` to `origin/<branch>` (PR #412's branch).
- Step 17: Auto-PR — explicitly skipped per this invocation's instruction (and would independently
  no-op anyway, since it sees PR #412 already open — belt-and-suspenders, not the load-bearing skip).

## Step 4 — Read back the commit

From `git-kit:commit`'s own output: confirm the new commit SHA and branch name, and confirm the push
step actually completed (it was confirmed in step 3, so yes — new commits are now on the remote branch
tracked by PR #412).

## Step 5 — Record `commit-linked`

Invoke `Skill(linear-github-linking)`: append a `git-github-evidence` entry
(`stage: "commit-linked"`, `commits: [{sha: <read-back SHA>, recorded_at: <now>}]`) per
`../../FOUNDATION_CONTRACTS.md`'s Git/GitHub Evidence Record.

## Step 6 — Discover pre-push gate configuration

Invoke `Skill(repository-gates)` to discover what pre-push gate(s), if any, this repository enforces
(e.g. a required-status-check on PRs, a branch-protection rule). Discovery only — never execution; a
real pre-push git hook already had its chance to fire during step 3's actual push, and a required-check
gate only starts running once a PR exists against the newly pushed SHA. Carry the discovered gate
identity forward to step 12.

## Steps 7-9 — Skipped (new-PR path only)

This is the existing-PR path: no new PR description to draft (7), no separate publication confirmation
needed since step 3's own commit-time push confirmation already covered the push (8), and no
`git-kit:create-pr` delegation — that would create a duplicate PR (9). All three explicitly skipped per
the skill's own instructions.

## Step 10 — Read back (existing-PR path)

Since no `git-kit` skill's own output supplies PR state for a push to an already-existing PR, read it
directly and read-only:

`Bash(gh pr view 412 --json headRefName,headRefOid,number,url,baseRefName,isDraft)`

Simulated result:
```json
{
  "headRefName": "<branch>",
  "headRefOid": "<new head SHA, matches step 4's commit>",
  "number": 412,
  "url": "https://github.com/<org>/<repo>/pull/412",
  "baseRefName": "main",
  "isDraft": true
}
```

Confirms: PR #412's `headRefOid` now matches the just-pushed commit — the push landed on the right PR.

## Step 11 — Verify no native status change

Check the Linear Issue's workflow status (via `linear-work-management`/`linear-github-linking`) before
and after this push. Confirm GitHub's native Linear integration (if configured) attached informational
evidence (a link/comment referencing the commit) without changing the Issue's own workflow status. No
drift observed — status unchanged. (Had it changed, this would be reported as drift, not treated as
expected.)

## Step 12 — Confirm the pre-push gate's outcome

Only now, after the actual push (step 3's push, on this existing-PR path): read back the gate identified
in step 6, via `repository-gates`, bound to the exact head SHA confirmed in step 10 (not step 4's raw
commit read, but the SHA GitHub itself confirms is now `HEAD` of PR #412).

Simulated result: the repository's configured required-check-style gate reports `pass` for this SHA.
(No assumption of a pass without this explicit read-back — had it come back `pending` or `fail`, that
real state would be recorded as-is in step 13, never upgraded.)

## Step 13 — Record `pr-published`

Invoke `Skill(linear-github-linking)`: append a `git-github-evidence` entry
(`stage: "pr-published"`) per `../../FOUNDATION_CONTRACTS.md`'s Git/GitHub Evidence Record, using the
read-back PR identity from step 10 (PR #412, head SHA, URL). This is recorded on the existing-PR path
too — a new commit reaching an already-open PR is publication evidence just as much as creating a new PR
would be.

Carrying step 12's gate read-back into this same entry's `gates[]` array: `["pass"]` for the gate
discovered in step 6. Per the skill: this run never mints a separate `stage: "ci-gates-passed"` entry —
that stage is reserved for a later, dedicated confirmation if a gate had instead resolved as
`pending`/`fail` here and later transitioned to `pass` on a follow-up check outside this skill's scope.

## Summary

- PR #412 classified `Exact` — no extra confirmation needed (step 2).
- Checkout verified against PR #412's repo/branch before anything else ran (step 2.5(a)) — both matched.
- `Skill(git-kit:cross-model-review)` invoked with **`BASE=HEAD`** (not the tool's default `BASE=main`)
  against the pending uncommitted diff only, before `commit` was invoked at all (step 2.5(b)) —
  First-Send Confirmation for the nested Codex dispatch fired and was confirmed; gate cleared clean.
- `Skill(git-kit:commit)` invoked with an explicit instruction to skip only its own step 17 (Auto-PR),
  letting step 16's push proceed normally and land the new commits on PR #412's branch.
- Read-back (`gh pr view 412`) confirms PR #412's head SHA now matches the new commit; no native
  Linear status drift; pre-push gate confirmed `pass` at the real post-push SHA.
- `commit-linked` and `pr-published` evidence entries recorded via `linear-github-linking`, with the
  gate result carried into `pr-published`'s own `gates[]` array rather than a separate
  `ci-gates-passed` entry.

No raw `git add`/`git commit`/`git push`/`gh pr create` was run directly at any point — every mutating
git/GitHub action went through `git-kit:commit`; PR #412 itself was updated purely as a side effect of
that push, per the skill's own "no adopt action exists or is needed" note.
