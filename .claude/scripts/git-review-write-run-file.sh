#!/usr/bin/env bash
# Write one file into a cross-model-review run directory (issue #541).
#
# usage: git-review-write-run-file.sh <run-dir> <dest-name> [--append] <part>...
#
# A part is one of:
#   -                 stdin, at most once per call
#   @<relative/path>  a regular file that resolves inside <run-dir>
#   @plugin:review    the skill's fixed prompts/review.md, from this script's own plugin root
#   @plugin:refute    the skill's fixed prompts/refute.md, likewise
#
# `cross-model-review` writes its scratch files through this helper instead of a `Write` grant, because
# a `Write` grant cannot be limited to a path. The helper writes exactly one file, <run-dir>/<dest-name>,
# and only into a directory shaped like `mktemp -d`'s output: tmp.<random>, mode 0700, owned by the
# caller, not a symlink, directly under the temp directory and outside the repository. That shape is a
# check on the path, not proof the skill made the directory: any such directory the caller owns is
# accepted. <dest-name> is a bare file name. The file is replaced atomically through a temporary file in
# <run-dir> (a symlink at the destination is replaced, never followed); with --append the existing
# regular file's content comes first. The result is readable by the owner only. Parts are concatenated
# verbatim, in order, so the caller supplies any newlines it wants between them.
set -euo pipefail

fail() {
  echo "git-review-write-run-file.sh: $*" >&2
  exit 2
}

[ "$#" -ge 3 ] || fail "usage: <run-dir> <dest-name> [--append] <part>..."
run_dir=$1
dest_name=$2
shift 2
append=0
if [ "$1" = "--append" ]; then
  append=1
  shift
fi
[ "$#" -ge 1 ] || fail "at least one part is required"

[[ $run_dir != -* && $run_dir != *$'\n'* ]] || fail "invalid run directory"
[ -d "$run_dir" ] && [ ! -L "$run_dir" ] || fail "run directory must be an existing directory, not a symlink"
[ -O "$run_dir" ] || fail "run directory must be owned by the current user"
[ -z "$(find "$run_dir" -maxdepth 0 \( -perm -020 -o -perm -002 \) 2>/dev/null)" ] ||
  fail "run directory must not be writable by group or others"
[[ $dest_name =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$ ]] || fail "invalid destination name"

unset GIT_INDEX_FILE GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR GIT_CONFIG_COUNT GIT_CONFIG_PARAMETERS \
  GIT_CEILING_DIRECTORIES

run_dir=$(CDPATH='' cd -P -- "$run_dir" && pwd -P)
# Only a directory `mktemp -d` makes: tmp.<random> (mode 0700) directly under the temp directory. Any
# other directory the caller owns (a home directory, .git, another checkout) is refused.
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

dest=$run_dir/$dest_name
[ ! -d "$dest" ] || fail "destination is a directory"
if [ "$append" -eq 1 ]; then
  [ -f "$dest" ] && [ ! -L "$dest" ] || fail "--append needs an existing regular file"
fi

plugin_root=$(CDPATH='' cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)

# Resolve every part to a source path before writing anything, so a bad part leaves no partial file.
sources=()
stdin_used=0
for part in "$@"; do
  case "$part" in
    -)
      [ "$stdin_used" -eq 0 ] || fail "stdin may be used once per call"
      stdin_used=1
      sources+=("-")
      ;;
    @plugin:review | @plugin:refute)
      src=$plugin_root/skills/cross-model-review/prompts/${part#@plugin:}.md
      [ -f "$src" ] || fail "missing fixed prompt: $src"
      sources+=("$src")
      ;;
    @*)
      rel=${part#@}
      [[ $rel =~ ^[A-Za-z0-9._/-]+$ && $rel != /* && $rel != */ ]] || fail "invalid part path: $rel"
      case "/$rel/" in
        */../* | *//*) fail "invalid part path: $rel" ;;
      esac
      src=$(realpath -e -- "$run_dir/$rel" 2>/dev/null) || fail "part not found: $rel"
      case "$src" in
        "$run_dir"/*) ;;
        *) fail "part resolves outside the run directory: $rel" ;;
      esac
      [ -f "$src" ] || fail "part is not a regular file: $rel"
      [ "$src" != "$dest" ] || fail "a file cannot be built from itself"
      sources+=("$src")
      ;;
    *) fail "invalid part: $part" ;;
  esac
done

umask 077
out=$(mktemp "$run_dir/.write.XXXXXX")
trap 'rm -f -- "$out"' EXIT
if [ "$append" -eq 1 ]; then
  cat -- "$dest" >>"$out"
fi
for src in "${sources[@]}"; do
  if [ "$src" = "-" ]; then cat >>"$out"; else cat -- "$src" >>"$out"; fi
done
mv -fT -- "$out" "$dest"
trap - EXIT
