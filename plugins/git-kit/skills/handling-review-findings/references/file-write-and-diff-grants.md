# File-Write and Diff Grants (Issue #582)

Why this skill's `allowed-tools` holds scoped `Edit(...)` rules and a pinned diff script instead of a bare
`Write` and `Bash(git diff:*)`, what was verified live, and what this change does **not** close. Everything
below is a record of checks, not an instruction to the reader: each result is dated to the versions it was
run on.

## What this closes: the skill's own two direct routes

A pinned `Bash(python3 -I ${CLAUDE_PLUGIN_ROOT}/scripts/<script>:*)` grant is only as strong as the
protection of that script file. This skill had two direct ways to overwrite one without a prompt:

1. **The `Write` tool.** A bare `Write` grant lets a skill overwrite any file. Now:
   `Edit(//tmp/claude-*/*/*/scratchpad/**)` (scratchpad body files) and `Edit(issues/**)` (the local issue
   draft). An `Edit(...)` rule also covers the `Write` tool; a `Write(<glob>)` rule is accepted but never
   matches, so it would grant nothing.
2. **`git diff --output=<path>`.** The `Bash(git diff:*)` prefix allows that option, a write to any path.
   Now: `git-review-fix-diff.py`, which runs `git diff-tree` and takes one validated argument
   (`--base <full commit id>`).

## Why not a safer `git diff`

`git diff` reads the index and the working tree, and each can run a command or write a file the caller did
not ask for. Reproduced live against a first version of the wrapper (git 2.43.0), with a marker file as
the evidence, using `git diff HEAD` on a working tree with an uncommitted edit: a configured
`core.fsmonitor` command, a configured clean filter, a `post-index-change` hook (git also rewrites the
index), `GIT_TRACE=<path>` in the inherited environment (git appends to that file) and
`GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_n`/`GIT_CONFIG_VALUE_n` injecting `core.fsmonitor`. `git diff <commit>
HEAD` did not run fsmonitor.

## What the wrapper does, and does not

- `git diff-tree` compares two commits' trees. It never opens the index and never reads a working-tree
  file's contents, so none of the routes above exist for it. It does still read the working tree's
  `.gitattributes` and `.gitmodules` and the repository configuration; the flags neutralize their effect on
  the output: `--text` (a `-diff` attribute cannot hide a change), `--no-ext-diff`, `--no-textconv`,
  `--ignore-submodules=none` (a `.gitmodules` `ignore = all` cannot hide a changed submodule pointer; the
  test fails without the flag, confirmed by removing it), `--submodule=short`, `--no-relative`.
- The environment passed to git is an allowlist (locale and time zone), with no global or system
  configuration, `GIT_NO_LAZY_FETCH`, an absolute `git` from `PATH` that is not inside the starting
  directory, output read under a 1,000,000-byte cap, a 60-second limit on POSIX, and no echo of git's own
  error text. A tree or blob id is refused as `--base`, and an empty diff exits 2.
- **It cannot show an uncommitted fix**, so the self-review of an uncommitted fix (the usual case) reads the
  agent's own edits and the changed files (`fix-self-review.md` 4c). That review is weaker than a diff: it
  misses file deletions, mode or symlink changes and anything changed by a route other than `Edit`.
- `tests/marketplace_ci/test_git_review_fix_diff_script.py` plants each command with a marker file, leaves
  the working tree dirty, and runs plain `git diff HEAD` as a control so a passing marker test is not
  vacuous. `smoke_test.py` pins the whole `allowed-tools` line to an exact list.

## Verified live (Claude Code 2.1.302, Linux, headless run in default permission mode)

- A bare `Write` overwrote a script file with no prompt; a skill with no write grant was denied every write.
- `Write(<glob>)` was denied everywhere, including inside the glob.
- `Edit(//<absolute glob>)`, a cwd-relative `Edit(issues/**)` and a wildcard segment such as `claude-*` all
  scoped the `Write` tool: the write inside the glob succeeded, the write outside was denied.
- `Edit(//tmp/claude-*/*/*/scratchpad/**)` allowed a `scratchpad` directory and denied a sibling `tasks/`
  directory and a `scratchpad` directory at the wrong depth (tested on a copy of the layout).
- Comma-separated and space-separated `allowed-tools` lists both worked.
- A shell redirect (`... > <path>`) to a path not granted for writing was blocked before the command ran.

## Still open: not closed by this change

1. **`Skill(commit)` is pre-approved here, and `commit` carries its own grants**: a bare `Write`,
   `Bash(git diff:*)` and `Bash(sed -E:*)`. Whether a nested skill's `allowed-tools` apply without a
   prompt is unverified; if they do, an injected agent can reach both closed routes through `commit`. Fixing
   it means scoping `commit`'s own grants, which is out of scope here.
2. **Step 4a runs `git-verify-fix-diff.py --worktree`**, which runs `git add -A` on the real working tree
   with a denylist environment, `git` by bare name, and a temporary clone that uses global configuration
   and template hooks. The filter, hook and `GIT_TRACE`/`GIT_CONFIG_*` routes can apply there. It is not
   hardened here.
3. **Environment hardening is per script.** The `git rev-parse` and `git ls-files` grants, and the
   `git-verify-fix-diff.py` and `git-review-ledger.py` grants (which have no `-I`), run with the inherited
   environment. Whether a prefix grant also matches a command with a leading `VAR=value` is unverified.
4. **Other components still carry the same `--output=<path>` route.** `Bash(git diff:*)` (or a longer prefix
   such as `git diff --name-only -z:*`) is granted in `commit`, `standalone-commits`, `explain-pr-changes`,
   `git-worktrees`, `git-rebase-sync`, `create-pr`, `dependency-updater` and the `git-status` and
   `git-update-branch-name` commands. `git log:*` or `git show:*`, which also accept `--output`, is granted
   in `git-bisect`, `git-notes`, `git-cleanup`, `git-worktrees`, `git-rebase-sync` and
   `resolving-merge-conflicts`. `resolving-merge-conflicts` grants only the exact `git diff --cached`.
5. **Smaller gaps.** `GIT_NO_LAZY_FETCH` needs a newer git than 2.43.0 (the exact version is unverified), so
   a partial clone could still fetch; the 60-second limit needs `SIGALRM` (not on Windows); `--text` on a
   very large blob is bounded by that limit, not by memory; and in this repository's own sessions the
   pinned scripts resolve to the `.claude/scripts/` mirror inside the checkout, which a PR can change. Only
   `allowed-tools` is pinned by the smoke check: other frontmatter keys are not.

## Not checked

A macOS temp root, the `.claude/` protected-path case, and a real `${CLAUDE_PLUGIN_ROOT}` install directory.
Where Claude Code's scratch directory is not laid out as `/tmp/claude-<uid>/<project>/<session>/scratchpad`,
a scratchpad write falls back to a prompt rather than succeeding silently.
