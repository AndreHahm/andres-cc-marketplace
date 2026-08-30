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

## Why `|| true` on `git add -N` matters for a deletion-only `$SCOPE`

A deletion-only `$SCOPE` pathspec needs a disk match, so `git add -N` fails outright against it — and,
untolerated, that failure aborts the whole `&&`-chained Preflight sequence before any later step runs.
`git diff "$MERGE_BASE" -- "$SCOPE"` still shows the deletion correctly on its own; `git add -N`'s
failure here is expected and harmless, not a sign anything is actually wrong.

## Why `$UNTRACKED_FILES` matters beyond the Preflight chain

Codex never runs `git diff` itself at all — Phase 1 and Phase 2 both embed diff content directly into
Codex's instruction file instead (see `references/embed-diff-not-run-rationale.md` for why). The diff
they embed is `$CODEX_DIFF_STR`, not `$DIFF_STR` — scoped to eligible paths only (Preflight step 2).
Once an untracked file is intent-added, `git diff` shows its **full real content** as an addition, not
an empty placeholder (verified empirically: intent-adding a two-line untracked file and diffing it
shows both lines, not a contentless add) — so an untracked file inside `$SCOPE` normally already
appears in full in whatever diff includes it.

The gap is narrower than "Codex can't see untracked files at all": an untracked path can still be
present in `$UNTRACKED_FILES` while being *excluded* from `$TARGET_PATHS`/the eligible-files list that
`$CODEX_DIFF_STR` is scoped to — the invalid-character check and the no-longer-exists check (Preflight
step 2) only reassign `$TARGET_PATHS`, not `$UNTRACKED_FILES`; only the symlink-outside-repo check
(also step 2) reassigns both. An untracked file dropped from `$TARGET_PATHS` for either of those two
reasons stays fully visible in Claude's own native `$DIFF_STR` but never appears in `$CODEX_DIFF_STR` at
all. If `$UNTRACKED_FILES` is non-empty, Phase 1 and Phase 2 both additionally append it explicitly to
Codex's instructions (see each phase's Codex-facing assembly step) so Codex reads those files directly
via a read-only file tool, covering exactly this gap rather than a general "Codex can't see untracked
files" claim.
