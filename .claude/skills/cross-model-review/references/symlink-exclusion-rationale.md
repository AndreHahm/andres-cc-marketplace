# Symlink exclusion: why not a bare string-prefix test

Extracted from SKILL.md's Preflight step 2 per plugin-rulebook's R13 (SKILL.md grew past the 500-line
Critical threshold). SKILL.md keeps the actual requirement (exact match or path-separator boundary,
never a bare string-prefix test); this file holds the fuller rationale.

A plain `starts with` check would wrongly accept `/repo-sibling/file` as "inside" `/repo`, since the
string `/repo-sibling` lexically starts with `/repo` even though it's a sibling directory, not a
descendant — the same class of bug `codex-review-bridge`'s own `isWithin()` helper already guards
against for exactly this reason. Exclude the candidate unless it equals the repo root exactly or
starts with `<repo root>/` (trailing separator included). Both dispatch scripts canonicalize target
paths before their own containment check; per issues #236/#111 that check now only drops the one
finding/citation the symlink ends up cited in rather than rejecting the entire dispatch, but
excluding it here in Preflight is still preferred — it stops the symlink's content from reaching
Codex at all, not just its citation from surviving semantic validation afterward.

## Why `$UNTRACKED_FILES` needs the same treatment

`$UNTRACKED_FILES` is a separate list (`git ls-files --others`, computed in the Inputs section) —
it never goes through this step's own changed-file computation above, so nothing else filters it.
Phase 1 and Phase 2 both append it verbatim to Codex's instructions, telling Codex to read each path
directly (see the Inputs section's own note on why). An untracked path that's a symlink resolving
outside the repository would otherwise be named there unfiltered — and since the confirmation already
states `--target-paths` doesn't constrain what a dispatched process can *read*, following that
instruction could send content from outside the consented repository to Codex, on top of any
resulting citation being dropped by semantic validation (per issues #236/#111, just that finding —
not the whole envelope — but the read-boundary leak itself already happened by that point).
