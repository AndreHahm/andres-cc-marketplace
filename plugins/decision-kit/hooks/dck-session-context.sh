#!/usr/bin/env bash
# Prints a short context note at SessionStart, only when an OpenRouter key is set.
# Blocks nothing, reads no stdin, and never prints the key.
[ -n "${OPENROUTER_API_KEY:-}" ] || exit 0
cat <<'NOTE'
decision-kit: before acting on a critical, security-relevant or low- or mid-confidence decision you made yourself, run the consulting-decision-model skill. Skip it when the user explicitly asked for that exact action, unless that order rests on your own judgment. It can only add a stop, never authorize.
NOTE
