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
# own block message. The hook message can only appear if Codex ran the hook entry (`command`, or
# `commandWindows` on Windows) and it started bash on the script. A generic rejection without
# either text is reported INCONCLUSIVE, not PASS.
#
# Prerequisites, all in your normal Codex setup: the project is trusted, the project PreToolUse hook
# is trusted in /hooks, Codex is logged in, and jq and timeout are on PATH. It makes one model call and costs
# tokens. In a linked worktree Codex loads the main checkout's hooks.json, so this tests that copy.
#
# Usage: bash .codex/hooks/tests/test-live-codex-hook-and-rules.sh [timeout-seconds [codex-exec-args...]]
# Arguments after the timeout go to `codex exec` unchanged, e.g. -c 'default_permissions=":workspace"'.
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
command -v timeout >/dev/null 2>&1 || { echo "FAIL: timeout (GNU coreutils) is required" >&2; exit 1; }

SENTINEL="CODEX_PROJECT_RULE_TEST"
HOOK_MSG="This git command is forbidden by the exec-policy rules"
RULE_MSG="PROJECT RULE LOADED"

# Preconditions: each probe must be stopped by exactly one layer, or a block proves nothing.
decision() { codex execpolicy check --rules "$1" -- "${@:2}" | jq -r '.decision // "none"'; }
[[ "$(decision "${RULES}" echo "${SENTINEL}")" == forbidden ]] ||
    { echo "FAIL: ${RULES} does not forbid 'echo ${SENTINEL}'" >&2; exit 1; }
[[ "$(decision "${RULES}" git -C nonexistent-issue-803 stash)" == none ]] ||
    { echo "FAIL: a project rule matches the hook probe, so a block would not prove the hook ran" >&2; exit 1; }
user_sentinel=""
for f in "${CODEX_HOME:-${HOME}/.codex}"/rules/*.rules; do
    [[ -f "${f}" ]] && grep -q "${SENTINEL}" "${f}" && user_sentinel="${f}" &&
        echo "WARN: ${f} also holds the sentinel; the rules result can only be INCONCLUSIVE"
done

OUT=$(mktemp "${TMPDIR:-/tmp}/codex-live-XXXXXX")
PROMPT="Run each of these three shell commands exactly once, in this order, without changing them and without retrying: (1) git -C . rev-parse --is-inside-work-tree (2) echo ${SENTINEL} (3) git -C nonexistent-issue-803 stash. Then reply with the exact output or error text of each, verbatim."
echo "Running codex exec (timeout ${TIMEOUT}s); transcript: ${OUT}"
timeout "${TIMEOUT}" codex exec --json --ephemeral --color never -C "${root}" "${@:2}" "${PROMPT}" \
    </dev/null >"${OUT}" 2>&1
rc=$?
[[ "${rc}" -eq 124 ]] && { echo "INCONCLUSIVE: codex exec timed out after ${TIMEOUT}s"; exit 3; }

# Shell the tool commands ran under, when Codex reports it (Windows: pwsh.exe -Command '...').
shell=$(grep -o -m1 '[A-Za-z0-9_.-]*\(pwsh\|powershell\|bash\|cmd\)\.exe' "${OUT}" || true)
echo "codex exec exit ${rc}; tool-command shell seen in transcript: ${shell:-not reported}"

# Command items for a command. The transcript also holds stderr lines that are not JSON, so read raw
# lines and parse only the JSON ones. A started item has no exit code yet and does not count as a run.
items() {
    jq -cR --arg c "$1" 'fromjson? | select(.item.type? == "command_execution") | .item
        | select((.command // "") | contains($c)) | select(.exit_code != null)' "${OUT}" 2>/dev/null
}
# Exit codes of the finished runs of a command that no hook blocked (no BLOCKED: in its own output).
runs() { items "$1" | jq -r 'select((.aggregated_output // "") | contains("BLOCKED:") | not) | .exit_code'; }
# Finished runs of a command that printed a hook BLOCKED: message in their own output (empty if none).
blocked() { items "$1" | jq -c 'select((.aggregated_output // "") | contains("BLOCKED:"))'; }
# Results are kept in variables and matched with here-strings: `producer | grep -q` under pipefail can
# fail when grep exits early and the producer gets SIGPIPE.
control_runs=$(runs "rev-parse --is-inside-work-tree")
control_blocked=$(blocked "rev-parse --is-inside-work-tree")
rule_runs=$(runs "echo ${SENTINEL}")
probe_runs=$(runs "nonexistent-issue-803 stash")

status=0
report() { printf '%-12s %s\n' "$1" "$2"; [[ "$1" == FAIL ]] && status=1;
    [[ "$1" == INCONCLUSIVE && "${status}" -eq 0 ]] && status=3; return 0; }

if grep -qx 0 <<<"${control_runs}"; then
    report PASS "control: ran (the hook does not block every command)"
elif [[ -n "${control_blocked}" ]]; then
    report FAIL "control: blocked; the hook may be failing closed on every command"
else
    report INCONCLUSIVE "control: no successful run found in the transcript"
fi

# A run of a probe outranks any text in the transcript: text alone could come from the model's reply.
if grep -qx 0 <<<"${rule_runs}"; then
    report FAIL "rules: 'echo ${SENTINEL}' ran; the project rules were not loaded"
elif grep -q "${RULE_MSG}" "${OUT}" && [[ -n "${user_sentinel}" ]]; then
    report INCONCLUSIVE "rules: justification seen, but ${user_sentinel} also holds the sentinel"
elif grep -q "${RULE_MSG}" "${OUT}"; then
    report PASS "rules: project rule matched (justification '${RULE_MSG}' seen)"
else
    report INCONCLUSIVE "rules: no justification text and no successful run"
fi

if [[ -n "${probe_runs}" ]]; then
    report FAIL "hook: the probe ran; the project hook did not block it (check /hooks trust; a worktree runs the main checkout's hooks.json)"
elif grep -q "${HOOK_MSG}" "${OUT}"; then
    report PASS "hook: project hook blocked the probe (bash ran the hook script)"
elif grep -q "cannot locate the repository root" "${OUT}"; then
    report FAIL "hook: hooks.json could not resolve the repository root"
elif grep -q -e "cannot find Git Bash or the command-policy script" -e "could not start Git Bash" "${OUT}"; then
    report FAIL "hook: commandWindows could not find or start Git Bash or the hook script"
elif grep -q "the command-policy hook failed with exit" "${OUT}"; then
    report FAIL "hook: the hook script failed (fail-closed block, not a policy decision)"
else
    report INCONCLUSIVE "hook: no hook message and no run of the probe"
fi

exit "${status}"
