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

is_flagged() {
  local path="$1" name segments seg
  name="$(basename "$path")"
  case "$name" in
    .env|.env.*|*secret*|*credential*|*.key|*.pem|*password*|*token*|\
    id_rsa|id_ed25519|id_ecdsa|id_dsa|service-account.json|*.p12|*.pfx|*.jks|\
    .npmrc|.pgpass|.netrc)
      return 0
      ;;
  esac
  # Basename-only matching misses a sensitive *directory* component (e.g.
  # config/secrets/prod.yaml) -- also check each path segment against the
  # loose-substring patterns (the exact-filename and extension patterns above
  # don't apply to directory names, so they're deliberately not repeated here).
  IFS='/' read -ra segments <<< "$path"
  for seg in "${segments[@]}"; do
    case "$seg" in
      *secret*|*credential*|*password*|*token*)
        return 0
        ;;
    esac
  done
  return 1
}

emit() {
  if [ "$null_mode" = "1" ]; then
    printf '%s\0' "$1"
  else
    printf '%s\n' "$1"
  fi
}

# --name-status (not --name-only) and -M (rename detection) are required to
# catch a staged rename correctly: `git diff --cached --name-only` reports
# only the destination path for a rename, so a file renamed *into* a flagged
# directory (e.g. config/plain.txt -> config/secrets/plain.txt) would be
# flagged and unstaged at its new path only -- leaving the rename's other
# half (the staged deletion of the old path) untouched. Restoring just the
# new path from the index then silently turns the rename into "delete the
# old path, don't add the new one" once committed, rather than actually
# rejecting the rename. Emitting *both* paths for a flagged rename lets
# unstage-flagged-files.sh restore the whole rename, not half of it.
git -c diff.relative=false diff --cached --name-status -z -M | \
while IFS= read -r -d '' status; do
  case "$status" in
    R*)
      IFS= read -r -d '' old_path
      IFS= read -r -d '' new_path
      if is_flagged "$new_path" || is_flagged "$old_path"; then
        emit "$old_path"
        emit "$new_path"
      fi
      ;;
    *)
      IFS= read -r -d '' path
      if is_flagged "$path"; then
        emit "$path"
      fi
      ;;
  esac
done
