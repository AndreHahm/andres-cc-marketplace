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
    local expected=$1 cmd rc got
    cmd=$(printf '%b' "$2")
    # MSYS_NO_PATHCONV: Git Bash would otherwise rewrite a path-like argument such as
    # `/bin/rm -Rf x` before the native jq.exe sees it. Ignored elsewhere.
    MSYS_NO_PATHCONV=1 jq -n --arg c "${cmd}" '{tool_input:{command:$c}}' |
        bash "${HOOK}" >/dev/null 2>&1
    rc=$?
    case "${rc}" in
        0) got=A ;;
        2) got=B ;;
        *) got="exit ${rc}" ;;
    esac
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
# --- heredocs: a quoted body is text, an unquoted or executed body is code
A	cat > note.md <<'EOF'\ngit rebase main\nEOF
A	cat > note.md <<"EOF"\ngit -C x stash\nEOF
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
CASES

printf 'pass=%d fail=%d (%s)\n' "${pass}" "${fail}" "${HOOK}"
[[ "${fail}" -eq 0 ]]
