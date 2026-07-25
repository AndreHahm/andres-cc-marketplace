#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
# PostToolUse + PostToolUseFailure hook (matcher: Agent|Bash on both events):
# best-effort, log-only reminder for plugin-rulebook R25 (Unplanned-Overhead
# Disclosure).
#
# Unlike R26's backing hook (r26-expensive-action-check.py), this hook cannot
# *verify* R25 compliance after the fact -- PostToolUse fires before Claude
# drafts its response text, so there is no way to check whether the eventual
# response actually discloses overhead in plain language. Instead, this hook
# detects the overhead SIGNAL itself (a tool call that recently failed on the
# same target, now succeeding) and emits a forward-looking reminder via
# systemMessage -- fed back to Claude before it writes its response, as a
# nudge to comply with R25, not a check that it already did. This is a
# structurally different mechanism from the R26 hook, not a copy of it.
#
# LOG-ONLY: never blocks (PostToolUse/PostToolUseFailure cannot block
# regardless of what this script does). Matches the security-precommit-check.py
# / r26-expensive-action-check.py precedent.
#
# Known limitations (first version, not yet broadened):
# - Target-key matching truncates to 50 chars (subagent_type is short and
#   unaffected, but two distinct Bash commands/Agent descriptions sharing an
#   identical 50-char prefix would be treated as the same target, producing
#   a false-positive reminder). Revisit if false positives are reported.
# - The PostToolUseFailure side's tool_name convention for a failed Agent
#   dispatch has not been directly confirmed against a real failed-dispatch
#   transcript (unlike the R26 hook's PostToolUse assumption, which was
#   transcript-verified). Spot-check before broad reliance.

import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Only correlate a failure with a later retry within this window -- a
# success on the same target an hour later is unrelated, not a retry.
STATE_TTL_SECONDS = 15 * 60

# Cap how long to wait for the state-file lock before giving up and skipping
# this invocation's update -- fail open, never block the underlying tool call.
LOCK_TIMEOUT_SECONDS = 2.0
LOCK_STALE_SECONDS = 5.0


def state_path(session_id):
    safe_id = "".join(c for c in str(session_id) if c.isalnum() or c in "-_") or "unknown"
    return Path(tempfile.gettempdir()) / f"plugin-devkit-r25-state-{safe_id}.json"


def target_key(tool_name, tool_input):
    if tool_name == "Agent":
        return tool_input.get("subagent_type") or str(tool_input.get("description", ""))[:50]
    if tool_name == "Bash":
        return str(tool_input.get("command", ""))[:50]
    return ""


def load_state(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(path, state):
    try:
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(state), encoding="utf-8")
        os.replace(tmp_path, path)
    except Exception:
        pass  # log-only, best-effort -- a failed write just means this observation is lost


def prune_stale(state, now):
    return {k: v for k, v in state.items() if now - v <= STATE_TTL_SECONDS}


def acquire_lock(lock_path):
    """Simple cross-platform mutex via exclusive file creation. Returns True if
    acquired, False if it timed out (caller should skip the update, fail open)."""
    start = time.time()
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > LOCK_STALE_SECONDS:
                    lock_path.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            if time.time() - start > LOCK_TIMEOUT_SECONDS:
                return False
            time.sleep(0.05)
        except OSError:
            return False


def release_lock(lock_path):
    try:
        lock_path.unlink()
    except OSError:
        pass


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)

    event = payload.get("hook_event_name", "")
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    session_id = payload.get("session_id", "unknown")

    if tool_name not in ("Agent", "Bash"):
        sys.exit(0)

    key = target_key(tool_name, tool_input)
    if not key:
        sys.exit(0)

    state_key = f"{tool_name}:{key}"
    path = state_path(session_id)
    lock_path = path.with_suffix(".lock")

    if not acquire_lock(lock_path):
        sys.exit(0)  # couldn't get the lock in time -- fail open, skip this update

    try:
        now = time.time()
        state = prune_stale(load_state(path), now)
        original = dict(state)

        if event == "PostToolUseFailure":
            state[state_key] = now
            if state != original:
                save_state(path, state)
            sys.exit(0)

        if event == "PostToolUse":
            if state_key in state:
                del state[state_key]
                save_state(path, state)
                print(json.dumps({
                    "systemMessage": (
                        "r25-overhead-disclosure-check (log-only, best-effort, does not "
                        f"block): {tool_name} target '{key}' just succeeded after a recent "
                        "failure on the same target in this session. Per plugin-rulebook "
                        "R25, disclose this retry/overhead to the user in plain language "
                        "alongside the result -- don't fold it silently into a "
                        "clean-looking final report. This hook cannot verify the "
                        "disclosure happens (it fires before your response is drafted); "
                        "it can only remind you the signal was detected."
                    ),
                }))
            elif state != original:
                save_state(path, state)
            sys.exit(0)
    finally:
        release_lock(lock_path)

    sys.exit(0)


if __name__ == "__main__":
    main()
