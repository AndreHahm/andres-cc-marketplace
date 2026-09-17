#!/usr/bin/env bash
#
# SessionStart hook: lightweight check that the Antigravity CLI (`agy`) is usable.
# Warns on stderr but NEVER fails the session (always exits 0). The full health
# check lives in scripts/doctor.sh — this one stays fast (no `agy models` network
# call) so it doesn't slow every session start.
#
set -uo pipefail

if ! command -v agy >/dev/null 2>&1; then
  echo "[antigravity] agy not on PATH — install the Antigravity CLI to enable delegation:" >&2
  echo "[antigravity]   https://antigravity.google/docs/cli-using" >&2
  exit 0
fi

if ! agy --version >/dev/null 2>&1; then
  echo "[antigravity] agy is on PATH but '--version' failed — it may need authentication (run \`agy\` once)." >&2
fi

exit 0
