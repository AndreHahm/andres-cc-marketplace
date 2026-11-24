#!/bin/bash
set -euo pipefail

# Copy to ~/.codex/hooks/block-dangerous-command.sh.
# Codex PreToolUse hook for Bash. Blocks high-risk command patterns before
# execution. This is a guardrail, not a security boundary; keep sandboxing on.

block() {
    printf 'BLOCKED: %s\n' "$1" >&2
    exit 2
}

# --inner: this run checks the decoded string of an outer `bash -c '...'` (see the shell-string
# check at the end). Such a run never recurses again and also blocks the plain forbidden git
# commands that default.rules would match at the start of the outer command.
INNER=0
[[ "${1:-}" == "--inner" ]] && INNER=1

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
# The command as given; CMD gains the copies the checks read further down.
ORIG_CMD=${CMD}

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
# mode=arith prints the same copy, but goes on past a << that may be arithmetic (`$((1<<2))`).
# mode=blank prints the command unchanged except for the value of a message or pattern
# option (`commit -m "use --amend"` becomes `-m ""`), for the forbidden-git check only, so
# text inside a message is not read as a flag. A value is blanked only where the words are
# certain: a top-level git command, after assignments or `env` with assignments, with the
# subcommand found past git's global options, and only commit -m/--message, tag
# -m/--message and --format, branch --format and clean -e/--exclude, after options known to
# take no value or a known value (commit -S, --author, --date, --trailer; tag -u). A tag
# argument that is one single-quoted word (a name or a pattern) is blanked too, but only when the
# whole command is plain words and single-quoted strings: a later command could run the argument
# again (`$_`, BASH_COMMAND). An unknown
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
    if (mode != "blank") printf "%s", x
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
function blank_cmd(    k, set, v, long, long2, longb, sv, so, lv, lo, o, p, r, re, tag) {
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
        if (cn[k] ~ /^(-C|-c|--git-dir|--work-tree|--namespace|--super-prefix|--config-env|--attr-source|--shallow-file)$/) {
            # Under `set -k` a NAME=value word is dropped and the next word is the value.
            if (k < nk && cn[k + 1] ~ /^[A-Za-z_][A-Za-z0-9_]*\+?=/) return
            k++
        }
        else if (cn[k] !~ /^(-p|-P|--paginate|--no-pager|--bare|--no-replace-objects|--no-lazy-fetch|--no-optional-locks|--no-advice|--literal-pathspecs|--glob-pathspecs|--noglob-pathspecs|--icase-pathspecs)$/ &&
            cn[k] !~ /^--(git-dir|work-tree|namespace|super-prefix|config-env|attr-source|shallow-file)=/) return
    }
    if (k > nk || ct[k]) return
    # set: short options that take no value and may share a cluster with v. v, long and long2
    # are the options whose value is blanked. The others take a value that is kept but skipped,
    # so it is not read as an option: sv is a short one whose value is the rest of its word or
    # else the next word (`tag -u key`), lv a long one with the value in the next word or after
    # `=`. so and lo take only an attached value: `commit -Sm` signs with key m, so -S ends its
    # word and nothing in it is a message; lo is the long form (`--gpg-sign=key`).
    sv = ""; so = ""; lv = ""; lo = ""; long2 = ""; tag = (cn[k] == "tag")
    if (cn[k] == "commit") {
        set = "asneqviopz"; v = "m"; long = "--message"; so = "S"
        lv = "|--author|--date|--trailer|"; lo = "|--gpg-sign|"
        longb = "|--all|--signoff|--no-signoff|--no-verify|--verify|--edit|--no-edit|--quiet|"
        longb = longb "--verbose|--include|--only|--patch|--null|--dry-run|--short|--branch|"
        longb = longb "--porcelain|--long|--reset-author|--allow-empty|--allow-empty-message|"
        longb = longb "--no-post-rewrite|--status|--no-status|--no-gpg-sign|"
    } else if (cn[k] == "tag") {
        set = "asfl"; v = "m"; long = "--message"; long2 = "--format"; sv = "u"
        lv = "|--local-user|"; longb = "|--annotate|--sign|--force|--list|"
    } else if (cn[k] == "branch") {
        # A listing: only the --format value is blanked, so a `-d` printed as text is not a flag.
        set = "arvlq"; v = ""; long = "--format"
        longb = "|--list|--all|--remotes|--verbose|--quiet|--ignore-case|"
    } else if (cn[k] == "clean") {
        set = "dfinqxX"; v = "e"; long = "--exclude"
        longb = "|--force|--dry-run|--quiet|--interactive|"
    } else return
    # With no short value option, re cannot match: every word tested here starts with `-`.
    re = (v == "") ? "^[^-]" : "^-[" set "]*" v
    for (k++; k <= nk; k++) {
        o = cn[k]
        # A cut word read as an option could end differently; a cut value is skipped above.
        if (ct[k] || o == "--") return
        if (o !~ /^-/) {
            # Not an option and not a value of one: a name or a pattern, whose text is no flag.
            if (tag && plain && raw(k) ~ ("^" sq "[^" sq "]*" sq "$")) span(cs[k], ce[k])
            continue
        }
        if (o ~ (re "$") || o == long || (long2 != "" && o == long2)) {
            # Under `set -k` bash moves a NAME=value word out of the arguments, so the
            # next word would be the value: stop rather than guess.
            if (k < nk && cn[k + 1] ~ /^[A-Za-z_][A-Za-z0-9_]*\+?=/) return
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
        if (long2 != "" && index(o, long2 "=") == 1) {
            if (index(r, long2 "=") != 1) return
            span(cs[k] + length(long2) + 1, ce[k])
            continue
        }
        if (so != "" && o ~ ("^-[" set "]*[" so "]")) continue
        if (sv != "" && o ~ ("^-[" set "]*[" sv "]")) {
            if (o ~ ("^-[" set "]*[" sv "]$")) {
                if (k < nk && cn[k + 1] ~ /^[A-Za-z_][A-Za-z0-9_]*\+?=/) return
                k++
            }
            continue
        }
        if (index(lv, "|" o "|")) {
            if (k < nk && cn[k + 1] ~ /^[A-Za-z_][A-Za-z0-9_]*\+?=/) return
            k++
            continue
        }
        p = index(o, "=")
        if (p > 1 && (index(lv, "|" substr(o, 1, p - 1) "|") || index(lo, "|" substr(o, 1, p - 1) "|")))
            continue
        if (o ~ ("^-[" set "]+$") || index(longb, "|" o "|") || index(lo, "|" o "|")) continue
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
    # A blanked argument may be run again by name: `$_`, an indirect `${!v}`, BASH_COMMAND or
    # BASH_EXECUTION_STRING. Other variables that hold a command are not read (known limit).
    t = s
    gsub(/\\\n/, "", t)
    rerun = (index(t, "$_") || index(t, "${_") || index(t, "${!") || index(t, "BASH_COMMAND") ||
        index(t, "BASH_EXECUTION_STRING"))
    plain = (mode == "blank" && length(s) < 4096 && s ~ ("^([A-Za-z0-9_./ \t-]|" sq "[^" sq "\n]*" sq ")*$"))
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
                # so no escape can read past the end (a backslash-c just before the
                # closing quote still ends the string there).
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
                    # bash ends a dollar-quoted string at a NUL.
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
                if (substr(s, i + 2, 1) != "<") {
                    # In arithmetic (`$((1<<2))`, `$[1<<2]`, `x[1<<2]=1`, `x=([1<<2]=1)`) this is no
                    # heredoc: after text that may open one, mode=arith goes on. The norm copy
                    # still ends here, since some checks need its line end.
                    if (!arith) {
                        t = substr(s, 1, i)
                        gsub(/\\\n/, "", t)
                        arith = (index(t, "((") || index(t, "$[") || index(t, "=(") || t ~ /[A-Za-z0-9_]\[/)
                    }
                    endword(); bail = 1
                    if (mode != "arith" || !arith) { stopped = 1; break }
                    emit("<<"); i += 2; if (!depth) redir = 1; wb = 1; continue
                }
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
    if (mode != "blank") { printf "\n"; exit }
    if (unclean || rerun) { print s; exit }
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
CMD_ARITH=""
FLAGS_ARITH=""
if [[ "${CMD}" == *"<<"* ]]; then
    CMD_ARITH=$(split_words arith <<<"${CMD_CODE}") || block "Could not read the command."
    FLAGS_ARITH=$(split_words arith <<<"${CMD_FLAGS}") || block "Could not read the command."
fi

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
# The copies that go on past an arithmetic <<, as extra lines only.
if [[ -n "${CMD_ARITH}" ]]; then
    CMD+=$'\n'"${CMD_ARITH}"
    CMD_CODE+=$'\n'"${CMD_ARITH}"
    CMD_FLAGS+=$'\n'"${FLAGS_ARITH}"
fi
# The same copies with the blanks after < and > removed, so `> x git stash` is read like
# `>x git stash`. Only these copies: there quoted text is one word with `_` for each blank,
# and a heredoc body is cut off, so a quoted reply line (`> Never git rebase ...`) in a
# message or PR body never starts a line.
close_redirects() {
    awk -v BINMODE=3 '{ gsub(/>[ \t]+/, ">"); gsub(/<[ \t]+/, "<"); print }'
}
CMD_WORDS_CLOSED=$(close_redirects <<<"${CMD_WORDS}") || block "Could not read the command."
FLAGS_WORDS_CLOSED=$(close_redirects <<<"${FLAGS_WORDS}") || block "Could not read the command."
if [[ "${CMD_WORDS_CLOSED}" != "${CMD_WORDS}" ]]; then
    CMD+=$'\n'"${CMD_WORDS_CLOSED}"
    CMD_CODE+=$'\n'"${CMD_WORDS_CLOSED}"
fi
[[ "${FLAGS_WORDS_CLOSED}" != "${FLAGS_WORDS}" ]] && CMD_FLAGS+=$'\n'"${FLAGS_WORDS_CLOSED}"
# The same copies with the & of a redirection removed: the checks take & for a separator, so
# `git push 2>&1 -f` would end at it. An extra copy again, so it can only block more.
open_ampersands() {
    awk -v BINMODE=3 '{ gsub(/&>/, ">"); gsub(/>&/, ">"); gsub(/<&/, "<"); print }'
}
CMD_AMP=$(printf '%s\n' "${CMD_WORDS_CLOSED}" "${CMD_ARITH}" | open_ampersands) || block "Could not read the command."
FLAGS_AMP=$(printf '%s\n' "${FLAGS_WORDS_CLOSED}" "${FLAGS_ARITH}" | open_ampersands) || block "Could not read the command."
CMD+=$'\n'"${CMD_AMP}"
CMD_CODE+=$'\n'"${CMD_AMP}"
CMD_FLAGS+=$'\n'"${FLAGS_AMP}"
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

# A word of a check that reads raw text ends at whitespace, the end or an operator written against
# it (`git push origin main>log`). A backtick is left out: messages use it around commands.
WORD_END='([[:space:];&|<>)]|$)'
PUSH_END='([[:space:];&|<>]|$)'
COMMAND_PREFIX='(^|;[[:space:]]*|&&[[:space:]]*|[|][|][[:space:]]*|[|][[:space:]]*)'
# `git <subcommand>`, also after git's global options (`git -C repo push`, `git -c k=v push`,
# `git --git-dir path push`), with an option value that may be quoted (`git -C "a b" push`).
# The exec-policy rules match exact tokens, so they cannot catch these forms; the hook does.
GIT_OPT_VALUE="([^[:space:];&|\"']|\"[^\"]*\"|'[^']*')+"
# Under `set -k` bash drops every NAME=value word from the arguments, so one may stand
# before an option's value or between the options (`git -C X=1 . stash` is `git -C . stash`).
GIT_ASSIGN="[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[+]?=([^[:space:];&|\"']|\"[^\"]*\"|'[^']*')*"
# A redirection word, which bash allows anywhere in a command (`git 2>/dev/null -C . stash`).
# Only the form with the target written against the operator: a line of text that starts
# with `> ` (a quoted reply in a PR body) is not read as one.
REDIR_OP="([0-9]+|&|[{][A-Za-z_][A-Za-z0-9_]*[}])?(<<<|<>|>>|>[|]|[<>]&|<|>)"
REDIR_TARGET="([^[:space:];&|\"']|\"[^\"]*\"|'[^']*')+"
REDIR_WORD="${REDIR_OP}${REDIR_TARGET}"
GIT_OPT="([[:space:]]+-[Cc](${GIT_ASSIGN})*[[:space:]]+${GIT_OPT_VALUE}"
GIT_OPT+="|[[:space:]]+--(git-dir|work-tree|namespace|exec-path|super-prefix|config-env|attr-source|shallow-file)"
GIT_OPT+="(${GIT_ASSIGN})*[[:space:]]+${GIT_OPT_VALUE}"
GIT_OPT+="|${GIT_ASSIGN}"
# After git a line of text cannot be meant, so a blank before the target is allowed here.
GIT_OPT+="|[[:space:]]+${REDIR_OP}[[:space:]]*${REDIR_TARGET}"
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
# A redirection may also come before the command (`>x git stash`, `2>&1 git stash`).
REDIR="${REDIR_WORD}[[:space:]]+"
SEGMENT_START='(^|[;&|{]|[$<][(]|=`)([[:space:]]|[(!]|(if|then|do|else|elif|while|until)[[:space:]])*'
SEGMENT_START+="([A-Za-z_][A-Za-z0-9_]*=(${WORD_PART})*[[:space:]]+|${REDIR})*"
SEGMENT_START+='((xargs|command|builtin|env|nice|nohup|time|exec|timeout|doas|eval)'
SEGMENT_START+="([[:space:]]+(-(${WORD_PART})*([[:space:]]+(${WORD_START})(${WORD_PART})*)?"
SEGMENT_START+="|[0-9](${WORD_PART})*|[A-Za-z_][A-Za-z0-9_]*=(${WORD_PART})*))*"
SEGMENT_START+="[[:space:]]+)*(${REDIR})*([^[:space:];&|]*/)?"
GIT_AT_START="${SEGMENT_START}${GIT_CMD}"
# The same, but only with at least one global option before the subcommand.
GIT_WITH_OPTS_AT_START="${SEGMENT_START}git${GIT_OPT}+[[:space:]]+"
# Git commands default.rules forbids. Its exact-token rules cannot match them once a global
# option comes first (`git -C repo stash`), so the hook blocks that form.
# A subcommand ends at whitespace, the end, the close of a group (`$(git -C x stash)`), or
# an operator or redirection written against it (`git -C . stash|cat`, `stash>x`).
GIT_SUB_END='([[:space:]);}`&|<>]|$)'
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
# For tag, git deletes only with -d alone or with -i (`tag -di`, `tag -id`); it rejects -d with
# any other flag. Only -i may come before the d: after -m, -F, -u or -n the rest of the word is
# that option's value (`tag -mdone`, `tag -Fd`), and the match ignores case, so f would match F.
ABBREV_GIT_RE+="|tag([^;&|]*[[:space:]])?-i*d[a-zA-Z]*${GIT_SUB_END}"
ABBREV_GIT_RE+="|pull([^;&|]*[[:space:]])?-[a-zA-Z]*r${GIT_SUB_END}"
ABBREV_GIT_RE+="|submodule(--helper)?([[:space:]]+(-q|--quiet|${REDIR_WORD})|${GIT_ASSIGN})*[[:space:]]+update([^;&|]*[[:space:]])?"
ABBREV_GIT_RE+="(--reb(a(s(e)?)?)?|--m(e(r(g(e)?)?)?)?|-[a-zA-Z]*[rm])${GIT_SUB_END}"
# A setting given for one command only (`git -c ...`, `--config-env`, GIT_CONFIG_* variables)
# that turns off clean's force check, makes pull rebase or merge (branch.autoSetupRebase does
# so for a later pull on a branch created with it), makes submodule update rebase, merge or run a
# command, force-pushes (remote.<name>.mirror or push), pushes more than one
# branch (push.default), expires reflogs, or defines any alias (an
# alias can name a forbidden subcommand, `alias.x=stash`, or run a shell, `alias.x=!cmd`).
# The exec-policy rules cannot see it: the command no longer starts with `git clean`.
# A persistent `git config` stays with the rules, which ask the user. Known limits of a text
# check: config read from a file (`include.path`, GIT_CONFIG_GLOBAL, another --git-dir) and
# keys that run a command (core.pager, core.editor, core.sshCommand, core.hooksPath,
# GIT_PAGER, GIT_SSH_COMMAND, GIT_EXTERNAL_DIFF), and a key held in a variable, are not checked.
# The -c and --config-env forms must follow `git` and its global options at the start of a
# command or of a shell string (added below), and need `=` after the key, so `gcc -c alias.c`, `make -C alias.d` or a search for
# `-c alias.x=` in text is not read as one; a rebase key may also stand alone, since git reads
# `-c pull.rebase` as true, and so may `pull.ff` and `merge.ff`, whose bare `true` overrides a
# persistent `only`. `branch.<name>.mergeOptions` passes options such as `--no-ff` to the merge
# that pull runs. A GIT_CONFIG_KEY_<n> value is the bare key.
CONFIG_KEYS='(clean\.requireforce|pull\.(rebase|ff)|merge\.ff|branch\.[^[:space:]=]*\.(rebase|mergeoptions)|branch\.autosetuprebase|push\.default|submodule\.[^[:space:]]*\.update|remote\.[^[:space:]]*\.(mirror|push)|gc\.([^[:space:]]*\.)?reflogexpire(unreachable)?|alias\.[^[:space:]=]*)'
# A `-c` value written in the command is read too: `pull.ff=only` keeps pull fast-forward-only
# and `clean.requireForce=true` keeps the force check, and `push.default=current`, `simple` or
# `nothing` pushes at most the current branch, so only another value of those keys is blocked. A value must be exactly that word, ended by a blank, a quote, an operator or the
# end; any other `-c` of the same key in the command is still matched on its own. A value
# split by a backslash also reads as `_` in one copy, so it is blocked. --config-env and the
# GIT_CONFIG_* forms take the value from elsewhere, so every value of these keys stays blocked.
CONFIG_VALUE_END='([[:space:]"'"'"';&|)}`<>]|$)'
CONFIG_VALUE_NOT='[:space:]"'"'"';&|)}`<>'
# not_words <word>...: any value that is not exactly one of the words, which start with
# different letters.
not_words() {
    local w i first='' out=${CONFIG_VALUE_END}
    for w in "$@"; do
        first+=${w:0:1}
        for ((i = 1; i < ${#w}; i++)); do
            out+="|${w:0:i}(${CONFIG_VALUE_END}|[^${w:i:1}${CONFIG_VALUE_NOT}])"
        done
        out+="|${w}[^${CONFIG_VALUE_NOT}]"
    done
    printf '%s' "(${out}|[^${first}${CONFIG_VALUE_NOT}])"
}
CONFIG_NOT_ONLY="(${CONFIG_VALUE_END}|(o|on|onl)${CONFIG_VALUE_END}|[^o${CONFIG_VALUE_NOT}]"
CONFIG_NOT_ONLY+="|o[^n${CONFIG_VALUE_NOT}]|on[^l${CONFIG_VALUE_NOT}]|onl[^y${CONFIG_VALUE_NOT}]|only[^${CONFIG_VALUE_NOT}])"
CONFIG_NOT_TRUE="(${CONFIG_VALUE_END}|(t|tr|tru)${CONFIG_VALUE_END}|[^t${CONFIG_VALUE_NOT}]"
CONFIG_NOT_TRUE+="|t[^r${CONFIG_VALUE_NOT}]|tr[^u${CONFIG_VALUE_NOT}]|tru[^e${CONFIG_VALUE_NOT}]|true[^${CONFIG_VALUE_NOT}])"
CONFIG_C_SET="((pull\.rebase|merge\.ff|branch\.[^[:space:]=]*\.(rebase|mergeoptions)|branch\.autosetuprebase|submodule\.[^[:space:]=]*\.update|remote\.[^[:space:]=]*\.(mirror|push)|gc\.([^[:space:]=]*\.)?reflogexpire(unreachable)?|alias\.[^[:space:]=]*)="
CONFIG_C_SET+="|pull\.ff=${CONFIG_NOT_ONLY}|clean\.requireforce=${CONFIG_NOT_TRUE}"
CONFIG_C_SET+="|push\.default=$(not_words current simple nothing))"
# The option itself; under `set -k` a dropped NAME=value word may stand before the key.
CONFIG_FLAG_C="-c(${GIT_ASSIGN})*[[:space:]]*"
CONFIG_FLAG_E="--config-env(${GIT_ASSIGN})*[=[:space:]]+"
CONFIG_FLAG="(${CONFIG_FLAG_C}|${CONFIG_FLAG_E})"
# config_set_re <prefix>: the prefix followed by a per-command setting of one of the keys.
config_set_re() {
    printf '%s' "$1${CONFIG_FLAG_C}${CONFIG_C_SET}|$1${CONFIG_FLAG_E}${CONFIG_KEYS}="
}
CONFIG_PRE="${SEGMENT_START}git${GIT_OPT}*[[:space:]]+"
CONFIG_OPT="${CONFIG_PRE}${CONFIG_FLAG}"
UNSAFE_CONFIG_RE=$(config_set_re "${CONFIG_PRE}")
UNSAFE_CONFIG_RE+="|${CONFIG_OPT}((pull|branch\.[^[:space:]=]*)\.rebase|(pull|merge)\.ff|remote\.[^[:space:]=]*\.mirror)${GIT_SUB_END}"
# A GIT_CONFIG_* variable set for git (read below, after the other per-command checks).
GIT_CONFIG_ENV="GIT_CONFIG_(KEY_[0-9]+|PARAMETERS)[+]?=[^[:space:]]*${CONFIG_KEYS}"
# A forbidden git command inside a string that a shell runs (`bash -c 'git stash'`, also after
# other commands, keywords or assignments in the string). The exec-policy rules match only the
# outer command. Every check reads one line, so a string split over lines, or one piped into a
# shell (`echo 'git stash' | sh`), is not seen.
SHELL_STRING_OPEN='(^|[^A-Za-z0-9_.-])(bash|sh|zsh|dash|ksh|eval|su|ssh)([[:space:]][^;&|"'"'"']*)?'
SHELL_STRING_OPEN+="[[:space:]][\$]?[\"']"
# What may come before git inside the string: other commands, keywords, wrappers, assignments.
SHELL_STRING_BODY="(([^\"']|\"[^\"]*\"|'[^']*')*[;&|({][[:space:]]*)?"
SHELL_STRING_BODY+="((if|then|do|else|elif|while|until|!)[[:space:]]+"
SHELL_STRING_BODY+="|(xargs|command|builtin|env|nice|nohup|time|exec|timeout|doas|eval)"
SHELL_STRING_BODY+="([[:space:]]+(-[^[:space:]\"']*|[0-9][^[:space:]\"']*|[A-Za-z_][A-Za-z0-9_]*=[^[:space:]\"']*))*[[:space:]]+"
SHELL_STRING_BODY+="|[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+"
SHELL_STRING_BODY+="|${REDIR_OP}[[:space:]]*${REDIR_TARGET}[[:space:]]+)*"
SHELL_STRING_BODY+="([^\"'[:space:];&|]*/)?"
SHELL_STRING_START="${SHELL_STRING_OPEN}${SHELL_STRING_BODY}"
# Inside the string, the closing quote also ends a subcommand (`'git stash'`).
GIT_SUB_END_Q='([[:space:]);}`&|<>"'"'"']|$)'
SHELL_STRING_GIT="git${GIT_OPT}*[[:space:]]+(${FORBIDDEN_GIT_RE//"${GIT_SUB_END}"/"${GIT_SUB_END_Q}"}"
SHELL_STRING_GIT+="|${ABBREV_GIT_RE//"${GIT_SUB_END}"/"${GIT_SUB_END_Q}"}|rebase${GIT_SUB_END_Q})"
SHELL_STRING_GIT_RE="${SHELL_STRING_START}${SHELL_STRING_GIT}"
# The same pattern for a decoded string read with --inner, from the start of each of its lines.
INNER_GIT_RE="^[[:space:]]*${SHELL_STRING_BODY}${SHELL_STRING_GIT}"
# The per-command settings above, also inside such a string (`ssh host 'git -c alias.x=stash x'`).
SHELL_CONFIG_PRE="${SHELL_STRING_START}git${GIT_OPT}*[[:space:]]+"
UNSAFE_CONFIG_RE+="|$(config_set_re "${SHELL_CONFIG_PRE}")"
UNSAFE_CONFIG_RE+="|${SHELL_CONFIG_PRE}${CONFIG_FLAG}((pull|branch\.[^[:space:]=]*)\.rebase|(pull|merge)\.ff|remote\.[^[:space:]=]*\.mirror)${GIT_SUB_END_Q}"
UNSAFE_CONFIG_RE+="|${SHELL_STRING_START}${GIT_CONFIG_ENV}"
# Read in the copies without quote characters, for a key quoted inside the string
# (`bash -c 'git -c "alias.x=stash" x'`) or a quoted argument before it (`ssh -o "A b" host`).
SHELL_CONFIG_PRE='(^|[^A-Za-z0-9_.-])(bash|sh|zsh|dash|ksh|eval|su|ssh)[[:space:]]([^;&|]*[[:space:];&|({])?'
SHELL_CONFIG_PRE+="git${GIT_OPT}*[[:space:]]+"
UNSAFE_CONFIG_RE+="|$(config_set_re "${SHELL_CONFIG_PRE}")"
UNSAFE_CONFIG_RE+="|${SHELL_CONFIG_PRE}${CONFIG_FLAG}((pull|branch\.[^[:space:]=]*)\.rebase|(pull|merge)\.ff|remote\.[^[:space:]=]*\.mirror)${GIT_SUB_END}"
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
PUSH_FORCE_RE+="|${GIT_PUSH}([^;&|]*)[[:space:]]-f${WORD_END}"
PUSH_FORCE_RE+="|${GIT_PUSH}([^;&|]*)[[:space:]]--m(i(r(r(o(r)?)?)?)?)?([\"'\`]|${WORD_END})"
# A leading `+` on a refspec (`git push origin +main`) is also a force push.
PUSH_FORCE_RE+="|${GIT_PUSH}([^;&|]*)[[:space:]][+]"
DIRECT_MAIN_RE="${GIT_PUSH}([^;&|]*[[:space:]])?"
DIRECT_MAIN_RE+="(origin[[:space:]]+)?[+]?((refs/)?heads/)?(main|master)${PUSH_END}"
DIRECT_MAIN_RE+="|${GIT_PUSH}[^;&|]*:((refs/)?heads/)?(main|master)${PUSH_END}"
# `(git push origin main)`, only where a command starts: a message may end a parenthesis there.
DIRECT_MAIN_GROUP_RE="${GIT_AT_START}push([^;&|]*[[:space:]])?([^[:space:];&|]*:|[+])?((refs/)?heads/)?(main|master)[)]"
# A push at the start of a command or of a shell string, so text that only mentions one is not
# read: every branch (`--all`, `--branches`, `:`, a wildcard), a delete of a remote branch, and a
# force flag in a cluster.
GIT_START_RE="(${GIT_AT_START}|${SHELL_STRING_START}git${GIT_OPT}*[[:space:]]+)"
PUSH_REFS_END="([\"'\`]|${WORD_END})"
PUSH_REFS_RE="${GIT_START_RE}push([^;&|]*)[[:space:]]((--al(l)?|--b(r(a(n(c(h(e(s)?)?)?)?)?)?)?"
PUSH_REFS_RE+="|--de(l(e(t(e)?)?)?)?|-[vqnfu46]*d[a-zA-Z46]*)${PUSH_REFS_END}"
PUSH_REFS_RE+="|[+]?:([^;&|[:space:]]|${WORD_END})|[^-;&|[:space:]][^;&|[:space:]]*[*])"
PUSH_CLUSTER_RE="${GIT_START_RE}push([^;&|]*)[[:space:]]-[vqndu46]*f[a-zA-Z46]*${PUSH_REFS_END}"
FETCH_TO_SHELL_RE='(curl|wget|iwr|irm|invoke-webrequest|invoke-restmethod)[^|]*[|][[:space:]]*'
FETCH_TO_SHELL_RE+="(bash|sh|zsh|iex|invoke-expression)${WORD_END}"

# What `git submodule foreach` runs, as command lines of their own with and without quotes.
# Only for a command or shell string that runs git submodule, not for text that mentions it.
foreach_tail() {
    awk -v BINMODE=3 '
BEGIN {
    r = "[0-9]*[<>&]+[ \t]*[^ \t;&|]+"
    a = "[A-Za-z_][A-Za-z0-9_]*=[^ \t;&|]*"
    re = "submodule(--helper)?([ \t]+(-[^ \t;&|]*|" r "|" a "))*[ \t]+[\"\047]?foreach[\"\047]?"
    re = re "([ \t]+(-[^ \t;&|]*|" r "|" a "))*[ \t]+[\"\047]?"
}
{
    while (match($0, re)) {
        $0 = substr($0, RSTART + RLENGTH); print
        t = $0; gsub(/["\047]/, "", t); print t
    }
}'
}
FOREACH_TEXT=""
if matches_flags "${GIT_START_RE}submodule"; then
    FOREACH_TEXT=$(foreach_tail <<<"${FLAGS_TEXT}") || block "Could not read the command."
    MATCH_TEXT+=$'\n'"${FOREACH_TEXT}"
    CODE_TEXT+=$'\n'"${FOREACH_TEXT}"
    FLAGS_TEXT+=$'\n'"${FOREACH_TEXT}"
fi

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

if matches "${COMMAND_PREFIX}sudo${WORD_END}"; then
    block "Do not run sudo from Codex without explicit human approval."
fi

if matches "${COMMAND_PREFIX}mkfs([.[:alnum:]_-]*)${WORD_END}"; then
    block "Refusing filesystem formatting commands."
fi

if matches "${COMMAND_PREFIX}dd${WORD_END}"; then
    block "Refusing raw disk write command dd."
fi

if matches "${FETCH_TO_SHELL_RE}"; then
    block "Do not pipe downloaded scripts directly into a shell."
fi

if matches_code "${PUSH_REFS_RE}"; then
    block "Do not push all branches or delete a remote branch unless the user explicitly requested it."
fi

if matches "${PUSH_FORCE_RE}" || matches_code "${PUSH_CLUSTER_RE}"; then
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

# A GIT_CONFIG_* assignment can reach git from many places: after any wrapper or path, a
# backtick, `>(`, `case ... )`, `export --`, `env -S`, after the command under `set -k`, or as
# a quoted `env`/`export`/`declare` argument, with quotes, `$'...'` or a backslash-newline
# inside its value. So it is matched anywhere, in every copy, the quote-free ones included.
# The one exception is a search for the text: the whole command is one `git grep`, `grep` or
# `rg` whose only quoted part is one single-quoted argument that does not start with `-`, with
# every other word a plain option or path (no `=`, no `-O` or `--open-files-in-pager` or its
# abbreviation `--op`, no `--pre`: those run a program). Single quotes expand nothing, and a
# quoted `'-O...'` would still be an option, so the argument is a pattern or an option value.
search_only_command() {
    local cmd=${ORIG_CMD} word='[A-Za-z0-9_./][A-Za-z0-9_./-]*' opt='-[-A-Za-z0-9]*' re
    [[ "${cmd}" == *[$'\n\r']* ]] && return 1
    [[ "${cmd}" =~ [[:blank:]]-[^-[:blank:]]*O|--(op|pre) ]] && return 1
    re="^[[:blank:]]*(git([[:blank:]]+-C[[:blank:]]+${word})*[[:blank:]]+grep|grep|rg)"
    re+="([[:blank:]]+(${opt}|${word}))*[[:blank:]]+'([^-'][^']*)?'"
    re+="([[:blank:]]+(${opt}|${word}))*[[:blank:]]*\$"
    [[ "${cmd}" =~ ${re} ]]
}
# A longer key is another key (`pull.ffx`), but the shell or `env -S` can cut the rest off
# (`${v%X}`, IFS, `\c`), and another program can rewrite it (`xargs -I`). So the key's end is read
# only when the whole command is one line of plain assignments, git and plain words, where nothing
# is expanded, split, unquoted or decoded.
other_key_only() {
    local re='^([A-Za-z_][A-Za-z0-9_]*=[A-Za-z0-9_./:-]* +)+git( [A-Za-z0-9_./: -]*)?$'
    [[ "${ORIG_CMD}" != *GIT_CONFIG_PARAMETERS* && "${ORIG_CMD}" =~ ${re} ]] || return 1
    ! matches "${GIT_CONFIG_ENV}([^[:alnum:].-]|\$)"
}
if { matches "${GIT_CONFIG_ENV}" || matches_code "${GIT_CONFIG_ENV}" ||
    matches_flags "${GIT_CONFIG_ENV}"; } && ! search_only_command && ! other_key_only; then
    block "Do not set clean.requireForce or a shell alias for one git command; ask the user."
fi

if grep -qiE "${INNER_GIT_RE}" <<<"${FOREACH_TEXT}"; then
    block "This git command is forbidden by the exec-policy rules, also in git submodule foreach."
fi

if ((INNER)) && { matches_flags "${INNER_GIT_RE}" || matches_flags "${GIT_AT_START}(${FORBIDDEN_GIT_RE})"; }; then
    block "This git command is forbidden by the exec-policy rules, also inside a shell string."
fi

# The shell-string pattern reads the raw text, so a message inside the string
# (`bash -c 'git commit -m "about --amend"'`) looks like an option. When the whole command is
# one `bash -c` or `sh -c` with a single- or double-quoted string, nothing after it, and no
# character in the string that bash would expand or unescape, the string's value is exactly
# its text: this hook checks that value as a command of its own, with message blanking, and
# the pattern is not applied. Anything else, or any failure of that run, keeps the pattern.
inner_string_allowed() {
    local re value json back
    ((INNER)) && return 1
    re='^[ 	]*(/[A-Za-z0-9_./-]*/)?(bash|sh)([ 	]+(-[a-np-zA-NP-Z]+|--(login|noprofile|norc|posix)))*'
    re+="[ 	]+-[a-np-zA-NP-Z]*c[a-np-zA-NP-Z]*[ 	]+('([^']*)'|\"([^\"\$\`\\\\]*)\")[ 	]*\$"
    [[ "${ORIG_CMD}" =~ ${re} ]] || return 1
    value="${BASH_REMATCH[7]}${BASH_REMATCH[8]}"
    # With -k (keyword), bash drops every NAME=value word from the arguments, so a word this
    # hook reads as an option value can vanish (`git -C X=1 . stash`). This keeps the pattern
    # for the plain spellings; it narrows that older gap, which the pattern misses too, and
    # does not close it (`shopt -so keyword`, `set $o`). Message blanking stops at such a
    # word on its own (split_words), so -k cannot hide an option behind a message.
    [[ "${ORIG_CMD%%[\"\']*}" =~ [[:space:]]-[a-zA-Z]*k ]] && return 1
    [[ "${value}" =~ (^|[^A-Za-z0-9_])set[[:space:]][^\;\&\|]*(-[a-zA-Z]*k|keyword) ]] && return 1
    # Git Bash rewrites a path-like argument (`/usr/bin/git`) for a native jq.exe; turn that
    # off, and use the string only if the input decodes back to the same text.
    json=$(MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' jq -n --arg c "${value}" '{tool_input:{command:$c}}') ||
        return 1
    back=$(jq -r '.tool_input.command' <<<"${json}") || return 1
    # A native Windows jq.exe writes each newline as CRLF (see the start of this file).
    [[ "$(jq -rn '"a\nb"')" == $'a\r\nb' ]] && back=${back//$'\r\n'/$'\n'}
    [[ "${back}" == "${value}" ]] || return 1
    # The inner run's reason is kept, so a policy block and a failed run read differently
    # (the tests check which one they got). Only this hook's own `BLOCKED: ` line is passed on.
    local rc=0 out ok='^BLOCKED: [^[:cntrl:]]+$'
    out=$(printf '%s\n' "${json}" | bash "${BASH_SOURCE[0]}" --inner 2>&1 >/dev/null) || rc=$?
    ((rc == 0)) && return 0
    out=${out%%$'\n'*}
    out=${out%$'\r'}
    # The length is checked apart: some regex libraries reject a repeat bound over 255.
    if ((rc == 2 && ${#out} <= 300)) && [[ "${out}" =~ ${ok} ]]; then
        INNER_REASON=${out#BLOCKED: }
    else
        INNER_REASON="the check of the string failed (exit ${rc})."
    fi
    return 1
}

INNER_REASON=""
if matches "${SHELL_STRING_GIT_RE}" && ! inner_string_allowed; then
    if [[ -n "${INNER_REASON}" ]]; then
        block "Inside a shell string: ${INNER_REASON}"
    fi
    block "This git command is forbidden by the exec-policy rules, also inside a shell string."
fi

if matches_code "${PUBLISH_RE}"; then
    block "Publishing packages is not allowed from Codex; publish manually."
fi

if matches_code "${CHMOD_WORLD_RE}"; then
    block "World-writable permissions are not allowed from Codex."
fi

if matches "${DIRECT_MAIN_RE}" || matches_code "${DIRECT_MAIN_GROUP_RE}"; then
    block "Use feature branches and PRs; do not push directly to main/master."
fi

exit 0
