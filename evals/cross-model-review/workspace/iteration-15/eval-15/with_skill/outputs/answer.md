# Planner re-run and manifest cross-check in an EnterWorktree session (describe-only)

Sources: `SKILL.md` (Inputs, Preflight), `references/codex-pass-assembly.md` ("In an EnterWorktree
session"), and `references/scoped-review.md` (sections 1 and 2) from the plugins/ copy. Nothing was run.

## Situation

- The session entered the worktree with `EnterWorktree`. A chained Preflight call was refused, so Preflight
  ran as `bash <scratchpad>/preflight.sh` from the worktree root. Its closing `echo` printed the resolved
  values, including `RUN=/tmp/tmp.abc` and the literal `MERGE_BASE` and `BASE` values (and `SCOPE`, if one
  was set).
- Preflight's Inputs block exported `GIT_INDEX_FILE="$RUN/index"`, copied the real index into
  `/tmp/tmp.abc/index`, and ran `git-review-intent-add.sh` there. That intent-added (`git add -N`) the new
  untracked file **in the throwaway index only**. The real `.git/index` was never touched.
- That `export` lived only inside the script's shell. It ended with the script. Bash calls share no shell
  state, so no later call inherits `GIT_INDEX_FILE`.
- The user picked one folder to leave out, so (`scoped-review.md` section 2) the planner is re-run once with
  `--exclude-dir <folder>` and tag `1b`. Then the section 1 cross-check runs against the new manifest.

## How the two calls are issued

In an EnterWorktree session, after a refusal, every call other than Preflight is **one command per Bash
call, with no `&&` or `;`**. An `export` in a call of its own would be lost before the next call, so the
documented "start the call with `export GIT_INDEX_FILE=...`" becomes a **prefix assignment on the command
itself**, with the literal `$RUN` path written out. Both calls run from the session's current working
directory, which is the worktree root `EnterWorktree` set. The planner wrapper requires the work-tree root,
so never `cd` anywhere first.

**Call 1: the planner re-run (tag `1b`)**

```bash
GIT_INDEX_FILE="/tmp/tmp.abc/index" bash "${CLAUDE_PLUGIN_ROOT:-.claude}/scripts/git-review-scope-run.sh" "/tmp/tmp.abc" 1b "<literal MERGE_BASE>" "<literal BASE>" --exclude-dir <picked-folder>/
```

- Use the same merge base, base ref and scope as the first plan. If a scope was set, append
  `--scope "<literal SCOPE>"`. The wrapper takes the merge base and base positionally, in the same shape
  as Preflight step 1.
- `<picked-folder>/` is the folder label the user selected. It was only offered because it matches
  `^[A-Za-z0-9_][A-Za-z0-9._-]*/$`.
- The wrapper writes to **new** paths, `/tmp/tmp.abc/manifest-1b.json` and `/tmp/tmp.abc/diffs-1b`, and
  never overwrites the first plan's files.
- In this repository `CLAUDE_PLUGIN_ROOT` is empty, so the `:-.claude` default picks the mirror wrapper at
  `.claude/scripts/git-review-scope-run.sh`, relative to the worktree root. That mirror form is
  deliberately not granted. The `GIT_INDEX_FILE` prefix has no grant either. So expect this call to raise a
  permission prompt. That prompt is the intended human gate, not a failure.
- After it finishes, `Read` `/tmp/tmp.abc/manifest-1b.json` and use that manifest from then on.

**Call 2: the cross-check of the new manifest against the changed-file list**

```bash
GIT_INDEX_FILE="/tmp/tmp.abc/index" git diff --no-renames --name-only "<literal MERGE_BASE>" > "/tmp/tmp.abc/changed.names"
```

(If a scope is set, append `-- "<literal SCOPE>"`.) Then:

- `Read` `/tmp/tmp.abc/changed.names`.
- Every changed path must appear in `manifest-1b.json`'s `files`, `excluded` or `dropped_slices`. The
  picked folder's files should now show up as excluded.
- Every `files` entry that is not a deletion must have a non-empty section in its slice's `.diff` under
  `/tmp/tmp.abc/diffs-1b`. Check this with `Grep` for its `diff --git` line.
- A path that is in none of those lists, or a listed file with an empty diff, counts as `PLAN_FAILED`. In
  that case, ask via `AskUserQuestion` whether to review the whole diff unscoped or stop, and never treat
  it as a pass.

## Why it matters for the untracked file

Only the throwaway index at `/tmp/tmp.abc/index` holds the intent-to-add entry for the new untracked file.
`git diff` against the merge base only shows an untracked file once it is intent-added in the index that
git reads. If a call runs without the `GIT_INDEX_FILE` prefix, git reads the real `.git/index`, where the
file is still untracked. Then:

- **In the planner re-run**, the new file silently drops out of `manifest-1b.json` and its slice diffs, so
  it is never sent for review.
- **In the cross-check**, the file is missing from `changed.names`. The check cannot notice the gap,
  because both sides lack the file. The review then goes ahead looking complete, with the new file
  unreviewed.

In the skill's words, "Without the index variable, intent-added untracked files silently drop out of the
review." The prefix form also keeps the real index untouched. Pointing these calls at the real index
instead, for example by running `git add -N` there, would be a persistent change. A later `git commit -a`
could then commit the file's content.

## What happens if that form is refused

If the isolation check (or anything else) refuses the single-command, prefix-assignment form too, **stop
and report the refusal** to the user. Never fall back to another way of running the step, such as:

- a chained or `export`-then-command call,
- a heredoc,
- writing these commands into a new scratchpad script (the scratchpad-script exception covers only
  Preflight and the write helper's stdin text),
- dropping the `GIT_INDEX_FILE` prefix,
- running the planner or diff against the real index,
- `cd`-ing elsewhere.

A permission prompt is not a refusal. Approving the prompt for that one call is the expected path. The
stop applies only to a real refusal, such as the worktree-isolation check rejecting the call.
