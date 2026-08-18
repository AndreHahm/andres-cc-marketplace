# Symlink exclusion: why not a bare string-prefix test

Extracted from SKILL.md's Preflight step 2 per plugin-rulebook's R13 (SKILL.md grew past the 500-line
Critical threshold). SKILL.md keeps the actual requirement (exact match or path-separator boundary,
never a bare string-prefix test); this file holds the fuller rationale.

A plain `starts with` check would wrongly accept `/repo-sibling/file` as "inside" `/repo`, since the
string `/repo-sibling` lexically starts with `/repo` even though it's a sibling directory, not a
descendant — the same class of bug `codex-review-bridge`'s own `isWithin()` helper already guards
against for exactly this reason. Exclude the candidate unless it equals the repo root exactly or
starts with `<repo root>/` (trailing separator included). Both dispatch scripts canonicalize target
paths before their own containment check and reject the *entire dispatch* on one such entry, forcing
an unnecessary single-model fallback over one symlink.
