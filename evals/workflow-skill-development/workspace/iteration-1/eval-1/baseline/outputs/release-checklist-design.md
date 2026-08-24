# `release-checklist` — Skill Design

## Structural Pattern Decision

**Pattern: Linear, gated phase-pipeline (checklist-with-gates), not a decision tree or a
single-shot command.**

Reasoning:

- The four tasks named in the request — verify CI, generate changelog, bump version, create tag —
  have a strict real-world dependency order. You cannot honestly bump a version number for a
  release whose CI is red, and a git tag should not be cut before the changelog and version bump
  it's supposed to represent are actually committed. A decision-tree pattern (branching on "what
  kind of request is this?") doesn't fit because there's really only one path through this task,
  not several distinct request types to route between.
- Each step also has a natural, checkable **entry condition** (is the prior step's output actually
  in place?) and **exit condition** (did this step's output get produced correctly?). That maps
  directly onto a phase-gated workflow skill rather than a flat numbered list of actions, because a
  flat list has no place to say "stop here if CI is red" — a gate needs to be a first-class
  structural element, not a bullet buried in step 3.
- Release prep is also a place where silently continuing past a failure is actively harmful (a bad
  tag is hard to walk back cleanly once pushed), so each phase needs an explicit exit gate that can
  halt the whole workflow before moving on, rather than a best-effort pass through all steps
  regardless of what happened earlier.

This yields a **five-phase pipeline**: Preflight → CI Verification → Changelog Generation →
Version Bump → Tag Creation, each with its own entry criteria, numbered actions, and exit
criteria, plus a short Quick Start for the common case where everything just works.

---

## Quick Start

For the common case — you're on the branch that should ship, CI has already run, and you just want
the release cut:

1. Run this skill from the release branch (usually `main`/`master`) after your last release commit
   has been pushed and CI has finished running on it.
2. The skill will:
   - Confirm the latest CI run on the current commit is green (Phase 1).
   - Draft a changelog entry from commits/PRs since the last tag and show it to you before writing
     it (Phase 2).
   - Propose a new version number (semver bump: patch/minor/major, inferred from changelog content
     unless you specify) and show the diff before applying it (Phase 3).
   - Create an annotated git tag pointing at the release commit, after confirming with you (Phase 4).
3. You will be asked to confirm before each write action (changelog write, version file edit, tag
   creation) — nothing is pushed or published without an explicit go-ahead. Pushing the tag/commit
   to the remote is treated as a separate, final confirmation, not implied by the earlier ones.
4. If any phase's exit criteria aren't met (CI red, no committable changes since last tag, working
   tree dirty, tag already exists), the skill stops and reports exactly why, rather than skipping
   ahead.

---

## Full Phase-by-Phase Structure

### Phase 0 — Preflight

**Entry criteria**
- User has invoked the skill and named (or the skill can infer) which branch/commit represents the
  release candidate.

**Actions**
1. Confirm the working tree is clean (`git status`); if not, stop and ask the user to commit,
   stash, or discard changes before proceeding — do not stash automatically without asking.
2. Confirm the current branch is the intended release branch; if ambiguous, ask the user to
   confirm.
3. Identify the last release tag (e.g. `git describe --tags --abbrev=0`) to use as the base for the
   changelog and version-bump range in later phases. If no prior tag exists, treat this as the
   first release and use the repository's root commit as the range base.
4. Confirm the remote is reachable and the local branch is up to date with its remote counterpart
   (fetch, compare `HEAD` to `origin/<branch>`); if local is behind, ask whether to pull first
   rather than proceeding on stale state.

**Exit criteria**
- Working tree is clean.
- Release branch and base tag/commit are both identified and confirmed.
- Local branch is not behind its remote tracking branch (or the user has explicitly accepted
  proceeding anyway).

---

### Phase 1 — Verify CI Is Green

**Entry criteria**
- Phase 0 exit criteria met.

**Actions**
1. Identify the CI system in use (GitHub Actions, etc.) from repo config if not already known.
2. Look up the CI status for the exact commit SHA at `HEAD` of the release branch — not merely
   "the latest run for this branch," since a newer commit may have landed after the run started.
3. Re-check the status live at this point rather than reusing any status observed earlier in the
   session, since CI state can change between when the user started this conversation and now.
4. If any required check is not yet complete, stop and report which check(s) are pending — do not
   wait/poll silently; tell the user the current state and let them decide whether to wait and
   re-run this phase, or proceed only if they explicitly override.
5. If any required check failed, stop and report which check(s) failed and a link/reference to the
   failure — do not proceed to changelog/version/tag phases on red CI.

**Exit criteria**
- All required CI checks for the exact release-candidate commit report a passing/success
  conclusion.
- No required check is in a pending/queued/in-progress state.

---

### Phase 2 — Generate Changelog

**Entry criteria**
- Phase 1 exit criteria met (CI green on the release commit).

**Actions**
1. Determine the commit/PR range: from the last release tag (identified in Phase 0) to the current
   release-candidate commit.
2. Collect the commits/merged PRs in that range, grouped by conventional-commit type or label if
   the repo uses either convention (feat/fix/docs/chore, etc.); otherwise group by a sensible
   default (Added/Changed/Fixed/Other).
3. Exclude merge commits and any commits already covered by a prior changelog entry, to avoid
   duplicate lines if this phase is re-run.
4. Draft the changelog entry text and show it to the user for review before writing anything to
   disk.
5. On approval, write the entry into the project's changelog file (e.g. `CHANGELOG.md`) following
   the existing file's own format/heading conventions — do not introduce a new format if one is
   already established. If no changelog file exists, ask the user whether to create one and in what
   format, rather than assuming.
6. Stage the changelog change but do not commit yet — committing happens together with any other
   release-prep changes in Phase 3's commit step, so the release commit is a single reviewable
   unit.

**Exit criteria**
- A changelog entry covering exactly the commit range since the last release has been drafted,
  approved by the user, and staged.
- No duplicate or missing entries relative to the last release tag.

---

### Phase 3 — Bump Version Number

**Entry criteria**
- Phase 2 exit criteria met (changelog entry approved and staged).

**Actions**
1. Locate the file(s) that declare the project's version (e.g. `package.json`, `pyproject.toml`,
   `plugin.json`, `Cargo.toml`, `VERSION`) — confirm with the user if more than one plausible
   location exists, since bumping only one of several version files silently leaves the others
   stale.
2. Determine the current version and propose the next version, using semantic-versioning rules:
   infer patch/minor/major from the changelog's own categorization (breaking change → major, new
   feature → minor, fix-only → patch) unless the user specifies the bump type directly.
3. Present the proposed old → new version to the user for confirmation before editing any file.
4. On approval, update the version in every located version-declaration file consistently.
5. Stage the version-file changes alongside the changelog changes from Phase 2.
6. Create a single release-prep commit containing the changelog and version-bump changes together,
   with a clear commit message (e.g. `chore(release): vX.Y.Z`), after a final confirmation of the
   commit message.

**Exit criteria**
- All identified version-declaration files show the same, newly agreed-upon version number.
- A single commit containing both the changelog entry and the version bump exists on the release
  branch.

---

### Phase 4 — Create Git Tag

**Entry criteria**
- Phase 3 exit criteria met (release-prep commit exists on the branch).

**Actions**
1. Re-derive the tag name from the version agreed in Phase 3 (e.g. `vX.Y.Z`), following the
   repository's existing tag-naming convention if one is already in use.
2. Check whether a tag with that name already exists locally or on the remote; if so, stop and
   report the conflict rather than overwriting or force-updating a tag silently.
3. Present the exact tag name and the commit it will point to (the Phase 3 release-prep commit) to
   the user for confirmation.
4. On approval, create an annotated tag (not a lightweight tag) with a message summarizing the
   release, pointing at the release-prep commit.
5. Ask the user, as a separate explicit confirmation, whether to push the release-prep commit and
   the new tag to the remote now, or leave both local for the user to push manually. Do not push
   automatically as a continuation of the tag-creation approval.
6. On approval to push, push the branch and the tag, then report the resulting remote state
   (branch pushed, tag pushed, links to the commit/tag if the platform provides them).

**Exit criteria**
- An annotated tag matching the agreed version exists locally, pointing at the release-prep commit.
- The user has been explicitly asked about pushing, and the outcome (pushed or left local) is
  reported back clearly.
- No unresolved naming conflict with a pre-existing tag.

---

## Cross-Phase Notes

- **No silent auto-continuation across a failed gate.** If any phase's exit criteria are not met,
  the skill stops and reports the specific unmet criterion rather than attempting a workaround or
  skipping ahead — this matches the entry/exit-gate structure above, where each phase's entry
  criteria are literally the previous phase's exit criteria.
- **Re-check state, don't reuse stale reads.** CI status (Phase 1) and tag-existence checks
  (Phase 4) are re-verified at the moment they're acted on, not carried over from an earlier check
  in the same conversation, since both can change out from under the workflow between phases.
- **Every write is confirmed before it happens.** Changelog file writes, version file edits, tag
  creation, and pushing to the remote are each their own confirmation point — approval of an
  earlier step (e.g. the changelog draft) does not imply approval of a later one (e.g. pushing to
  the remote).
