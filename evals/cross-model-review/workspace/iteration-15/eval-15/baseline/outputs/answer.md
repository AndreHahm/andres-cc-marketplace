# Re-running the planner after a folder pick, then cross-checking the new manifest (describe-only)

Source: the provided copy of `plugins/git-kit/skills/cross-model-review/` (SKILL.md, `references/scoped-review.md` sections 1-2, `references/codex-pass-assembly.md`). Nothing was run.

## What this copy says about how the calls are issued

**Each call is a fresh shell.** SKILL.md's Preflight says Bash tool calls share no shell state, so
after Preflight every `$VAR` stands for the literal value Preflight printed. `RUN` is therefore typed
as `/tmp/tmp.abc`, never as `$RUN`. The same goes for `MERGE_BASE`, `BASE` and `SCOPE`.

**Call 1: re-run the planner (scoped-review.md section 2).** It is one Bash call that starts with the
throwaway-index export, then runs the fixed-shape wrapper with tag `1b` and one `--exclude-dir` for the
picked folder:

```bash
export GIT_INDEX_FILE="/tmp/tmp.abc/index"
bash "${CLAUDE_PLUGIN_ROOT:-.claude}/scripts/git-review-scope-run.sh" "/tmp/tmp.abc" 1b "<literal MERGE_BASE>" "<literal BASE>" [--scope "<literal SCOPE>"] --exclude-dir "<picked-folder>/" || PLAN_FAILED=1
```

- Before the folder label is typed, it must match `^[A-Za-z0-9_][A-Za-z0-9._-]*/$`, and it must come from
  the manifest's `candidate_dirs`. The manifest is data.
- The output goes to new paths, `/tmp/tmp.abc/manifest-1b.json` and `/tmp/tmp.abc/diffs-1b`. The
  wrapper refuses an output path that already exists, so tag-1 files are never overwritten.
- The wrapper must run from the work tree root, because the repository is its current directory. In an
  EnterWorktree session the persistent cwd is the worktree root, so that holds. From a subdirectory the
  wrapper exits 2, which gives `PLAN_FAILED`.
- The `PLANNER_TOUCHED` check from section 1 still applies to this round.

**Call 2: the cross-check (section 1, run against the new manifest).** It is also one Bash call that
starts with the same export:

```bash
export GIT_INDEX_FILE="/tmp/tmp.abc/index"
git diff --no-renames --name-only "<literal MERGE_BASE>" [-- "<literal SCOPE>"] > "/tmp/tmp.abc/changed.names"
```

Then `Read` `/tmp/tmp.abc/changed.names` and `/tmp/tmp.abc/manifest-1b.json`. Every changed path must
appear in `files`, in `excluded` (the picked folder's files now land here) or in `dropped_slices`. For
every non-deleted `files` entry, `Grep` its slice's `/tmp/tmp.abc/diffs-1b/<slice>.diff` for the
`diff --git` line. If a path is in none of those lists, or a listed file has an empty section, treat it
as `PLAN_FAILED`.

## Why the export matters for the untracked file

Preflight made the new file visible to `git diff` by intent-adding it (`git add -N`, through
`git-review-intent-add.sh`). That change exists only in the throwaway index `/tmp/tmp.abc/index`, never
in the real `.git/index`. The throwaway index is used on purpose, so the review does not leave a
persistent `git add -N` behind that a later `git commit -a` would pick up.

- **Without the export in the planner call**, git falls back to the real index. The untracked file is
  then not intent-added, so the planner never sees it. The file is missing from `manifest-1b.json` and
  from every slice diff, and neither model reviews it. Section 1 says the planner "must run in the call
  that exports `GIT_INDEX_FILE`, so intent-added untracked files are seen."
- **Without the export in the cross-check call**, `changed.names` also leaves the file out, because
  section 1 says that otherwise "intent-added untracked files are missing from the list." The
  cross-check then compares two lists that are both missing the file and passes, so the gap goes
  undetected. Putting the export in both calls gives a list that names the file, and the check can then
  catch a manifest that dropped it.
- The value must be the literal path. A bare `$RUN` would expand to empty in the fresh shell and point
  `GIT_INDEX_FILE` at `/index`, which is wrong.

## What happens if that form is refused

What this copy says:
- The `export GIT_INDEX_FILE=...` line deliberately has no grant ("a grant cannot pin the value they
  set"), so it raises a permission prompt every time. In this repository's own sessions,
  `CLAUDE_PLUGIN_ROOT` is empty and the `:-.claude` mirror wrapper is deliberately ungranted, so it
  prompts too. `git diff` is also ungranted, because `--output` writes a file. The skill tells you to
  approve each run once and not add a persistent allow rule.
- If the planner re-run fails or does not run, set `PLAN_FAILED=1`, which never counts as a pass. Ask via
  `AskUserQuestion` whether to review the whole diff unscoped (section 7) or stop, and record "review
  scope planner unavailable" if unscoped is chosen. A cross-check failure is handled the same way. The
  unscoped fallback's own `changed.names` step still needs the `export GIT_INDEX_FILE` prefix.
- Never drop the export to get past a refusal. Never fall back to a different command shape, such as
  running the planner without the export, typing manifest paths into a `git diff`, or using the real
  index. Any of these silently loses the untracked file. The same stance appears in the write helper's
  rule ("a refusal is a failed write: stop and report it, never fall back to another way").
  `.claude/rules/resolve-plugin-root-to-claude-mirror.md` says the same about a substituted command that
  is still denied: stop and report.

**Gap in this copy:** it has no guidance specific to EnterWorktree. It does not say whether a
scratchpad-script form of Preflight, or the separate `export` line, is refused after EnterWorktree, and
it gives no alternative form, such as an inline `GIT_INDEX_FILE=... command` prefix or a scratchpad
script for these two calls. From this copy alone, the only supported answer is the one above: issue the
calls with the leading `export GIT_INDEX_FILE="/tmp/tmp.abc/index"`. If that is refused, treat it as
`PLAN_FAILED` (stop, or go unscoped with the user's consent) and report the refusal. Do not improvise a
workaround the skill does not document.
