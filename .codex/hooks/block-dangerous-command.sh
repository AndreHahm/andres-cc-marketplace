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

# Splits the command into words the way bash does (issues #838, #840). The substitution
# copies below each handle one kind of quote or escape, so a word that mixes them (an escaped
# space beside a single-quoted backslash, `x.y='a b\'c\ d`) was read differently from bash.
# mode=norm prints the normalized copy: each word as bash reads it, with quote characters
# dropped; a backslash-newline removed outside single quotes; an unquoted backslash and the
# next character as that character; single quotes literal; in double quotes, a backslash
# escaping only $ ` " \ and newline; $'...' decoded. Inside a word, a character that a check
# could read as structure (space, separator, quote, backslash, $, braces) becomes `_`, so the
# word stays one word. Code inside $( ), backticks and <( ) keeps its spaces. The copy stops
# at a heredoc (<<), whose body the other copies still check. It only adds a copy, so
# it can only block more.
# mode=blank prints the command unchanged except for the value of a message or pattern
# option (`commit -m "use --amend"` becomes `-m ""`), for the forbidden-git check only, so
# text inside a message is not read as a flag. A value is blanked only where the words are
# certain: a top-level git command, after assignments or `env` with assignments, with the
# subcommand found past git's global options, and only commit -m/--message, tag
# -m/--message and clean -e/--exclude after options known to take no value. An unknown
# option stops blanking for that command (`commit -F x -m` would make -m the file). Blanking
# stops for the rest of the command at anything not modeled here: $( ), a backtick, ${ },
# <( ), a heredoc, [[ ]], case, alias, function or a parenthesis inside a command; a word
# holding an unquoted $ or glob character, or a $ parameter inside double quotes, stops it for
# that command, since expansion could split it or turn it into an option. A word over 256
# characters stops it wherever it would be read as the git word, an option or the subcommand.
# An unclosed quote cancels all blanking.
# BINMODE=3 keeps CRs on Windows gawk; a CR is an ordinary character in bash, written `_`.
split_words() {
    awk -v BINMODE=3 -v mode="$1" -v sq="'" -v dq='"' '
function nc(c) { return index(SP, c) ? "_" : c }
function hexval(d) { return d == "" ? -1 : index("0123456789abcdef", tolower(d)) - 1 }
function chrv(v) {
    if (v == 0) return "NUL"
    return (v >= 32 && v < 127) ? nc(chr[v]) : "_"
}
# Output is streamed and a word keeps at most 256 characters (only short option names are
# compared), so a long command takes linear time, also in awks that copy on concatenation.
# A word cut at the cap is marked: blank_cmd stops wherever it would compare one, but may
# still blank one whole as a value, since the span comes from the raw text.
function emit(x) {
    if (mode == "norm") printf "%s", x
    if (inword) { if (length(wn) < 256) wn = wn x; else wc = 1 }
}
function push(t) { depth++; st[depth] = t; pd[depth] = 0 }
function startword() {
    if (!depth && !inword) { inword = 1; ws = i; wn = ""; wg = 0; wc = 0 }
    wb = 0
}
function endword() {
    if (depth || !inword) return
    inword = 0
    if (wn == "[[" || wn == "case" || wn == "alias" || wn == "function" || wn == "coproc" ||
        wn == "select") bail = 1
    if (redir) { redir = 0; return }
    nk++; cs[nk] = ws; ce[nk] = i; cn[nk] = wn; cg[nk] = wg; ct[nk] = wc
}
function endcmd() {
    if (depth) return
    if (mode == "blank" && !bail) blank_cmd()
    nk = 0; redir = 0
}
function raw(k) { return substr(s, cs[k], ce[k] - cs[k]) }
function span(a, b) { nb++; sa[nb] = a; sb[nb] = b }
function blank_cmd(    k, set, v, long, longb, o, r, re) {
    for (k = 1; k <= nk; k++) if (cg[k]) return
    k = 1
    while (k <= nk && raw(k) ~ /^[A-Za-z_][A-Za-z0-9_]*=/) k++
    if (k <= nk && raw(k) == "env") {
        k++
        while (k <= nk && raw(k) ~ /^[A-Za-z_][A-Za-z0-9_]*=/) k++
    }
    if (k > nk || ct[k] || (cn[k] != "git" && cn[k] !~ /\/git$/)) return
    # git global options: the first list takes the next word as its value, the second takes
    # none. Any other option stops blanking, since its value could be read as the subcommand.
    for (k++; k <= nk && cn[k] ~ /^-/; k++) {
        if (ct[k]) return
        if (cn[k] ~ /^(-C|-c|--git-dir|--work-tree|--namespace|--super-prefix|--config-env|--attr-source|--shallow-file)$/) k++
        else if (cn[k] !~ /^(-p|-P|--paginate|--no-pager|--bare|--no-replace-objects|--no-lazy-fetch|--no-optional-locks|--no-advice|--literal-pathspecs|--glob-pathspecs|--noglob-pathspecs|--icase-pathspecs)$/ &&
            cn[k] !~ /^--(git-dir|work-tree|namespace|super-prefix|config-env|attr-source|shallow-file)=/) return
    }
    if (k > nk || ct[k]) return
    # set: short options that take no value and may share a cluster with v.
    if (cn[k] == "commit") {
        set = "asneqviopz"; v = "m"; long = "--message"
        longb = "|--all|--signoff|--no-signoff|--no-verify|--verify|--edit|--no-edit|--quiet|"
        longb = longb "--verbose|--include|--only|--patch|--null|--dry-run|--short|--branch|"
        longb = longb "--porcelain|--long|--reset-author|--allow-empty|--allow-empty-message|"
        longb = longb "--no-post-rewrite|--status|--no-status|--no-gpg-sign|"
    } else if (cn[k] == "tag") {
        set = "asf"; v = "m"; long = "--message"; longb = "|--annotate|--sign|--force|"
    } else if (cn[k] == "clean") {
        set = "dfinqxX"; v = "e"; long = "--exclude"
        longb = "|--force|--dry-run|--quiet|--interactive|"
    } else return
    re = "^-[" set "]*" v
    for (k++; k <= nk; k++) {
        o = cn[k]
        # A cut word read as an option could end differently; a cut value is skipped above.
        if (ct[k] || o == "--") return
        if (o !~ /^-/) continue
        if (o ~ (re "$") || o == long) {
            if (k < nk) span(cs[k + 1], ce[k + 1])
            k++
            continue
        }
        r = raw(k)
        if (o ~ re) {
            if (!match(r, re)) return
            span(cs[k] + RLENGTH, ce[k])
            continue
        }
        if (index(o, long "=") == 1) {
            if (index(r, long "=") != 1) return
            span(cs[k] + length(long) + 1, ce[k])
            continue
        }
        if (o ~ ("^-[" set "]+$") || index(longb, "|" o "|")) continue
        return
    }
}
BEGIN {
    SP = " \t\r\n\v\f;&|<>()" sq dq "`\\${}"
    for (k = 32; k < 127; k++) chr[k] = sprintf("%c", k)
}
{ ln[NR] = $0 }
END {
    # Join the lines pairwise, so the copying stays near linear.
    for (m = NR; m > 1; m = h) {
        h = 0
        for (k = 1; k <= m; k += 2) ln[++h] = (k < m) ? ln[k] "\n" ln[k + 1] : ln[k]
    }
    s = ln[1]
    n = length(s); i = 1; wb = 1
    while (i <= n) {
        c = substr(s, i, 1); c2 = substr(s, i + 1, 1)
        ctx = depth ? st[depth] : "c"
        if (ctx == "d") {
            if (c == dq) { depth--; i++; continue }
            if (c == "\\") {
                if (c2 == "\n") { i += 2; continue }
                if (c2 != "" && index("$`\\" dq, c2)) { emit(nc(c2)); i += 2; continue }
                emit("_"); i++; continue
            }
        } else if (ctx == "r") {
            if (c == "}") { depth--; emit("}"); i++; continue }
            if (c == "\\") { emit("_"); i += 2; continue }
            if (!(c == "$" && (c2 == "{" || c2 == "(")) && c != "`") { emit(nc(c)); i++; continue }
        } else {
            # Code: top level, or inside $( ), backticks or <( ).
            if (ctx == "b" && c == "`") { depth--; emit("`"); i++; wb = 0; continue }
            if (c == "\\") {
                if (c2 == "\n") { i += 2; continue }
                startword()
                if (c2 == "") { emit("_"); i++ } else { emit(nc(c2)); i += 2 }
                continue
            }
            if (c == sq) {
                startword()
                for (j = i + 1; j <= n && substr(s, j, 1) != sq; j++) emit(nc(substr(s, j, 1)))
                if (j > n) unclean = 1
                i = j + 1
                continue
            }
            if (c == "$" && c2 == sq) {
                startword()
                # bash finds the end first: a backslash pairs with the next character, and
                # the first unpaired quote ends the string. Only then are escapes decoded,
                # so no escape can read past the end (`$'\c'` ends at its last quote).
                for (q = i + 2; q <= n && substr(s, q, 1) != sq; q++)
                    if (substr(s, q, 1) == "\\") q++
                if (q > n) unclean = 1
                j = i + 2; nul = 0
                while (j < q && j <= n) {
                    e = substr(s, j, 1)
                    if (e != "\\") { if (!nul) emit(nc(e)); j++; continue }
                    e = substr(s, j + 1, 1); j += 2
                    if (e == "x" || e == "u" || e == "U") {
                        lim = (e == "x") ? 2 : (e == "u") ? 4 : 8
                        val = 0
                        for (m = 0; m < lim && (h = hexval(substr(s, j, 1))) >= 0; m++) {
                            val = val * 16 + h; j++
                        }
                        x = m ? chrv(val) : "_" e
                    } else if (e ~ /^[0-7]$/) {
                        val = e + 0
                        for (m = 1; m < 3 && substr(s, j, 1) ~ /^[0-7]$/; m++) {
                            val = val * 8 + substr(s, j, 1); j++
                        }
                        x = chrv(val % 256)
                    } else if (e == "c") {
                        if (j + 1 < q && substr(s, j, 2) == "\\\\") j += 2
                        else if (j < q) j++
                        x = "_"
                    }
                    else if (e == "") { x = "_" }
                    else if (index("abefnrtvE", e)) x = "_"
                    else if (e == "\\" || e == sq || e == dq || e == "?") x = nc(e)
                    else x = "_" nc(e)
                    # bash ends a $'\'...'\'' string at a NUL.
                    if (x == "NUL") nul = 1
                    else if (!nul) emit(x)
                }
                i = q + 1; continue
            }
            if (c == dq) { startword(); push("d"); i++; continue }
            if (c == "#" && wb) {
                while (i <= n && substr(s, i, 1) != "\n") i++
                continue
            }
            if (c == " " || c == "\t") { endword(); emit(c); i++; wb = 1; continue }
            if (c == "\n") { endword(); endcmd(); emit(c); i++; wb = 1; continue }
            if (c == "<" && c2 == "<") {
                if (substr(s, i + 2, 1) != "<") { endword(); bail = 1; stopped = 1; break }
                endword(); emit("<<<"); i += 3; if (!depth) redir = 1; wb = 1; continue
            }
            if ((c == "<" || c == ">") && c2 == "(") {
                startword(); bail = 1; push("p"); emit(c "("); i += 2; wb = 1; continue
            }
            if (c == "<" || c == ">" || (c == "&" && c2 == ">")) {
                # A file descriptor number written against the operator is not a word.
                if (!depth && inword && raw_digits()) inword = 0
                else endword()
                j = i + 1
                if (c == "&" || (c == ">" && index(">&|", c2)) || (c == "<" && index("&>", c2))) j++
                if (c == "&" && substr(s, j, 1) == ">") j++
                emit(substr(s, i, j - i)); i = j
                if (!depth) redir = 1
                wb = 1; continue
            }
            if (c == "(") {
                if (depth) pd[depth]++
                else {
                    if (inword || nk > 0 || c2 == "(") bail = 1
                    pd0++
                }
                endword(); emit(c); i++; wb = 1; continue
            }
            if (c == ")") {
                if (depth) {
                    if (pd[depth] > 0) { pd[depth]--; emit(c); i++; wb = 1; continue }
                    if (ctx == "p") { depth--; emit(c); i++; wb = 0; continue }
                    emit(c); i++; continue
                }
                endword()
                if (pd0 > 0) pd0--; else bail = 1
                endcmd(); emit(c); i++; wb = 1; continue
            }
            if (c == ";" || c == "&" || c == "|") { endword(); endcmd(); emit(c); i++; wb = 1; continue }
        }
        # Shared by every context: substitutions, and an ordinary character.
        if (c == "$" && c2 == "(") {
            startword(); bail = 1; push("p")
            if (substr(s, i + 2, 1) == "(") { emit("$(("); i += 3 } else { emit("$("); i += 2 }
            wb = 1; continue
        }
        if (c == "$" && c2 == "{") { startword(); bail = 1; push("r"); emit("${"); i += 2; continue }
        if (c == "`") { startword(); bail = 1; push("b"); emit(c); i++; wb = 1; continue }
        if (ctx == "d") {
            # "$o" or "$@" is a word of unknown value: it could be an option that takes one.
            if (c == "$" && c2 ~ /^[A-Za-z0-9_@*#?$!-]$/) wg = 1
            emit(nc(c)); i++; continue
        }
        startword()
        if (!depth && index("$*?[{~", c)) wg = 1
        emit((c == "\r" || c == "\v" || c == "\f") ? "_" : c)
        i++
    }
    if (depth) unclean = 1
    if (!stopped) { endword(); endcmd() }
    if (mode == "norm") { printf "\n"; exit }
    if (unclean) { print s; exit }
    p = 1
    for (k = 1; k <= nb; k++) { printf "%s", substr(s, p, sa[k] - p) dq dq; p = sb[k] }
    print substr(s, p)
}
function raw_digits() { return substr(s, ws, i - ws) ~ /^[0-9]+$/ }'
}

# Fail closed like jq above: a missing or failing awk must not let the command through.
command -v awk >/dev/null 2>&1 || block "awk is required by the command-policy hook."
CMD_CODE=$(strip_heredocs <<<"${CMD}") || block "Could not read the command."
CMD_FLAGS=$(split_words blank <<<"${CMD_CODE}") || block "Could not read the command."
CMD_WORDS=$(split_words norm <<<"${CMD_CODE}") || block "Could not read the command."
FLAGS_WORDS=$(split_words norm <<<"${CMD_FLAGS}") || block "Could not read the command."

# Every check reads one line at a time, so `git -C x \` + newline + `reset --hard` would
# slip past them. Each check also reads copies with backslash-newline pairs joined. Not
# every such pair is a continuation (`echo x\\` or a comment ending in a backslash), so
# the lines as written are kept, never replaced. bash removes the pair with nothing, so
# one copy joins that way (`git re\` + newline + `base` is `git rebase`, issue #802); a
# second joins with a space, for a pair after a space whose surrounding whitespace a
# check may need. The code copy is joined after the heredoc filter, not before: bash
# does not join lines inside a quoted heredoc body, so joining first could merge away
# the body's end (`x\` + newline + `EOF`) and hide the command after it. The flags copy
# is likewise joined after the flag scanner: the join does not count backslashes, so a
# quoted `\\` + newline would become `\"` and the scanner would misread where a quote ends.
ORIGINAL_CMD=${CMD}
ORIGINAL_CODE=${CMD_CODE}
ORIGINAL_FLAGS=${CMD_FLAGS}
for JOIN in '' ' '; do
    CMD_JOINED=${ORIGINAL_CMD//$'\\\n'/"${JOIN}"}
    if [[ "${CMD_JOINED}" != "${ORIGINAL_CMD}" ]]; then
        JOINED_CODE=${ORIGINAL_CODE//$'\\\n'/"${JOIN}"}
        JOINED_FLAGS=${ORIGINAL_FLAGS//$'\\\n'/"${JOIN}"}
        CMD+=$'\n'"${CMD_JOINED}"
        CMD_CODE+=$'\n'"${JOINED_CODE}"
        CMD_FLAGS+=$'\n'"${JOINED_FLAGS}"
    fi
done
# The normalized copies from split_words, on lines of their own, so every check also reads
# each word as bash reads it (`git -c x.y='a b\'c\ d stash` becomes
# `git -c x.y=a_b_c_d stash`, `$'st\x61sh'` becomes `stash`).
CMD+=$'\n'"${CMD_WORDS}"
CMD_CODE+=$'\n'"${CMD_WORDS}"
CMD_FLAGS+=$'\n'"${FLAGS_WORDS}"

# Here-strings, not `printf | grep -q`: under pipefail, grep -q exiting early
# can kill printf with SIGPIPE on a long command and turn a match into a miss.
# Every check also reads two copies for backslashes. bash removes an unquoted one before an
# ordinary character, so one copy removes every backslash: `git re\base` is the rebase
# subcommand and `--ha\rd` is `--hard`. An escaped space or separator stays inside its word
# (`git -c x.y=a\ b stash` sets `x.y` to `a b`), so the other copy turns a backslash and the
# character after it into one ordinary character (`a_b`), and the option value stays whole.
# The backslash itself is never what a check looks for.
# The anchored checks also read copies with every quote character removed: bash removes
# them before git sees the words, so `git -C . "stash"` or `st''ash` is the stash subcommand.
# Each backslash copy is read with and without quotes, for a word that mixes the two
# (`st\a"sh"`).
# The copies are built once and joined, one per line group, so each check is a single grep.
# Every check matches within one line and every copy starts on a new line, so this reads the
# same as one grep per copy, and a long command takes seconds less.
# awk builds the copies: bash's own ${var//\\?/_} slows down sharply on a long command. In awk
# as in bash, `.` also matches a newline, so a backslash-newline becomes `_` in that copy.
# make_copies 0|1: the text, without backslashes, with each backslash pair as `_`; with 1,
# each of those also without quote characters.
make_copies() {
    awk -v BINMODE=3 -v unq="$1" -v sq="'" -v dq='"' '
{ ln[NR] = $0 }
END {
    for (m = NR; m > 1; m = h) {
        h = 0
        for (k = 1; k <= m; k += 2) ln[++h] = (k < m) ? ln[k] "\n" ln[k + 1] : ln[k]
    }
    c[1] = ln[1]; c[2] = c[1]; c[3] = c[1]
    gsub(/\\/, "", c[2])
    gsub(/\\./, "_", c[3])
    for (k = 1; k <= 3; k++) {
        print c[k]
        if (unq) { t = c[k]; gsub("[" dq sq "]", "", t); print t }
    }
}'
}
MATCH_TEXT=$(make_copies 0 <<<"${CMD}") || block "Could not read the command."
CODE_TEXT=$(make_copies 1 <<<"${CMD_CODE}") || block "Could not read the command."
FLAGS_TEXT=$(make_copies 1 <<<"${CMD_FLAGS}") || block "Could not read the command."
matches() {
    grep -qiE "$1" <<<"${MATCH_TEXT}"
}
matches_code() {
    grep -qiE "$1" <<<"${CODE_TEXT}"
}
matches_flags() {
    grep -qiE "$1" <<<"${FLAGS_TEXT}"
}

COMMAND_PREFIX='(^|;[[:space:]]*|&&[[:space:]]*|[|][|][[:space:]]*|[|][[:space:]]*)'
# `git <subcommand>`, also after git's global options (`git -C repo push`, `git -c k=v push`,
# `git --git-dir path push`), with an option value that may be quoted (`git -C "a b" push`).
# The exec-policy rules match exact tokens, so they cannot catch these forms; the hook does.
GIT_OPT_VALUE="([^[:space:];&|\"']|\"[^\"]*\"|'[^']*')+"
GIT_OPT="([[:space:]]+-[Cc][[:space:]]+${GIT_OPT_VALUE}"
GIT_OPT+="|[[:space:]]+--(git-dir|work-tree|namespace|exec-path|super-prefix|config-env|attr-source|shallow-file)"
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
# the same list as RM_WRAPPER below) and a path (`/usr/bin/git`). An assignment or
# option value may be quoted (`X="a b" git ...`, `env -u "a b" git ...`).
WORD_PART="[^[:space:];&|\"']|\"[^\"]*\"|'[^']*'"
WORD_START="[^-[:space:];&|\"']|\"[^\"]*\"|'[^']*'"
SEGMENT_START='(^|[;&|{]|[$<][(]|=`)([[:space:]]|[(!]|(if|then|do|else|elif|while|until)[[:space:]])*'
SEGMENT_START+="([A-Za-z_][A-Za-z0-9_]*=(${WORD_PART})*[[:space:]]+)*"
SEGMENT_START+='((xargs|command|builtin|env|nice|nohup|time|exec|timeout|doas|eval)'
SEGMENT_START+="([[:space:]]+(-(${WORD_PART})*([[:space:]]+(${WORD_START})(${WORD_PART})*)?"
SEGMENT_START+="|[0-9](${WORD_PART})*|[A-Za-z_][A-Za-z0-9_]*=(${WORD_PART})*))*"
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
# git accepts any unambiguous prefix of a long option (`commit --am` is `--amend`), which the
# exec-policy rules' exact tokens cannot match, so these are checked with or without global
# options. Prefixes that git finds ambiguous (`push --forc`) are rejected by git itself.
ABBREV_GIT_RE="commit([^;&|]*[[:space:]])?--am(e(n(d)?)?)?${GIT_SUB_END}"
ABBREV_GIT_RE+="|(branch|tag)([^;&|]*[[:space:]])?--d(e(l(e(t(e)?)?)?)?)?${GIT_SUB_END}"
ABBREV_GIT_RE+="|clean([^;&|]*[[:space:]])?--f(o(r(c(e)?)?)?)?${GIT_SUB_END}"
ABBREV_GIT_RE+="|pull([^;&|]*[[:space:]])?--((no-)?reb(a(s(e)?)?)?|sq(u(a(s(h)?)?)?)?)([=]|${GIT_SUB_END})"
# A short-option cluster that holds a forbidden one (`branch -Dq`, `pull -qr`).
ABBREV_GIT_RE+="|branch([^;&|]*[[:space:]])?-[a-zA-Z]*[dD][a-zA-Z]*${GIT_SUB_END}"
ABBREV_GIT_RE+="|pull([^;&|]*[[:space:]])?-[a-zA-Z]*r${GIT_SUB_END}"
# A setting given for one command only (`git -c ...`, `--config-env`, GIT_CONFIG_* variables)
# that turns off clean's force check, makes pull rebase or merge, or defines any alias (an
# alias can name a forbidden subcommand, `alias.x=stash`, or run a shell, `alias.x=!cmd`).
# The exec-policy rules cannot see it: the command no longer starts with `git clean`.
# A persistent `git config` stays with the rules, which ask the user. Known limits of a text
# check: config read from a file (`include.path`, GIT_CONFIG_GLOBAL, another --git-dir) and
# keys that run a command (core.pager, core.editor, core.sshCommand, core.hooksPath,
# GIT_PAGER, GIT_SSH_COMMAND, GIT_EXTERNAL_DIFF), and a key held in a variable, are not checked.
# The -c and --config-env forms must follow `git` and its global options at the start of a
# command or of a shell string (added below), and need `=` after the key, so `gcc -c alias.c`, `make -C alias.d` or a search for
# `-c alias.x=` in text is not read as one; a rebase key may also stand alone, since git reads
# `-c pull.rebase` as true. A GIT_CONFIG_KEY_<n> value is the bare key.
CONFIG_KEYS='(clean\.requireforce|pull\.(rebase|ff)|merge\.ff|branch\.[^[:space:]=]*\.rebase|alias\.[^[:space:]=]*)'
CONFIG_OPT="${SEGMENT_START}git${GIT_OPT}*[[:space:]]+(-c[[:space:]]*|--config-env[=[:space:]]+)"
UNSAFE_CONFIG_RE="${CONFIG_OPT}${CONFIG_KEYS}="
UNSAFE_CONFIG_RE+="|${CONFIG_OPT}(pull|branch\.[^[:space:]=]*)\.rebase([[:space:]]|\$)"
UNSAFE_CONFIG_RE+="|GIT_CONFIG_(KEY_[0-9]+|PARAMETERS)=[^[:space:]]*${CONFIG_KEYS}"
# A forbidden git command inside a string that a shell runs (`bash -c 'git stash'`, also after
# other commands, keywords or assignments in the string). The exec-policy rules match only the
# outer command. Every check reads one line, so a string split over lines, or one piped into a
# shell (`echo 'git stash' | sh`), is not seen.
SHELL_STRING_START='(^|[^A-Za-z0-9_.-])(bash|sh|zsh|dash|ksh|eval|su|ssh)([[:space:]][^;&|"'"'"']*)?'
SHELL_STRING_START+="[[:space:]][\$]?[\"'](([^\"']|\"[^\"]*\"|'[^']*')*[;&|({][[:space:]]*)?"
SHELL_STRING_START+="((if|then|do|else|elif|while|until|!)[[:space:]]+"
SHELL_STRING_START+="|(xargs|command|builtin|env|nice|nohup|time|exec|timeout|doas|eval)"
SHELL_STRING_START+="([[:space:]]+(-[^[:space:]\"']*|[0-9][^[:space:]\"']*|[A-Za-z_][A-Za-z0-9_]*=[^[:space:]\"']*))*[[:space:]]+"
SHELL_STRING_START+="|[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*"
SHELL_STRING_START+="([^\"'[:space:];&|]*/)?"
# Inside the string, the closing quote also ends a subcommand (`'git stash'`).
GIT_SUB_END_Q='([[:space:]);}`"'"'"']|$)'
SHELL_STRING_GIT_RE="${SHELL_STRING_START}git${GIT_OPT}*[[:space:]]+(${FORBIDDEN_GIT_RE//"${GIT_SUB_END}"/"${GIT_SUB_END_Q}"}"
SHELL_STRING_GIT_RE+="|${ABBREV_GIT_RE//"${GIT_SUB_END}"/"${GIT_SUB_END_Q}"})"
# The per-command settings above, also inside such a string (`ssh host 'git -c alias.x=stash x'`).
SHELL_CONFIG_OPT="${SHELL_STRING_START}git${GIT_OPT}*[[:space:]]+(-c[[:space:]]*|--config-env[=[:space:]]+)"
UNSAFE_CONFIG_RE+="|${SHELL_CONFIG_OPT}${CONFIG_KEYS}="
UNSAFE_CONFIG_RE+="|${SHELL_CONFIG_OPT}(pull|branch\.[^[:space:]=]*)\.rebase${GIT_SUB_END_Q}"
# Read in the copies without quote characters, for a key quoted inside the string
# (`bash -c 'git -c "alias.x=stash" x'`) or a quoted argument before it (`ssh -o "A b" host`).
SHELL_CONFIG_OPT='(^|[^A-Za-z0-9_.-])(bash|sh|zsh|dash|ksh|eval|su|ssh)[[:space:]]([^;&|]*[[:space:];&|({])?'
SHELL_CONFIG_OPT+="git${GIT_OPT}*[[:space:]]+(-c[[:space:]]*|--config-env[=[:space:]]+)"
UNSAFE_CONFIG_RE+="|${SHELL_CONFIG_OPT}${CONFIG_KEYS}="
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
RM_WRAPPER='(xargs|command|builtin|env|nice|nohup|time|exec|timeout|doas|eval)'
RM_RE="${COMMAND_PREFIX}(${RM_WRAPPER}[[:space:]]([^;&|]*[[:space:]])?)?"
RM_RE+="([^[:space:];&|]*/)?[\"']?rm[\"']?[[:space:]][^;&|]*"
# Also read with backslashes removed, like `matches`: `\rm -rf` and `rm -r\f` are rm -rf.
RM_SEGMENTS=$(grep -oiE "${RM_RE}" <<<"${MATCH_TEXT}" || true)
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

if matches_flags "${GIT_AT_START}(${ABBREV_GIT_RE})"; then
    block "This git command is forbidden by the exec-policy rules, also with an abbreviated option."
fi

if matches_flags "${UNSAFE_CONFIG_RE}"; then
    block "Do not set clean.requireForce or a shell alias for one git command; ask the user."
fi

if matches "${SHELL_STRING_GIT_RE}"; then
    block "This git command is forbidden by the exec-policy rules, also inside a shell string."
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
