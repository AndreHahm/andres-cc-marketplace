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
CMD=$(jq -r '.tool_input.command // empty' <<<"${INPUT}") ||
    block "Could not parse the hook input."

[[ -z "${CMD}" ]] && exit 0

# Here-strings, not `printf | grep -q`: under pipefail, grep -q exiting early
# can kill printf with SIGPIPE on a long command and turn a match into a miss.
matches() {
    grep -qiE "$1" <<<"${CMD}"
}

COMMAND_PREFIX='(^|;[[:space:]]*|&&[[:space:]]*|[|][|][[:space:]]*|[|][[:space:]]*)'
# `git push`, also after git's global options (`git -C repo push`, `git -c k=v push`).
GIT_PUSH='git([[:space:]]+-[Cc][[:space:]]+[^[:space:];&|]+|[[:space:]]+-[^[:space:];&|]+)*[[:space:]]+push'
PUSH_FORCE_RE="${GIT_PUSH}([^;&|]*)--force"
PUSH_FORCE_RE+="|${GIT_PUSH}([^;&|]*)[[:space:]]-f([[:space:]]|\$)"
# A leading `+` on a refspec (`git push origin +main`) is also a force push.
PUSH_FORCE_RE+="|${GIT_PUSH}([^;&|]*)[[:space:]][+]"
DIRECT_MAIN_RE="${GIT_PUSH}([^;&|]*[[:space:]])?"
DIRECT_MAIN_RE+='(origin[[:space:]]+)?[+]?(main|master)([[:space:]]|$)'
DIRECT_MAIN_RE+="|${GIT_PUSH}[^;&|]*:(refs/heads/)?(main|master)([[:space:]]|\$)"
FETCH_TO_SHELL_RE='(curl|wget|iwr|irm|invoke-webrequest|invoke-restmethod)[^|]*[|][[:space:]]*'
FETCH_TO_SHELL_RE+='(bash|sh|zsh|iex|invoke-expression)([[:space:]]|$)'

# Check the flags of each rm invocation only, so `rm x && cp -rf a b` passes.
# An rm behind a common wrapper (`xargs rm -rf`, `command rm`) or given by path
# (`/bin/rm`) counts too; the wrapper's own options are checked with it.
RM_WRAPPER='(xargs|command|builtin|env|nice|nohup|time|exec|timeout|doas)'
RM_RE="${COMMAND_PREFIX}(${RM_WRAPPER}[[:space:]]([^;&|]*[[:space:]])?)?"
RM_RE+="([^[:space:];&|]*/)?[\"']?rm[\"']?[[:space:]][^;&|]*"
RM_SEGMENTS=$(grep -oiE "${RM_RE}" <<<"${CMD}" || true)
while IFS= read -r segment; do
    [[ -z "${segment}" ]] && continue
    if grep -qiE '(^|[[:space:]])-[a-zA-Z]*[rR]|--recursive' <<<"${segment}" &&
        grep -qiE '(^|[[:space:]])-[a-zA-Z]*[fF]|--force' <<<"${segment}"; then
        block "Use trash instead of rm -rf."
    fi
done <<<"${RM_SEGMENTS}"

if matches "${COMMAND_PREFIX}sudo([[:space:]]|$)"; then
    block "Do not run sudo from Codex without explicit human approval."
fi

if matches "${COMMAND_PREFIX}mkfs([.[:alnum:]_-]*)([[:space:]]|$)"; then
    block "Refusing filesystem formatting commands."
fi

if matches "${COMMAND_PREFIX}dd([[:space:]]|$)"; then
    block "Refusing raw disk write command dd."
fi

if matches "${FETCH_TO_SHELL_RE}"; then
    block "Do not pipe downloaded scripts directly into a shell."
fi

if matches "${PUSH_FORCE_RE}"; then
    block "Do not force-push unless the user explicitly requested it."
fi

if matches 'git[[:space:]]+reset[[:space:]]+--hard'; then
    block "Do not run git reset --hard unless the user explicitly requested it."
fi

if matches "${DIRECT_MAIN_RE}"; then
    block "Use feature branches and PRs; do not push directly to main/master."
fi

exit 0
