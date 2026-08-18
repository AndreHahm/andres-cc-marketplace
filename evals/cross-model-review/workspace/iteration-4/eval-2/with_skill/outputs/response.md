# Does the frontmatter's `allowed-tools` cover Preflight's chained Bash invocation?

**Short answer: yes.** Every external command that Preflight steps 1-6 (plus the closing `echo`) actually
invoke is covered by an explicit `Bash(<cmd>:*)` entry in the frontmatter. No gap requiring an extra
permission prompt.

## What Preflight requires as a single chained call

The Preflight section opens with an explicit structural requirement (SKILL.md lines 82-88):

> "Bash tool calls do not share shell state with each other — only the working directory persists
> between them. Run steps 1-6 below as a single chained Bash invocation (`&&` between them, one tool
> call), ending with an `echo` of the resolved `BASE`, `REPO_ROOT`, `RUN`, `DIFF_STR`, and
> `CODEX_DIFF_STR` values."

So the question is: within *that one Bash tool call*, what external programs get invoked, and is each
one declared in:

```
allowed-tools: ["Bash(git diff:*)", "Bash(git show:*)", "Bash(git rev-parse:*)", "Bash(mktemp:*)",
"Bash(date:*)", "Bash(export:*)", "Bash(printf:*)", "Bash(grep:*)", "Bash(echo:*)",
"Bash(node plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs:*)",
"Bash(node plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs:*)",
"Read", "Write", "Grep", "Glob", "AskUserQuestion"]
```
(SKILL.md line 14)

## Walking through steps 1-6

**Step 1** (lines 90-94): runs `"${DIFF[@]}"`, which expands to `git diff "$BASE...HEAD"` (built in the
Inputs section, lines 70-75, which the skill explicitly says to "build ... once in preflight" — so this
expansion happens inside the same chained call). This also needs `DIFF_STR=$(printf '%q ' "${DIFF[@]}")`
(Inputs section, line 74) since the closing `echo` must print `DIFF_STR`.
→ requires **`git diff`** and **`printf`**.

**Step 2** (lines 95-113): computes the changed-file list via `git diff --name-only "$BASE...HEAD" [--
"$SCOPE"]` (line 95), and — when any path was excluded — builds `CODEX_DIFF=(git diff "$BASE...HEAD" --
<eligible files>)` and `CODEX_DIFF_STR=$(printf '%q ' "${CODEX_DIFF[@]}")` (lines 108-109), which the
closing echo also needs.
→ requires **`git diff`** (again, different flags — still matches the same prefix) and **`printf`**.

**Step 3** (line 114): `RUN=$(mktemp -d)`.
→ requires **`mktemp`**.

**Step 4** (line 117): resolves `REPO_ROOT` via `git rev-parse --show-toplevel`.
→ requires **`git rev-parse`**.

**Step 5** (lines 118-138): materializes trusted instructions with
```
git show "$BASE:plugins/git-kit/skills/cross-model-review/prompts/review.md" > "$RUN/review.md" 2>/dev/null
git show "$BASE:plugins/git-kit/skills/cross-model-review/prompts/refute.md" > "$RUN/refute.md" 2>/dev/null
```
(lines 123-126).
→ requires **`git show`**. (The `>`/`2>/dev/null` redirection is shell syntax attached to that same `git
show` invocation, not a separately-permissioned action — it doesn't go through the `Write` tool.)

**Step 6** (lines 139-155): "grep for `plugins/codex-kit/(.*/)?scripts/` against the **unscoped** changed-
file list (`git diff --name-only "$BASE...HEAD"` ...)" — the step names `grep` explicitly as the
mechanism.
→ requires **`git diff`** (again) and **`grep`**.

**Closing echo** (line 84, "ending with an `echo` of the resolved ... values"):
→ requires **`echo`**.

## Cross-check against the declared list

| Command needed by Preflight 1-6 | Declared in `allowed-tools`? |
|---|---|
| `git diff` (steps 1, 2, 6) | Yes — `Bash(git diff:*)` |
| `git show` (step 5) | Yes — `Bash(git show:*)` |
| `git rev-parse` (step 4) | Yes — `Bash(git rev-parse:*)` |
| `mktemp` (step 3) | Yes — `Bash(mktemp:*)` |
| `printf` (steps 1, 2, for `DIFF_STR`/`CODEX_DIFF_STR`) | Yes — `Bash(printf:*)` |
| `grep` (step 6) | Yes — `Bash(grep:*)` |
| `echo` (closing line) | Yes — `Bash(echo:*)` |

All seven are present with `:*` wildcards, so any flags/arguments used (`--show-toplevel`, `--name-only`,
`-d`, `'%q '`, etc.) are covered by the prefix match, not just a bare invocation of the command with no
arguments.

Two entries in the list are **not** needed by Preflight but are declared anyway, because they're used
later in the skill, outside the Preflight chain:
- **`Bash(date:*)`** — used in Phase 1/2 to build `--dispatch-id "cross-model-review-$(date
  +%s)-fresh-eyes-codex"` (line 240) and the challenger dispatch-id (line 298). Not referenced anywhere in
  Preflight steps 1-6.
- **`Bash(export:*)`** — used in the "Codex dispatch resolver" section's Step 1 code block, `export
  CODEX_KIT_REVIEW_REPO_ROOT="$REPO_ROOT"` (line 166), which runs at dispatch time in Phase 1/2, not
  inside Preflight's own chained call.

The two `node ...` entries are likewise for the Phase 1/2 Codex dispatch calls (`bridge-invoke.mjs` /
`guarded-dispatch.mjs`), not for anything Preflight itself runs.

Having these extra grants present doesn't hurt Preflight's completeness — it just means the frontmatter
was scoped to the whole skill's lifecycle, not narrowly to Preflight alone. The question was specifically
whether Preflight's own needs are met, and they are.

## Caveats worth naming explicitly

1. **Shell syntax vs. invoked commands.** Preflight's chain also uses plain shell constructs — variable
   assignment (`BASE="${BASE:-main}"`), array building (`DIFF=(git diff ...)`, `DIFF+=(-- "$SCOPE")`),
   the `[ -n "$SCOPE" ]` test, command substitution (`$(...)`), `&&` chaining, and I/O redirection (`>`,
   `2>/dev/null`). None of these are separately-named external programs the way `git diff` or `mktemp`
   are, so they don't need their own `Bash(...)` allow-list entry under Claude Code's permission model —
   only the actual invoked commands are matched against the allow-list patterns. If this assumption were
   wrong (i.e., if bare shell builtins/tests also required individual grants), essentially no
   multi-step chained Bash workflow in any skill could run without prompting, which would make the
   skill's own explicit "run as a single chained invocation" instruction (line 83) unworkable by design —
   so it's reasonable to treat builtins/control-flow as not gated.
2. **How compound commands get permission-matched.** The frontmatter's patterns are per-command prefixes
   (e.g. `Bash(git diff:*)`). Preflight's actual tool call is one long `cmd1 && cmd2 && ... && echo ...`
   string. This answer assumes Claude Code's Bash permission check decomposes a `&&`-joined compound
   command into its individual subcommands and checks each one's prefix independently (the documented
   behavior that prevents bypassing an allow-list via chaining, e.g. `git diff && rm -rf /` shouldn't
   pass just because `git diff` is allowed). Under that model, every subcommand in Preflight's chain
   individually matches a declared prefix, so the whole chain passes cleanly. If instead the checker only
   matched the *literal head* of the entire compound string, no chained multi-command skill would ever
   pass without a prompt — a strictly worse and effectively unworkable model — so the per-subcommand
   interpretation is the correct one to assume here.

## Conclusion

Preflight steps 1-6, run as the single chained Bash invocation the skill mandates, need exactly seven
external commands: `git diff`, `git show`, `git rev-parse`, `mktemp`, `printf`, `grep`, and `echo`. All
seven are explicitly declared in the frontmatter's `allowed-tools` with unrestricted `:*` argument
wildcards (SKILL.md line 14). Nothing in Preflight's own chain touches the `node ...` dispatcher entries,
`date`, or `export` — those are declared for later phases (the Codex dispatch resolver and Phase 1/2),
not because Preflight needs them. So yes: the frontmatter grants everything Preflight's chained
invocation requires, and it should complete without triggering an additional permission prompt.
