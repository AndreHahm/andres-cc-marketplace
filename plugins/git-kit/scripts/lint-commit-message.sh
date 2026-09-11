#!/bin/bash
# Lints a drafted commit message against this repository's real commitlint
# config, using the same isolated toolchain CI's commit-branch-guard.yml
# workflow installs (.github/commitlint-tools/) -- not a hand-maintained
# approximation of commitlint's rules (e.g. a hardcoded 100-char setting),
# which could silently drift out of sync with .commitlintrc.cjs or its
# extended @commitlint/config-conventional base if either ever changes.
# Running the real tool can't drift by construction.
#
# A no-op (exit 0, no output) when this repository has no commitlint setup
# at all (.commitlintrc.cjs / .github/commitlint-tools/package.json
# missing) -- git-kit is a marketplace plugin used across repos that may
# not have either.
#
# Exit codes: 0 = no-op or checked-and-clean; 1 = a real commitlint rule
# violation (its own output names the rule(s) in brackets); 2 = the check
# could not run at all (pnpm missing, or the toolchain install failed --
# e.g. offline/blocked registry) -- distinct from 1 so a caller never
# mistakes an infrastructure failure for a message-content violation. Every
# exit-2 path prints a line prefixed "SKIP:" to stderr identifying why.
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
TOOLCHAIN_DIR="$REPO_ROOT/.github/commitlint-tools"
CONFIG_FILE="$REPO_ROOT/.commitlintrc.cjs"

if [ ! -f "$CONFIG_FILE" ] || [ ! -f "$TOOLCHAIN_DIR/package.json" ]; then
  # This repository has no commitlint setup -- nothing to check against.
  exit 0
fi

if ! command -v pnpm >/dev/null 2>&1; then
  echo "SKIP: pnpm not available -- local commitlint check could not run (CI will still enforce it)" >&2
  exit 2
fi

if [ ! -x "$TOOLCHAIN_DIR/node_modules/.bin/commitlint" ]; then
  echo "Installing isolated commitlint toolchain (.github/commitlint-tools/, first run only)..." >&2
  if ! pnpm --dir "$TOOLCHAIN_DIR" install --frozen-lockfile --ignore-scripts >&2; then
    echo "SKIP: commitlint toolchain install failed -- local commitlint check could not run (CI will still enforce it)" >&2
    exit 2
  fi
fi

# commitlint's own resolveExtends resolves module specifiers (e.g.
# @commitlint/config-conventional, named by this repo's own .commitlintrc.cjs
# `extends`) relative to process.cwd() -- verified locally: neither --cwd
# nor -g change that, only actually changing the shell's own working
# directory does (same finding commit-branch-guard.yml's own comment
# documents for CI). `cd` into the toolchain directory so the extended base
# config resolves from ITS OWN install, not the repo root, which has no
# node_modules at all.
#
# .commitlintrc.cjs is a CommonJS module -- commitlint's --config flag
# `require()`s it, executing whatever top-level code it contains, not just
# reading it as data. Loading the raw checked-out working-tree copy would
# let a fetched/contributed branch's own .commitlintrc.cjs run with this
# developer's local privileges the moment `commit` runs on it -- the same
# "attacker-controlled on a fetched branch" threat model this file's own
# scan-staged-files.sh/stage-selected-files.sh/lint-staged-python.sh
# siblings already treat as live (found by cross-model-review, round 2).
# Mirror CI's own trust-boundary restore instead: load it from a trusted
# ref (origin/<default branch>), never the working tree directly. Resolve
# the default branch the same way starting-work/finishing-work do, falling
# back to 'main' if origin/HEAD isn't set (e.g. no origin remote).
DEFAULT_BRANCH="$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's#^refs/remotes/origin/##')"
DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"

TRUSTED_CONFIG="$(mktemp)"
# MSYS_NO_PATHCONV=1: on Windows git-bash, MSYS's automatic path-conversion
# heuristic mangles a "ref:path" refspec containing a dotfile (verified
# live: "origin/main:.commitlintrc.cjs" silently became an invalid
# "origin\main;.commitlintrc.cjs" argument without this, making the lookup
# always fail and silently fall through to the working-tree copy below --
# defeating this fix's entire purpose on the platform it was written on).
if MSYS_NO_PATHCONV=1 git show "origin/$DEFAULT_BRANCH:.commitlintrc.cjs" > "$TRUSTED_CONFIG" 2>/dev/null; then
  if ! cmp -s "$CONFIG_FILE" "$TRUSTED_CONFIG"; then
    echo "Note: .commitlintrc.cjs differs from origin/$DEFAULT_BRANCH -- validating against the trusted origin/$DEFAULT_BRANCH copy, not this branch's own edit." >&2
  fi
  CONFIG_SOURCE="$TRUSTED_CONFIG"
else
  # No origin remote, or the file doesn't exist there yet (e.g. bootstrapping
  # this same feature) -- fall back to the working-tree copy, the only one
  # available; still better than refusing to check anything at all.
  echo "Note: could not read a trusted origin/$DEFAULT_BRANCH copy of .commitlintrc.cjs -- falling back to this branch's own working-tree copy." >&2
  CONFIG_SOURCE="$CONFIG_FILE"
fi
if ! cp "$CONFIG_SOURCE" "$TOOLCHAIN_DIR/.commitlintrc.cjs"; then
  echo "SKIP: could not write the local commitlint config copy -- local commitlint check could not run (CI will still enforce it)" >&2
  rm -f "$TRUSTED_CONFIG"
  exit 2
fi
rm -f "$TRUSTED_CONFIG"

# A commitlint crash for a non-rule reason (a corrupted install, or a
# genuinely malformed .commitlintrc.cjs -- which would also be breaking CI
# identically for every contributor, not a silent local-only problem) still
# exits non-zero here, indistinguishable from exit 1's real rule-violation
# case. Accepted as a known limitation rather than solved: reliably telling
# "commitlint crashed" from "commitlint reported a real violation" isn't
# possible from the exit code alone without parsing its own output format,
# which would be fragile (found by cross-model-review, round 2; downgraded
# from the reviewer's proposed full fix as disproportionate to the risk).
cd "$TOOLCHAIN_DIR"
./node_modules/.bin/commitlint --config .commitlintrc.cjs < "$MESSAGE_FILE"
