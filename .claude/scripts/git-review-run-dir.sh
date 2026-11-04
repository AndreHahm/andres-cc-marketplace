#!/usr/bin/env bash
# The privacy check on a cross-model-review run directory, shared by its four helpers (issue #637).
#
# Sourced, never run: git-review-copy-index.sh, git-review-intent-add.sh, git-review-scope-run.sh and
# git-review-write-run-file.sh call check_run_dir_private and check_run_dir_outside_repo with their
# resolved paths, and both use the caller's fail().
#
# Everywhere except Git Bash the directory must have mode 0700. Git Bash mounts its temp directory
# without ACLs, so it invents mode bits (a directory reads as 755 and chmod changes nothing) and that
# check could never pass. There the directory must instead sit below the user profile, whose ACL is the
# boundary. That is weaker: it trusts the profile's ACL and USERPROFILE, which a process running as the
# same user can change, and the helpers' owner and group-write checks prove nothing there either. The
# comparison is lexical, so a temp directory that is itself a junction to a shared place would pass.
# The platform comes from an absolute /usr/bin/uname, so neither OSTYPE nor PATH can select the weaker
# branch. Cygwin reports as CYGWIN and keeps the 0700 check.

run_dir_is_git_bash() {
  case $(/usr/bin/uname -s 2>/dev/null) in
    MINGW* | MSYS*) return 0 ;;
    *) return 1 ;;
  esac
}

check_run_dir_private() {
  if ! run_dir_is_git_bash; then
    [[ -n "$(find "$1" -maxdepth 0 -perm 700 2>/dev/null)" ]] || fail "run directory must have mode 0700"
    return 0
  fi
  [[ -n "${USERPROFILE:-}" ]] || fail "USERPROFILE is not set"
  local profile real
  # Windows form on purpose: the POSIX form of /tmp/x stays /tmp/x, and -l (which expands a short name
  # such as RUNNER~1) only works with -m or -w.
  profile=$(cygpath -lm "$USERPROFILE") || fail "cannot resolve the user profile"
  real=$(cygpath -lm "$1") || fail "cannot resolve the run directory"
  profile=${profile%/}
  [[ $profile =~ ^[A-Za-z]:/.+ ]] || fail "user profile must be a directory on a local drive"
  # Windows paths are case-insensitive.
  case "${real,,}/" in
    "${profile,,}"/*) ;;
    *) fail "run directory must be inside the user profile on Windows" ;;
  esac
}

# Git Bash keeps a run directory as /tmp/... but a repository as /c/..., so their POSIX forms never share
# a prefix even when the temp directory is inside the work tree. Compare the Windows forms there.
check_run_dir_outside_repo() {
  local run=$1 root=$2
  if run_dir_is_git_bash; then
    run=$(cygpath -lm "$run") || fail "cannot resolve the run directory"
    root=$(cygpath -lm "$root") || fail "cannot resolve the repository"
    run=${run,,}
    root=${root%/} # a drive root is C:/, and the pattern below adds its own slash
    root=${root,,}
  fi
  case "$run/" in
    "$root"/*) fail "run directory must be outside the repository" ;;
  esac
}
