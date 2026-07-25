#!/bin/bash
# R20 Duplicate Fact Sweep: find stale rule-count-ceiling mentions across the
# plugin tree before finalizing a new plugin-rulebook rule addition. Covers
# the "grep the whole plugin tree" step of references/adding-a-new-rule.md
# Section 3 -- that file's known-locations list remains the fallback of
# record for a restatement this pattern doesn't anticipate.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <previous-rule-number>" >&2
  echo "Example: when adding R25, run: $0 24" >&2
  echo "  (sweeps for stale R1-R24 / R1<en-dash>R24 / \"24 total\" mentions)" >&2
  exit 1
fi

PREV="$1"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Matches the previous ceiling's restatements: "R1-R24", "R1–R24" (en dash),
# and "24 total". Deliberately greps the OLD number, not RNN -- per
# adding-a-new-rule.md's note, a stale mention cites the ceiling being
# replaced, not the one being added.
PATTERN="R1[-–]R${PREV}\\b|\\b${PREV} total\\b"

MATCHES="$(cd "$REPO_ROOT" && grep -rEn "$PATTERN" \
  --include="*.md" --include="*.json" \
  --exclude-dir=".git" \
  --exclude-dir="output" \
  --exclude-dir="worktrees" \
  --exclude-dir="node_modules" \
  --exclude-dir=".draft" \
  --exclude-dir=".backup" \
  --exclude-dir=".temp" \
  . || true)"

if [ -z "$MATCHES" ]; then
  echo "No stale R1-R${PREV} / ${PREV}-total mentions found."
  exit 0
fi

echo "$MATCHES"
echo ""
COUNT="$(echo "$MATCHES" | wc -l)"
echo "${COUNT} stale mention(s) found above -- update each to the new ceiling before finalizing."
