# Does the canonical diff command include a brand-new, never-`git add`ed file's content?

**Short answer: Yes — but only because the skill's own Preflight process runs `git add -N` before
building the diff command, not because the "canonical diff command" would pick it up on its own.**
Left completely alone, a `??` untracked file produces *no* output from `git diff` in any form. The
skill's Inputs section explicitly builds in a step that neutralizes exactly this gap before the
canonical diff command is even assembled.

## Walkthrough of what the skill actually does

### 1. The skill states the raw problem explicitly

In the **Inputs** section (SKILL.md lines 80–87), the skill flags this exact scenario by name:

> "**Intent-add untracked files before diffing, or they never appear at all.** A brand-new file that
> was never `git add`ed shows up in `git status` as `??` but produces *no* output from `git diff` in
> any ref form, single or two-dot — Git only diffs tracked content. Verified empirically: an isolated
> untracked file yields nothing from `git diff "$MERGE_BASE" -- <file>` until `git add -N`
> (intent-to-add) records it in the index with an empty placeholder blob, after which the same diff
> command shows its full content as an addition."

So the skill's own documented finding is: without intervention, the answer would be **no**, the new
file's content would not appear, and the skill calls this out as a real failure mode — "an
all-untracked change set... reports 'nothing to review' despite genuinely having something to
review."

### 2. The skill's canonical-diff-construction code neutralizes that gap

The exact code block given for building the canonical diff (lines 89–96) is:

```bash
BASE="${BASE:-main}"
MERGE_BASE=$(git merge-base "$BASE" HEAD)
git add -N -- "${SCOPE:-.}"
DIFF=(git diff "$MERGE_BASE")
[ -n "$SCOPE" ] && DIFF+=(-- "$SCOPE")
DIFF_STR=$(printf '%q ' "${DIFF[@]}")   # shell-quoted rendering, for embedding in a prompt
```

Note the ordering: `git add -N -- "${SCOPE:-.}"` runs **before** `DIFF=(git diff "$MERGE_BASE")` is
even constructed. Since no `SCOPE` was given in this scenario, `${SCOPE:-.}` defaults to `.` — the
whole working tree — so the intent-to-add sweep covers the entire repo, including the one new file
in the described scenario (it would also intent-add any *other* untracked files if there were any,
though the scenario states there are none).

By the time `DIFF` is actually built and later run, the new file already has an index entry (an
empty placeholder blob, per the "Verified empirically" note above), so `git diff "$MERGE_BASE"` now
sees it as a genuine addition and includes its full content — the same mechanism the skill describes
in the quoted passage.

### 3. This same, already-intent-added state is reused everywhere else in the skill

Lines 98–101 state: "Every other diff invocation in this document (Preflight steps 2 and 6, and the
`CODEX_DIFF` variant) uses this same `$MERGE_BASE`, never a re-spelled `$BASE...HEAD` — and all of
them run *after* the `git add -N` above, so they all see intent-added untracked files too." So:

- **Preflight step 1** (line 115) runs `"${DIFF[@]}"` and checks its exit status — with the file
  already intent-added, this succeeds with non-empty stdout containing the new file's content (not
  the "nothing to review" case, since intent-to-add already happened).
- **Preflight step 2** (line 120) computes `git diff --name-only "$MERGE_BASE" [-- "$SCOPE"]` for
  `--target-paths` — the new file's path is included in this list too, again because of the earlier
  `git add -N`.
- **Preflight step 6** (lines 191–196) uses the unscoped `git diff --name-only "$MERGE_BASE"` list to
  check whether the diff touches Codex dispatcher scripts — this list also reflects the intent-added
  file.
- The `CODEX_DIFF`/`CODEX_DIFF_STR` variant (Preflight step 2, lines 137–148) is a filtered subset of
  the same eligible-files set, so it too would include the new file's content (assuming its path
  passes the `^[A-Za-z0-9._/-]+$` charset and existence checks in that step).

## What kind of git operation `git add -N` is, and whether it's safe/reversible

The skill is explicit about this, both up front in its safety framing (lines 29–36) and again inline
at the point of use (lines 82–84):

> "The one deliberate exception is `git add -N` (Inputs section, below): it mutates the Git **index**
> only — recording an untracked path with an empty placeholder blob so it appears in `git diff`
> output — never the working tree, never file content, never a commit. Trivially reversible (`git
> reset -- <path>`) and never touches anything this skill doesn't already read."

Breaking that down against the scenario:

- **What it does**: `git add -N -- <pathspec>` ("intent-to-add") is a git-index-only mutation. It
  registers the new file's path in the index with an **empty placeholder blob** — it does not copy
  the file's actual content into the index/object store the way a normal `git add` would. This is
  purely bookkeeping that lets `git diff` recognize the path as something to compare against, which
  is what makes the file's real content (read live from the working tree at diff time) show up as an
  addition in the diff output.
- **What it does *not* do**: it does not touch the working tree (the file on disk is untouched), it
  does not stage the file's actual content (unlike `git add <file>`), and it does not create a
  commit. `git status` after this operation would show the file transitioning from a plain `??`
  untracked entry to an intent-to-add entry, but the file has not been "really" staged in the
  git-add sense.
- **Safety/reversibility**: the skill asserts this is "trivially reversible" via `git reset --
  <path>`, which removes the index entry and returns the file to its original untracked (`??`)
  state, with the working tree file itself never modified at any point. Because the operation never
  writes file content anywhere (only an empty placeholder blob keyed to the path) and never commits,
  there is no risk of the new file's actual content persisting anywhere as a result of this
  operation — the only artifact is the index entry itself, which is exactly what makes it safe and
  cleanly reversible.

## Summary

- Literally interpreted as just `git diff <merge-base> [-- <scope>]`, the "canonical diff command" by
  itself would **not** show a `??` untracked file's content — the skill states this explicitly as an
  empirically verified gap (lines 80–87).
- The skill closes this gap procedurally: its Inputs-section code block that builds the canonical diff
  (lines 89–96) runs `git add -N -- "${SCOPE:-.}"` immediately before constructing `DIFF`, so by the
  time any diff command in the skill actually executes — Preflight steps 1, 2, 6, and the
  `CODEX_DIFF`/`CODEX_DIFF_STR` variant — the new file has already been intent-added and its content
  **does** appear as an addition.
- The git operation performed is `git add -N` (intent-to-add), an index-only mutation using an empty
  placeholder blob. Per the skill's own explicit statement (lines 29–36), it never touches the working
  tree, never stages real file content, never creates a commit, and is "trivially reversible" via
  `git reset -- <path>` — making it safe for a skill whose `Write` access is otherwise scoped to its
  own scratch directory and which is explicitly forbidden from other repository mutations.
