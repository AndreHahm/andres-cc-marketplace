#!/usr/bin/env bash
set -euo pipefail
# Prints a short context note at SessionStart, only when an OpenRouter key is set.
# Blocks nothing, reads no stdin, and never prints the key.
has_key() {
  [ -n "${OPENROUTER_API_KEY:-}" ] && return 0
  local dir parent
  dir=$PWD
  while :; do
    if [ -f "$dir/.env" ] && grep -Eq '^[[:space:]]*(export[[:space:]]+)?OPENROUTER_API_KEY[[:space:]]*=[[:space:]]*[^[:space:]#]' "$dir/.env"; then
      return 0
    fi
    parent=$(dirname "$dir")
    [ "$parent" != "$dir" ] || return 1
    dir=$parent
  done
}
has_key || exit 0
cat <<'NOTE'
decision-kit: before acting on a critical, security-relevant or low- or mid-confidence decision you made yourself, run the consulting-decision-model skill. Skip it when the user explicitly asked for that exact action, unless that order rests on your own judgment. It can only add a stop, never authorize.
NOTE
