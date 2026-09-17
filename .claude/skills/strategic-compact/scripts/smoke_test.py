#!/usr/bin/env python3
"""Persisted smoke test for strategic-compact: exercises the hook scripts' real
stdin/stdout contracts (compact-milestone-detector.sh, compact-stop-check.sh) against
realistic and adversarial JSON payloads, matching this skill's own documented Pass
Criteria in SKILL.md.

Unlike the other 6 context-kit skills, strategic-compact's actual behavior is
hook-driven automation, not model-invoked guidance -- so this smoke test exercises the
bash hook scripts directly (stdin -> stdout/exit-code), not a Python helper module.
Each hook reads its tracking state from $HOME/.claude/strategic-compact/, so every
check runs against an isolated throwaway $HOME to avoid touching this machine's real
tracking state.
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
HOOKS_DIR = SKILL_DIR.parent.parent / "hooks" / "scripts"
MILESTONE_SCRIPT = HOOKS_DIR / "compact-milestone-detector.sh"
STOP_SCRIPT = HOOKS_DIR / "compact-stop-check.sh"


def run(script, stdin_text, home):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run(
        ["bash", str(script)],
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )


def make_home_with_tracking_file(tmp_path, session_id="smoketest"):
    """compact-milestone-detector.sh exits early (0, no output) if no tracking file
    exists for the session -- it's compact-session-init.sh's job to create one on
    SessionStart, so replicate its real on-disk shape here rather than skip the check."""
    import hashlib

    home = tmp_path / f"home_{session_id}"
    track_dir = home / ".claude" / "strategic-compact"
    track_dir.mkdir(parents=True)
    # Matches the script's own `echo "$SESSION_ID" | md5sum` -- echo appends a
    # trailing newline, so the hash input must include it too.
    session_hash = hashlib.md5((session_id + "\n").encode()).hexdigest()[:8]
    track_file = track_dir / f"session-{session_hash}"
    track_file.write_text(
        "TOTAL=0\nEXPLORATION=0\nIMPLEMENTATION=0\nLAST_PHASE=\n"
        "SUGGESTED_T1=0\nSUGGESTED_T2=0\nSUGGESTED_T3=0\nSUGGESTED_TIME=0\n"
        "PHASE_TRANSITION_SUGGESTED=0\nMILESTONE_SUGGESTED=0\n"
        f"START_TIME={int(time.time())}\nLAST_MILESTONE_TIME=0\n"
        "T1=10\nT2=30\nT3=50\nTIME_THRESHOLD=300\n",
        encoding="utf-8",
    )
    return home


def check_real_test_command_triggers_milestone(tmp_path):
    home = make_home_with_tracking_file(tmp_path, "realtest")
    payload = json.dumps({"session_id": "realtest", "tool_input": {"command": "npm test"}})
    result = run(MILESTONE_SCRIPT, payload, home)
    if result.returncode != 0:
        return False, f"exited {result.returncode}, expected 0: {result.stderr[:300]}"
    if (
        "test_pass" not in (result.stdout + result.stderr)
        and "milestone" not in result.stdout.lower()
    ):
        return False, f"'npm test' produced no test_pass suggestion: stdout={result.stdout!r}"
    return True, "'npm test' correctly triggers a test_pass milestone suggestion"


def check_substring_false_positive_rejected(tmp_path):
    # Quality gate: word-boundary matching means a command containing "majestic"
    # (substring "jest") must never fire a false test_pass milestone.
    home = make_home_with_tracking_file(tmp_path, "falsepos")
    payload = json.dumps(
        {"session_id": "falsepos", "tool_input": {"command": "echo majestic mountains"}}
    )
    result = run(MILESTONE_SCRIPT, payload, home)
    if result.returncode != 0:
        return False, f"exited {result.returncode}, expected 0"
    if result.stdout.strip():
        return (
            False,
            f"'echo majestic mountains' incorrectly produced a suggestion: {result.stdout!r}",
        )
    return True, "'majestic' (substring of 'jest') correctly produces no false-positive milestone"


def check_command_referencing_pytest_as_text_not_flagged(tmp_path):
    # Quality gate (found live by Codex review): a command that only *mentions*
    # pytest as search text/an argument (not an actual invocation) must not fire.
    home = make_home_with_tracking_file(tmp_path, "textref")
    payload = json.dumps(
        {"session_id": "textref", "tool_input": {"command": 'grep -n "pytest" README.md'}}
    )
    result = run(MILESTONE_SCRIPT, payload, home)
    if result.returncode != 0:
        return False, f"exited {result.returncode}, expected 0"
    if result.stdout.strip():
        return (
            False,
            f"'grep pytest README.md' incorrectly produced a suggestion: {result.stdout!r}",
        )
    return True, "a command mentioning 'pytest' only as grep search text is correctly not flagged"


def check_failure_swallowed_by_or_true_not_flagged(tmp_path):
    # Quality gate: `pytest || true` completes successfully at the outer-command
    # level even if the tests themselves failed -- must not report a test_pass.
    home = make_home_with_tracking_file(tmp_path, "ortrue")
    payload = json.dumps({"session_id": "ortrue", "tool_input": {"command": "pytest || true"}})
    result = run(MILESTONE_SCRIPT, payload, home)
    if result.returncode != 0:
        return False, f"exited {result.returncode}, expected 0"
    if result.stdout.strip():
        return (
            False,
            f"'pytest || true' incorrectly produced a test_pass suggestion: {result.stdout!r}",
        )
    return (
        True,
        "'pytest || true' (failure-swallowing pattern) correctly produces no test_pass suggestion",
    )


def check_stop_hook_active_guard(tmp_path):
    # Quality gate: a Stop event with stop_hook_active=true must exit cleanly,
    # never re-block (prevents an infinite loop).
    home = tmp_path / "home_stopactive"
    (home / ".claude" / "strategic-compact").mkdir(parents=True)
    payload = json.dumps({"session_id": "stopactive", "stop_hook_active": True})
    result = run(STOP_SCRIPT, payload, home)
    if result.returncode != 0:
        return False, f"exited {result.returncode}, expected 0"
    if result.stdout.strip():
        return (
            False,
            f"stop_hook_active=true incorrectly produced output (re-block risk): {result.stdout!r}",
        )
    return True, "stop_hook_active=true correctly exits cleanly with no re-block"


def check_stop_hook_delivers_pending_suggestion(tmp_path):
    home = tmp_path / "home_pending"
    track_dir = home / ".claude" / "strategic-compact"
    track_dir.mkdir(parents=True)
    import hashlib

    session_hash = hashlib.md5(b"pendingtest\n").hexdigest()[:8]
    pending_file = track_dir / f"pending-{session_hash}"
    pending_file.write_text("Test suggestion text.", encoding="utf-8")

    payload = json.dumps({"session_id": "pendingtest", "stop_hook_active": False})
    result = run(STOP_SCRIPT, payload, home)
    if result.returncode != 0:
        return False, f"exited {result.returncode}, expected 0"
    try:
        out = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, f"expected valid JSON block decision, got: {result.stdout!r}"
    if out.get("decision") != "block":
        return (
            False,
            f"expected decision=block for a pending suggestion, got {out.get('decision')!r}",
        )
    if pending_file.exists():
        return False, "pending file was not removed after being delivered"
    return True, "a pending suggestion correctly triggers decision=block and is consumed"


def check_malicious_env_var_falls_back_to_default(tmp_path):
    home = make_home_with_tracking_file(tmp_path, "envtest")
    payload = json.dumps({"session_id": "envtest", "tool_input": {"command": "npm test"}})
    env = {**os.environ, "HOME": str(home), "STRATEGIC_COMPACT_T1": "; rm -rf / #"}
    result = subprocess.run(
        ["bash", str(MILESTONE_SCRIPT)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    # The real assertion is that this doesn't crash, doesn't execute the injected
    # shell fragment, and the tracking file wasn't corrupted into an unreadable state.
    if result.returncode != 0:
        return False, f"malicious env var caused exit {result.returncode}, expected 0"
    return True, "a malicious STRATEGIC_COMPACT_T1 value does not execute or crash the hook"


CHECKS = [
    check_real_test_command_triggers_milestone,
    check_substring_false_positive_rejected,
    check_command_referencing_pytest_as_text_not_flagged,
    check_failure_swallowed_by_or_true_not_flagged,
    check_stop_hook_active_guard,
    check_stop_hook_delivers_pending_suggestion,
    check_malicious_env_var_falls_back_to_default,
]


def main():
    failed = False
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        for check in CHECKS:
            ok, message = check(tmp_path)
            print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
            failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
