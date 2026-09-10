# Taking ENG-205 from Start of Work to Merged PR and Linear Disposition

I don't have a live Linear or GitHub connection in this environment, so I can't pull the actual ENG-205
record or push real commits. Below is the concrete, step-by-step plan I would execute if I did, based on
ordinary software-engineering and issue-tracker workflow practice. I'll note the assumptions I'm making
along the way and what I'd check/confirm at each step.

## Assumptions

- ENG-205 is a Linear issue in the "Accepted" (or equivalent ready-for-work) state, meaning it already has
  a clear description, acceptance criteria, and has been triaged/estimated by the team.
- The team's convention is: Linear issue -> feature branch -> PR on GitHub -> code review -> merge ->
  Linear issue auto/manually closed, with the two systems linked (either via Linear's native GitHub
  integration or via a magic branch-name/PR-description convention like `Fixes ENG-205`).
- I have write access to the repo and to the Linear issue (or am pairing with someone who does).

If any of these assumptions are wrong for the real ENG-205, the very first step below (reading the issue)
is where I'd catch and correct them.

## Step 1 — Read and confirm the issue before touching anything

1. Open ENG-205 in Linear and read the full description, acceptance criteria, any linked designs/specs,
   and the comment thread for context or scope changes since it was accepted.
2. Check for blocking relationships: does ENG-205 depend on another issue that isn't done yet? Is it
   blocking something else that's time-sensitive?
3. Confirm the issue is actually assigned to me (or self-assign it) and that no one else is already
   working it — duplicate work is the most common failure at this stage.
4. If anything in the ticket is ambiguous (unclear acceptance criteria, missing repro steps for a bug,
   no mockup for a UI change), leave a clarifying comment on the issue or ping the reporter *before*
   writing code. Starting implementation against a guess is how you end up with a PR that technically
   "works" but doesn't satisfy the actual ask.
5. Identify which repository/repositories the work touches. If ENG-205 doesn't already say, this is
   something I'd resolve now rather than discover mid-implementation.

**Checkpoint:** I have a concrete, unambiguous understanding of "done" for this issue, expressed as a
short list of acceptance criteria I can literally check off later.

## Step 2 — Signal "start of work" in Linear

1. Move ENG-205's status from Accepted/Todo to **In Progress** (or the team's equivalent "started"
   state). This is important even before any code exists — it's the signal to the rest of the team that
   this is actively being worked, prevents duplicate pickup, and keeps the board honest for anyone
   reviewing sprint status.
2. If the team's process expects a status-update comment or a linked "start" timestamp, add a short
   comment noting the plan (e.g., "Starting implementation — plan is to touch X, will open a PR against
   main").

## Step 3 — Branch creation

1. Sync the local default branch (`main`) so the new branch is cut from current `HEAD`, not a stale
   local copy — pull/fetch first.
2. Create a branch using the repo's naming convention. If Linear's GitHub integration is enabled, the
   convention is usually the one Linear itself suggests from the issue (e.g.
   `andre/eng-205-short-slug` or `eng-205-short-slug`), because that's what lets Linear auto-link the
   branch to the issue and auto-transition status later. Absent a stated convention, I'd default to
   something like `feature/eng-205-<short-description>` or `fix/eng-205-<short-description>` depending on
   whether ENG-205 is a feature or a bug.
3. Confirm the branch name actually contains the issue identifier (`ENG-205` or `eng-205`) somewhere,
   since that's what most Linear<->GitHub integrations pattern-match on for auto-linking, independent of
   whatever I put in the PR description.

## Step 4 — Implement the change

1. Re-read the acceptance criteria from Step 1 and turn each into a mental (or literal, in a scratch
   note) checklist.
2. Make the smallest change that satisfies the criteria — avoid opportunistic refactors or unrelated
   cleanup in the same branch; that's a fast way to bloat the PR, slow down review, and increase risk of
   an unrelated regression getting blamed on this change.
3. Write or update automated tests that exercise the new/changed behavior. If ENG-205 is a bug fix, first
   write a test that reproduces the bug and fails, then fix the code and confirm the test now passes —
   that's the strongest evidence the fix actually addresses the reported problem rather than a
   symptom.
4. Run the full local test suite (not just the new tests) to catch regressions elsewhere.
5. Run linters/formatters/type-checkers the project uses, and fix anything they flag.
6. Manually exercise the change if it has any user-facing or runtime behavior a test suite wouldn't
   fully cover (e.g., actually run the CLI command, hit the endpoint, load the UI).
7. Update any documentation (README, CHANGELOG, inline docs, API docs) that the change makes stale. A
   PR that changes behavior without updating the docs that describe that behavior is incomplete.

**Checkpoint:** every acceptance criterion from Step 1 is demonstrably satisfied — tests pass, docs are
current, and I could explain in one sentence per criterion why it's met.

## Step 5 — Commit

1. Review the diff (`git status` / `git diff`) before staging anything, specifically checking for:
   - Accidentally included unrelated files or debug/scratch code.
   - Secrets, tokens, or credentials that shouldn't be committed.
   - Large or generated files that shouldn't be tracked.
2. Stage only the files relevant to this change.
3. Write a commit message that explains *why*, not just *what* — conventional-commit style
   (`fix:`/`feat:`/`chore:` prefix) if that's the repo's convention, matching whatever the recent commit
   history in the repo actually shows rather than inventing a new style.
4. Reference the issue in the commit message or (more commonly) leave that linkage to the PR
   description instead, depending on which the team's Linear-GitHub integration actually keys off of —
   I'd check the integration's docs/settings rather than assume.
5. If the change is large enough to be hard to review as one commit, consider splitting into logically
   separate commits (e.g., "add failing test" then "fix the bug"), but keep the PR itself scoped to
   ENG-205 only.

## Step 6 — Push and open the PR

1. Push the branch to the remote.
2. Open a PR against `main` (or the repo's actual default/integration branch — I'd confirm this from the
   repo settings rather than assume `main`).
3. PR title: clear, imperative, ideally including the issue ID (e.g. "ENG-205: <short description>").
4. PR description:
   - A closing keyword that links and auto-closes the Linear issue on merge, if the Linear-GitHub
     integration is set up to honor GitHub closing keywords (`Fixes ENG-205` / `Closes ENG-205`), *or*
     the Linear-specific magic-word syntax if that's what the integration expects — I'd check which one
     is actually wired up rather than guess, since using the wrong syntax silently fails to link.
   - Summary of what changed and why.
   - How it was tested (which tests were added/run, any manual verification steps).
   - Any deliberate scope exclusions ("this PR does not handle X, tracked separately as ENG-2xx") so
     reviewers don't flag it as an oversight.
   - Screenshots/recordings if it's a UI change.
5. Mark it "Ready for review" (not draft) once the above is actually true — I would not open it ready
   for review before CI has a chance to run, and would flip it to draft if I need to push more WIP
   commits before it's actually reviewable.
6. Confirm in Linear that the issue picked up the PR link (most integrations auto-attach it and often
   auto-transition the issue to an "In Review" state). If it didn't auto-link, add the PR link to the
   issue manually and set the status by hand — don't assume the automation worked; verify it.

## Step 7 — CI and automated checks

1. Watch the PR's CI run to completion — don't request review while checks are still pending or
   unknown.
2. If CI fails: read the actual failure output (not just "CI is red"), fix the root cause, push a new
   commit, and re-verify CI goes green. Never merge with a required check failing, and never disable/skip
   a check to get around a failure without understanding why it failed first.
3. Confirm branch protection requirements are satisfied (required checks, required reviewers, any
   required status like "no merge conflicts with base").

## Step 8 — Code review

1. Request review from the appropriate reviewer(s) — CODEOWNERS if the repo has them, otherwise whoever
   owns the touched area.
2. While waiting, do a self-review pass on the PR's own diff as rendered on GitHub — often surfaces
   things (a stray console.log, a debug flag left on) that are easy to miss locally.
3. Respond to every review comment, not just the ones I agree with — if I disagree, explain why rather
   than silently ignoring it; if I agree, fix it and reply noting the commit that addresses it.
4. Re-request review after pushing fixes rather than assuming the reviewer will notice new commits.
5. Resolve conversation threads only once actually addressed, not preemptively.
6. If review surfaces something out of scope for ENG-205, don't silently expand the PR — either do a
   quick, clearly-scoped fix and call it out explicitly in the PR description, or file a new Linear issue
   for it and link back to ENG-205, whichever the reviewer and I agree is more appropriate.
7. Keep the branch up to date with the base branch (merge or rebase, matching repo convention) if it
   drifts significantly during a long review cycle, and re-run CI after doing so.

## Step 9 — Merge

1. Before merging, do a final readiness check:
   - All required status checks green.
   - All required reviewers approved, no outstanding "changes requested."
   - No merge conflicts with the base branch.
   - PR is not marked draft.
2. Confirm I (or whoever is merging) actually has merge rights on the repo/branch.
3. Use the repo's standard merge strategy (squash vs. merge commit vs. rebase-merge) — match whatever
   the repo already does for other PRs rather than picking my own preference.
4. Merge, then confirm the merge actually landed (PR shows "Merged", commit appears on the base branch).
5. Delete the feature branch after merge (most repos default to this) unless there's a reason to keep it.

## Step 10 — Linear disposition

1. Verify ENG-205 automatically transitioned to "Done"/"Merged"/whatever the team's terminal state is,
   via the Linear-GitHub integration reacting to the merge. Don't assume this happened silently and
   correctly — open the issue and check.
2. If it did **not** auto-transition (integration not configured for that repo, closing keyword didn't
   match, etc.), manually:
   - Set the issue status to Done/Complete.
   - Confirm the merged PR is linked on the issue.
   - Add a closing comment summarizing what shipped and linking the PR, for anyone who lands on the
     issue later without git history handy.
3. Check whether ENG-205 was part of a Linear project/milestone/cycle and whether closing it should
   trigger any downstream update (e.g., a parent issue's sub-issue checklist, a project's percent-complete
   rollup) — these are usually automatic but worth a glance if the project is close to fully done.
4. If the change requires a follow-up action beyond the merge — a deploy, a feature-flag flip, a
   migration to run, a changelog/release-notes entry, notifying a specific stakeholder — do that now and
   note it on the issue before considering it truly finished. "Merged" and "actually shipped to users"
   are not always the same moment, and the issue shouldn't be marked fully Done until whichever of those
   the team considers the real finish line has actually happened.
5. If ENG-205 uncovered follow-up work that's explicitly out of scope, file it as new Linear issue(s) now
   (while context is fresh) and link them to ENG-205 (e.g., "relates to" / "blocks"), rather than letting
   the observation evaporate.

## Summary checklist

- [ ] Issue read, scope confirmed, ambiguities resolved before coding
- [ ] Linear status set to In Progress at start
- [ ] Branch created from up-to-date main, named per convention (includes ENG-205)
- [ ] Implementation matches every acceptance criterion
- [ ] Tests added/updated and passing; bug fixes have a reproducing test
- [ ] Docs updated if behavior changed
- [ ] Diff reviewed before commit; commit message explains why
- [ ] PR opened with issue-linking syntax, clear description, testing notes
- [ ] CI green
- [ ] Review requested, comments addressed, re-approved
- [ ] Merge readiness confirmed (checks, approvals, no conflicts, merge rights)
- [ ] Merged, branch cleaned up
- [ ] Linear issue confirmed Done, PR link present, closing comment added if not automatic
- [ ] Any post-merge action (deploy, flag flip, release notes) completed and noted
- [ ] Any discovered follow-up work filed as new linked issues
