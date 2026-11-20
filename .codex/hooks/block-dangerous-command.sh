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
# `git <subcommand>`, also after git's global options (`git -C repo push`, `git -c k=v push`,
# `git --git-dir path push`), with an option value that may be quoted (`git -C "a b" push`).
# The exec-policy rules match exact tokens, so they cannot catch these forms; the hook does.
GIT_OPT_VALUE="([^[:space:];&|\"']|\"[^\"]*\"|'[^']*')+"
GIT_OPT="([[:space:]]+-[Cc][[:space:]]+${GIT_OPT_VALUE}"
GIT_OPT+="|[[:space:]]+--(git-dir|work-tree|namespace|exec-path|super-prefix|config-env)"
GIT_OPT+="[[:space:]]+${GIT_OPT_VALUE}"
GIT_OPT+="|[[:space:]]+-[^[:space:];&|]+)"
GIT_CMD="git${GIT_OPT}*[[:space:]]+"
# A git command at the start of a command segment, so text that only mentions one
# (a commit message, a PR body, a heredoc) does not match. A segment starts at the
# line start or after ; & | ( { ! or `=` plus a backtick (`x=`git ...``). A bare
# backtick does not start one: commit messages and docs quote commands in
# backticks. Then a segment may carry shell keywords
# (`if`, `then`, ...), variable assignments (`GIT_EDITOR=true`), command wrappers
# with their options (`env X=1`, `timeout 60`, the same list as RM_WRAPPER below)
# and a path (`/usr/bin/git`).
SEGMENT_START='(^|[;&|({!]|=`)[[:space:]]*((if|then|do|else|elif|while|until|!)[[:space:]]+)*'
SEGMENT_START+='([A-Za-z_][A-Za-z0-9_]*=[^[:space:];&|]*[[:space:]]+)*'
SEGMENT_START+='((xargs|command|builtin|env|nice|nohup|time|exec|timeout|doas)'
SEGMENT_START+='([[:space:]]+(-[^[:space:];&|]*|[0-9][^[:space:];&|]*|[A-Za-z_][A-Za-z0-9_]*=[^[:space:];&|]*))*'
SEGMENT_START+='[[:space:]]+)*([^[:space:];&|]*/)?'
GIT_AT_START="${SEGMENT_START}${GIT_CMD}"
# The same, but only with at least one global option before the subcommand.
GIT_WITH_OPTS_AT_START="${SEGMENT_START}git${GIT_OPT}+[[:space:]]+"
# Git commands default.rules forbids. Its exact-token rules cannot match them once a global
# option comes first (`git -C repo stash`), so the hook blocks that form.
# A subcommand ends at whitespace, the end, or the close of a group (`$(git -C x stash)`).
GIT_SUB_END='([[:space:]);}`]|$)'
FORBIDDEN_GIT_RE="(reset|filter-branch|stash|clone|cherry-pick|revert|merge)${GIT_SUB_END}"
FORBIDDEN_GIT_RE+="|branch([^;&|]*[[:space:]])?(-[dD]|--delete)([[:space:]]|\$)"
FORBIDDEN_GIT_RE+="|tag([^;&|]*[[:space:]])?-d([[:space:]]|\$)"
FORBIDDEN_GIT_RE+="|reflog[[:space:]]+(expire|delete)([[:space:]]|\$)"
FORBIDDEN_GIT_RE+="|commit([^;&|]*[[:space:]])?--amend([[:space:]]|\$)"
FORBIDDEN_GIT_RE+="|clean([^;&|]*[[:space:]])?(-[a-zA-Z]*f|--force)"
FORBIDDEN_GIT_RE+="|pull([^;&|]*[[:space:]])?(--rebase|-r|--no-ff|--squash|--no-rebase)([[:space:]=]|\$)"
# A package publish with options or a workspace before `publish` (`npm -w pkg publish`,
# `pnpm --filter pkg publish`, `yarn workspaces foreach -A npm publish`). default.rules
# forbids the plain forms but cannot match a value before the subcommand.
PUBLISH_RE="${SEGMENT_START}(npm|pnpm|bun|yarn)([[:space:]]+[^;&|[:space:]]+)*"
PUBLISH_RE+="[[:space:]]+publish${GIT_SUB_END}"
GIT_PUSH="${GIT_CMD}push"
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

if matches "${GIT_AT_START}reset([^;&|]*[[:space:]])?--hard"; then
    block "Do not run git reset --hard unless the user explicitly requested it."
fi

if matches "${GIT_AT_START}rebase${GIT_SUB_END}"; then
    block "Do not rebase; propose a follow-up commit or a fresh branch instead."
fi

if matches "${GIT_WITH_OPTS_AT_START}(${FORBIDDEN_GIT_RE})"; then
    block "This git command is forbidden by the exec-policy rules, also with git -C or other global options."
fi

if matches "${PUBLISH_RE}"; then
    block "Publishing packages is not allowed from Codex; publish manually."
fi

if matches "${DIRECT_MAIN_RE}"; then
    block "Use feature branches and PRs; do not push directly to main/master."
fi

exit 0
