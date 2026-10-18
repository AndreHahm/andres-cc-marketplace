#!/usr/bin/env bash
# Read-only previews for a PR that conflicts with its base only on GitHub (#585).
#
# usage: git-pr-conflict-preview.sh view <number>
#        git-pr-conflict-preview.sh merge-tree <base>
#        git-pr-conflict-preview.sh default-branch
#
# `Bash(gh pr view:*)` as a tool grant also admits other repositories (`--repo`), `--web` and any other
# option, and `git merge-tree ...:*` admits other refs and options. A grant that names this script
# permits only the three shapes below: `gh pr view <digits> --json <fixed fields>`, a `git merge-tree`
# of the fully qualified remote-tracking base ref against HEAD, and `gh repo view` for the default branch
# name. Anything else exits 2 without running. The rest of the environment (PATH, HOME, git and gh
# configuration, credentials) is inherited from the user's own session and trusted; the `unset` below only
# stops variables that would redirect gh or git to another repository from leaking in by accident.
set -euo pipefail

fail() {
  echo "git-pr-conflict-preview.sh: $*" >&2
  exit 2
}

# The target repository comes from the checkout, never from the environment.
unset GH_REPO GH_HOST GIT_INDEX_FILE GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR GIT_CONFIG_COUNT GIT_CONFIG_PARAMETERS \
  GIT_CEILING_DIRECTORIES

[ "$#" -ge 1 ] || fail "usage: view <number> | merge-tree <base> | default-branch"

case "$1" in
  default-branch)
    [ "$#" -eq 1 ] || fail "usage: default-branch"
    exec gh repo view --json defaultBranchRef --jq .defaultBranchRef.name
    ;;
  view)
    [ "$#" -eq 2 ] || fail "usage: view <number>"
    [[ $2 =~ ^[0-9]{1,9}$ ]] || fail "invalid PR number"
    exec gh pr view "$2" --json mergeable,mergeStateStatus,baseRefName,headRefName,headRefOid,isCrossRepository,url
    ;;
  merge-tree)
    [ "$#" -eq 2 ] || fail "usage: merge-tree <base>"
    [[ $2 =~ ^[A-Za-z0-9_][A-Za-z0-9._/-]*$ ]] || fail "invalid ref name"
    [[ $2 != *..* && $2 != */ && $2 != *.lock && $2 != HEAD ]] || fail "invalid ref name"
    exec git merge-tree --write-tree --name-only "refs/remotes/origin/$2" HEAD
    ;;
  *)
    fail "unknown mode"
    ;;
esac
