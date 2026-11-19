#!/bin/bash
set -euo pipefail

# Copy to ~/.codex/hooks/block-dangerous-command.sh.
# Codex PreToolUse hook for Bash. Blocks high-risk command patterns before
# execution. This is a guardrail, not a security boundary; keep sandboxing on.

block() {
    printf 'BLOCKED: %s\n' "$1" >&2
    exit 2
}

# Fail closed: without a parsed command the checks below cannot run.
command -v jq >/dev/null 2>&1 || block "jq is required by the command-policy hook."

INPUT=$(cat)
CMD=$(printf '%s' "${INPUT}" | jq -r '.tool_input.command // empty') ||
    block "Could not parse the hook input."

[[ -z "${CMD}" ]] && exit 0

COMMAND_PREFIX='(^|;[[:space:]]*|&&[[:space:]]*|[|][|][[:space:]]*|[|][[:space:]]*)'
PUSH_FORCE_RE='git[[:space:]]+push([^;&|]*)--force'
PUSH_FORCE_RE+='|git[[:space:]]+push([^;&|]*)[[:space:]]-f([[:space:]]|$)'
# A leading `+` on a refspec (`git push origin +main`) is also a force push.
PUSH_FORCE_RE+='|git[[:space:]]+push([^;&|]*)[[:space:]][+]'
DIRECT_MAIN_RE='git[[:space:]]+push([^;&|]*[[:space:]])?'
DIRECT_MAIN_RE+='(origin[[:space:]]+)?[+]?(main|master)([[:space:]]|$)'
DIRECT_MAIN_RE+='|git[[:space:]]+push[^;&|]*:(refs/heads/)?(main|master)([[:space:]]|$)'
FETCH_TO_SHELL_RE='(curl|wget|iwr|irm|invoke-webrequest|invoke-restmethod)[^|]*[|][[:space:]]*'
FETCH_TO_SHELL_RE+='(bash|sh|zsh|iex|invoke-expression)([[:space:]]|$)'

if printf '%s\n' "${CMD}" | grep -qiE "${COMMAND_PREFIX}rm[[:space:]]" &&
    printf '%s\n' "${CMD}" | grep -qiE '(^|[[:space:]])-[a-zA-Z]*[rR]|--recursive' &&
    printf '%s\n' "${CMD}" | grep -qiE '(^|[[:space:]])-[a-zA-Z]*[fF]|--force'; then
    block "Use trash instead of rm -rf."
fi

if printf '%s\n' "${CMD}" | grep -qiE "${COMMAND_PREFIX}sudo([[:space:]]|$)"; then
    block "Do not run sudo from Codex without explicit human approval."
fi

if printf '%s\n' "${CMD}" | grep -qiE "${COMMAND_PREFIX}mkfs([.[:alnum:]_-]*)([[:space:]]|$)"; then
    block "Refusing filesystem formatting commands."
fi

if printf '%s\n' "${CMD}" | grep -qiE "${COMMAND_PREFIX}dd([[:space:]]|$)"; then
    block "Refusing raw disk write command dd."
fi

if printf '%s\n' "${CMD}" | grep -qiE "${FETCH_TO_SHELL_RE}"; then
    block "Do not pipe downloaded scripts directly into a shell."
fi

if printf '%s\n' "${CMD}" | grep -qiE "${PUSH_FORCE_RE}"; then
    block "Do not force-push unless the user explicitly requested it."
fi

if printf '%s\n' "${CMD}" | grep -qiE 'git[[:space:]]+reset[[:space:]]+--hard'; then
    block "Do not run git reset --hard unless the user explicitly requested it."
fi

if printf '%s\n' "${CMD}" | grep -qiE "${DIRECT_MAIN_RE}"; then
    block "Use feature branches and PRs; do not push directly to main/master."
fi

exit 0
