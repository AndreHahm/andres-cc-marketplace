#!/bin/bash
# Lints, formats, and type-checks every fully-staged .py file, without ever
# composing a shell command from a staged filename. A staged filename is
# untrusted staged-diff content (attacker-controlled on a fetched or
# contributed branch) -- quoting it inside a model-constructed command
# string does not suppress $(...)/``/`$VAR` expansion. This script instead
# reads NUL-separated filenames into a bash loop and passes each one as a
# single argv element via a properly quoted variable expansion, which is
# safe: the shell substitutes the variable's literal value, it never
# re-parses that value as code the way it would if the same text appeared
# inside a command string the model built and handed to a shell.
#
# Full-staging check: for each staged .py path, `git status --porcelain -z`
# is asked specifically about that path (root-anchored, glob-disabled via
# `:(top,literal)`) and its two-character XY code is read: X (index) is
# non-space for anything staged; Y (worktree) is ' ' only when there are no
# additional unstaged changes on top -- that positive confirmation is what
# gates auto-fix, never an inference from empty `git diff` output (which
# returns empty+exit-0 for "no unstaged changes" and "pathspec mismatch"
# alike, and can't be told apart from output alone).
#
# Called by the commit skill (step 7.5), unless --no-verify was given.
set -euo pipefail

git rev-parse --git-dir >/dev/null 2>&1 || { echo "Error: not inside a git repository" >&2; exit 1; }

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not available -- skipping Python lint/format/type-check" >&2
  exit 0
fi

modified=()
skipped=()
to_check=()
lint_failed=0

# --diff-filter=ACMR excludes staged deletions/type-changes -- ruff has
# nothing to format on a path that no longer exists on disk, and letting a
# deleted path reach ruff would abort the whole loop (a routine "delete a
# .py file" commit, not an edge case). :(top) anchors the '*.py' pathspec to
# the repo root regardless of the invoking shell's cwd -- a bare '*.py' is
# resolved cwd-relatively and can miss staged files outside the invoking
# subdirectory. Deliberately `:(top)`, not `:(top,glob)`: git's *default*
# (non-magic) pathspec matching already lets '*' cross '/' (so '*.py'
# matches a nested path); the `glob` magic word switches to POSIX glob
# semantics where '*' does NOT cross '/', which would silently narrow this
# to top-level .py files only -- verified live, both forms tested directly.
while IFS= read -r -d '' file; do
  to_check+=("$file")

  # status_line is "XY <path>", NUL-terminated -- read via -d '' rather than a
  # $(...) capture, which would truncate at the embedded NUL. X is index
  # status, Y is worktree status. Y == ' ' means no unstaged changes on top
  # of the staged ones for this exact path.
  IFS= read -r -d '' status_line < <(git status --porcelain -z -- ":(top,literal)$file") || true
  y_char="${status_line:1:1}"

  if [ "$y_char" != " " ]; then
    skipped+=("$file (partially staged or status could not be confirmed -- skipped)")
    continue
  fi

  # Each external command's failure is captured, not allowed to abort the
  # loop under set -e -- a ruff violation on one file must not silently skip
  # git add for that file (leaving the reformatted worktree content out of
  # the commit) or skip every remaining file and the ty check entirely.
  format_ok=1
  uv run ruff format -- "$file" </dev/null || format_ok=0
  check_ok=1
  uv run ruff check --fix -- "$file" </dev/null || check_ok=0
  git add -- "$file"
  modified+=("$file")
  if [ "$format_ok" -eq 0 ] || [ "$check_ok" -eq 0 ]; then
    lint_failed=1
  fi
done < <(git -c diff.relative=false diff --cached --name-only -z --diff-filter=ACMR -- ':(top)*.py')

if [ "${#to_check[@]}" -eq 0 ]; then
  exit 0
fi

echo "--- ruff format/fix applied to ---"
if [ "${#modified[@]}" -eq 0 ]; then
  echo "(none)"
else
  printf '%s\n' "${modified[@]}"
fi

echo "--- skipped (not auto-fixed) ---"
if [ "${#skipped[@]}" -eq 0 ]; then
  echo "(none)"
else
  printf '%s\n' "${skipped[@]}"
fi

echo "--- ty check (all staged .py paths, including skipped-from-autofix ones) ---"
ty_failed=0
uv run ty check -- "${to_check[@]}" </dev/null || ty_failed=1

if [ "$lint_failed" -eq 1 ] || [ "$ty_failed" -eq 1 ]; then
  echo "ruff check and/or ty check reported violation(s) above" >&2
  exit 1
fi
exit 0
