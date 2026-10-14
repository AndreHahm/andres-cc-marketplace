#!/usr/bin/env bash
# Copy the repository's real index into <run-dir>/index (issue #541).
#
# usage: git-review-copy-index.sh <run-dir>
#
# `cross-model-review` reviews against a throwaway index so that intent-adding untracked files never
# touches the real one. This helper is what its allowed-tools grant names instead of a bare `cp`:
# it copies exactly one file, the real index, to exactly one place, <run-dir>/index, in a directory
# that exists, is not a symlink, is owned by the caller and lies outside the repository. It never
# overwrites, and the copy is readable by the owner only. GIT_INDEX_FILE (and the other variables that
# redirect git) are ignored on purpose: the caller has already pointed GIT_INDEX_FILE at the copy.
set -euo pipefail

fail() {
  echo "git-review-copy-index.sh: $*" >&2
  exit 2
}

[ "$#" -eq 1 ] || fail "usage: <run-dir>"
run_dir=$1

[[ $run_dir != - && $run_dir != *$'\n'* ]] || fail "invalid run directory"
[ -d "$run_dir" ] && [ ! -L "$run_dir" ] || fail "run directory must be an existing directory, not a symlink"
[ -O "$run_dir" ] || fail "run directory must be owned by the current user"
[ -z "$(find "$run_dir" -maxdepth 0 \( -perm -020 -o -perm -002 \) 2>/dev/null)" ] ||
  fail "run directory must not be writable by group or others"

unset GIT_INDEX_FILE GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR

run_dir=$(CDPATH='' cd -P -- "$run_dir" && pwd -P)
top=$(git rev-parse --show-toplevel 2>/dev/null || true)
[ -n "$top" ] || fail "not inside a git work tree"
top=$(CDPATH='' cd -P -- "$top" && pwd -P)
[ "$top" != / ] || fail "refusing to treat / as the repository"
case "$run_dir/" in
  "$top"/*) fail "run directory must be outside the repository" ;;
esac

real=$(git rev-parse --git-path index)
[ -f "$real" ] || fail "the repository has no index file to copy"
[ ! -e "$run_dir/index" ] && [ ! -L "$run_dir/index" ] || fail "$run_dir/index already exists"

umask 077
cp -- "$real" "$run_dir/index"
