#!/bin/bash
# Scans currently staged files against git-kit's fixed sensitive-filename
# patterns and prints the matches, one per line by default (no output = no
# matches). Pass --null (or -z) to emit NUL-separated output instead -- the
# form unstage-flagged-files.sh consumes, since a flagged filename is
# untrusted staged-diff content and must never be interpolated into a shell
# string even quoted (double quotes do not suppress $()/``/`$VAR` expansion).
#
# Filename-pattern-only: this does not inspect staged diff content for
# credential-shaped strings (API keys, tokens) in a file whose name doesn't
# itself match one of these patterns.
#
# Called by the commit skill (step 7), immediately after staging, so the
# pattern list is applied deterministically instead of relying on the
# model's own judgment.
set -euo pipefail

git rev-parse --git-dir >/dev/null 2>&1 || { echo "Error: not inside a git repository" >&2; exit 1; }

null_mode=0
if [ "${1:-}" = "--null" ] || [ "${1:-}" = "-z" ]; then
  null_mode=1
fi

git -c diff.relative=false diff --cached --name-only -z | while IFS= read -r -d '' file; do
  flagged=0
  name="$(basename "$file")"
  case "$name" in
    .env|.env.*|*secret*|*credential*|*.key|*.pem|*password*|*token*|\
    id_rsa|id_ed25519|id_ecdsa|id_dsa|service-account.json|*.p12|*.pfx|*.jks|\
    .npmrc|.pgpass|.netrc)
      flagged=1
      ;;
  esac
  # Basename-only matching misses a sensitive *directory* component (e.g.
  # config/secrets/prod.yaml) -- also check each path segment against the
  # loose-substring patterns (the exact-filename and extension patterns above
  # don't apply to directory names, so they're deliberately not repeated here).
  if [ "$flagged" = "0" ]; then
    IFS='/' read -ra segments <<< "$file"
    for seg in "${segments[@]}"; do
      case "$seg" in
        *secret*|*credential*|*password*|*token*)
          flagged=1
          break
          ;;
      esac
    done
  fi
  if [ "$flagged" = "1" ]; then
    if [ "$null_mode" = "1" ]; then
      printf '%s\0' "$file"
    else
      printf '%s\n' "$file"
    fi
  fi
done
