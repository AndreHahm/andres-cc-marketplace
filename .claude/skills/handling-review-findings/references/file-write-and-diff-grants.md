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
  configuration, `GIT_NO_LAZY_FETCH`, an absolute `git` from `PATH` that is not anywhere inside the
  repository (the nearest ancestor of the starting directory holding a `.git` entry, found without running
  git; a git under that root, a home-directory dotfiles repository included, is refused with exit 2), output
  read under a 1,000,000-byte cap, a 60-second limit enforced by a timer thread that stops git's whole
  process group (so it holds without `SIGALRM` and a child that keeps the pipe open cannot outlast it),
  and no echo of git's own error text. A tree or blob id is refused as `--base`, and an empty diff exits 2.
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

1. **`Skill(commit)` is pre-approved here, and a nested skill's `allowed-tools` do apply without a
   prompt** (verified live, issue #588, Claude Code 2.1.302: a skill that held only `Skill(inner)` ran
   `inner`'s granted command with no prompt). `commit` used to carry a bare `Write`, `Bash(git diff:*)` and
   `Bash(sed -E:*)`; issue #588 scoped them to `Edit(//tmp/claude-*/*/*/scratchpad/**)`, the exact
   `Bash(git diff --cached)` and nothing, so the nested route no longer reaches either closed route
   through `commit`. Any other skill this one pre-approves is still reachable the same way.
2. **Step 4a runs `git-verify-fix-diff.py --worktree`**, which runs `git add -A` on the real working tree.
   Issue #588 hardened it: an absolute `git` that is not inside the repository, an environment limited to
   locale and time zone with no global or system configuration, `-c core.fsmonitor=false -c
   core.hooksPath=/dev/null` on every git call, an empty template directory for its two clones, and every
   inherited `GIT_*` variable removed from the process the imported verifiers run in.
   `tests/marketplace_ci/test_git_verify_fix_diff_script.py` plants a marker-writing command on each route
   (repository `core.fsmonitor`, a `post-index-change` hook, `GIT_TRACE`, `GIT_CONFIG_*`, a global
   `init.templateDir` hook, a `git` earlier on `PATH` inside the repository) and runs plain git as a
   control. Still open: `git add -A` runs a clean filter that the repository's own `.git/config` defines
   (a `-c` flag cannot switch off a filter whose name is unknown; an in-tree `.gitattributes` can only
   select a driver already configured locally).
3. **Environment hardening is per script.** The `git rev-parse` and `git ls-files` grants, and the
   `git-review-ledger.py` grant, run with the inherited environment, and the `git-verify-fix-diff.py` and
   `git-review-ledger.py` grants have no `-I`, so Python's own `PYTHON*` variables are inherited too (the
   verify script sanitizes only git's environment). A prefix grant does not match a command with a leading `VAR=value` (verified live, issue
   #588: `FOO=bar python3 -c ...` and `FOO=bar git diff ...` both prompted), so the command line cannot
   carry `GIT_TRACE`/`GIT_CONFIG_*`; the inherited session environment still can.
4. **Other components still carry the same `--output=<path>` route.** `check-all` runs
   `check-git-output-grants` (`scripts/marketplace_ci/git_output_grants.py`). It fails on a wildcard git
   grant in a plugin component's `allowed-tools` (or an agent's `tools`), decoded as YAML so an escaped line
   break cannot hide one, whose command writes the file named by `--output=<path>`. The command list comes
   from running every git command with that option on git 2.43.0 in a scratch repository (119 tried,
   interactive and network ones skipped, then `difftool` and `bisect` by hand): `diff`, `log`, `show`,
   `stash`, `rev-list`, `cherry-pick`, `revert`, `shortlog`, `blame`, `reflog`, `range-diff`,
   `difftool`, `bisect view` and the others in the module, not only the three first named in #588. It
   also fails on a blanket `git:*`, `git *`, `git -C:*` or `git -C <path>:*`, on any of these after git
   global options such as `--no-pager` or `-C <path>`, and on a baseline entry whose grant is gone. A
   grant is exempt only when everything the wildcard adds follows a `--` (a pathspec) reached through
   options the module knows; an unknown option before the `--` could take it as its value, so that
   grant stays flagged. Rules are split as a shell would, so a quoted ` -- ` is not a separator. A
   wildcard inside the program word (`*/git`, `g*`) and an alias defined with `git -c alias.x=diff x:*`
   are flagged too. Still not caught, and out of this check's scope: shell-expansion spellings such as
   `$'git'` or `g?t`, `git` glued to punctuation, wrappers like `env git`, `xargs git` or
   `command git`, and components whose paths come from a `plugin.json` rather than the default
   directories. The
   baseline, `scripts/marketplace_ci/git_output_grants_baseline.json`, lists every component still
   open, in every plugin (not only git-kit); scoping a component means deleting its entries there in
   the same commit. The follow-up for the blanket grants in plugin-devkit and `git-cleanup` is #599. The
   check reads the baseline from the PR's own checkout, so the baseline is on the Tier-1 list
   (`docs/ci.md`): editing it needs the manual bypass attestation, including a PR that only shrinks it.
   The checker module is not on that list and runs from the PR's own checkout; running the check from a
   base-restored copy, as the `prefix-permanence` job does for its own checks, would close that.
5. **Smaller gaps.** `GIT_NO_LAZY_FETCH` needs a newer git than 2.43.0 (the exact version is unverified), so
   a partial clone could still fetch; `--text` on a very large blob is bounded by the time limit, not by
   memory; the process-group kill is POSIX-only (on Windows only git itself is killed; not run on a real
   Windows host); and in this repository's own sessions the
   pinned scripts resolve to the `.claude/scripts/` mirror inside the checkout, which a PR can change. Only
   `allowed-tools` is pinned by the smoke check: other frontmatter keys are not.

## Follow-up: the same fix in other skills (Issue #587)

Issue #587 applied this change's write-grant scoping to `github-issue-creator` (`Edit(issues/**)`) and to
the analysis-kit skills `reviewing-analysis-findings` and `mining-review-learnings` (scratchpad only) and
`managing-review-learnings` (scratchpad only: its draft-edit step prompts, since an `Edit(issues/**)` rule would also allow creating any file there). Two more results, from the same kind of
headless run (Claude Code 2.1.302, Linux, default permission mode, a throwaway skill in a throwaway
project):

- **Writes under the project's `.claude/` directory were refused as sensitive files in every combination
  tried.** A bare `Write` was refused for `.claude/NOTES.md` and `.claude/workledger-kit.local.json`, and the
  exact rule `Edit(.claude/NOTES.md)` was refused for `.claude/NOTES.md` and `.claude/other.md`. Other
  combinations were not tried. An `Edit` rule for a path under `.claude/` therefore appears to grant nothing,
  and `managing-review-learnings` has none for `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md`: that edit keeps
  prompting, a deliberate choice that preserves the prompt rather than a verified result for every
  `.claude/` path.
- **A cwd-relative `Edit(issues/**)` allowed `issues/a.md` and denied a write to a repo-root file.** The
  bare `Write` allowed a repo-root file with no prompt. The same rule denied a write through an `issues`
  symlink that pointed at a directory outside it, and denied `issues/../root.md`.
- **A `Bash(python */analysis-kit/scripts/anls_x.py:*)` grant allowed `python -c "open('c.txt','w')..."
  analysis-kit/scripts/anls_x.py` and the same command with a `/x/` path prefix; both created the file.**
  The leading `*` matches any text, so a scoped `Edit` does not stop writes in a skill that also holds such
  a grant. The three analysis-kit skills changed here hold one (19 skills, all in `analysis-kit`, have a
  `Bash(python */...)` grant, counted by pattern match on their `allowed-tools` lines), so their write scope bounds direct `Write`/`Edit` calls only. Pinning those grants to the
  plugin root is tracked in #106.
- Every probe ran in default permission mode. In `acceptEdits` or bypass mode edits inside the working
  directory are generally allowed whatever the rule says, so the scoping matters in default mode.
- The scratchpad glob's `claude-*/*/*` matches every project and session of the same user, so an
  injected run could overwrite another live session's scratch file.

Each of the four skills' smoke tests pins its exact file-write grant set (`check_file_write_grants_scoped`),
and `tests/marketplace_ci/test_write_grant_smoke_checks.py` checks that a bare or inert grant fails it.
66 other skills still list a bare `Write` (counted by a pattern match on each `plugins/*/skills/*/SKILL.md`
`allowed-tools` line, on the date of this change); each needs its own decision on write targets and is
tracked in #591.

## Not checked

A macOS temp root, and a real `${CLAUDE_PLUGIN_ROOT}` install directory. The `.claude/` protected-path case
is covered in the follow-up section above for the project `.claude/` directory only. Where Claude Code's scratch directory is not laid out as `/tmp/claude-<uid>/<project>/<session>/scratchpad`,
a scratchpad write falls back to a prompt rather than succeeding silently.
