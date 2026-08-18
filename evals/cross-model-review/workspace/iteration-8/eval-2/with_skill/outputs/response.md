# Does Preflight step 2's symlink-containment check correctly exclude `/path/repo-sibling/file.txt`?

**Yes — the skill correctly excludes it as outside the repository.** The check is specified in a way
that is immune to the bare-string-prefix bug the question describes; in fact, the skill's own text uses
almost this exact scenario as its worked example of the bug it is deliberately avoiding.

## The exact comparison logic specified

From `SKILL.md`, Preflight step 2, the "Also exclude a path that's a symlink resolving outside the
repository" paragraph (lines 137–151):

> `realpath -- <path>` each candidate and compare against `$(git rev-parse --show-toplevel)` ...
> **Require an exact match or a path-separator boundary right after it — never a bare string-prefix
> test.** A plain `starts with` check would wrongly accept `/repo-sibling/file` as "inside" `/repo`,
> since the string `/repo-sibling` lexically starts with `/repo` even though it's a sibling directory,
> not a descendant — the same class of bug `codex-review-bridge`'s own `isWithin()` helper already
> guards against for exactly this reason. **Exclude the candidate unless it equals the repo root
> exactly or starts with `<repo root>/`** (trailing separator included in the comparison).

So the specified algorithm, applied per candidate changed-file path, is:

1. Resolve the candidate's real target with `realpath -- <path>`.
2. Resolve the repo root with `git rev-parse --show-toplevel` (re-run inline at this point in the
   document, since `$REPO_ROOT` as a named variable isn't assigned until step 4 — the skill explicitly
   calls this out: "this step runs before step 4 resolves `$REPO_ROOT` as a named variable — re-run the
   same command inline here rather than depending on a not-yet-assigned value").
3. Accept (treat as inside the repo) **only** if the resolved target:
   - equals the repo root string exactly, **or**
   - starts with `<repo root>` **followed immediately by a path separator** (i.e., the literal prefix
     tested is `<repo root>/`, trailing slash included).
4. Otherwise, exclude the candidate as outside the repository, and note it in the final report as an
   inspection limit (per the general step-2 exclusion-reporting rule that applies to any excluded
   changed path).

This is explicitly **not** a bare `starts_with(target, repo_root)` test — the skill calls that out by
name as the wrong implementation and requires the separator-boundary variant instead.

## Applying it to the given example

- Repo root: `/path/repo`
- Candidate symlink target (after `realpath`): `/path/repo-sibling/file.txt`

Bare string-prefix test (what the skill says NOT to do):
`"/path/repo-sibling/file.txt".startswith("/path/repo")` → `True` — this is the incorrect check the
skill is warning against, and it would wrongly accept the path as inside the repo.

Skill-specified test (exact match OR `<repo root>/` prefix):
- Exact match: `/path/repo-sibling/file.txt` == `/path/repo` → false.
- Separator-bounded prefix: does `/path/repo-sibling/file.txt` start with `/path/repo/` (note the
  trailing `/`)? The character immediately following `/path/repo` in the candidate is `-` (from
  `repo-sibling`), not `/`. So it does **not** start with `/path/repo/`.

Both conditions fail, so under the skill's specified logic the candidate is **excluded** — correctly
treated as outside the repository, exactly as intended, and exactly matching the failure mode the skill
names verbatim (`/repo-sibling/file` vs. `/repo`) as the reason the check must use a separator boundary
rather than a raw prefix test.

## What happens once it's excluded

Per the rest of step 2, once this symlink candidate is excluded from containment:

- It is removed from the `--target-paths` list built for Codex's dispatch (both `codex-review-bridge`
  and `codex-windows-guardrails` canonicalize target paths and reject the *entire dispatch* on one
  containment-violating entry — a `non_zero_exit`/containment-violation typed failure — so excluding it
  up front avoids forcing an unnecessary single-model fallback for the whole review over just this one
  symlink).
- It is still kept in **Claude's own native review** regardless ("Claude has no such containment
  constraint; only the Codex-facing `--target-paths` list is affected").
- If this exclusion (combined with any other step-2 exclusions) leaves the Codex-eligible file list
  empty, the skill directs skipping Codex entirely and entering single-model mode before any dispatch
  attempt, recording the `inspection_limits` reason as "zero Codex-eligible paths in this diff" rather
  than "Codex unavailable."
- The excluded path also affects the Codex-scoped diff text (`CODEX_DIFF_STR`), which is built from
  eligible paths only, separately from the full `$DIFF_STR` used in Claude's native pass — so the
  symlink's target content is not embedded into Codex's instruction files either.

## Bottom line

The skill's Preflight step 2 symlink-containment check does **not** fall for the string-prefix trap
described in the question. It specifies an exact-match-or-separator-boundary comparison
(`<repo root>` exactly, or `<repo root>/` as a literal prefix) precisely to reject sibling-directory
paths like `/path/repo-sibling/file.txt` that merely share a lexical prefix with `/path/repo` without
actually being inside it. Applying that logic to the given inputs correctly excludes the symlink as
outside the repository.
