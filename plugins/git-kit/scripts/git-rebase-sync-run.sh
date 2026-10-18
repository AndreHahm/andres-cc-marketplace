#!/usr/bin/env bash
# Run git-rebase-sync's two history-rewriting commands in exactly one shape each (#585).
#
# usage: git-rebase-sync-run.sh rebase <base>
#        git-rebase-sync-run.sh rebase-merges <base>
#        git-rebase-sync-run.sh push <branch> <lease_oid>
#        git-rebase-sync-run.sh push-plain <branch>
#
# `git rebase origin/:*` and `git push --force-with-lease=:*` as tool grants also admit anything appended
# after the documented text: `--exec`/`-x` (an arbitrary command per replayed commit), `--onto`, another
# remote, a `+` refspec. A grant that names this script instead permits only the four shapes below. Each
# runs one fixed git command with plain-ref arguments that were checked first; nothing else is accepted,
# and every refusal exits 2 without running git. Refs are fully qualified (refs/remotes/origin/<base>,
# refs/heads/<branch>) so a tag or local branch that happens to be named like them cannot shadow the
# remote-tracking ref or the remote branch. A push also requires that HEAD is the branch being pushed,
# that no rebase is in progress, and that the branch is not main, master or the remote's default branch.
set -euo pipefail

# Variables that redirect git to another repository or inject configuration are not honored.
unset GIT_INDEX_FILE GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR GIT_CONFIG_COUNT GIT_CONFIG_PARAMETERS \
  GIT_CEILING_DIRECTORIES

fail() {
  echo "git-rebase-sync-run.sh: $*" >&2
  exit 2
}

# A ref name is data from GitHub or a contributor's checkout: plain characters only, no leading '-' or
# '.', no '..', no trailing '/' or '.lock', and never the literal HEAD.
check_ref() {
  [[ $1 =~ ^[A-Za-z0-9_][A-Za-z0-9._/-]*$ ]] || fail "invalid ref name"
  [[ $1 != *..* && $1 != */ && $1 != *.lock && $1 != HEAD ]] || fail "invalid ref name"
}

# A push rewrites the remote branch: HEAD must be exactly that branch, finished, and not a base branch.
check_push_target() {
  local branch=$1 default
  [ "$(git symbolic-ref -q HEAD || true)" = "refs/heads/$branch" ] || fail "HEAD is not the branch to push"
  if [ -e "$(git rev-parse --git-path rebase-merge)" ] || [ -e "$(git rev-parse --git-path rebase-apply)" ]; then
    fail "a rebase is still in progress"
  fi
  default=$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null || true)
  [[ $branch != main && $branch != master && $branch != "${default#origin/}" ]] ||
    fail "refusing to force-push a base branch"
}

[ "$#" -ge 2 ] || fail "usage: rebase|rebase-merges <base> | push <branch> <lease_oid> | push-plain <branch>"
mode=$1

case "$mode" in
  rebase | rebase-merges)
    [ "$#" -eq 2 ] || fail "usage: $mode <base>"
    check_ref "$2"
    if [ "$mode" = "rebase-merges" ]; then
      exec git rebase --rebase-merges "refs/remotes/origin/$2"
    fi
    exec git rebase "refs/remotes/origin/$2"
    ;;
  push)
    [ "$#" -eq 3 ] || fail "usage: push <branch> <lease_oid>"
    check_ref "$2"
    [[ $3 =~ ^[0-9a-f]{40}([0-9a-f]{24})?$ ]] || fail "invalid lease commit id"
    check_push_target "$2"
    exec git push --no-follow-tags "--force-with-lease=refs/heads/$2:$3" origin "HEAD:refs/heads/$2"
    ;;
  push-plain)
    [ "$#" -eq 2 ] || fail "usage: push-plain <branch>"
    check_ref "$2"
    check_push_target "$2"
    exec git push --no-follow-tags --force-with-lease origin "HEAD:refs/heads/$2"
    ;;
  *)
    fail "unknown mode"
    ;;
esac
