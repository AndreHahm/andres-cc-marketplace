# Does the canonical diff command include an unstaged edit when HEAD == BASE?

**Yes.** In this scenario — HEAD equal to BASE, with only an unstaged (uncommitted) edit on top —
the skill's canonical diff command *does* include that edit. This follows directly from how the
skill builds the diff command in the "Inputs" section of
`plugins/git-kit/skills/cross-model-review/SKILL.md`.

## How the canonical diff command is built

The "Inputs" section (lines 66–86) instructs that the canonical diff command must be built once in
Preflight and reused everywhere, as an argv array, using **the merge-base as a single ref**, never
the two-dot `$BASE...HEAD` form:

```bash
BASE="${BASE:-main}"
MERGE_BASE=$(git merge-base "$BASE" HEAD)
DIFF=(git diff "$MERGE_BASE")
[ -n "$SCOPE" ] && DIFF+=(-- "$SCOPE")
DIFF_STR=$(printf '%q ' "${DIFF[@]}")   # shell-quoted rendering, for embedding in a prompt
```

The skill is explicit about *why* it must be single-ref rather than two-dot:

> "**Use the merge-base as a single ref, not the two-dot `$BASE...HEAD` form** — `git diff A...B`
> only shows *committed* differences between the merge-base and `B`; it never includes staged or
> unstaged working-tree changes... A single-ref `git diff <merge-base>` includes the working tree
> (index and unstaged changes both) on top of the merge-base."

So the mechanism that makes the unstaged edit visible is the plain single-ref form
`git diff <MERGE_BASE>` (no second ref). Git's own semantics for `git diff <commit>` (one ref, no
`--cached`) compare the **working tree** — index and unstaged changes together — against that
commit. This is exactly the property the skill is deliberately relying on, and it says so directly:
using the two-dot form "would silently skip any uncommitted work-in-progress — including the common
case of reviewing before the first commit is even made," which is precisely the scenario in this
question (no committed divergence yet, just a pending edit).

## Applying it to HEAD == BASE

In the scenario described, `HEAD` and `BASE` point at the same commit (no committed divergence).
`MERGE_BASE=$(git merge-base "$BASE" HEAD)` therefore resolves to that same shared commit — when
two refs are identical (or one is an ancestor via being equal), `git merge-base` returns that
commit itself. So:

```bash
DIFF=(git diff "$MERGE_BASE")
```

becomes, concretely, `git diff <that-shared-commit>`. Because this is the single-ref form the
skill mandates, it compares the working tree (including the unstaged edit) against that commit,
not commit-to-commit. The unstaged edit therefore shows up in `"${DIFF[@]}"`'s output.

This also lines up with Preflight step 1 (lines 100–104), which treats a successful-but-empty diff
as "nothing to review," and would *not* be triggered here — the diff is non-empty precisely because
the unstaged edit is picked up by the working-tree comparison, even though HEAD and BASE are
otherwise identical.

## Corroborating detail: every other diff invocation reuses the same `$MERGE_BASE`

The skill is explicit that this isn't a one-off: "Every other diff invocation in this document
(Preflight steps 2 and 6, and the `CODEX_DIFF` variant) uses this same `$MERGE_BASE`, never a
re-spelled `$BASE...HEAD`" (Inputs section, lines 85–86). So the same working-tree-inclusive
behavior propagates consistently to:

- **Preflight step 2** (`git diff --name-only "$MERGE_BASE" [-- "$SCOPE"]`, line 105) — the
  changed-file list used for `--target-paths` would also include the unstaged edit's file.
- **Preflight step 6** (line 171) — the unscoped changed-file check for whether the diff touches
  Codex dispatcher scripts also runs off `git diff --name-only "$MERGE_BASE"`, so it too would see
  an unstaged edit to a dispatcher script.
- **The `CODEX_DIFF` variant** (Preflight step 2, lines 118–119) — built as
  `git diff "$MERGE_BASE" -- <eligible files only>`, same single-ref base, so Codex's own review
  text also includes the unstaged edit (for eligible files).

## Answer summary

Yes — the canonical diff command includes the unstaged edit. Because `MERGE_BASE` collapses to the
shared HEAD/BASE commit in this scenario, `git diff "$MERGE_BASE"` reduces to a single-ref
`git diff <commit>` against the working tree, which by Git's own semantics (and by the skill's
explicit, stated design intent) picks up both staged and unstaged changes — there is no committed
divergence needed for the edit to appear. This is not an incidental side effect; the skill's
"Inputs" section explicitly designed the single-ref form for exactly this purpose, calling out "the
common case of reviewing before the first commit is even made" as a scenario the two-dot form would
have wrongly excluded.
