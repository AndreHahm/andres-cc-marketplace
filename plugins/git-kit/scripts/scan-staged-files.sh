#!/bin/bash
# Scans currently staged files against git-kit's fixed sensitive-filename
# patterns and prints the matches, one per line (no output = no matches).
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

git diff --cached --name-only -z | while IFS= read -r -d '' file; do
  name="$(basename "$file")"
  case "$name" in
    .env|.env.*|*secret*|*credential*|*.key|*.pem|*password*|*token*|\
    id_rsa|id_ed25519|id_ecdsa|id_dsa|service-account.json|*.p12|*.pfx|*.jks|\
    .npmrc|.pgpass|.netrc)
      echo "$file"
      ;;
  esac
done
