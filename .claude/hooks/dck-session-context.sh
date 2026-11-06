#!/usr/bin/env bash
set -euo pipefail
# Prints a short context note at SessionStart, only when an OpenRouter key is set.
# Blocks nothing, reads no stdin, and never prints the key.
readonly EXAMPLE_VALUE=your-openrouter-api-key
readonly BOM=$'\xEF\xBB\xBF'
has_key() {
  if [ -n "${OPENROUTER_API_KEY:-}" ]; then
    [ "$OPENROUTER_API_KEY" != "$EXAMPLE_VALUE" ]
    return
  fi
  local dir line parent
  dir=$PWD
  while :; do
    if [ -f "$dir/.env" ]; then
      line=$(LC_ALL=C grep -E "^(${BOM})?"'[[:space:]]*(export[[:space:]]+)?OPENROUTER_API_KEY[[:space:]]*=[[:space:]]*[^[:space:]#]' "$dir/.env" 2>/dev/null | tail -n 1 || true)
      if [ -n "$line" ]; then
        case "$line" in
          *"$EXAMPLE_VALUE"*) return 1 ;;
          *) return 0 ;;
        esac
      fi
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
