#!/usr/bin/env python3
"""Persisted smoke test for context-mode.

Runs scripts/set_mode.py as a subprocess against an isolated throwaway $HOME and checks its contract
(set, refresh, status, off, invalid and path-shaped values, missing session id, tampered state
file), the post-compact restore that re-injects the saved mode, and the skill's structure.
Model-driven activation of the /context-mode command is not covered here.
"""

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
PLUGIN_DIR = SKILL_DIR.parent.parent
SET_MODE = SKILL_DIR / "scripts" / "set_mode.py"
RESTORE = PLUGIN_DIR / "scripts" / "ctx-post-compact-restore.py"
SESSION = "smoke-session-1"
MODES = ("admin", "review", "ship")


def run(
    args: list[str],
    home: pathlib.Path,
    session: str | None = SESSION,
    script: pathlib.Path = SET_MODE,
    stdin: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env: dict[str, str] = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    if session is not None:
        env["CLAUDE_CODE_SESSION_ID"] = session
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, "-I", str(script), *args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )


def state_files(home):
    d = pathlib.Path(home) / ".claude" / "context-kit"
    return sorted(d.glob("mode-*")) if d.exists() else []


def check_structure():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return False, "SKILL.md has no frontmatter"
    fm = m.group(1)
    if not re.search(r"^name:\s*context-mode\s*$", fm, re.MULTILINE):
        return False, "frontmatter name is not context-mode"
    for rel in (
        "references/generic.md",
        "references/admin.md",
        "references/review.md",
        "references/ship.md",
        "scripts/set_mode.py",
    ):
        if not (SKILL_DIR / rel).is_file():
            return False, f"missing {rel}"
        if rel not in text:
            return False, f"SKILL.md does not reference {rel}"
    for rel in ("scripts/detect_mode.py", "triggers.json", "references/dev.md"):
        if (SKILL_DIR / rel).exists():
            return False, f"removed automation file still present: {rel}"
    return True, "frontmatter, references and removed files as expected"


def check_hook_removed():
    hooks = json.loads((PLUGIN_DIR / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    raw = json.dumps(hooks)
    if "detect_mode" in raw or "UserPromptSubmit" in hooks.get("hooks", {}):
        return False, "hooks.json still wires the detection hook"
    return True, "no detection hook in hooks.json"


def check_set_each_mode(tmp):
    for mode in MODES:
        home = pathlib.Path(tmp) / f"home_{mode}"
        home.mkdir()
        r = run([mode], home)
        if r.returncode != 0:
            return False, f"{mode}: exit {r.returncode}: {r.stderr.strip()}"
        if f"[Context-Mode] {mode} active" not in r.stdout:
            return False, f"{mode}: announcement missing"
        if "# Generic Posture" not in r.stdout or f"# {mode.capitalize()} Mode" not in r.stdout:
            return False, f"{mode}: generic or mode profile missing from output"
        files = state_files(home)
        if len(files) != 1 or files[0].read_text(encoding="utf-8").strip() != mode:
            return False, f"{mode}: state file not written correctly"
    return True, "admin, review and ship each print the profile and save state"


def check_refresh_status_off(tmp):
    home = pathlib.Path(tmp) / "home_cycle"
    home.mkdir()
    if "No context mode is active" not in run(["status"], home).stdout:
        return False, "status before any mode should say none"
    run(["review"], home)
    if "Active context mode: review" not in run(["status"], home).stdout:
        return False, "status did not report review"
    r = run(["refresh"], home)
    if "# Review Mode" not in r.stdout:
        return False, "refresh did not reprint the review profile"
    off = run(["off"], home)
    if off.returncode != 0 or state_files(home):
        return False, "off did not clear the state file"
    if "No context mode is active" not in run(["refresh"], home).stdout:
        return False, "refresh after off should say none"
    return True, "status, refresh and off behave"


def check_invalid_values(tmp):
    home = pathlib.Path(tmp) / "home_invalid"
    home.mkdir()
    run(["ship"], home)
    before = [f.read_text(encoding="utf-8") for f in state_files(home)]
    for bad in ("dev", "ADMIN", "../../etc/passwd", "admin;ls", ""):
        r = run([bad], home)
        if r.returncode != 2:
            return False, f"{bad!r}: expected exit 2, got {r.returncode}"
        if "Generic Posture" in r.stdout:
            return False, f"{bad!r}: a profile was printed for an invalid value"
    after = [f.read_text(encoding="utf-8") for f in state_files(home)]
    if before != after:
        return False, "an invalid value changed the saved state"
    if run([], home).returncode != 2:
        return False, "no argument should exit 2"
    return True, "invalid and path-shaped values are rejected with state untouched"


def check_no_session_id(tmp):
    home = pathlib.Path(tmp) / "home_nosession"
    home.mkdir()
    r = run(["admin"], home, session=None)
    if r.returncode != 0 or "# Admin Mode" not in r.stdout or "not saved" not in r.stdout:
        return False, "missing session id should print the profile and say it is not saved"
    if state_files(home):
        return False, "a state file was written without a session id"
    return True, "missing session id degrades to print-only"


def check_tampered_state(tmp):
    home = pathlib.Path(tmp) / "home_tampered"
    home.mkdir()
    run(["admin"], home)
    (state,) = state_files(home)
    state.write_text("../../../etc/passwd\n", encoding="utf-8")
    if "No context mode is active" not in run(["status"], home).stdout:
        return False, "a tampered state value was trusted"
    if "Generic Posture" in run(["refresh"], home).stdout:
        return False, "refresh read a profile for a tampered state value"
    return True, "a tampered state file is ignored"


def check_refuses_switch_and_replace(tmp):
    home = pathlib.Path(tmp) / "home_switch"
    home.mkdir()
    run(["ship"], home)
    r = run(["review"], home)
    if r.returncode != 3 or "Generic Posture" in r.stdout:
        return (
            False,
            f"switching to a different mode should exit 3 with no profile, got {r.returncode}",
        )
    if "Active context mode: ship" not in run(["status"], home).stdout:
        return False, "a refused switch changed the saved mode"
    if run(["ship"], home).returncode != 0:
        return False, "re-setting the same mode should succeed"
    for bad in (["replace"], ["replace", "dev"], ["replace", "review", "x"], ["swap", "review"]):
        if run(bad, home).returncode != 2:
            return False, f"{bad!r} should exit 2"
    ok = run(["replace", "review"], home)
    if ok.returncode != 0 or "# Review Mode" not in ok.stdout:
        return False, "replace <mode> should switch and print the new profile"
    if "Active context mode: review" not in run(["status"], home).stdout:
        return False, "replace did not save the new mode"
    return True, "a different mode is refused; only an explicit replace switches it"


def check_state_file_hardening(tmp):
    home = pathlib.Path(tmp) / "home_harden"
    home.mkdir()
    run(["admin"], home)
    directory = home / ".claude" / "context-kit"
    if (directory.stat().st_mode & 0o777) != 0o700:
        return False, "state directory should be created with mode 0700"
    if [p.name for p in directory.iterdir() if p.name.endswith(".tmp") or ".mode-" in p.name]:
        return False, "a temp file was left behind"
    (state,) = state_files(home)
    target = pathlib.Path(tmp) / "elsewhere.txt"
    target.write_text("ship\n", encoding="utf-8")
    state.unlink()
    state.symlink_to(target)
    if "No context mode is active" not in run(["status"], home).stdout:
        return False, "a symlinked state file was trusted"
    state.unlink()
    state.write_text("ship" + " " * 4000, encoding="utf-8")
    if "No context mode is active" not in run(["status"], home).stdout:
        return False, "an oversized state file was trusted"
    return True, "state directory is 0700; symlinked and oversized state files are ignored"


def check_restore_without_project_dir(tmp):
    home = pathlib.Path(tmp) / "home_restore_noproj"
    home.mkdir()
    run(["review"], home)
    payload = json.dumps({"source": "compact", "session_id": SESSION})
    env = {"CLAUDE_PROJECT_DIR": ""}
    r = run([], home, session=None, script=RESTORE, stdin=payload, extra_env=env)
    if "# Review Mode" not in r.stdout:
        return False, "restore skipped the saved mode when CLAUDE_PROJECT_DIR is unset"
    return True, "restore re-injects the saved mode even without CLAUDE_PROJECT_DIR"


def check_post_compact_restore(tmp):
    home = pathlib.Path(tmp) / "home_restore"
    home.mkdir()
    run(["ship"], home)
    payload = json.dumps({"source": "compact", "session_id": SESSION})
    r = run(
        [],
        home,
        session=None,
        script=RESTORE,
        stdin=payload,
        extra_env={"CLAUDE_PROJECT_DIR": str(home)},
    )
    if r.returncode != 0:
        return False, f"restore exited {r.returncode}"
    try:
        context = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    except (ValueError, KeyError):
        return False, "restore printed no additionalContext after a saved mode"
    if "# Ship Mode" not in context or "# Generic Posture" not in context:
        return False, "restore did not re-inject the saved mode's profile"
    other = json.dumps({"source": "compact", "session_id": "another-session"})
    r2 = run(
        [],
        home,
        session=None,
        script=RESTORE,
        stdin=other,
        extra_env={"CLAUDE_PROJECT_DIR": str(home)},
    )
    if "Ship Mode" in r2.stdout:
        return False, "restore leaked one session's mode into another session"
    return True, "post-compact restore re-injects the saved mode, per session"


def main():
    results = [check_structure(), check_hook_removed()]
    with tempfile.TemporaryDirectory() as tmp:
        for check in (
            check_set_each_mode,
            check_refresh_status_off,
            check_invalid_values,
            check_no_session_id,
            check_tampered_state,
            check_refuses_switch_and_replace,
            check_state_file_hardening,
            check_post_compact_restore,
            check_restore_without_project_dir,
        ):
            results.append(check(tmp))
    failed = 0
    for ok, msg in results:
        print(("PASS " if ok else "FAIL ") + msg)
        failed += 0 if ok else 1
    print(f"{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
