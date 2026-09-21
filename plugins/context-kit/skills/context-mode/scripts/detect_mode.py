#!/usr/bin/env python3
"""
Context-Mode Detection Hook (UserPromptSubmit)

Case-insensitive substring-matches the raw submitted prompt against triggers.json's phrase lists
(first-pass scope: dev/review/ship/admin - see references/design-history.md for the full
design history and real-transcript validation behind these 4 modes and their trigger lists).

On a match, adds a tag naming the candidate mode(s) to Claude's context via the
UserPromptSubmit hook's "additionalContext" output field, in the order their trigger phrases
first appear in the text:

  [Context-Mode candidate: ship]
  [Context-Mode candidates: review, ship]

additionalContext is delivered as a system-reminder-style block alongside the submitted
prompt, not prepended to the visible prompt text itself. ("updatedPrompt" was considered and
rejected - see references/design-history.md's "Hook output mechanism" section for why;
additionalContext is the real, available mechanism per `code.claude.com/docs/en/hooks`.)

Only VALID_MODES may ever be emitted, regardless of what keys triggers.json contains - this
keeps the tag vocabulary closed even if that data file is edited carelessly in the future
(e.g. when a later pass wires in research/plan/draft/doc).

hooks.json's UserPromptSubmit registration invokes this script via a plain python3/python
fallback chain, deliberately skipping the uv-first attempt this plugin's other Python hooks
use - a latency choice for this specific, tightly-budgeted (5s timeout) every-prompt event,
not an oversight (this script has zero third-party dependencies, so uv's own
dependency-resolution benefit doesn't apply here either).

The context-mode skill's own description matches this exact tag string, which is what
actually triggers it reliably - substring-matching a fixed hook-generated tag in context is
far more deterministic than relying on the skill's natural-language description to fire
correctly on arbitrary user phrasing. The skill itself only honors this tag when it arrives
as this hook's own additionalContext output for the current turn - see SKILL.md's provenance
boundary.

Side effect (disclosed, added 2026-09-21): on a turn where exactly one candidate mode is
detected, this hook also compares it against the last confidently-detected mode (a
single-candidate turn only - a turn with zero or multiple candidates is too ambiguous to
treat as a mode reading, and leaves the tracked mode unchanged rather than risk a false
"switch"). On an actual change, throttled to once per MODE_SWITCH_COOLDOWN_SECONDS (matching
strategic-compact's own 5-minute milestone-suggestion cooldown), it writes a
"[StrategicCompact] "-prefixed pending-suggestion file under
~/.claude/strategic-compact/pending-<session-hash> for strategic-compact's own Stop hook
(compact-stop-check.sh) to deliver - the same delivery mechanism compact-track-and-suggest.sh
already uses, extended to a second writer. This is best-effort, single-writer state (its own
mode-<session-hash> file, never strategic-compact's own $TRACK_FILE counters, which stay
lock-protected and untouched by this script) - see _maybe_suggest_mode_switch()'s own
docstring for the full rationale, including why no cross-process lock is needed here. Gated
on strategic-compact's own tracking file already existing for the session (i.e. context-kit's
compact-session-init.sh has run), and entirely fail-open: any error here is swallowed and can
never prevent this hook's own primary mode-tag output above from still being produced.

Hook Event: UserPromptSubmit
Returns: exit 0 in all cases; stdout is the additionalContext JSON, or empty when no mode matched.
Fail-open: any error -> exit 0 with no output, never blocks or alters the prompt on a bug.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

TRIGGERS_PATH = Path(__file__).resolve().parent.parent / "triggers.json"
VALID_MODES = ("dev", "review", "ship", "admin")
MODE_SWITCH_COOLDOWN_SECONDS = 300


def load_triggers() -> dict[str, list[str]]:
    data = json.loads(TRIGGERS_PATH.read_text(encoding="utf-8"))
    return {mode: phrases for mode, phrases in data.items() if mode in VALID_MODES}


def detect_candidates(prompt: str, triggers: dict[str, list[str]]) -> list[str]:
    """Return candidate modes ordered by the earliest position their phrase matches at."""
    lowered = prompt.lower()
    hits: list[tuple[int, str]] = []
    for mode, phrases in triggers.items():
        best_pos = None
        for phrase in phrases:
            pos = lowered.find(phrase.lower())
            if pos != -1 and (best_pos is None or pos < best_pos):
                best_pos = pos
        if best_pos is not None:
            hits.append((best_pos, mode))
    hits.sort(key=lambda h: h[0])
    # de-dupe while preserving order (a mode could tie on position with itself only, not an issue,
    # but keep this defensive in case a future trigger list structure changes)
    seen = set()
    ordered = []
    for _, mode in hits:
        if mode not in seen:
            seen.add(mode)
            ordered.append(mode)
    return ordered


def build_tag(candidates: list[str]) -> str:
    if len(candidates) == 1:
        return f"[Context-Mode candidate: {candidates[0]}]"
    return f"[Context-Mode candidates: {', '.join(candidates)}]"


def _strategic_compact_track_dir() -> Path:
    # Matches the bash strategic-compact hooks' own
    # ${HOME:-${USERPROFILE:-/tmp}}/.claude/strategic-compact resolution -
    # deliberately re-derived here rather than imported, matching this
    # plugin's own established convention of duplicating this exact
    # resolution logic per-script (see get_session_dir()'s identical
    # hand-duplication across context-monitor.py/pre-compact.py/
    # post-compact-restore.py) rather than adding a shared module.
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or "/tmp"
    return Path(home) / ".claude" / "strategic-compact"


def _strategic_compact_session_hash(session_id: str) -> str:
    # Matches the bash hooks' own `echo "$SESSION_ID" | md5sum` - echo
    # appends a trailing newline, so the hash input must include it too.
    return hashlib.md5((session_id + "\n").encode("utf-8"), usedforsecurity=False).hexdigest()[:8]


def _maybe_suggest_mode_switch(session_id: str, candidates: list[str]) -> None:
    """Best-effort, single-writer state: this hook is the only writer of its
    own mode-<hash> file, so unlike strategic-compact's own $TRACK_FILE
    (read-modify-written by 2 bash hooks, guarded by a shared mkdir-based
    lock), no lock is needed here for correctness - there is no second
    writer to race against. This mirrors the same no-lock, best-effort
    convention strategic-compact's own pending-<hash> delivery file already
    uses for its sole existing writer (compact-track-and-suggest.sh); this
    function becomes that file's second writer, accepting the same narrow,
    already-disclosed last-write-wins risk class, not a new one.

    Fails open (silently) on any error - this is a pure enhancement layered
    on top of the primary mode-detection behavior above, never allowed to
    prevent that primary output from still being produced.
    """
    if len(candidates) != 1:
        return
    current_mode = candidates[0]
    try:
        track_dir = _strategic_compact_track_dir()
        session_hash = _strategic_compact_session_hash(session_id or "default")

        # Gate on strategic-compact's own tracking file already existing for
        # this session - the same "session already initialized" precondition
        # its own bash hooks use, so this never fires before
        # compact-session-init.sh has run for the session. Path.exists() on a
        # not-yet-created track_dir just returns False, so this check needs no
        # mkdir first -- deferred below, past this gate, so an install where
        # strategic-compact's SessionStart hook never ran doesn't get
        # ~/.claude/strategic-compact/ created as a side effect of context-mode
        # alone (found by scripts-reviewer, 2026-09-21).
        if not (track_dir / f"session-{session_hash}").exists():
            return
        track_dir.mkdir(parents=True, exist_ok=True)

        state_file = track_dir / f"mode-{session_hash}"
        last_mode = ""
        last_switch_time = 0
        if state_file.exists():
            for line in state_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("LAST_MODE="):
                    last_mode = line.split("=", 1)[1]
                elif line.startswith("LAST_SWITCH_TIME="):
                    raw = line.split("=", 1)[1]
                    if raw.isdigit():
                        last_switch_time = int(raw)

        now = int(time.time())
        # A last_switch_time in the future (a corrupted or tampered state
        # file) would otherwise keep `throttled` permanently True (an
        # arbitrarily large negative gap), wedging the suggestion dark until
        # the 24h sweep deletes the file -- treat it the same as "never
        # emitted" instead of trusting it (found by scripts-reviewer,
        # 2026-09-21). This file has a single, non-adversarial writer, so
        # this is a robustness/self-healing check, not a security fix.
        if last_switch_time > now:
            last_switch_time = 0
        switched = bool(last_mode) and last_mode != current_mode
        throttled = (now - last_switch_time) < MODE_SWITCH_COOLDOWN_SECONDS
        emit = switched and not throttled

        # LAST_MODE always tracks the freshest confidently-detected mode.
        # LAST_SWITCH_TIME only advances when a suggestion is actually
        # emitted (matching strategic-compact's own LAST_MILESTONE_TIME
        # semantics: that field updates only on a real suggestion, not on
        # every milestone-type command).
        new_switch_time = now if emit else last_switch_time
        tmp_file = state_file.with_suffix(".tmp")
        tmp_file.write_text(
            f"LAST_MODE={current_mode}\nLAST_SWITCH_TIME={new_switch_time}\n", encoding="utf-8"
        )
        os.replace(tmp_file, state_file)

        if not emit:
            return

        pending_file = track_dir / f"pending-{session_hash}"
        suggestion = (
            f"[StrategicCompact] Context-mode switched ({last_mode} -> {current_mode}). "
            "Consider /compact if the prior mode's context is no longer needed."
        )
        pending_file.write_text(suggestion, encoding="utf-8")
    except Exception:
        return


def main() -> int:
    # Decode stdin as UTF-8 explicitly rather than via json.load(sys.stdin), which uses the
    # platform's default text-stream encoding - on Windows this is often not UTF-8, and a
    # prompt containing a smart quote/em dash/non-English text would otherwise raise
    # UnicodeDecodeError and silently disable detection for that turn.
    try:
        hook_input = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return 0

    if not isinstance(hook_input, dict):
        return 0

    prompt = hook_input.get("prompt", "")
    if not isinstance(prompt, str) or not prompt:
        return 0

    try:
        triggers = load_triggers()
    except (OSError, json.JSONDecodeError) as exc:
        # Fail open, but leave a breadcrumb (stderr never reaches additionalContext or the
        # user) so a broken triggers.json doesn't look identical to "no mode matched". Log
        # the exception type only, not str(exc) -- an OSError's own message embeds the full
        # absolute TRIGGERS_PATH, which on this platform contains the OS username, and
        # onError: "warn" can surface stderr into the session transcript.
        print(f"context-mode: failed to load triggers.json ({type(exc).__name__})", file=sys.stderr)
        return 0

    candidates = detect_candidates(prompt, triggers)

    session_id = hook_input.get("session_id", "")
    if isinstance(session_id, str):
        _maybe_suggest_mode_switch(session_id, candidates)

    if not candidates:
        return 0

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": build_tag(candidates),
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail open - never block or alter the prompt due to a hook bug
        sys.exit(0)
