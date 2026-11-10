#!/usr/bin/env python3
"""
Context Usage Monitor Hook

Monitors approximate context usage and provides progressive, de-duplicated nudges:
- At 65%: suggest capturing a reusable discovery before auto-compaction
- At 80%: info-level note (auto-compact approaching)
- At 90%: caution-level note (finish the current task at full quality)

Hook Event: PostToolUse (matcher ".*", every successful tool call -- a
narrower Bash/Agent/Task-only matcher would silently skip a read-only
session and never nudge it). Throttled to 60-second intervals when below
the warning threshold. Runs synchronously, not async (unlike this plugin's
PreToolUse ".*" handler): a context-fullness warning is only useful if it
lands on the same turn the threshold was crossed -- an async result would
deliver on a later turn, defeating the point of a timely nudge. The
per-call cost is bounded by the same 60-second throttle plus a benchmarked
83-97ms real overhead (see strategic-compact's own SKILL.md).

Output contract (PostToolUse, exit 0): emits JSON on stdout with a `systemMessage`
(shown to the user) AND `hookSpecificOutput.additionalContext` (injected into
Claude's context). Plain stdout would reach Claude but NOT the user, and would
carry literal ANSI escape codes as noise — so we emit clean structured JSON.
See `code.claude.com/docs/en/hooks`.

Context %% comes from the real token usage the API reported for the latest
main-chain assistant turn in the transcript (input + cache-read + cache-creation
tokens), against the configured window. The window is resolved in this order:
the CLAUDE_CONTEXT_WINDOW_TOKENS env var, then `context_window_tokens` in
`.claude/context-kit.local.json` (gitignored, per project), then the same key in
the shipped `assets/context-kit.settings.json`, then 200,000. Only
when no usage record exists yet do we fall back to a tool-call counter
(CLAUDE_CONTEXT_MAX_TOOL_CALLS, default 400). The transcript FILE SIZE is
deliberately not used: it counts records that never reach the model (instructions
and prompt-snapshot attachments, API request blobs) and read ~97%% at the first
tool call of every session (issue #690).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Thresholds (effective percentage, where 100% ~ auto-compact)
LEARN_THRESHOLDS = [65]
THRESHOLD_WARN = 80
THRESHOLD_CRITICAL = 90

# Throttle interval in seconds (skip checks if below threshold and recent check)
THROTTLE_INTERVAL = 60

# Calibration defaults (both overridable via env)
# Last-resort fallback; keep equal to `context_window_tokens` in context-kit.settings.json.
# It is the effective value in the .claude/ mirror copies of this script, which sit
# next to no settings file.
DEFAULT_CONTEXT_WINDOW_TOKENS = 200_000
DEFAULT_ALERT_MIN_PERCENT = 50  # likewise equal to alert_min_context_percent in the settings file
DEFAULT_MAX_TOOL_CALLS = 400  # fallback proxy when no usage record exists yet
SETTINGS_FILE_NAME = "context-kit.settings.json"
LOCAL_SETTINGS_REL = Path(".claude") / "context-kit.local.json"
# Bytes read from the end of the transcript when looking for the latest usage
# record, then retried once with the larger size. Single records can be >100 KB.
USAGE_TAIL_BYTES = (512 * 1024, 8 * 1024 * 1024)


def _env_int(name: str, default: int) -> int:
    """Read a positive int from the environment, falling back to `default`."""
    try:
        value = int(os.environ.get(name, "") or default)
        return value if value > 0 else default
    except ValueError:
        return default


def _read_int_setting(path: Path, key: str, low: int, high: int | None) -> int | None:
    """Read integer `key` from a settings JSON file, or None when the file is
    missing, unparseable, or the value is not an integer within [low, high].

    No trust-boundary check, unlike git-kit's settings: these values only tune
    advisory nudges and gate no safety control or automation, so a tracked copy
    of the local file is harmless."""
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get(key)
    except (OSError, ValueError, AttributeError):
        return None
    if isinstance(value, int) and not isinstance(value, bool) and value >= low:
        if high is None or value <= high:
            return value
    return None


def _lookup_setting(key: str, low: int, high: int | None, default: int) -> int:
    """Resolve `key`: the project's local override, then the plugin's shipped
    default file, then `default`. An invalid value in one file falls through to
    the next."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    candidates = []
    if project_dir:
        candidates.append(Path(project_dir) / LOCAL_SETTINGS_REL)
    candidates.append(Path(__file__).resolve().parent.parent / "assets" / SETTINGS_FILE_NAME)
    for candidate in candidates:
        value = _read_int_setting(candidate, key, low, high)
        if value is not None:
            return value
    return default


def _context_window_tokens() -> int:
    """Resolve the context window size: env var, then the settings files, then
    the built-in fallback."""
    env_value = _env_int("CLAUDE_CONTEXT_WINDOW_TOKENS", 0)
    if env_value:
        return env_value
    return _lookup_setting("context_window_tokens", 1, None, DEFAULT_CONTEXT_WINDOW_TOKENS)


def _alert_min_percent() -> int:
    """Real-context percentage at or above which the shell hooks may emit their
    call-count, time and phase alerts (0 = always)."""
    return _lookup_setting("alert_min_context_percent", 0, 100, DEFAULT_ALERT_MIN_PERCENT)


def _publish_for_hooks(session_id: str, percentage: float) -> None:
    """Hand the real percentage and the alert gate to the Bash hooks as
    `pct-<hash>` ("<percent> <min-percent>") in their tracking directory.

    The hash must equal ctx-compact-track-and-suggest.sh's SESSION_HASH, which is
    the first 8 hex characters of md5 over the session id plus a trailing newline
    (`echo "$id" | md5sum`). Best-effort: a failure just leaves the gate closed."""
    import hashlib

    digest = hashlib.md5(f"{session_id or 'default'}\n".encode(), usedforsecurity=False)
    track_dir = Path.home() / ".claude" / "strategic-compact"
    target = track_dir / f"pct-{digest.hexdigest()[:8]}"
    try:
        track_dir.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        tmp.write_text(f"{round(percentage)} {_alert_min_percent()}", encoding="utf-8")
        tmp.replace(target)
    except OSError:
        pass


def _latest_usage_tokens(
    transcript_path: str, tails: tuple[int, ...] = USAGE_TAIL_BYTES
) -> int | None:
    """Total input-side tokens (input + cache read + cache creation) the API
    reported for the latest main-chain assistant turn, or None if the
    transcript has no such record within the given tail sizes (tried in order).
    Reads only the file's tail, newest first.

    Sidechain (subagent) records are skipped: their usage describes a separate,
    smaller context, not this session's."""
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as fh:
            for tail in tails:
                start = max(size - tail, 0)
                fh.seek(start)
                lines = fh.read().splitlines()
                if start > 0:
                    lines = lines[1:]  # first line is likely cut mid-record
                for raw in reversed(lines):
                    if b'"usage"' not in raw:
                        continue
                    try:
                        record = json.loads(raw)
                    except ValueError:
                        continue
                    if record.get("type") != "assistant" or record.get("isSidechain"):
                        continue
                    usage = (record.get("message") or {}).get("usage")
                    if not isinstance(usage, dict):
                        continue
                    total = sum(
                        v
                        for k in (
                            "input_tokens",
                            "cache_read_input_tokens",
                            "cache_creation_input_tokens",
                        )
                        if isinstance(v := usage.get(k), int) and not isinstance(v, bool)
                    )
                    if total > 0:
                        return total
                if start == 0:
                    break
    except OSError:
        return None
    return None


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
    own two-phase scheme (see ctx-compact-track-and-suggest.sh's comment for
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
    actually landed (see _maybe_reset_after_compaction's marker-unlink ordering)
    check this instead of assuming success.

    Writes to a temp file then os.replace()s it into place -- matching this
    plugin's own Bash hooks' `> "$FILE.tmp" && mv "$FILE.tmp" "$FILE"`
    convention -- so a crash/kill mid-write, or an AV scanner holding the
    file, can never leave a truncated cache for a later read to trip over."""
    cache_file = get_session_dir(session_id) / "context-monitor-cache.json"
    tmp_file = cache_file.with_suffix(cache_file.suffix + ".tmp")
    try:
        tmp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_file.replace(cache_file)
        return True
    except OSError:
        return False


def _maybe_reset_after_compaction(session_id: str = "") -> None:
    """If ctx-post-compact-restore.py signaled a compaction just completed (via a
    marker file in the shared session dir), reset every progressive-nudge flag
    and the fallback tool-call counter, so a threshold already shown
    pre-compaction can fire again as the new, post-compaction context climbs back
    through it.

    The usage-based estimate needs no baseline: the first assistant turn after a
    compaction already reports the smaller post-compaction usage.

    The marker is set at SessionStart(source=compact) time and consumed here, on
    the first PostToolUse call after it. It is deleted only after the reset is
    durably persisted via save_cache() -- if that write hits a transient OSError,
    the marker stays in place so this reset is retried on the next PostToolUse
    call instead of silently being lost (found by CodeRabbit's automated review,
    2026-09-11).
    """
    marker = get_session_dir(session_id) / "compact-baseline-reset-pending"
    if not marker.exists():
        return

    cache = read_cache(session_id)
    cache["shown_learn"] = []
    cache["shown_warn_80"] = False
    cache["shown_warn_90"] = False
    cache["tool_calls"] = 0
    cache.pop("last_usage_tokens", None)  # pre-compaction usage is stale now
    if save_cache(cache, session_id):
        try:
            marker.unlink()
        except OSError:
            pass


def estimate_context_percentage(hook_input: dict, session_id: str = "") -> tuple[float, bool]:
    """
    Estimate context usage as `(percentage 0-100, measured)` from the latest real
    token usage in the transcript (see _latest_usage_tokens) against the configured
    window (see _context_window_tokens). Fallback when the transcript has no
    usage record yet: a tool-call counter (CLAUDE_CONTEXT_MAX_TOOL_CALLS), which
    is very rough and returns `measured=False`.
    """
    _maybe_reset_after_compaction(session_id)

    transcript_path = hook_input.get("transcript_path", "")
    if transcript_path:
        # The small tail almost always holds the latest usage record. When a huge tool
        # result pushed it out, reuse the last value seen in this session instead of
        # re-reading the large tail on every call; only a session with no value yet
        # pays for the large scan. The reused value can lag by one assistant turn (the
        # call whose record a >512 KB result pushed out); the next call sees a fresh record.
        used = _latest_usage_tokens(transcript_path, USAGE_TAIL_BYTES[:1])
        cache = read_cache(session_id)
        cached = cache.get("last_usage_tokens")
        if used is None:
            if isinstance(cached, int) and not isinstance(cached, bool) and cached > 0:
                used = cached
            else:
                used = _latest_usage_tokens(transcript_path, USAGE_TAIL_BYTES[1:])
        if used is not None:
            if cached != used:
                cache["last_usage_tokens"] = used
                save_cache(cache, session_id)
            return min(used / _context_window_tokens() * 100, 100), True

    # Fallback: tool-call counter (very rough)
    cache = read_cache(session_id)
    tool_calls = cache.get("tool_calls", 0) + 1
    cache["tool_calls"] = tool_calls
    save_cache(cache, session_id)
    max_calls = _env_int("CLAUDE_CONTEXT_MAX_TOOL_CALLS", DEFAULT_MAX_TOOL_CALLS)
    return min((tool_calls / max_calls) * 100, 100), False


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
        percentage, measured = estimate_context_percentage(hook_input, session_id)

        # Persist the latest estimate so the status line can surface it (best-effort).
        try:
            (session_dir / "context-pct.txt").write_text(f"{percentage:.0f}", encoding="utf-8")
        except Exception:
            pass
        # The shell hooks gate their alerts on *real* context usage. A tool-call-count
        # estimate is not that, so publish 0 (a closed gate whenever the minimum is positive).
        _publish_for_hooks(session_id, percentage if measured else 0.0)

        # Check throttling
        if is_throttled(percentage, session_id):
            return 0

        shown = get_shown_thresholds(session_id)

        # Check the two urgency thresholds BEFORE the learn-threshold loop
        # below: if the very first unthrottled observation already lands
        # at 90%+ (e.g. resuming a session with an already-large
        # transcript, or one big tool call), the learn loop would
        # otherwise emit the 65% learn nudge on this tool call and only reach
        # the urgent 90% warning on the next one -- delaying the most
        # important warning exactly when auto-compaction is closest.

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

        # Check reusable-discovery thresholds (65%)
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
