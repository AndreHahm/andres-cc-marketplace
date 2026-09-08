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

REPO_ROOT="$(git rev-parse --show-toplevel)"
SECRETLINTIGNORE="$REPO_ROOT/.secretlintignore"

null_mode=0
if [ "${1:-}" = "--null" ] || [ "${1:-}" = "-z" ]; then
  null_mode=1
fi

# True if $1 (a path as reported by `git diff`, already repo-root-relative
# per diff.relative=false below) is covered by .gitignore and/or
# .secretlintignore (issue #295) -- consulted as a combined signal: a file
# matching a sensitive-filename pattern below is not flagged if either
# ignore file already covers it.
#
# --no-index is required: without it, `git check-ignore` never reports an
# already-TRACKED path as ignored, regardless of pattern match (verified
# live: exit 1 for a tracked file matching a real .secretlintignore entry,
# exit 0 once --no-index is added) -- since every file this function is
# asked about is, by definition, staged/tracked, omitting --no-index would
# make this check silently never match anything.
#
# core.excludesFile gracefully contributes no extra patterns when
# .secretlintignore doesn't exist (e.g. a repo that installed git-kit
# without adopting this convention) -- degrades to plain .gitignore
# matching there, no behavior change for that case.
#
# NOTE (deliberate tradeoff, issue #295): this also exempts a force-added,
# otherwise-gitignored file (e.g. .env) from THIS local pre-commit
# convenience check specifically. The CI secretlint job's own
# .secretlintignore deliberately does not list .env/.env.*, so that job
# still catches a force-added .env even though this script no longer flags
# it locally. That compensating-CI-check reasoning does NOT extend to a
# path .secretlintignore DOES list (e.g. the 5 curated plugin files, or
# .secretlintignore itself): the same entry that exempts a path here is
# also what makes CI's secretlint job skip content-scanning it, so a real
# secret introduced into one of those specific, already-allowlisted files
# in the future would not be caught by either layer (security review
# finding, issue #295). Accepted as consistent with the existing model --
# CI's own secretlintignore already carried this same residual risk before
# this change, for the same small, human-curated set of paths -- rather
# than narrowed further here, unlike guarded-dispatch.mjs's stricter,
# exact-path-and-no-strict-pattern gate (that consumer protects an
# unsandboxed danger-full-access process against the WHOLE repo tree, a
# meaningfully higher-stakes surface than this human-reviewed, staged-files-
# only local convenience check).
#
# Separately, note that .gitignore's own negations for .claude/.codex/
# .agents/.devin (`!.claude/` etc.) take precedence over core.excludesFile
# per git's own source-precedence rules -- verified live: `/.claude` in
# .secretlintignore does NOT actually exempt an arbitrary .claude/** path
# here, only the narrower sub-patterns .gitignore itself already carries
# (e.g. `.claude/worktrees/`) do. `/tests` has no such negation and works
# as documented. This divergence from guarded-dispatch.mjs's JS-side
# matcher (which never reads .gitignore, so its own directory-scale
# matching would have been fully broad before it was tightened to
# exact-path-only) is a side effect of git's precedence rules, not a
# design choice -- noted here so it isn't mistaken for a bug later.
is_covered_by_ignore_files() {
  git -C "$REPO_ROOT" -c core.excludesFile="$SECRETLINTIGNORE" check-ignore -q --no-index -- "$1"
}

is_flagged() {
  local path="$1" name segments seg matched=1
  name="$(basename "$path")"
  case "$name" in
    .env|.env.*|*secret*|*credential*|*.key|*.pem|*password*|*token*|\
    id_rsa|id_ed25519|id_ecdsa|id_dsa|service-account.json|*.p12|*.pfx|*.jks|\
    .npmrc|.pgpass|.netrc)
      matched=0
      ;;
  esac
  if [ "$matched" != 0 ]; then
    # Basename-only matching misses a sensitive *directory* component (e.g.
    # config/secrets/prod.yaml) -- also check each path segment against the
    # loose-substring patterns (the exact-filename and extension patterns
    # above don't apply to directory names, so they're deliberately not
    # repeated here).
    IFS='/' read -ra segments <<< "$path"
    for seg in "${segments[@]}"; do
      case "$seg" in
        *secret*|*credential*|*password*|*token*)
          matched=0
          break
          ;;
      esac
    done
  fi
  [ "$matched" = 0 ] || return 1
  is_covered_by_ignore_files "$path" && return 1
  return 0
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
