#!/usr/bin/env bash
# Intent-add untracked files to the review's throwaway index (issue #541).
#
# usage: git-review-intent-add.sh <run-dir> [pathspec]
#
# `cross-model-review` needs `git diff` to show untracked files, which only works once they are
# intent-added (`git add -N`). Against the repository's real index that would be a lasting change, so
# the skill points git at a copy in its own run directory. This helper is what its allowed-tools grant
# names instead of a bare `git add -N`: it sets GIT_INDEX_FILE itself, to <run-dir>/index, after
# dropping every other GIT_* variable, in an owner-only temp directory shaped like `mktemp -d` output
# (tmp.<random>, mode 0700, owned by the caller, not a symlink, directly under the temp directory,
# outside the repository). That is a check on the path, not proof the skill made the directory. The
# index file, if it exists, must be a regular file, not a symlink (a swap after that check is not
# prevented). Git hooks and fsmonitor are disabled for the call. The one optional pathspec is passed
# after `--`. Besides the index (and its lock file), git may write the fixed empty blob object.
set -euo pipefail

fail() {
  echo "git-review-intent-add.sh: $*" >&2
  exit 2
}

[ "$#" -ge 1 ] && [ "$#" -le 2 ] || fail "usage: <run-dir> [pathspec]"
run_dir=$1
spec=${2:-.}

[[ $run_dir != -* && $run_dir != *$'\n'* ]] || fail "invalid run directory"
[[ $spec != *$'\n'* ]] || fail "invalid pathspec"
[ -d "$run_dir" ] && [ ! -L "$run_dir" ] || fail "run directory must be an existing directory, not a symlink"
[ -O "$run_dir" ] || fail "run directory must be owned by the current user"
[ -z "$(find "$run_dir" -maxdepth 0 \( -perm -020 -o -perm -002 \) 2>/dev/null)" ] ||
  fail "run directory must not be writable by group or others"

for name in $(compgen -e); do
  case $name in
    GIT_*) unset "$name" ;;
  esac
done

run_dir=$(CDPATH='' cd -P -- "$run_dir" && pwd -P)
[[ $(basename -- "$run_dir") =~ ^tmp\.[A-Za-z0-9]{8,12}$ ]] || fail "run directory must be a mktemp -d directory"
[ -n "$(find "$run_dir" -maxdepth 0 -perm 700 2>/dev/null)" ] || fail "run directory must have mode 0700"
run_parent=$(dirname -- "$run_dir")
tmp_a=$(CDPATH='' cd -P -- /tmp 2>/dev/null && pwd -P || true)
tmp_b=$(CDPATH='' cd -P -- "${TMPDIR:-/tmp}" 2>/dev/null && pwd -P || true)
[ "$run_parent" = "$tmp_a" ] || [ "$run_parent" = "$tmp_b" ] ||
  fail "run directory must be directly under the temp directory"

top=$(git rev-parse --show-toplevel 2>/dev/null || true)
[ -n "$top" ] || fail "not inside a git work tree"
top=$(CDPATH='' cd -P -- "$top" && pwd -P)
[ "$top" != / ] || fail "refusing to treat / as the repository"
case "$run_dir/" in
  "$top"/*) fail "run directory must be outside the repository" ;;
esac

index=$run_dir/index
if [ -e "$index" ] || [ -L "$index" ]; then
  [ -f "$index" ] && [ ! -L "$index" ] || fail "$index must be a regular file"
fi

# Writing an index can run a post-index-change hook or a core.fsmonitor command, and either could come
# from the branch under review (a core.hooksPath inside the work tree), so both are switched off.
export GIT_INDEX_FILE=$index
exec git -c core.hooksPath=/dev/null -c core.fsmonitor=false add -N -- "$spec"
