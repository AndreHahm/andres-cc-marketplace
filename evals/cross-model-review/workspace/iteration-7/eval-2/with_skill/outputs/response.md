# cross-model-review — `allowed-tools` Bash subcommand audit

Source read: `plugins/git-kit/skills/cross-model-review/SKILL.md` (frontmatter line 14).

## 1. Every Bash subcommand the frontmatter grants

The frontmatter `allowed-tools` array (SKILL.md line 14) is:

```
allowed-tools: ["Bash(git diff:*)", "Bash(git show:*)", "Bash(git rev-parse:*)", "Bash(git merge-base:*)", "Bash(git add:*)", "Bash(mktemp:*)", "Bash(date:*)", "Bash(export:*)", "Bash(printf:*)", "Bash(grep:*)", "Bash(echo:*)", "Bash(realpath:*)", "Bash(node plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs:*)", "Bash(node plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs:*)", "Read", "Write", "Grep", "Glob", "AskUserQuestion"]
```

Pulling out just the `Bash(...)` entries, the granted Bash subcommands (14 total) are:

1. `git diff`
2. `git show`
3. `git rev-parse`
4. `git merge-base`
5. `git add`
6. `mktemp`
7. `date`
8. `export`
9. `printf`
10. `grep`
11. `echo`
12. `realpath`
13. `node plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs` (a specific script invocation, not a bare command)
14. `node plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs` (likewise, a specific script invocation)

(The remaining five entries — `Read`, `Write`, `Grep`, `Glob`, `AskUserQuestion` — are not Bash subcommands at all; they're separate top-level tool grants, listed for completeness but out of scope for "Bash subcommand.")

## 2. `git merge-base` — usage vs. grant

**Usage in body:** Inputs section, in the canonical-diff code block:

```bash
BASE="${BASE:-main}"
MERGE_BASE=$(git merge-base "$BASE" HEAD)
```

(SKILL.md line 91). This resolves `$MERGE_BASE`, which the skill explicitly says (lines 70–78, 99–101) must be reused as the single ref for every later diff invocation instead of the two-dot `$BASE...HEAD` form, "so they all see intent-added untracked files too."

**Grant match:** `Bash(git merge-base:*)` is present in the frontmatter list (item 4 above). **Match confirmed** — the invocation `git merge-base "$BASE" HEAD` falls under the `git merge-base:*` wildcard grant.

## 3. `git add` — usage vs. grant

**Usage in body:** Same Inputs-section code block, immediately after computing `$MERGE_BASE`:

```bash
git add -N -- "${SCOPE:-.}"
```

(SKILL.md line 92). This is the "intent-to-add" call the skill describes at length just above (lines 80–87): a brand-new untracked file never shows up in `git diff` output at all until it's recorded in the index via `git add -N`, so this call is what makes an all-untracked change set reviewable.

This same call is also called out explicitly in the frontmatter's own preamble (lines 29–36) as "the one deliberate exception" to the skill's otherwise no-repo-writes posture: `git add -N` "mutates the Git **index** only... never the working tree, never file content, never a commit," and is described as "trivially reversible (`git reset -- <path>`)."

**Grant match:** `Bash(git add:*)` is present in the frontmatter list (item 5 above). **Match confirmed** — `git add -N -- "${SCOPE:-.}"` falls under the `git add:*` wildcard grant.

**Aside (not asked, but relevant context):** that same sentence mentions `git reset -- <path>` as the reversal mechanism for `git add -N` — but `git reset` does **not** appear anywhere in the `allowed-tools` grant list. It's mentioned only as descriptive text about the operation's reversibility, not as a command the skill body actually invokes anywhere in a runnable step, so this isn't a missing-grant bug, just worth flagging since it sits right next to the `git add` discussion.

## 4. `realpath` — usage vs. grant

**Usage in body:** Preflight step 2, in the symlink-containment check:

```
**Also exclude a path that's a symlink resolving outside the repository.** `realpath -- <path>`
each candidate; if the result doesn't start with `$(git rev-parse --show-toplevel)` ...
```

(SKILL.md lines 127–130). This runs `realpath -- <path>` on each candidate changed-file path to canonicalize it, so the skill can detect and exclude a symlink that resolves outside the repository root before adding that path to `--target-paths` for the Codex dispatch — mirroring the same containment check the dispatch scripts themselves perform.

**Grant match:** `Bash(realpath:*)` is present in the frontmatter list (item 12 above). **Match confirmed** — `realpath -- <path>` falls under the `realpath:*` wildcard grant.

## Summary table

| Command | Body location | Frontmatter grant | Matches? |
|---|---|---|---|
| `git merge-base` | Inputs section code block, line 91 (`MERGE_BASE=$(git merge-base "$BASE" HEAD)`) | `Bash(git merge-base:*)` | Yes |
| `git add` | Inputs section code block, line 92 (`git add -N -- "${SCOPE:-.}"`); also referenced in frontmatter preamble lines 29–36 | `Bash(git add:*)` | Yes |
| `realpath` | Preflight step 2, lines 127–130 (`realpath -- <path>` for symlink-containment check) | `Bash(realpath:*)` | Yes |

All three commands in question — `git merge-base`, `git add`, and `realpath` — are used exactly as described in the skill body, and each has a corresponding wildcard grant (`Bash(git merge-base:*)`, `Bash(git add:*)`, `Bash(realpath:*)`) in the frontmatter's `allowed-tools` list (SKILL.md line 14). No mismatch found for any of the three.
