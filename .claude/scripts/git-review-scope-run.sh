#!/usr/bin/env bash
# Run git-review-scope.py with a fixed shape (issue #541).
#
# usage: git-review-scope-run.sh <run-dir> <tag> <merge-base> <base-ref> [option value]...
#
# The planner itself accepts --repo, --output, --diff-dir and more. This wrapper is what the
# `cross-model-review` skill's allowed-tools grant names, so it takes only what that skill needs and
# binds the rest: the repository is the current directory, and the manifest and slice diffs always
# land at <run-dir>/manifest-<tag>.json and <run-dir>/diffs-<tag>, in a directory that exists, is
# not a symlink, is owned by the caller and lies outside the repository. The only options passed
# through are --scope, --exclude-dir, --prior-manifest and --completed-slice; the planner validates
# their values itself. Environment variables that redirect git or Python (GIT_DIR, GIT_WORK_TREE,
# GIT_COMMON_DIR, GIT_CONFIG_*, PYTHON*, ...) are dropped before the planner starts; GIT_INDEX_FILE
# is kept, because the skill relies on it. <base-ref> is trusted for settings and the mirror map, so
# pass the branch the work will land on, never HEAD.
set -euo pipefail

fail() {
  echo "git-review-scope-run.sh: $*" >&2
  exit 2
}

[ "$#" -ge 4 ] || fail "usage: <run-dir> <tag> <merge-base> <base-ref> [option value]..."
run_dir=$1
tag=$2
merge_base=$3
base_ref=$4
shift 4

[[ $tag =~ ^[0-9]+[a-z]?$ ]] || fail "invalid tag: use digits and at most one lowercase letter"
[[ $merge_base =~ ^([0-9a-f]{40}|[0-9a-f]{64})$ ]] || fail "invalid merge-base: pass the full commit SHA"
[[ $base_ref =~ ^[A-Za-z0-9._/][A-Za-z0-9._/-]*$ ]] || fail "invalid base ref"
[[ $run_dir != - && $run_dir != *$'\n'* ]] || fail "invalid run directory"
[ -d "$run_dir" ] && [ ! -L "$run_dir" ] || fail "run directory must be an existing directory, not a symlink"
[ -O "$run_dir" ] || fail "run directory must be owned by the current user"

run_dir=$(CDPATH='' cd -P -- "$run_dir" && pwd -P)
repo=$(pwd -P)
top=$(git rev-parse --show-toplevel 2>/dev/null || true)
[ -n "$top" ] || fail "not inside a git work tree"
top=$(CDPATH='' cd -P -- "$top" && pwd -P)
[ "$repo" != / ] && [ "$top" != / ] || fail "refusing to treat / as the repository"
for root in "$repo" "$top"; do
  case "$run_dir/" in
    "$root"/*) fail "run directory must be outside the repository" ;;
  esac
done

for name in $(compgen -e); do
  case $name in
    GIT_DIR | GIT_WORK_TREE | GIT_COMMON_DIR | GIT_CONFIG* | GIT_EXTERNAL_DIFF | GIT_PAGER) unset "$name" ;;
    GIT_NAMESPACE | GIT_OBJECT_DIRECTORY | GIT_ALTERNATE_OBJECT_DIRECTORIES | GIT_EXEC_PATH) unset "$name" ;;
    PYTHON* | BASH_ENV | ENV | CDPATH) unset "$name" ;;
  esac
done

args=(
  --merge-base "$merge_base"
  --base-ref "$base_ref"
  --diff-dir "$run_dir/diffs-$tag"
  --output "$run_dir/manifest-$tag.json"
)
while [ "$#" -gt 0 ]; do
  case "$1" in
    --scope | --exclude-dir | --prior-manifest | --completed-slice)
      [ "$#" -ge 2 ] || fail "missing value for $1"
      args+=("$1=$2") # one word, so a value starting with '-' is never read as an option
      shift 2
      ;;
    *) fail "unsupported argument: $1" ;;
  esac
done

exec python3 -I "$(dirname -- "${BASH_SOURCE[0]}")/git-review-scope.py" "${args[@]}"
