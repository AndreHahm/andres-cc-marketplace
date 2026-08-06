# Branch and Open-PR Pre-Flight Checks

Two independent checks, shared by `plugin-lifecycle-upstream`, `plugin-lifecycle-downstream`, and `plugin-lifecycle-maintenance` — each skill's own SKILL.md/workflow states *when* in its own procedure these run; this file is the single source of truth for *how* they run, so the exact `gh`/`git` commands and question wording don't drift out of sync across three separate skills.

## Open-PR Check

**Purpose:** catch the case where new work is about to start on a branch that already has an unmerged PR open — piling more commits onto a stale open PR, or losing track of it, is easy to do by accident.

**Procedure:**
1. `gh pr view --json number,state,url` for the current branch (`Bash(gh pr view:*)`). A non-zero exit / "no pull requests found" means there's no PR for this branch — proceed, no ask.
2. If a PR is found and `state == "OPEN"`: ask via `AskUserQuestion` — "An open PR already exists for this branch (#`<number>`: `<url>`). It's recommended to merge it before starting new work here." Options: **"I'll merge it first — stop here"** (halt the whole run cleanly; point at `Skill(git-kit:merge-pr)` to actually do the merge) / **"Continue anyway"** (proceed; the new work will land as additional commits on the same branch/PR rather than a fresh one).
3. If `state` is `MERGED` or `CLOSED`, that PR is no longer open — proceed, no ask.

Never skip this silently when an open PR is found — always ask; never hard-block with no escape hatch (matches every other gate in this plugin, which always leaves the human a way to proceed).

## Branch-Scope Check

**Purpose:** catch the case where real changes are about to be written while sitting on `main`/`master`, or on a branch whose name doesn't reflect what this run is about to do.

**Procedure:**
1. `git branch --show-current` (`Bash(git branch:*)`).
2. **Not scoped** if either is true: the name is `main` or `master`; or the name doesn't fit git-kit's `<type>/<description>` convention (see `commit`'s own "Branch Naming Convention" section for the canonical type list and kebab-case rule for `<description>` — don't restate or re-derive that list here, just apply it).
3. If not scoped: ask via `AskUserQuestion` — "Current branch `<name>` doesn't look scoped for this work. Create a new branch, or continue on `<name>` anyway?" Options: **"Create a new branch"** (invoke `Skill(git-kit:starting-work)` — do not reimplement its sync/name-validation/checkout logic here — then resume this run on the newly created branch) / **"Continue on `<name>` anyway"** (proceed as-is; this is a deliberate override, not an error).
4. If scoped (a non-main/master branch matching the convention): proceed, no ask.

This check only needs to run once per invocation, immediately before the first actual file write/commit that invocation will make — not before every phase or step that merely reads or drafts content in-memory.

## Why Two Separate Checks, Not One

The Open-PR check is about *timing relative to other work in flight* (is there already a PR waiting on this branch); the Branch-scope check is about *where new commits are about to land*. A branch can fail one without failing the other — e.g. a properly-named `fix/foo` branch can still have a stale open PR from a previous session, and `main` can have no open PR at all but still be the wrong place to commit new work. Keep them as two independent asks rather than collapsing them into one, so the failure reason presented to the user is always specific to what's actually wrong.
