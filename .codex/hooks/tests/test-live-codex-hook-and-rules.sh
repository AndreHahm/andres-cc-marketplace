#!/bin/bash
# Live check that a real Codex session loads this repository's project hook (.codex/hooks.json)
# and project exec-policy rules (.codex/rules/default.rules), issue #803. Unlike
# test-block-dangerous-command.sh, which pipes hook JSON into the script directly, this starts
# `codex exec` and asks the model to run three commands:
#
#   control     git -C . rev-parse --is-inside-work-tree   must run (the hook does not block all)
#   rule probe  echo CODEX_PROJECT_RULE_TEST                only the project rule forbids it
#   hook probe  git -C nonexistent-issue-803 stash          only the hook blocks it; harmless if run
#
# A PASS needs Codex's own evidence: the rule's justification `PROJECT RULE LOADED`, and the hook's
# own block message. The hook message can only appear if the hooks.json command string ran in a
# POSIX shell (it uses `$(...)`, `||` and `{ ...; }`) and that shell started bash on the script, so
# it also answers which kind of shell Codex uses to launch the hook. A generic rejection without
# either text is reported INCONCLUSIVE, not PASS.
#
# Prerequisites, all in your normal Codex setup: the project is trusted, the project PreToolUse hook
# is trusted in /hooks (trust is recorded per absolute hooks.json path, so a worktree may need its
# own), Codex is logged in, and jq is on PATH. It makes one model call and costs tokens.
#
# Usage: bash .codex/hooks/tests/test-live-codex-hook-and-rules.sh [timeout-seconds]
# Exit: 0 all PASS, 1 a FAIL, 3 INCONCLUSIVE (no FAIL). The raw transcript is kept for inspection.
set -uo pipefail

TIMEOUT="${1:-300}"
# From PowerShell or cmd, a bare `bash` can start WSL instead of Git Bash. WSL would test a different
# Codex and git, and cannot read a Windows worktree's .git file.
if grep -qi microsoft /proc/version 2>/dev/null; then
    echo "FAIL: running under WSL; on Windows run this with Git Bash, e.g. from PowerShell:" >&2
    printf '%s\n' '  & "C:\Program Files\Git\bin\bash.exe" .codex/hooks/tests/test-live-codex-hook-and-rules.sh' >&2
    exit 1
fi
root=$(git rev-parse --show-toplevel) || { echo "FAIL: not inside a git repository" >&2; exit 1; }
RULES="${root}/.codex/rules/default.rules"
command -v codex >/dev/null 2>&1 || { echo "FAIL: codex is not on PATH" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "FAIL: jq is required" >&2; exit 1; }

SENTINEL="CODEX_PROJECT_RULE_TEST"
HOOK_MSG="This git command is forbidden by the exec-policy rules"
RULE_MSG="PROJECT RULE LOADED"

# Preconditions: each probe must be stopped by exactly one layer, or a block proves nothing.
decision() { codex execpolicy check --rules "$1" -- "${@:2}" | jq -r '.decision // "none"'; }
[[ "$(decision "${RULES}" echo "${SENTINEL}")" == forbidden ]] ||
    { echo "FAIL: ${RULES} does not forbid 'echo ${SENTINEL}'" >&2; exit 1; }
[[ "$(decision "${RULES}" git -C nonexistent-issue-803 stash)" == none ]] ||
    { echo "FAIL: a project rule matches the hook probe, so a block would not prove the hook ran" >&2; exit 1; }
for f in "${CODEX_HOME:-${HOME}/.codex}"/rules/*.rules; do
    [[ -f "${f}" ]] && grep -q "${SENTINEL}" "${f}" &&
        echo "WARN: ${f} also holds the sentinel; a rule PASS no longer proves the project layer loaded"
done

OUT=$(mktemp "${TMPDIR:-/tmp}/codex-live-XXXXXX")
PROMPT="Run each of these three shell commands exactly once, in this order, without changing them and without retrying: (1) git -C . rev-parse --is-inside-work-tree (2) echo ${SENTINEL} (3) git -C nonexistent-issue-803 stash. Then reply with the exact output or error text of each, verbatim."
echo "Running codex exec (timeout ${TIMEOUT}s); transcript: ${OUT}"
timeout "${TIMEOUT}" codex exec --json --ephemeral --color never -C "${root}" "${PROMPT}" \
    </dev/null >"${OUT}" 2>&1
rc=$?
[[ "${rc}" -eq 124 ]] && { echo "INCONCLUSIVE: codex exec timed out after ${TIMEOUT}s"; exit 3; }

# Shell the tool commands ran under, when Codex reports it (Windows: pwsh.exe -Command '...').
shell=$(grep -o -m1 '[A-Za-z0-9_.-]*\(pwsh\|powershell\|bash\|cmd\)\.exe' "${OUT}" || true)
echo "codex exec exit ${rc}; tool-command shell seen in transcript: ${shell:-not reported}"

# Commands Codex actually ran, with their exit codes.
ran() {
    jq -r --arg c "$1" 'select(.item.type? == "command_execution") | .item
        | select((.command // "") | contains($c)) | "\(.exit_code // "none")"' "${OUT}" 2>/dev/null
}

status=0
report() { printf '%-12s %s\n' "$1" "$2"; [[ "$1" == FAIL ]] && status=1;
    [[ "$1" == INCONCLUSIVE && "${status}" -eq 0 ]] && status=3; return 0; }

if ran "rev-parse --is-inside-work-tree" | grep -qx 0; then
    report PASS "control: ran (the hook does not block every command)"
elif grep -q "rev-parse --is-inside-work-tree" "${OUT}" && grep -q "BLOCKED:" "${OUT}"; then
    report FAIL "control: blocked; the hook may be failing closed on every command"
else
    report INCONCLUSIVE "control: no successful run found in the transcript"
fi

if grep -q "${RULE_MSG}" "${OUT}"; then
    report PASS "rules: project rule matched (justification '${RULE_MSG}' seen)"
elif ran "echo ${SENTINEL}" | grep -qx 0; then
    report FAIL "rules: 'echo ${SENTINEL}' ran; the project rules were not loaded"
else
    report INCONCLUSIVE "rules: no justification text and no successful run"
fi

if grep -q "${HOOK_MSG}" "${OUT}"; then
    report PASS "hook: project hook blocked the probe (bash ran the hook script)"
elif ran "nonexistent-issue-803 stash" | grep -q .; then
    report FAIL "hook: the probe ran; the project hook did not block it"
elif grep -q "cannot locate the repository root" "${OUT}"; then
    report FAIL "hook: hooks.json could not resolve the repository root"
else
    report INCONCLUSIVE "hook: no hook message and no run of the probe"
fi

exit "${status}"
