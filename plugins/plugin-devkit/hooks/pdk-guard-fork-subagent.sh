#!/bin/bash
# PreToolUse guard: hard-blocks any Agent tool call with subagent_type "fork".
# Backs disallow-fork-subagent.md's absolute prohibition -- fork has
# repeatedly failed to reliably use this repo's own skills or follow its
# rules, producing unreliable output (see that rule's own Why section for
# the full rationale). Ships in plugin-devkit's own hooks.json, so this
# guard is active in any project that installs plugin-devkit, not only this
# repo -- a deliberate scope choice (2026-09-25), not an accident; see that
# rule's own Enforcement section for the disclosure.
#
# Unlike git-kit's raw-command guards (guard-raw-branch-create.sh etc.),
# there is no marker-handshake bypass here: the source rule is an absolute
# ban, not a "use the matching skill instead" redirect, so there is nothing
# for a legitimate caller to authorize around.
#
# Known fail-open residuals (same class guard-raw-branch-create.sh
# discloses): under this hook's "onError": "warn" registration, a fork call
# is let through with just a warning -- never silently, always logged -- if
# this script's own process is killed by the hook timeout, its interpreter
# or the script file itself is missing/non-executable, or a bash parse/
# expansion error occurs before the trap below can install. None of these
# are within this script's own control to close. Confirmed against
# hook-development's own how-hooks-work.md ("Hook Result & onError"): under
# "warn", a failed hook logs and Claude continues -- i.e. the guarded call
# proceeds -- so this is a documented tradeoff, not a guess.
#
# Signaling mode: this script only ever uses structured JSON on stdout with
# exit 0 (never exit 2) -- both the substantive deny and every fail-closed
# path below emit a JSON permissionDecision and exit 0, per this hook
# system's "pick exactly one signaling mode" contract.
set -euo pipefail

# Fail closed on an unexpected non-zero exit below (e.g. jq choking on
# malformed input) -- an ordinary command failure must not silently crash
# this script and let an unverified Agent call through unguarded. Same
# pattern as git-kit's guard-raw-branch-create.sh (see its header comment
# for the fuller rationale); an `if`/`case` test itself is exempt from this
# trap, matching that precedent.
fail_closed_deny() {
  cat <<'EOF' || true
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "The fork-subagent guard failed unexpectedly and could not verify this Agent call's subagent_type -- denying by default rather than letting an unverified call through unguarded."
  }
}
EOF
  exit 0
}
trap fail_closed_deny ERR

# Fail closed, not open: without jq this script can't parse INPUT and would
# otherwise crash, which under this hook's "onError": "warn" registration
# would let the call proceed with just a warning. Deny explicitly instead,
# so a missing dependency can't silently defeat this guard -- same tradeoff
# guard-raw-branch-create.sh makes for the identical reason.
if ! command -v jq >/dev/null 2>&1; then
  cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "The fork-subagent guard requires `jq`, which isn't available in this environment -- ALL Agent calls (not just fork) are denied until jq is installed, since this guard cannot verify subagent_type without it."
  }
}
EOF
  exit 0
fi

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')

if [ "$TOOL_NAME" != "Agent" ]; then
  exit 0
fi

# Lowercased and trimmed before comparison: the Agent tool's subagent_type
# is a plain string with no enum constraint (verified against its live tool
# schema, not assumed), so a differently-cased or whitespace-padded "fork"
# value must not slip past an exact-match check.
SUBAGENT_TYPE=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // empty | ascii_downcase | gsub("^\\s+|\\s+$"; "")')

if [ "$SUBAGENT_TYPE" != "fork" ]; then
  exit 0
fi

cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Agent(subagent_type: \"fork\") is disallowed by plugin-devkit's disallow-fork-subagent rule (see that plugin's rules/ directory, or .claude/rules/disallow-fork-subagent.md in this repo). Fork has repeatedly failed to reliably use skills or follow rules, producing unreliable output. Dispatch a fresh (non-fork) subagent_type instead, e.g. \"general-purpose\" or a specific named agent -- it starts without inherited context, so write it a self-contained prompt."
  }
}
EOF
exit 0
