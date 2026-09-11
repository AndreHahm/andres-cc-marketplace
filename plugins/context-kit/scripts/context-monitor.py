#!/usr/bin/env python3
"""
Context Usage Monitor Hook

Monitors approximate context usage and provides progressive, de-duplicated nudges:
- At 40%, 55%, 65%: suggest capturing a reusable discovery before auto-compaction
- At 80%: info-level note (auto-compact approaching)
- At 90%: caution-level note (finish the current task at full quality)

Hook Event: PostToolUse (matcher ".*", every successful tool call -- a
narrower Bash/Agent/Task-only matcher would silently skip a read-only
session and never nudge it). Throttled to 60-second intervals when below
the warning threshold.

Output contract (PostToolUse, exit 0): emits JSON on stdout with a `systemMessage`
(shown to the user) AND `hookSpecificOutput.additionalContext` (injected into
Claude's context). Plain stdout would reach Claude but NOT the user, and would
carry literal ANSI escape codes as noise — so we emit clean structured JSON.
See https://code.claude.com/docs/en/hooks.

Context %% is a COARSE PROXY. When the hook receives a `transcript_path`, we
estimate tokens from the transcript size against CLAUDE_CONTEXT_WINDOW_TOKENS
(default 200,000 — the standard context window; override via env var for a
larger-context tier). Otherwise we fall back to a tool-call counter
(CLAUDE_CONTEXT_MAX_TOOL_CALLS, default 400). Neither is exact; treat the
percentage as a rough early-warning signal, not a precise gauge.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Thresholds (effective percentage, where 100% ~ auto-compact)
LEARN_THRESHOLDS = [40, 55, 65]
THRESHOLD_WARN = 80
THRESHOLD_CRITICAL = 90

# Throttle interval in seconds (skip checks if below threshold and recent check)
THROTTLE_INTERVAL = 60

# Calibration defaults (both overridable via env)
DEFAULT_CONTEXT_WINDOW_TOKENS = 200_000  # standard context window
DEFAULT_MAX_TOOL_CALLS = 400  # fallback proxy when transcript size is unavailable
APPROX_BYTES_PER_TOKEN = 4.0


def _env_int(name: str, default: int) -> int:
    """Read a positive int from the environment, falling back to `default`."""
    try:
        value = int(os.environ.get(name, "") or default)
        return value if value > 0 else default
    except ValueError:
        return default


def _win_pid_alive(pid: int) -> bool:
    """Windows liveness check via OpenProcess + GetExitCodeProcess.

    `os.kill(pid, 0)` is NOT a liveness probe on Windows -- CPython routes
    signal 0 (== signal.CTRL_C_EVENT) through GenerateConsoleCtrlEvent,
    whose dwProcessGroupId parameter must be a recognized *process group*
    id, not an arbitrary PID. Live-tested: os.kill(explorer.exe's real,
    definitely-alive PID, 0) raises OSError WinError 87 -- the exact
    signature that would misclassify a genuinely alive, unrelated process
    as dead and bust its lock. OpenProcess is the actual Win32 existence
    check; live-tested against an unrelated alive process (explorer.exe),
    our own PID, a spawned-then-terminated child (alive, then dead after
    wait()), and a bogus PID -- all four classified correctly.
    """
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    ERROR_INVALID_PARAMETER = 87

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # Explicit restype/argtypes: without them, ctypes defaults a foreign
    # function's return value to c_int (32-bit signed) -- OpenProcess
    # actually returns a pointer-sized HANDLE, so an unset restype risks
    # silently truncating a handle value with any upper-32-bit content set
    # on 64-bit Windows. Every real handle value seen in live testing fit
    # in 32 bits (which is why the untyped version still passed those
    # tests), but that's not a guarantee -- pin the real types instead.
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        # ERROR_INVALID_PARAMETER means no such PID exists; any other
        # failure (e.g. access denied to a process owned by another user)
        # is treated as alive -- fail-safe, never bust a lock we can't
        # confirm dead.
        return ctypes.get_last_error() != ERROR_INVALID_PARAMETER
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return True  # couldn't query -- fail-safe, assume alive
        return exit_code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _pid_alive(pid: int) -> bool:
    """Best-effort process-liveness check. POSIX: os.kill(pid, 0) is a
    real liveness probe there (ProcessLookupError = dead, PermissionError
    = alive-but-owned-by-another-user). Windows: delegates to
    _win_pid_alive(), since os.kill(pid, 0) does not check process
    existence on that platform at all (see that function's docstring).
    """
    if os.name == "nt":
        return _win_pid_alive(pid)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True


def _write_lock_metadata(lock_dir: Path) -> bool:
    """Write this process's PID + creation time into an already-`mkdir`'d
    lock directory. Returns False (and removes the now-metadata-less lock
    directory) if the write itself fails, so a transient I/O error (disk
    full, an AV scanner momentarily holding the file, ...) can never leave
    a permanently stuck lock behind with no `created` file for a later
    invocation's stale-check to ever read -- every earlier `mkdir`-then-
    `write_text` call site in this module made that mistake; this helper
    is the single place both call it through now.
    """
    try:
        (lock_dir / "created").write_text(f"{os.getpid()}\n{int(time.time())}\n", encoding="utf-8")
        return True
    except OSError:
        try:
            for child in lock_dir.iterdir():
                child.unlink()
            lock_dir.rmdir()
        except OSError:
            pass
        return False


def _read_lock_metadata(lock_dir: Path) -> tuple[int, int] | None:
    """Read back the (pid, created_timestamp) recorded in a lock
    directory's `created` file, or None if it's missing/unparseable."""
    try:
        lines = (lock_dir / "created").read_text(encoding="utf-8").splitlines()
        return int(lines[0]), int(lines[1])
    except (OSError, ValueError, IndexError):
        return None


def _read_lock_owner(lock_dir: Path) -> int | None:
    """Read back just the PID recorded in a lock directory's `created`
    file, or None if it's missing/unparseable."""
    meta = _read_lock_metadata(lock_dir)
    return meta[0] if meta else None


def _acquire_cache_lock(session_dir: Path, max_attempts: int = 60) -> bool:
    """Acquire an exclusive lock on the session's cache directory via
    atomic `mkdir` (portable: works the same on POSIX and NTFS/Windows,
    unlike a plain file-existence check). Mirrors the Bash hook scripts'
    own two-phase scheme (see compact-track-and-suggest.sh's comment for
    the full rationale) -- many cheap mkdir-only retries first, then at
    most one bounded stale-lock check-and-bust before giving up. Returns
    False (fail-open: caller skips the cache update for this invocation
    rather than risk a torn read-modify-write) if the lock can't be
    acquired either way.
    """
    lock_dir = session_dir / "context-monitor-cache.lock"
    for _ in range(max_attempts):
        try:
            lock_dir.mkdir()
            return _write_lock_metadata(lock_dir)
        except FileExistsError:
            continue
        except OSError:
            return False

    meta = _read_lock_metadata(lock_dir)
    if meta is None:
        return False
    lock_pid, lock_created = meta

    age = time.time() - lock_created
    if age >= 10 and not _pid_alive(lock_pid):
        # Re-read immediately before the destructive delete below, rather
        # than trusting the read above: this narrows -- does not fully
        # eliminate -- the window in which a different waiter could have
        # already busted-and-recreated this same lock between the read
        # above and the delete here, which would otherwise make this
        # delete destroy a fresh, live lock instead of the stale one this
        # decision was based on. A fully race-proof version would need an
        # atomic claim (e.g. rename the stale dir to a uniquely-named path
        # first, which fails if another waiter already renamed it, before
        # deleting the renamed copy) -- not done here: this guards a
        # low-stakes, best-effort nudge cache, not safety-critical data,
        # and the remaining window is narrow.
        recheck = _read_lock_metadata(lock_dir)
        if recheck != meta:
            return False
        try:
            for child in lock_dir.iterdir():
                child.unlink()
            lock_dir.rmdir()
        except OSError:
            pass
        try:
            lock_dir.mkdir()
        except OSError:
            return False
        if not _write_lock_metadata(lock_dir):
            return False
        # Another waiter may have raced this same bust-and-recreate
        # window (two waiters both decide the same lock is stale at
        # nearly the same time) -- re-read the owner we just wrote and
        # confirm it's still us before declaring victory. If a different
        # PID now owns it, that waiter won the race; fail open rather
        # than proceed believing we hold a lock we don't.
        return _read_lock_owner(lock_dir) == os.getpid()
    return False


def _release_cache_lock(session_dir: Path) -> None:
    """Release the cache lock, only if this process still owns it -- a
    waiter that busted a stale lock and took ownership itself must never
    have that ownership pulled out from under it, mirroring the Bash hook
    scripts' own release-only-if-owner check.
    """
    lock_dir = session_dir / "context-monitor-cache.lock"
    owner_pid = _read_lock_owner(lock_dir)
    if owner_pid is None or owner_pid == os.getpid():
        try:
            for child in lock_dir.iterdir():
                child.unlink()
            lock_dir.rmdir()
        except OSError:
            pass


def get_session_dir(session_id: str = "") -> Path:
    """Get the session directory for storing cache files.

    Scoped by BOTH project and session: `session_id` (from the hook
    payload) is required for this cache to actually behave per-session as
    documented ("progressive, de-duplicated nudges") rather than silently
    per-project — a project-only key means a second session in the same
    project would inherit the first session's shown-threshold flags and
    tool-call count, suppressing/mistiming every nudge. An empty
    `session_id` (caller has no hook payload yet, or none was provided)
    falls back to a shared "default" bucket rather than crashing — a
    degraded-but-safe fallback, not the normal path.
    """
    import hashlib

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    project_hash = (
        hashlib.sha256(project_dir.encode()).hexdigest()[:8] if project_dir else "default"
    )
    session_hash = hashlib.sha256(session_id.encode()).hexdigest()[:8] if session_id else "default"

    session_dir = Path.home() / ".claude" / "sessions" / f"{project_hash}-{session_hash}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def read_cache(session_id: str = "") -> dict:
    """Read the context monitor cache."""
    cache_file = get_session_dir(session_id) / "context-monitor-cache.json"
    if not cache_file.exists():
        return {}
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def save_cache(data: dict, session_id: str = "") -> bool:
    """Save the context monitor cache. Returns True on success, False on a
    write failure -- callers that must not treat the write as done until it
    actually landed (see _maybe_reset_baseline's marker-unlink ordering)
    check this instead of assuming success."""
    cache_file = get_session_dir(session_id) / "context-monitor-cache.json"
    try:
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def _maybe_reset_baseline(transcript_path: str, session_id: str = "") -> None:
    """If post-compact-restore.py signaled a compaction just completed (via a
    marker file in the shared session dir), reset the byte baseline and every
    progressive-nudge flag.

    Compaction does not truncate the transcript file -- it retains every
    pre-compaction message plus a compact-summary marker in the same file
    (confirmed against plugins/session-kit/skills/session-recover/references/
    file-structure.md, this repo's own trusted reference: "the last compact
    boundary's summary reflects the most recent state... messages after the
    last boundary are the hot zone"). Without a baseline, `os.path.getsize()`
    on the whole file stays pegged near 100% forever after the first
    compaction, and a threshold already marked shown pre-compaction would
    never re-fire as the new, post-compaction context climbs back through it.

    The marker is set at SessionStart(source=compact) time (post-compact-
    restore.py) and consumed here, on the first PostToolUse call after it.
    post-compact-restore.py writes the transcript's byte size *at SessionStart
    time* into the marker's own content when `transcript_path` was present in
    its hook input (confirmed present on SessionStart's payload per Claude
    Code's own docs) -- read that pre-captured value here when present, so the
    baseline doesn't include the first post-compaction tool result's own bytes
    (found by CodeRabbit's automated review, 2026-09-11). Falls back to
    measuring `transcript_path` right now (this function's own long-standing
    behavior) when the marker is empty -- e.g. an older marker format, or
    post-compact-restore.py couldn't read transcript_path either.

    The marker is deleted only after the reset is durably persisted via
    save_cache() -- if that write hits a transient OSError, the marker stays
    in place so this reset is retried on the next PostToolUse call instead of
    silently being lost (found by CodeRabbit's automated review, 2026-09-11).
    """
    marker = get_session_dir(session_id) / "compact-baseline-reset-pending"
    if not marker.exists():
        return

    marker_content = ""
    try:
        marker_content = marker.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        marker_content = ""

    cache = read_cache(session_id)
    cache["shown_learn"] = []
    cache["shown_warn_80"] = False
    cache["shown_warn_90"] = False
    cache["tool_calls"] = 0
    baseline_bytes = 0
    if marker_content.isdigit():
        baseline_bytes = int(marker_content)
    elif transcript_path:
        try:
            baseline_bytes = os.path.getsize(transcript_path)
        except OSError:
            baseline_bytes = 0
    cache["baseline_bytes"] = baseline_bytes
    if save_cache(cache, session_id):
        try:
            marker.unlink()
        except OSError:
            pass


def estimate_context_percentage(hook_input: dict, session_id: str = "") -> float:
    """
    Estimate context usage as a percentage (0-100). COARSE PROXY.

    Preferred: a token estimate from the transcript file size (minus any
    post-compaction baseline -- see _maybe_reset_baseline) against the
    model's context window (CLAUDE_CONTEXT_WINDOW_TOKENS). Fallback when no
    transcript is available: a tool-call counter (CLAUDE_CONTEXT_MAX_TOOL_CALLS).
    Neither is exact.
    """
    window = _env_int("CLAUDE_CONTEXT_WINDOW_TOKENS", DEFAULT_CONTEXT_WINDOW_TOKENS)
    transcript_path = hook_input.get("transcript_path", "")
    _maybe_reset_baseline(transcript_path, session_id)

    if transcript_path:
        try:
            size_bytes = os.path.getsize(transcript_path)
            baseline = int(read_cache(session_id).get("baseline_bytes", 0))
            effective_bytes = max(size_bytes - baseline, 0)
            approx_tokens = effective_bytes / APPROX_BYTES_PER_TOKEN
            return min(approx_tokens / window * 100, 100)
        except OSError:
            pass

    # Fallback: tool-call counter (very rough)
    cache = read_cache(session_id)
    tool_calls = cache.get("tool_calls", 0) + 1
    cache["tool_calls"] = tool_calls
    save_cache(cache, session_id)
    max_calls = _env_int("CLAUDE_CONTEXT_MAX_TOOL_CALLS", DEFAULT_MAX_TOOL_CALLS)
    return min((tool_calls / max_calls) * 100, 100)


def is_throttled(percentage: float, session_id: str = "") -> bool:
    """Check if we should skip this check due to throttling."""
    cache = read_cache(session_id)
    last_check = cache.get("last_check_time", 0)
    now = time.time()

    # If below warning threshold and checked recently, skip
    if percentage < THRESHOLD_WARN and (now - last_check) < THROTTLE_INTERVAL:
        return True

    # Update last check time
    cache["last_check_time"] = now
    save_cache(cache, session_id)
    return False


def get_shown_thresholds(session_id: str = "") -> dict:
    """Get which thresholds have already been shown in this session."""
    cache = read_cache(session_id)
    return {
        "learn": cache.get("shown_learn", []),
        "warn_80": cache.get("shown_warn_80", False),
        "warn_90": cache.get("shown_warn_90", False),
    }


def mark_threshold_shown(
    threshold_type: str, value: int | bool = True, session_id: str = ""
) -> None:
    """Mark a threshold as shown."""
    cache = read_cache(session_id)
    if threshold_type == "learn":
        shown = cache.get("shown_learn", [])
        if value not in shown:
            shown.append(value)
        cache["shown_learn"] = shown
    else:
        cache[f"shown_{threshold_type}"] = value
    save_cache(cache, session_id)


def emit(system_message: str, claude_context: str) -> None:
    """Surface a note to BOTH the user and Claude via the PostToolUse JSON contract."""
    print(
        json.dumps(
            {
                "systemMessage": system_message,
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": claude_context,
                },
            }
        )
    )


def run_context_monitor() -> int:
    """Main monitoring logic."""
    # Read hook input
    try:
        hook_input = json.load(sys.stdin)
    except (OSError, json.JSONDecodeError):
        hook_input = {}

    session_id = hook_input.get("session_id", "") or ""
    session_dir = get_session_dir(session_id)

    # This hook can run concurrently for the same session (parallel tool
    # calls in one turn), and every cache-touching call below (estimate,
    # throttle check, shown-thresholds read, mark-shown write) forms one
    # logical read-modify-write cycle -- hold a single lock across all of
    # them for this invocation, mirroring the Bash hook scripts' own
    # per-invocation mkdir lock. Fail open (skip this invocation's cache
    # update and nudge entirely) if the lock can't be acquired, same as
    # the Bash scripts do -- a missed nudge self-corrects on the next
    # tool call; a torn cache write does not.
    if not _acquire_cache_lock(session_dir):
        return 0

    try:
        # Estimate current context usage (coarse proxy)
        percentage = estimate_context_percentage(hook_input, session_id)

        # Persist the latest estimate so the status line can surface it (best-effort).
        try:
            (session_dir / "context-pct.txt").write_text(f"{percentage:.0f}", encoding="utf-8")
        except Exception:
            pass

        # Check throttling
        if is_throttled(percentage, session_id):
            return 0

        shown = get_shown_thresholds(session_id)

        # Check the two urgency thresholds BEFORE the learn-threshold loop
        # below: if the very first unthrottled observation already lands
        # at 90%+ (e.g. resuming a session with an already-large
        # transcript, or one big tool call), the learn loop would
        # otherwise emit 40%, then 55%, then 65% across three separate
        # tool calls before ever reaching the urgent 90% warning on a
        # fourth call -- delaying the most important warning exactly when
        # auto-compaction is closest.

        # Check 90% threshold (critical)
        if percentage >= THRESHOLD_CRITICAL and not shown["warn_90"]:
            emit(
                f"⚠️ Context ~{percentage:.0f}% (approx) — auto-compact approaching. Finish the "
                "current task at full quality.",
                f"Context ~{percentage:.0f}% (coarse proxy); auto-compaction is approaching. "
                "Complete the current task without cutting corners or skipping verification, "
                "and make sure the session log and active plan are saved to disk — no context "
                "is lost, but summarize key decisions now.",
            )
            mark_threshold_shown("warn_90", True, session_id)
            # Also mark every lower, subsumed threshold shown -- otherwise a
            # sudden jump straight to 90%+ (skipping past 80% and the learn
            # thresholds without ever observing them individually) leaves
            # those flags False, and the next few tool calls would surface
            # progressively *less* urgent notices right after the most
            # urgent one already fired (found live by cross-model-review).
            mark_threshold_shown("warn_80", True, session_id)
            for threshold in LEARN_THRESHOLDS:
                mark_threshold_shown("learn", threshold, session_id)
            return 0  # Non-blocking note (exit 2 would feed stderr to Claude)

        # Check 80% threshold (info)
        if percentage >= THRESHOLD_WARN and not shown["warn_80"]:
            emit(
                f"💡 Context ~{percentage:.0f}% (approx) — auto-compact approaching; no rush.",
                f"Context ~{percentage:.0f}% (coarse proxy); auto-compaction will trigger soon. "
                "Ensure the session log and active plan are current on disk.",
            )
            mark_threshold_shown("warn_80", True, session_id)
            # Same subsumed-threshold reasoning as the 90% branch above.
            for threshold in LEARN_THRESHOLDS:
                mark_threshold_shown("learn", threshold, session_id)
            return 0

        # Check reusable-discovery thresholds (40%, 55%, 65%)
        for threshold in LEARN_THRESHOLDS:
            if percentage >= threshold and threshold not in shown["learn"]:
                emit(
                    f"💡 Context ~{percentage:.0f}% (approx) — if a reusable discovery emerged, "
                    "consider capturing it now before auto-compaction.",
                    f"Context usage is approximately {percentage:.0f}% (coarse proxy). If a "
                    "non-obvious discovery or reusable workflow emerged this session, consider "
                    "capturing it now — e.g. via session-kit's session-wrap-up skill, if "
                    "installed — before auto-compaction.",
                )
                mark_threshold_shown("learn", threshold, session_id)
                return 0  # Only show one message at a time

        return 0
    finally:
        _release_cache_lock(session_dir)


def main() -> int:
    """Main entry point."""
    return run_context_monitor()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail open — never block Claude due to a hook bug
        sys.exit(0)
