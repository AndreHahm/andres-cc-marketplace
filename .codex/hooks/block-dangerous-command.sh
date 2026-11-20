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
# A native Windows jq.exe writes every newline as CRLF, which would stop the
# backslash-newline join below from matching. Only when this jq adds CRs, remove the
# one it put before each newline. A CR the command itself holds stays, so the checks see
# the bytes bash sees: bash does not end a heredoc on `EOF` + CR. Git Bash already drops
# jq's CR at the end of a command substitution, so the probe has a newline inside and the
# last CR is left alone (one left over can only make the checks block more).
if [[ "$(jq -rn '"a\nb"')" == $'a\r\nb' ]]; then
    CMD=${CMD//$'\r\n'/$'\n'}
fi

[[ -z "${CMD}" ]] && exit 0

# The command without its heredoc body, for the checks that look for a command at the
# start of a line, so a note or commit message that mentions `git rebase` is text, not a
# command. Parsing bash in general proved unsafe (four review passes each found a way to
# hide a line that bash runs), so only these whole commands lose their body:
#   cat > FILE <<'EOF'   (or >> FILE, or the redirection after the delimiter)
#   git commit [-flags] -m "$(cat <<'EOF'   ... EOF, then a last line )"
# The delimiter must be single-quoted, FILE a plain path, and no body line may start with
# the delimiter (bash 5.3 also ends a heredoc inside $( at a line such as EOF) ). The first
# line, and the closing )" of the commit form, stay in and are checked. Any other command,
# including one with more lines after the heredoc, is checked whole.
# BINMODE=3 stops gawk on Windows from dropping CRs, so a line EOF + CR, which does not end
# the heredoc in bash, does not end it here either. Other awks ignore it.
strip_heredocs() {
    awk -v BINMODE=3 -v sq="'" -v dq='"' '
{ line[NR] = $0 }
END {
    n = NR
    w = "[A-Za-z_][A-Za-z0-9_]*"
    f = ">>?[ \t]*[A-Za-z0-9_./-]+"
    form = 0
    if (line[1] ~ ("^cat[ \t]+" f "[ \t]+<<[ \t]*" sq w sq "$") ||
        line[1] ~ ("^cat[ \t]+<<[ \t]*" sq w sq "[ \t]+" f "$")) form = 1
    else if (line[1] ~ ("^git[ \t]+commit([ \t]+-[A-Za-z0-9-]+)*[ \t]+-m[ \t]+" dq "[$][(]cat[ \t]+<<[ \t]*" sq w sq "$")) form = 2
    last = n
    if (form == 2) { if (line[n] != (")" dq)) form = 0; last = n - 1 }
    term = line[1]
    sub("^[^<]*<<[ \t]*" sq, "", term)
    sub(sq ".*$", "", term)
    if (last < 2 || line[last] != term) form = 0
    for (i = 2; form && i < last; i++) if (index(line[i], term) == 1) form = 0
    # Bash before 4.0 finds the end of $( by scanning the text, so a ) in the body could end
    # it early. The commit form keeps its body unless the scan cannot: parentheses balanced
    # and never closing more than they opened, no quote, backtick or backslash, and no # with
    # a parenthesis after it on its line.
    depth = 0
    for (i = 2; form == 2 && i < last; i++) {
        s = line[i]
        if (index(s, sq) || index(s, dq) || index(s, "`") || index(s, "\\")) form = 0
        h = index(s, "#")
        if (h && substr(s, h) ~ /[()]/) form = 0
        for (j = 1; form && j <= length(s); j++) {
            c = substr(s, j, 1)
            if (c == "(") depth++
            else if (c == ")" && --depth < 0) form = 0
        }
    }
    if (form == 2 && depth != 0) form = 0
    if (!form) { for (i = 1; i <= n; i++) print line[i]; exit }
    print line[1]
    if (form == 2) print line[n]
}'
}

# CMD_CODE with the quoted value of a message or pattern option blanked (`-m "use --amend"`
# becomes `-m ""`), for the forbidden-git check only, so text inside a message is not
# read as a flag. The scanner tracks quotes like bash (single, double, $'...', backslash).
# A line is not blanked when it holds `$(`, a backtick, `${` or `$'`, or names a shell,
# ssh, eval, source or a command runner; once a quote is left open at the end of a line,
# no later line is blanked, since bash is still inside that string.
blank_flag_values() {
    awk -v BINMODE=3 -v sq="'" -v dq='"' '
# Index of the quote q that closes a string opened before position i, or 0 if none
# on this line. esc: a backslash escapes the next character (double and ANSI-C quotes).
function close_at(s, i, q, esc,    n, c) {
    n = length(s)
    while (i <= n) {
        c = substr(s, i, 1)
        if (esc && c == "\\") { i += 2; continue }
        if (c == q) return i
        i++
    }
    return 0
}
# Copy line s, blanking an option value when blank is set. An unclosed quote sets open
# and returns s unchanged.
function scan(s, blank,    out, i, n, c, j, q, esc, start, rest) {
    out = ""; n = length(s); i = 1
    while (i <= n) {
        c = substr(s, i, 1)
        if (c == "\\") { out = out substr(s, i, 2); i += 2; continue }
        if (blank && c ~ /[;&|]/) { open = 1; return s }
        if (blank && (i == 1 || substr(s, i - 1, 1) ~ /[ \t]/)) {
            rest = substr(s, i)
            if (match(rest, "^(-a?m|--message|-e|--exclude|--list|-l)(=|[ \t]+)[" sq dq "]")) {
                q = substr(rest, RLENGTH, 1)
                j = close_at(s, i + RLENGTH, q, q == dq)
                if (!j) { open = 1; return s }
                out = out substr(rest, 1, RLENGTH) q
                i = j + 1
                continue
            }
        }
        start = i
        if (c == "$" && substr(s, i + 1, 1) == sq) { q = sq; esc = 1; i++ }
        else if (c == sq) { q = sq; esc = 0 }
        else if (c == dq) { q = dq; esc = 1 }
        else { out = out c; i++; continue }
        j = close_at(s, i + 1, q, esc)
        if (!j) { open = 1; return s }
        out = out substr(s, start, j - start + 1)
        i = j + 1
    }
    return out
}
{
    if (open) { print; next }
    # A line that is not one plain git command, or that holds anything whose quoting
    # this scanner does not model (command or parameter substitution, a backtick, ANSI-C
    # quoting, a heredoc, a shell or runner name), is printed as is and ends blanking
    # for the rest of the command.
    if ($0 !~ /^[ \t]*([^ \t;&|]*\/)?git[ \t]/ ||
        $0 ~ ("\\$\\(|`|\\$\\{|\\$" sq "|<<") ||
        $0 ~ /(^|[^A-Za-z0-9_.-])(bash|sh|zsh|dash|ksh|fish|pwsh|powershell|ssh|eval|source|watch|su|script|flock|parallel|xargs|trap|foreach)([^A-Za-z0-9_.-]|$)/) {
        open = 1; print; next
    }
    print scan($0, 1)
}'
}

CMD_CODE=$(strip_heredocs <<<"${CMD}")
CMD_FLAGS=$(blank_flag_values <<<"${CMD_CODE}")

# Every check reads one line at a time, so `git -C x \` + newline + `reset --hard` would
# slip past them. Each check also reads a copy with backslash-newline pairs joined. Not
# every such pair is a continuation (`echo x\\` or a comment ending in a backslash), so
# the lines as written are kept, never replaced. The joined copy goes through the
# heredoc filter and the flag scanner on its own, so no state carries over between the
# two copies.
CMD_JOINED=${CMD//$'\\\n'/ }
if [[ "${CMD_JOINED}" != "${CMD}" ]]; then
    JOINED_CODE=$(strip_heredocs <<<"${CMD_JOINED}")
    JOINED_FLAGS=$(blank_flag_values <<<"${JOINED_CODE}")
    CMD+=$'\n'"${CMD_JOINED}"
    CMD_CODE+=$'\n'"${JOINED_CODE}"
    CMD_FLAGS+=$'\n'"${JOINED_FLAGS}"
fi

# Here-strings, not `printf | grep -q`: under pipefail, grep -q exiting early
# can kill printf with SIGPIPE on a long command and turn a match into a miss.
matches() {
    grep -qiE "$1" <<<"${CMD}"
}
# The anchored checks also read a copy with every quote character removed: bash removes
# them before git sees the words, so `git -C . "stash"` or `st''ash` is the stash subcommand.
QUOTE_CHARS="[\"']"
matches_code() {
    grep -qiE "$1" <<<"${CMD_CODE}" || grep -qiE "$1" <<<"${CMD_CODE//${QUOTE_CHARS}/}"
}
matches_flags() {
    grep -qiE "$1" <<<"${CMD_FLAGS}" || grep -qiE "$1" <<<"${CMD_FLAGS//${QUOTE_CHARS}/}"
}

COMMAND_PREFIX='(^|;[[:space:]]*|&&[[:space:]]*|[|][|][[:space:]]*|[|][[:space:]]*)'
# `git <subcommand>`, also after git's global options (`git -C repo push`, `git -c k=v push`,
# `git --git-dir path push`), with an option value that may be quoted (`git -C "a b" push`).
# The exec-policy rules match exact tokens, so they cannot catch these forms; the hook does.
GIT_OPT_VALUE="([^[:space:];&|\"']|\"[^\"]*\"|'[^']*')+"
GIT_OPT="([[:space:]]+-[Cc][[:space:]]+${GIT_OPT_VALUE}"
GIT_OPT+="|[[:space:]]+--(git-dir|work-tree|namespace|exec-path|super-prefix|config-env)"
GIT_OPT+="[[:space:]]+${GIT_OPT_VALUE}"
# Any other option, which may carry an attached quoted value (`--git-dir="a b"`).
GIT_OPT+="|[[:space:]]+-${GIT_OPT_VALUE})"
GIT_CMD="git${GIT_OPT}*[[:space:]]+"
# A git command at the start of a command segment, so text that only mentions one
# (a commit message, a PR body, a heredoc) does not match. A segment starts at the
# line start, after ; & | {, at `$(` or `<(`, or at `=` plus a backtick (`x=`git ...``).
# A bare backtick, `(` or `!` inside text does not start one: messages and docs use
# them around commands. After a real start, a segment may carry `(`, `!`, shell
# keywords (`if`, `then`, ...), variable assignments (`GIT_EDITOR=true`), command
# wrappers with their options and option values (`env -u HOME`, `timeout -s KILL 60`,
# the same list as RM_WRAPPER below) and a path (`/usr/bin/git`).
SEGMENT_START='(^|[;&|{]|[$<][(]|=`)([[:space:]]|[(!]|(if|then|do|else|elif|while|until)[[:space:]])*'
SEGMENT_START+='([A-Za-z_][A-Za-z0-9_]*=[^[:space:];&|]*[[:space:]]+)*'
SEGMENT_START+='((xargs|command|builtin|env|nice|nohup|time|exec|timeout|doas)'
SEGMENT_START+='([[:space:]]+(-[^[:space:];&|]*([[:space:]]+[^-[:space:];&|][^[:space:];&|]*)?'
SEGMENT_START+='|[0-9][^[:space:];&|]*|[A-Za-z_][A-Za-z0-9_]*=[^[:space:];&|]*))*'
SEGMENT_START+='[[:space:]]+)*([^[:space:];&|]*/)?'
GIT_AT_START="${SEGMENT_START}${GIT_CMD}"
# The same, but only with at least one global option before the subcommand.
GIT_WITH_OPTS_AT_START="${SEGMENT_START}git${GIT_OPT}+[[:space:]]+"
# Git commands default.rules forbids. Its exact-token rules cannot match them once a global
# option comes first (`git -C repo stash`), so the hook blocks that form.
# A subcommand ends at whitespace, the end, or the close of a group (`$(git -C x stash)`).
GIT_SUB_END='([[:space:]);}`]|$)'
FORBIDDEN_GIT_RE="(reset|filter-branch|stash|clone|cherry-pick|revert|merge)${GIT_SUB_END}"
FORBIDDEN_GIT_RE+="|branch([^;&|]*[[:space:]])?(-[dD]|--delete)${GIT_SUB_END}"
FORBIDDEN_GIT_RE+="|tag([^;&|]*[[:space:]])?-d${GIT_SUB_END}"
FORBIDDEN_GIT_RE+="|reflog[[:space:]]+(expire|delete)${GIT_SUB_END}"
FORBIDDEN_GIT_RE+="|commit([^;&|]*[[:space:]])?--amend${GIT_SUB_END}"
FORBIDDEN_GIT_RE+="|clean([^;&|]*[[:space:]])?(-[a-zA-Z]*f|--force)"
FORBIDDEN_GIT_RE+="|pull([^;&|]*[[:space:]])?(--rebase|-r|--no-ff|--squash|--no-rebase)([=]|${GIT_SUB_END})"
# chmod that makes a file writable by others: an octal mode whose last digit has the
# write bit (2, 3, 6, 7), or a symbolic clause for o or a that adds or sets w. default.rules
# lists a few exact modes; it cannot test the bit, so the hook catches the rest.
CHMOD_WORLD_RE="${SEGMENT_START}chmod([[:space:]]+-[^[:space:];&|]*)*[[:space:]]+"
CHMOD_WORLD_RE+="([0-7]{0,3}[2367]|([^[:space:];&|]*,)?[ugoa]*[oa][ugoa]*[+=][rwxXst]*w[^[:space:];&|]*)"
CHMOD_WORLD_RE+="${GIT_SUB_END}"
# A package publish with options or a workspace before `publish` (`npm -w pkg publish`,
# `pnpm --filter pkg publish`, `yarn workspaces foreach -A npm publish`), or through
# lerna or changesets (`npx lerna publish`, `pnpm changeset publish`). default.rules
# forbids the plain forms but cannot match a value before the subcommand. Only options
# and their values may come before `publish`, so `npm help publish` or a test filter
# named publish (`pnpm vitest publish`) is not blocked.
# An option value may be quoted (`npm --prefix "a b" publish`), as GIT_OPT_VALUE allows.
PKG_OPT_PART="[^[:space:];&|\"']|\"[^\"]*\"|'[^']*'"
PKG_OPTS="([[:space:]]+-(${PKG_OPT_PART})*([[:space:]]+([^-[:space:];&|\"']|\"[^\"]*\"|'[^']*')(${PKG_OPT_PART})*)?)*"
PUBLISH_RE="${SEGMENT_START}(npm|pnpm|bun|yarn)${PKG_OPTS}[[:space:]]+publish${GIT_SUB_END}"
PUBLISH_RE+="|${SEGMENT_START}yarn[[:space:]]+workspaces[[:space:]]+foreach"
PUBLISH_RE+="([[:space:]]+[^;&|[:space:]]+)*[[:space:]]+npm[[:space:]]+publish${GIT_SUB_END}"
PUBLISH_RE+="|${SEGMENT_START}((npx|bunx|pnpm|yarn|npm)([[:space:]]+(exec|x|dlx))?[[:space:]]+)?"
PUBLISH_RE+="(lerna|changeset)[[:space:]]+publish${GIT_SUB_END}"
# npm publish run through yarn or pnpm for one workspace or all of them
# (`yarn workspace pkg npm publish`, `yarn --cwd dir npm publish`, `pnpm -r exec npm publish`).
PUBLISH_RE+="|${SEGMENT_START}(yarn|pnpm)${PKG_OPTS}"
PUBLISH_RE+="([[:space:]]+(workspace[[:space:]]+[^;&|[:space:]]+|exec|-r|--recursive))*"
PUBLISH_RE+="[[:space:]]+npm[[:space:]]+publish${GIT_SUB_END}"
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

# The raw-text match runs on the full command, as before this hook gained the anchored
# check, so a reset inside an executed string (`bash -c '...'`, `eval '...'`, a heredoc
# fed to an interpreter) stays blocked; the anchored check adds the global-option forms.
if matches 'git[[:space:]]+reset[[:space:]]+--hard' ||
    matches_code "${GIT_AT_START}reset([^;&|]*[[:space:]])?--hard"; then
    block "Do not run git reset --hard unless the user explicitly requested it."
fi

if matches_code "${GIT_AT_START}rebase${GIT_SUB_END}"; then
    block "Do not rebase; propose a follow-up commit or a fresh branch instead."
fi

if matches_flags "${GIT_WITH_OPTS_AT_START}(${FORBIDDEN_GIT_RE})"; then
    block "This git command is forbidden by the exec-policy rules, also with git -C or other global options."
fi

if matches_code "${PUBLISH_RE}"; then
    block "Publishing packages is not allowed from Codex; publish manually."
fi

if matches_code "${CHMOD_WORLD_RE}"; then
    block "World-writable permissions are not allowed from Codex."
fi

if matches "${DIRECT_MAIN_RE}"; then
    block "Use feature branches and PRs; do not push directly to main/master."
fi

exit 0
