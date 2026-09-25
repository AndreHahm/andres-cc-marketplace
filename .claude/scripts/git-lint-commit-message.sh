#!/bin/bash
# Lints a drafted commit message against this repository's real commitlint
# config, using the same commitlint version CI's commit-branch-guard.yml
# workflow installs -- not a hand-maintained approximation of commitlint's
# rules (e.g. a hardcoded 100-char setting), which could silently drift out
# of sync with .commitlintrc.cjs or its extended @commitlint/config-
# conventional base if either ever changes. Running the real tool can't
# drift by construction.
#
# A no-op (exit 0, no output) when this repository has no commitlint setup
# at all -- checked against both the working tree and origin's default
# branch, so a fetched branch deleting .commitlintrc.cjs/package.json
# locally can't silently suppress the check for a repo that legitimately
# has one -- git-kit is a marketplace plugin used across repos that may
# not have either.
#
# Trust boundary: .commitlintrc.cjs is a CommonJS module (commitlint's
# --config flag `require()`s it, executing whatever it contains, not just
# reading it as data), and the toolchain's package.json/pnpm-lock.yaml
# control what gets installed and later executed as the "commitlint"
# binary. All three are read from a TRUSTED ref (origin/<default branch>),
# never the checked-out working tree -- otherwise a fetched/contributed
# branch's own copies would run with this developer's local privileges the
# moment `commit` runs on it, the same "attacker-controlled on a fetched
# branch" threat model this file's own scan-staged-files.sh/
# stage-selected-files.sh/lint-staged-python.sh siblings already treat as
# live, and the exact scenario commit-branch-guard.yml's own CI workflow
# already defends against for these same files (found by cross-model-
# review across rounds 2-3). The install itself lives outside the tracked
# working tree entirely (under .git/), so this never mutates a developer's
# own checked-out copies of these files as a side effect of running a
# local lint check.
#
# Exit codes: 0 = no-op or checked-and-clean; 1 = a real commitlint rule
# violation (its own output names the rule(s) in brackets); 2 = the check
# could not run at all (pnpm missing, a trusted ref couldn't be read, or
# the toolchain install failed -- e.g. offline/blocked registry) --
# distinct from 1 so a caller never mistakes an infrastructure failure for
# a message-content violation. Every exit-2 path prints a line prefixed
# "SKIP:" to stderr identifying why.
#
# Usage: lint-commit-message.sh <path-to-drafted-message-file>
#
# Called by the commit skill (step 13.5), immediately before step 14's
# confirm-before-commit AskUserQuestion, unless --no-verify was given.
set -euo pipefail

MESSAGE_FILE="${1:?usage: lint-commit-message.sh <path-to-drafted-message-file>}"

[ -f "$MESSAGE_FILE" ] || { echo "Error: message file not found: $MESSAGE_FILE" >&2; exit 1; }

# Resolve to an absolute path before any `cd` below changes the working
# directory -- a relative path passed in would otherwise stop resolving
# correctly once cwd moves. Uses `cd ... && pwd`, not `realpath`/`readlink -f`
# (a Windows-drive-letter vs. POSIX-path format mismatch was already hit
# with realpath elsewhere in this repo's own Bash-tool environment).
MESSAGE_FILE_DIR="$(cd "$(dirname "$MESSAGE_FILE")" && pwd)"
MESSAGE_FILE="$MESSAGE_FILE_DIR/$(basename "$MESSAGE_FILE")"

git rev-parse --git-dir >/dev/null 2>&1 || { echo "Error: not inside a git repository" >&2; exit 1; }

REPO_ROOT="$(git rev-parse --show-toplevel)"
GIT_DIR="$(git rev-parse --git-dir)"
WORKTREE_TOOLCHAIN_DIR="$REPO_ROOT/.github/commitlint-tools"
CONFIG_FILE="$REPO_ROOT/.commitlintrc.cjs"

# Resolve the default branch the same way starting-work/finishing-work do,
# falling back to 'main' if origin/HEAD isn't set (e.g. no origin remote).
# Resolved before the no-op check below (not after) -- that check now needs
# it too.
DEFAULT_BRANCH=""
if REMOTE_HEAD="$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null)"; then
  # Wrapped in `if` rather than piped through `sed` -- under this script's
  # own `set -o pipefail`, a no-origin-remote repo makes `git symbolic-ref`
  # fail, and piping its output into `sed` would still propagate that
  # failure through the pipeline and abort the whole script here (verified
  # live in a throwaway no-origin test repo: exit 128, never reaching this
  # script's own exit-2 handling).
  DEFAULT_BRANCH="${REMOTE_HEAD#refs/remotes/origin/}"
fi
DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"

# "Does this repo use commitlint at all" is checked against BOTH the
# working tree (cheap, the common case for the many git-kit-using repos
# that never set commitlint up at all) AND the trusted ref -- checking the
# working tree alone let a fetched/contributed branch delete
# .commitlintrc.cjs/package.json locally to silently suppress this whole
# check, even though the trusted origin/<default-branch> setup was still
# there (found by cross-model-review, round 4). Exit 0 (genuine no-op)
# only when NEITHER signal indicates a setup -- so an ordinary repo with no
# commitlint setup at all still gets a silent, fast no-op exactly as
# before, with no spurious "couldn't resolve a trusted ref" noise.
WORKTREE_HAS_SETUP=1
if [ ! -f "$CONFIG_FILE" ] || [ ! -f "$WORKTREE_TOOLCHAIN_DIR/package.json" ]; then
  WORKTREE_HAS_SETUP=0
fi

TRUSTED_HAS_SETUP=0
if MSYS_NO_PATHCONV=1 git cat-file -e "origin/$DEFAULT_BRANCH:.commitlintrc.cjs" 2>/dev/null \
   && MSYS_NO_PATHCONV=1 git cat-file -e "origin/$DEFAULT_BRANCH:.github/commitlint-tools/package.json" 2>/dev/null; then
  TRUSTED_HAS_SETUP=1
fi

if [ "$WORKTREE_HAS_SETUP" -eq 0 ] && [ "$TRUSTED_HAS_SETUP" -eq 0 ]; then
  exit 0
fi

if ! command -v pnpm >/dev/null 2>&1; then
  echo "SKIP: pnpm not available -- local commitlint check could not run (CI will still enforce it)" >&2
  exit 2
fi

# Install/run entirely outside the tracked working tree, under .git/ -- a
# location every git-kit script already treats as local, untracked scratch
# space (write-git-kit-marker.sh's own marker file lives at
# "$GIT_DIR/git-kit-marker.txt"). This is what lets every file below be
# sourced from a trusted ref without ever mutating the developer's own
# checked-out copies as a side effect of running this check.
LOCAL_TOOLCHAIN_DIR="$GIT_DIR/commitlint-local-check"
mkdir -p "$LOCAL_TOOLCHAIN_DIR"

# MSYS_NO_PATHCONV=1: on Windows git-bash, MSYS's automatic path-conversion
# heuristic mangles a "ref:path" refspec containing a dotfile (verified
# live: "origin/main:.commitlintrc.cjs" silently became an invalid
# "origin\main;.commitlintrc.cjs" argument without this, making every
# lookup below always fail).
fetch_trusted() {
  # $1 = path at the trusted ref, $2 = destination file. Returns non-zero,
  # writing nothing to $2, if the trusted ref can't supply that path (no
  # origin remote, or the file doesn't exist there yet -- e.g. bootstrapping
  # this same feature).
  MSYS_NO_PATHCONV=1 git show "origin/$DEFAULT_BRANCH:$1" > "$2" 2>/dev/null
}

TRUSTED_CONFIG="$LOCAL_TOOLCHAIN_DIR/.commitlintrc.cjs.new"
TRUSTED_PKG="$LOCAL_TOOLCHAIN_DIR/package.json.new"
TRUSTED_LOCK="$LOCAL_TOOLCHAIN_DIR/pnpm-lock.yaml.new"
if ! fetch_trusted ".commitlintrc.cjs" "$TRUSTED_CONFIG" \
   || ! fetch_trusted ".github/commitlint-tools/package.json" "$TRUSTED_PKG" \
   || ! fetch_trusted ".github/commitlint-tools/pnpm-lock.yaml" "$TRUSTED_LOCK"; then
  # Never fall back to the working-tree copies here -- that would silently
  # re-open the exact execution risk this trusted-ref lookup exists to
  # close, for a caller with no way to tell "genuinely my own branch"
  # apart from "a fetched branch I haven't inspected." Skip the check
  # instead, same as the other infrastructure-gap cases in this script.
  echo "SKIP: could not read a trusted origin/$DEFAULT_BRANCH copy of the commitlint config/toolchain -- local commitlint check could not run (CI will still enforce it)" >&2
  rm -f "$TRUSTED_CONFIG" "$TRUSTED_PKG" "$TRUSTED_LOCK"
  exit 2
fi

if ! cmp -s "$CONFIG_FILE" "$TRUSTED_CONFIG"; then
  echo "Note: .commitlintrc.cjs differs from origin/$DEFAULT_BRANCH -- validating against the trusted origin/$DEFAULT_BRANCH copy, not this branch's own edit." >&2
fi

# Only reinstall when the trusted manifest/lockfile actually changed since
# the last SUCCESSFUL install (or nothing is installed yet) -- avoids a
# multi-second pnpm install on every single commit once the local cache is
# warm. Compared against a separate "last successfully installed" marker
# pair, never against package.json/pnpm-lock.yaml themselves -- those two
# get overwritten below unconditionally (pnpm needs them physically present
# at this exact path to run install at all), so comparing against them
# would read a promoted-but-not-yet-installed manifest as "already
# installed": if install then failed, the next run would see the cache
# files already matching the trusted copy and skip reinstalling entirely,
# silently executing the prior, stale node_modules/.bin/commitlint against
# rules that no longer match .commitlintrc.cjs (found by cross-model-review
# round 6 on the live PR, reproduced with a real ERR_PNPM_OUTDATED_LOCKFILE
# failure). The marker is only written after install actually succeeds.
INSTALLED_PKG_MARKER="$LOCAL_TOOLCHAIN_DIR/.last-installed-package.json"
INSTALLED_LOCK_MARKER="$LOCAL_TOOLCHAIN_DIR/.last-installed-pnpm-lock.yaml"
NEEDS_INSTALL=1
if [ -x "$LOCAL_TOOLCHAIN_DIR/node_modules/.bin/commitlint" ] \
   && cmp -s "$INSTALLED_PKG_MARKER" "$TRUSTED_PKG" 2>/dev/null \
   && cmp -s "$INSTALLED_LOCK_MARKER" "$TRUSTED_LOCK" 2>/dev/null; then
  NEEDS_INSTALL=0
fi

if ! mv "$TRUSTED_CONFIG" "$LOCAL_TOOLCHAIN_DIR/.commitlintrc.cjs" \
   || ! mv "$TRUSTED_PKG" "$LOCAL_TOOLCHAIN_DIR/package.json" \
   || ! mv "$TRUSTED_LOCK" "$LOCAL_TOOLCHAIN_DIR/pnpm-lock.yaml"; then
  echo "SKIP: could not write the local commitlint toolchain files -- local commitlint check could not run (CI will still enforce it)" >&2
  rm -f "$TRUSTED_CONFIG" "$TRUSTED_PKG" "$TRUSTED_LOCK"
  exit 2
fi

if [ "$NEEDS_INSTALL" -eq 1 ]; then
  echo "Installing isolated commitlint toolchain ($LOCAL_TOOLCHAIN_DIR, first use or after an update)..." >&2
  if ! pnpm --dir "$LOCAL_TOOLCHAIN_DIR" install --frozen-lockfile --ignore-scripts >&2; then
    echo "SKIP: commitlint toolchain install failed -- local commitlint check could not run (CI will still enforce it)" >&2
    exit 2
  fi
  # Install confirmed successful -- only now record what was installed, so
  # a failed install (caught above) never marks a manifest/lockfile pair as
  # trusted-and-installed when node_modules doesn't actually match it.
  cp "$LOCAL_TOOLCHAIN_DIR/package.json" "$INSTALLED_PKG_MARKER"
  cp "$LOCAL_TOOLCHAIN_DIR/pnpm-lock.yaml" "$INSTALLED_LOCK_MARKER"
fi

# A commitlint crash for a non-rule reason (a corrupted install, or a
# genuinely malformed .commitlintrc.cjs -- which would also be breaking CI
# identically for every contributor, not a silent local-only problem) still
# exits non-zero here, indistinguishable from exit 1's real rule-violation
# case. Accepted as a known limitation rather than solved: reliably telling
# "commitlint crashed" from "commitlint reported a real violation" isn't
# possible from the exit code alone without parsing its own output format,
# which would be fragile (found by cross-model-review, round 2; downgraded
# from the reviewer's proposed full fix as disproportionate to the risk).
#
# commitlint's own resolveExtends resolves module specifiers (e.g.
# @commitlint/config-conventional) relative to process.cwd() -- verified
# locally: neither --cwd nor -g change that, only actually changing the
# shell's own working directory does. `cd` here so the extended base
# config resolves from this directory's own install.
cd "$LOCAL_TOOLCHAIN_DIR"
./node_modules/.bin/commitlint --config .commitlintrc.cjs < "$MESSAGE_FILE"
