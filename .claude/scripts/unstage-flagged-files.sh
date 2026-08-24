#!/bin/bash
# Unstages every file scan-staged-files.sh flags as sensitive, without ever
# interpolating a scanned filename into a shell string. A flagged filename
# is untrusted staged-diff content (attacker-controlled on a fetched or
# contributed branch) -- double-quoting it inside a shell command does not
# suppress $(...)/``/`$VAR` expansion, so building a command string from it
# is a command-injection surface even when quoted. Feeding filenames to
# `git restore` via --pathspec-from-file/--pathspec-file-nul, with the
# repo-root-anchored, glob-disabled `:(top,literal)` magic prepended to
# each entry, avoids shell interpolation and cwd-relativity/glob-over-match
# issues entirely.
#
# Called by the commit skill (step 7) after scan-staged-files.sh flags one
# or more files. No output on success; exits non-zero if the restore fails.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/scan-staged-files.sh" --null | while IFS= read -r -d '' file; do
  printf ':(top,literal)%s\0' "$file"
done | git restore --staged --pathspec-from-file=- --pathspec-file-nul
