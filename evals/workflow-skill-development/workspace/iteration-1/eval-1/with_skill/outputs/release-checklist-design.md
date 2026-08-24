# release-checklist — Workflow Skill Design

## Pattern Decision

Walking the Pattern Selection decision tree from `workflow-skill-development`:

- Distinct paths: one — every release always executes the same four checks/actions in the
  same order (CI → changelog → version bump → tag). There is no branching into independent
  workflows based on user intent, so this is not a **Routing** skill.
- The four steps are **dependent** on each other in sequence: the changelog generation needs
  to know CI already passed (no point drafting release notes for a broken build); the version
  bump decision (major/minor/patch) is informed by what the changelog contains; the tag name
  embeds the bumped version. Each step feeds the next — this matches **Sequential Pipeline**
  over plain **Linear Progression**, and specifically the pipeline's "auto-detection may resume
  from partial progress" feature matters here: a release prep session that gets interrupted
  after the changelog is written but before the tag is cut should be able to resume at Phase 3,
  not redo the changelog.
- The dependencies are not *complex* (no fan-out, no conditional dependency graph, no partial-
  failure tolerance across independent branches) — so **Task-Driven** (TaskCreate/TaskUpdate)
  would be over-engineering for four steps that always run straight through.
- The final action (creating and pushing a git tag, and the version-bump commit that precedes
  it) is irreversible in the sense that matters for a release: once a tag is pushed, downstream
  consumers may already have pulled it, and re-tagging is disruptive. That single destructive
  step doesn't justify restructuring the *whole* skill as a **Safety Gate** pattern (the first
  three phases are safe, inspectable, read-only or locally-reversible actions), but it does mean
  Phase 4 embeds Safety-Gate-style double confirmation as a **local pattern within one phase** of
  an otherwise Sequential Pipeline skill.

**Chosen pattern: Sequential Pipeline**, with a Safety Gate sub-pattern applied inside Phase 4
(tag creation) only.

## Quick Start

1. **Confirm scope** — identify the repo, the target branch, and the version file(s) that hold
   the current version string (`package.json`, `pyproject.toml`, `plugin.json`, etc.).
2. **Run the pipeline phases in order** — Phase 1 (CI Verification) → Phase 2 (Changelog
   Generation) → Phase 3 (Version Bump) → Phase 4 (Tag Creation) → Phase 5 (Final Verification).
   Each phase's exit criteria gate entry into the next; do not skip ahead.
3. **Resume support** — before starting, check for a `.release-checklist-state` marker (or
   equivalent session state) indicating a prior interrupted run; if found, resume at the first
   phase whose exit criteria are not yet satisfied rather than restarting from Phase 1.
4. **Apply the Safety Gate inside Phase 4 only** — tag creation requires two explicit
   confirmations (preview then execute) before any push happens.
5. **Verify** — Phase 5 re-checks that CI is still green, the changelog file is committed, the
   version file matches the tag, and the tag exists both locally and on the remote.

## Phase-by-Phase Structure

### Phase 1 — Verify CI Is Green

**Entry criteria**
- A target branch/commit for the release has been identified (defaults to the current branch's
  HEAD, or a `--ref` argument if the skill is invoked with one).
- The repository has a remote configured that hosts CI status (e.g. GitHub Actions).

**Numbered actions**
1. Resolve the commit SHA the release will be cut from (current branch tip, or the given ref).
2. Query CI status for that exact SHA (e.g. `gh run list --commit <sha>` / equivalent for the
   CI provider in use).
3. If any required check is not `completed` + `success`, stop and report which check(s) are
   pending or failing — do not proceed to Phase 2.
4. If CI status was checked more than a few minutes ago in this same session (e.g. the user
   paused between invocations), re-query rather than reusing the earlier result — CI state is
   external and can change between steps.
5. Record the verified commit SHA for reuse by later phases (the changelog and tag must both
   refer to this exact SHA, not a re-resolved "current HEAD" that may have moved).

**Exit criteria**
- All required CI checks for the recorded SHA report `completed` / `success`.
- The verified SHA is recorded for downstream phases.

### Phase 2 — Generate Changelog

**Entry criteria**
- Phase 1 exit criteria met (CI green on a recorded SHA).
- The previous release's tag (or a stated starting point) is known, so commits can be scoped
  to "since last release."

**Numbered actions**
1. Determine the previous release tag (e.g. `git describe --tags --abbrev=0`) or ask the user
   for a starting point if no prior tag exists (first release).
2. Collect commits between the previous tag and the recorded SHA (`git log <prev-tag>..<sha>`).
3. Group commits by conventional-commit type (feat/fix/docs/chore/etc.) if the repo follows
   that convention; otherwise group by a simple heuristic or leave ungrouped — do not invent
   a categorization scheme the repo doesn't already use.
4. Draft changelog entries in the project's existing changelog format/file (append to
   `CHANGELOG.md` under a new "Unreleased" or version-pending heading — do not overwrite prior
   entries).
5. Present the draft to the user for review before writing it to disk, since changelog wording
   is a judgment call, not a mechanical transform.
6. On approval, write the changelog file and stage the change (commit deferred to Phase 3,
   bundled with the version bump, to keep the release commit atomic).

**Exit criteria**
- A changelog entry for the pending release exists in the repo's changelog file, covering
  every commit since the previous tag, and has been explicitly approved by the user.
- The change is staged but not yet committed.

### Phase 3 — Bump Version Number

**Entry criteria**
- Phase 2 exit criteria met (changelog drafted and approved).
- The version file(s) to update are known (detect from repo conventions: `package.json`,
  `pyproject.toml`, `plugin.json`, `VERSION`, etc.).

**Numbered actions**
1. Read the current version from the detected version file(s).
2. Determine the bump type (major/minor/patch) — infer from the changelog's contents if the
   repo follows conventional commits (any `feat!`/breaking change → major; any `feat` → minor;
   otherwise patch), or ask the user if it can't be inferred confidently.
3. Compute the new version string and confirm it with the user before writing (this is the
   number that will become the tag name — a wrong guess here propagates into Phase 4).
4. Update the version file(s) with the new version string.
5. Stage the version file change alongside the changelog change from Phase 2.
6. Create a single release commit covering both the changelog and the version bump, with a
   commit message following the repo's existing convention (e.g. `chore(release): vX.Y.Z`).

**Exit criteria**
- The version file(s) reflect the new, user-confirmed version number.
- A single commit exists containing both the changelog update and the version bump.

### Phase 4 — Create Git Tag (Safety Gate)

This phase is destructive/irreversible in effect (a pushed tag is expected to be immutable by
downstream consumers), so it applies the Safety Gate pattern's two-confirmation structure
rather than proceeding straight through like Phases 1–3.

**Entry criteria**
- Phase 3 exit criteria met (release commit exists locally with the new version).
- The tag name to create is known (derived from the confirmed version, e.g. `vX.Y.Z`).

**Numbered actions**
1. **Preview (confirmation gate 1):** show the user the exact tag name, the commit it will
   point to (the Phase-3 release commit), and whether the tag will be pushed immediately or
   left local. Do not create the tag yet.
2. Check whether a tag with this name already exists locally or on the remote; if so, stop and
   report the conflict rather than overwriting it.
3. **Execute confirmation gate 2:** ask explicitly whether to proceed with tag creation (and,
   separately, whether to push it now vs. leave it local for the user to push later) — two
   distinct yes/no decisions, not one bundled confirmation.
4. On approval, create the annotated tag locally (`git tag -a <tag> -m <message>`).
5. If the user approved pushing, push the release commit and the tag together
   (`git push` + `git push origin <tag>`); if not, stop here and report that the tag is local
   only and how to push it later.

**Exit criteria**
- The annotated tag exists locally, pointing at the Phase-3 release commit.
- If push was approved: the tag and the release commit both exist on the remote.
- The user was given two explicit, separate confirmations before any state-changing git
  command ran.

### Phase 5 — Final Verification

**Entry criteria**
- Phase 4 exit criteria met (tag created, and pushed if approved).

**Numbered actions**
1. Re-query CI status for the release commit (not reusing the Phase 1 result — CI may have
   re-run or a new required check may have appeared since then).
2. Confirm the version file(s) on the release commit match the tag name.
3. Confirm the changelog file on the release commit contains the new release's entry.
4. Confirm the tag exists on the remote (if push was approved) with `git ls-remote --tags`.
5. Report a final summary: verified commit SHA, tag name, changelog location, and whether the
   tag was pushed.

**Exit criteria**
- Every check in this phase passes, or any failure is explicitly reported to the user rather
  than silently ignored.
- The skill's output is a clear pass/fail summary of the release state, not just "done."

## Tool Assignment

Only tools the phases above actually call:

- `Bash` — `git log`, `git tag`, `git push`, `git ls-remote`, `git describe`, CI status queries
  (`gh run list` or provider equivalent).
- `Read` — reading current version files and the existing changelog.
- `Edit` / `Write` — updating the changelog and version file(s).
- `AskUserQuestion` — changelog approval (Phase 2), version-bump-type/number confirmation
  (Phase 3), the two Phase 4 confirmation gates.

## File Layout (Progressive Disclosure)

- `SKILL.md` — Quick Start, the five numbered phases with entry/numbered-actions/exit criteria
  (as above), and the Tool Assignment table. Kept under 500 lines; no CI-provider-specific
  command syntax inline.
- `references/ci-providers.md` — provider-specific CI status query commands (GitHub Actions,
  GitLab CI, CircleCI, etc.), linked from Phase 1 rather than inlined, so SKILL.md doesn't grow
  with every new provider supported.
- `references/version-file-conventions.md` — how to detect and update version strings per
  ecosystem (`package.json`, `pyproject.toml`, `Cargo.toml`, `plugin.json`, bare `VERSION`
  file), linked from Phase 3.
- `references/conventional-commits.md` — the bump-type inference rules used in Phase 3, and the
  commit-type grouping used in Phase 2, linked from both phases rather than duplicated.

## Validation Checklist (self-check against `workflow-skill-development`)

- [x] Uses a recognizable pattern — Sequential Pipeline (with a Safety Gate sub-pattern scoped
      to Phase 4 only, explicitly justified above rather than left implicit).
- [x] All five phases numbered with entry and exit criteria.
- [x] SKILL.md content above stays well under 500 lines; provider/ecosystem-specific detail is
      pushed to `references/`.
- [x] No broken file references — the three `references/` files are named consistently with
      where they're linked from (Phase 1, Phase 2/3, Phase 3).
- [x] Verification step present at the end (Phase 5), and it re-checks state rather than
      trusting earlier-phase results (per the re-check-before-side-effecting-action pattern:
      Phase 5 re-queries CI instead of reusing Phase 1's read, since Phase 4's push is itself
      a side-effecting action that should be re-verified afterward, not assumed successful from
      Phase 4's own optimistic report).
- [x] Each phase has a clear, specific goal (CI check / changelog / version bump / tag / verify)
      with no overlapping responsibility between phases.
