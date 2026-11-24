# Why the diff-construction mechanics work the way they do

Extracted from SKILL.md's Inputs section per plugin-rulebook's R13 (SKILL.md grew past the 500-line
Critical threshold). SKILL.md keeps the actual commands and the one-line pointers to each rationale
below; this file holds the fuller explanations.

## Why untracked files must be intent-added before diffing

A brand-new file that was never `git add`ed shows up in `git status` as `??` but produces *no* output
from `git diff` in any ref form, single or two-dot — Git only diffs tracked content. Verified
empirically: an isolated untracked file yields nothing from `git diff "$MERGE_BASE" -- <file>` until
`git add -N` (intent-to-add) records it in the index with an empty placeholder blob, after which the
same diff command shows its full content as an addition. Without this, an all-untracked change set
(the common case right after `git init` or creating a wholly new file) reports "nothing to review"
despite genuinely having something to review.

## Why a deletion-only `$SCOPE` passes while any other intent-add failure stops the review

A deletion-only `$SCOPE` pathspec matches nothing on disk, so `git add -N` fails outright against it,
although `git diff "$MERGE_BASE" -- "$SCOPE"` shows the deletion correctly on its own. The helper
therefore lists the untracked files first and exits 0 when there are none to add.

Every other failure exits 2, git's own included (issue #697: an index lock made `git add` exit 128, which
the chain then took for the deletion case). The chain treats any non-zero exit, a missing helper's 127
too, as a refusal: no untracked file can be trusted to have reached the diff.
That sets `$INTENT_ADD_REFUSED=1` (issue #637: a refusal here used to vanish behind a bare `|| true`).
The chain still continues so its closing `echo` runs, then Preflight step 1 stops the review: the diff
can't be trusted. A refused run directory is refused by the index helper too, so the throwaway index
stays empty and every tracked file reads as deleted. A refusal by this helper alone leaves untracked
files out, and an untracked-only change then gives an empty diff that looks like nothing to review.

## Why `$UNTRACKED_FILES` matters beyond the Preflight chain

Codex never runs `git diff` itself at all — Phase 1 and Phase 2 both embed diff content directly into
Codex's instruction file instead (a Codex-run diff of a large change failed every time on a real
Windows machine while the embedded diff succeeded, issue #78). The diff
they embed is the batch's `.codex.diff` files, not Claude's `.diff` files — scoped to eligible paths
only (Preflight step 2).
Once an untracked file is intent-added, `git diff` shows its **full real content** as an addition, not
an empty placeholder (verified empirically: intent-adding a two-line untracked file and diffing it
shows both lines, not a contentless add) — so an untracked file inside `$SCOPE` normally already
appears in full in whatever diff includes it.

Phase 1 and Phase 2 still name the batch's untracked files in an `<untracked_files>` block, because Codex's
own subprocess never sees intent-added files in the index. Since issue #697 the block holds only eligible
paths: a file dropped from `$TARGET_PATHS` (odd characters, a symlink, a sensitive name) is never listed
as untracked either, and stays in Claude's own review only.

## Why the canonical diff uses the merge-base as a single ref

`git diff A...B` only shows *committed* differences between the merge-base and `B`; it never includes
staged or unstaged working-tree changes. Since this skill reviews "the current diff" / "the local working
diff", the `$BASE...HEAD` form would silently skip any uncommitted work-in-progress, including the common
case of reviewing before the first commit is even made. A single-ref `git diff <merge-base>` includes the
working tree (index and unstaged changes both) on top of the merge-base.

## Why the chain drops PATH entries inside the checkout

The chain and the helpers run `git`, `bash`, `python3` and others by name. An absolute PATH entry inside the
repository under review (an activated virtualenv, direnv) would let the repository supply one of them, before
the `PLANNER_TOUCHED` question. Refusing such a PATH would stop every session with an active `.venv`, so the
entries are dropped instead, with built-ins only. The lines are the same as `git-review-path.sh`, which the
shell helpers source first; a test compares the two. The chain still stops on an empty or relative entry.
An entry counts as inside when it is spelled inside (also with a `..` that leads out again) or resolves
inside, so an entry spelled inside that is a link leading out is dropped too. A chain of links that only passes
through the checkout, from an entry outside to a target outside, is not followed. Another worktree of the
repository, the main checkout included, counts as inside: the folder's own `.git` must name the same common git
directory, so a worktree whose `.git` is gone or altered is not recognized. A checkout at `/` is not recognized either. Not caught: an entry outside the
repository that holds a link to a program inside it. If nothing is left, the chain stops: an empty PATH would make the shell look in the current
directory. `builtin` keeps a user's own `cd` function out of it. Each Bash call is a fresh shell, hence the
`export PATH` statement on later calls. An entry that could not be entered is dropped for the chain only, unless
it is spelled inside the checkout.
