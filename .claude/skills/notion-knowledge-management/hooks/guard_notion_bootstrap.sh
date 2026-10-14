#!/bin/bash
# Launcher for guard_notion_bootstrap.py (PreToolUse guard for notion-knowledge-management's Bootstrap
# grants). Uses the repo's required uv -> python3 -> python cascade. Unlike an advisory hook, this one is a
# guard, so when NO working interpreter is found it denies the call rather than letting it through.
#
# Each tier is probed FUNCTIONALLY (it must actually run a trivial program), not just found on PATH:
# `exec` replaces this process, so a present-but-broken interpreter (for example the Windows Store
# "python3" stub that prints "Python was not found" and exits 9009) would otherwise dead-end with an exit
# code the hook system treats as a non-blocking error, letting the guarded call through.
#
# The failure path below uses only shell builtins (cd, pwd, printf, ${var%/*}), so it still denies when
# PATH is empty or broken.
SELF="${BASH_SOURCE[0]}"
SELF="${SELF//\\//}" # a Windows path may reach bash with backslashes (e.g. from CLAUDE_PLUGIN_ROOT)
HERE="${SELF%/*}"
[ "$HERE" = "$SELF" ] && HERE="."
HERE="$(cd "$HERE" 2>/dev/null && pwd -P)"
SCRIPT="$HERE/guard_notion_bootstrap.py"

if [ -n "$HERE" ] && [ -f "$SCRIPT" ]; then
  if command -v uv >/dev/null 2>&1 && uv --version >/dev/null 2>&1; then
    exec uv run --no-project "$SCRIPT"
  elif command -v python3 >/dev/null 2>&1 && python3 -c 'import sys' >/dev/null 2>&1; then
    exec python3 "$SCRIPT"
  elif command -v python >/dev/null 2>&1 && python -c 'import sys' >/dev/null 2>&1; then
    exec python "$SCRIPT"
  fi
fi

printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Notion Bootstrap guard: no working Python interpreter (uv, python3 or python) or the guard script was not found, so this call cannot be verified. Install one, or stop and ask the user."}}'
exit 0
