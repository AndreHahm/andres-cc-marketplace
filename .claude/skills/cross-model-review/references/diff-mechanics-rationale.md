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

Codex's own dispatch can't see intent-added files. Phase 1 and Phase 2 both tell Codex to re-run the
diff command itself conceptually, but Codex's own subprocess never inherits this skill's env-scoped
`GIT_INDEX_FILE` — so from Codex's perspective, an intent-added untracked path is still bare `??`,
invisible to its own `git diff`. If `$UNTRACKED_FILES` is non-empty, Phase 1 and Phase 2 both append
it explicitly to Codex's instructions (see each phase's Codex-facing assembly step) so Codex reads
those files directly via a read-only file tool instead of silently missing them.
