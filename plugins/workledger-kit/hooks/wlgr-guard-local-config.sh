#!/bin/bash
# PreToolUse guard on Write, Edit and MultiEdit: the person is asked before
# .claude/workledger-kit.local.json is written. wlgr_config.py trusts that file because it is untracked:
# it decides which repositories are collected and which submissions are enabled. A hook cannot tell which
# skill is calling, so this one never allows or denies: it prints one fixed "ask", or nothing.
#
# Shell builtins plus cat: it runs no interpreter and opens no path from the repository being edited.
# cat is run by absolute path, never looked up on PATH; the builtin read is the slow last resort.
# Limits: wlgr-kit-dependencies.md, "Guard hook".
#
# Signaling: JSON on stdout with exit 0; nothing on stdout means "no opinion".
LC_ALL=C
if [[ -x /usr/bin/cat ]]; then
  INPUT="$(/usr/bin/cat)"
elif [[ -x /bin/cat ]]; then
  INPUT="$(/bin/cat)"
else
  IFS= read -r -d '' INPUT
fi
shopt -s nocasematch
# "workle~" is the Windows 8.3 short name's stem.
NAME='workledger-kit\.local\.json|workle~'
[[ $INPUT =~ $NAME ]] || exit 0

# A quote inside a JSON string is escaped, so text being written cannot look like a "file_path" key. Any
# such key naming the file asks, not only the first. Without a readable path the whole input decides.
KEY='"file_path"[[:space:]]*:[[:space:]]*"([^"\]|\\.)*'
ANY_PATH="$KEY\""
NAMED_PATH="$KEY($NAME)"
if [[ $INPUT =~ $ANY_PATH ]]; then
  [[ $INPUT =~ $NAMED_PATH ]] || exit 0
fi

printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"workledger-kit: this may change .claude/workledger-kit.local.json, the file that decides which repositories are collected and which Linear and Notion submissions are enabled. Confirm only if you expect this change, for example the one you just approved in onboarding-repositories."}}'
exit 0
