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
  echo "pnpm not available -- skipping local commitlint check (CI will still enforce it)" >&2
  exit 0
fi

if [ ! -x "$TOOLCHAIN_DIR/node_modules/.bin/commitlint" ]; then
  echo "Installing isolated commitlint toolchain (.github/commitlint-tools/, first run only)..." >&2
  pnpm --dir "$TOOLCHAIN_DIR" install --frozen-lockfile --ignore-scripts >&2
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
# The local .commitlintrc.cjs copy here is a plain, always-refreshed mirror
# of the repo-root file -- no trust-boundary restore-from-base-SHA step like
# CI's is needed locally, since a local commit run only ever lints the
# developer's own drafted message, never a fetched branch's CI grading.
cp "$CONFIG_FILE" "$TOOLCHAIN_DIR/.commitlintrc.cjs"

cd "$TOOLCHAIN_DIR"
./node_modules/.bin/commitlint --config .commitlintrc.cjs < "$MESSAGE_FILE"
