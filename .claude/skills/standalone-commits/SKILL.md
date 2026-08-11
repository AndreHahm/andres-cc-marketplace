---
name: standalone-commits
description: >-
  Make commits reviewable and auditable as self-contained units, order multi-file changes into atomic dependency-ordered waves, and decide which of several pending changes to stage first. Use when planning commits, 'split this into commits', 'break this up', 'commit strategy', splitting work into waves, staging changes, reviewing branch history, deciding whether a commit is too broad, too tiny, incomplete, or hard to revert, prioritizing which change to stage next, or filtering pending changes down to what's relevant to the current PR.
allowed-tools: Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(gh pr view:*), Bash(*/git-kit/scripts/write-git-kit-marker.sh:*)
---

# Standalone Commits

A standalone commit is a commit a reviewer can audit on its own, at that point in branch history. It may depend on earlier commits in the same branch, but it should not require future commits to explain, compile, test, or justify it.

> **Related Skill**: See git-kit's `commit` skill for conventional commit messages and PR text.

## Two Halves: Boundary And Order

This skill owns both halves of commit shaping. Hold them at once:

- **The review boundary** (this file): is each commit worth reviewing by itself? That is the philosophy and the acceptance checks below.
- **The ordering**: what order should the standalone commits happen in? For the detailed dependency-ordered wave procedure, read [references/splitting-into-ordered-waves.md](references/splitting-into-ordered-waves.md).

Without ordering, "standalone" drifts into polished but poorly sequenced commits. Without the boundary checks, technically ordered commits can still be hard to review.

## The Standard

Each commit should answer one sentence:

> This commit changes `<thing>` so that `<outcome>` because `<reason>`.

If the sentence needs "and also", split the commit. If the reason only becomes true in a later commit, move the work later or combine the dependent pieces.

## Acceptance Checks

Before committing, verify the staged diff against these checks:

| Check | Question |
| --- | --- |
| Reviewable | Can a reviewer understand the purpose from this diff and message alone? |
| Buildable | Does the repo still typecheck, build, or pass the relevant focused test after this commit? |
| Complete | Are all call sites, exports, tests, docs, and fixtures needed for this concern included? |
| Focused | Is there exactly one behavioral, structural, or documentation concern? |
| Auditable | Can someone inspect the before/after and see the invariant being preserved or changed? |
| Revertible | If this commit were reverted, would it remove one coherent change without dragging in unrelated work? |

When a commit fails one check, fix the staged set before writing the message.

## What Standalone Means

Standalone does mean:

- The commit is coherent at its point in history.
- The message explains why the diff exists.
- New public surface has the minimum implementation, exports, and tests needed to be credible.
- Refactors preserve behavior and include verification when risk is non-trivial.
- Mechanical changes are separated from semantic changes when mixing them would hide behavior.

Standalone does not mean:

- Every commit must be useful without earlier commits in the same branch.
- Every commit must be tiny.
- A large generated or mechanical change must be manually split into noise.
- The final branch cannot contain dependency chains.

## Wave Planning

When ordering work into waves, plan each wave as a standalone commit:

```
Wave 1 claim: Add the type or contract, plus any tests that prove the new shape.
Wave 2 claim: Add the implementation that satisfies the contract.
Wave 3 claim: Move consumers onto the implementation.
Wave 4 claim: Remove old paths once no consumers depend on them.
```

Do not create a "setup" commit that only makes a future commit possible unless it is independently reviewable. A foundation commit is fine when it introduces a real contract, helper, migration, or test fixture with a clear reason.

Before coding a wave, write its claim. After staging it, re-read the staged diff and ask whether the claim is still honest. If not, split, combine, or move the work.

## Prioritizing And Filtering Candidate Changes

Before the Staging Workflow's step 1, when the working tree has more pending changes than belong in one wave, decide what to stage first:

1. **Check for an open PR on the current branch**: `gh pr view --json number,files 2>/dev/null`. If one exists, treat its already-changed file list as the PR's declared scope.
2. **Filter to PR-relevant changes** when a PR exists: changes to files the PR already touches, or files that directly support what the PR is doing, are in scope. A change unrelated to the PR's own concern — drift that crept in from something else worked on in the same session — stays unstaged; don't fold it into this PR's commits. With no open PR, there's no filter to apply — every pending change is a candidate.
3. **Rank the remaining candidates by priority**, highest first: fixes that block or break something else, then changes the PR's own description or stated scope calls out explicitly, then everything else ordered by the wave-dependency rules in [references/splitting-into-ordered-waves.md](references/splitting-into-ordered-waves.md).
4. **Stage only the top-ranked group** — the changes needed for the next standalone commit, not everything that passed the filter. Repeat this procedure for the next commit once the current one lands, rather than ranking and staging the entire backlog in one pass.

This matters most when several unrelated concerns accumulate before a single staging pass. The acceptance checks above still decide whether any one grouping is reviewable; this section decides which grouping to reach for first.

## Staging Workflow

1. Inspect the full diff.
2. Write the one-sentence commit claim.
3. Stage only files and hunks that prove that claim.
4. Re-read the staged diff with `git diff --staged`.
5. Run focused verification for that staged state when practical.
6. Commit the staged wave in three parts:
   - 6a. **Compose** the message per `commit` skill's "Best Practices for Commits" (conventional format) and "Commit Message Footer" sections — link to those sections rather than restating the type list or trailer table here, so the two skills can't drift apart on format. Make the subject name the outcome, not the implementation detail (see "Commit Message Shape" below).
   - 6b. **Confirm** with `AskUserQuestion` — show the exact composed message and ask "Commit this wave with this message?" — options "Commit as shown" / "Revise the message" / "Stop". "Revise the message" loops back to 6a; "Stop" leaves the wave's files staged but uncommitted.
   - 6c. **Commit**: immediately before committing, run `"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" git-commit standalone-commits` — this writes the marker git-kit's commit-guard hook requires (it accepts markers up to 60 seconds old, so write it right before this step, not earlier, and after 6b's confirmation — not before it, since a slow confirmation could otherwise let the marker go stale before `git commit` runs). Then run `git commit` with the confirmed message.

   This flow does **not** add `commit`'s step-9 behavior-change test gate — a commit made through this skill is not currently checked against `.claude/rules/require-tests-for-behavior-changes.md` the way a `commit`-skill invocation is. This is a stated gap, not an oversight: if the wave being committed changes skill/agent behavior, apply that rule's applicable testing mechanism yourself before reaching this step.

   A commit made through this skill with no `attributionSkill` tag in its own session transcript is a transcript-metadata artifact of the surrounding harness — not evidence the marker-write step (6c) was skipped. The marker write is rewritten fresh before every wave's own commit by design, since this Staging Workflow is repeated once per wave (see "Wave Planning" above); `guard-raw-commit.sh`'s marker is single-use and consumed on every check regardless of outcome, so a stale or reused marker cannot silently let a later wave's commit through unconfirmed.

Prefer file-level staging when files cleanly map to the commit claim. Use hunk staging when one file contains multiple concerns.

## Split Or Combine Heuristics

Split when:

- A refactor and behavior change appear together.
- A rename or move hides logic changes.
- Tests cover a different concern than the implementation.
- A dependency bump is mixed with feature work.
- Reviewers would need to hold two mental models at once.

Combine when:

- A type without its only implementation would be dead surface.
- A helper without its call site would be speculative.
- A test without the fix would intentionally fail in the branch.
- A migration without the schema or reader change would break local state.

## Anti-Patterns

### Teaser Commit

```
feat(sync): add workspace sync types
```

Problem: The types are unused, untested, and only make sense after a later implementation commit.

Better: Include the contract-level implementation or test that proves why the types exist.

### Hidden Behavior In Refactor

```
refactor(auth): reorganize session helpers
```

Problem: The diff also changes session expiry behavior. Reviewers may scan it as a move-only change.

Better: Commit the move first with no behavior change, then commit the expiry behavior change with tests.

### Cleanup Hitchhiker

```
fix(settings): persist provider selection
```

Problem: The commit also renames unrelated variables and formats nearby files.

Better: Keep the fix focused. Put cleanup in a separate commit only if it is worth reviewing.

## Commit Message Shape

Use git-kit's `commit` skill for exact conventional commit formatting. For standalone commits, make the subject name the outcome, not the implementation detail.

Good:

```
fix(settings): persist selected provider across reloads
```

Weak:

```
fix(settings): update localStorage call
```

Add a body when the reason, invariant, or review boundary is not obvious from the diff.

## Testing & Validation

**Verify this skill activates on:**
- "split this diff into separate commits" / "break this up into multiple commits"
- "how should I order these changes into waves"
- "is this commit too broad / hard to revert"

**Verify it does NOT activate on:**
- "commit this" with a single, already-coherent staged change → `commit`
- "review this PR" → `explain-pr-changes` / `collaborating-on-a-pr`

**Verify the Staging Workflow's commit-confirmation gate (step 6):**
- A multi-wave sequence (e.g. 4 waves) — confirm each wave gets its own `AskUserQuestion` at step 6b, not
  one confirmation covering the whole sequence
- Choosing "Revise the message" at 6b — confirm it loops back to composing (6a), not straight to committing
- Choosing "Stop" at 6b — confirm the wave's files remain staged but the commit does not run
- Confirm step 6a's composed message never restates `commit`'s type list or footer-trailer table inline —
  it links to `commit`'s own sections instead

**Quality gates:**
- [ ] Step 6 is always split into compose (6a) / confirm (6b) / commit (6c) — never a single undifferentiated
      "commit with a message" step
- [ ] The marker write (6c) always happens after 6b's confirmation, never before it
- [ ] This flow never silently claims `commit`'s step-9 behavior-change test gate applies here — see step
      6's own stated gap
