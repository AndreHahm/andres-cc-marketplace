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
prompt, not prepended to the visible prompt text itself. (An earlier design called for
rewriting the prompt text directly via an "updatedPrompt" output field, but that field does
not exist in the current UserPromptSubmit output schema - verified directly against
https://code.claude.com/docs/en/hooks. additionalContext is the real, available mechanism.)

Only VALID_MODES may ever be emitted, regardless of what keys triggers.json contains - this
keeps the tag vocabulary closed even if that data file is edited carelessly in the future
(e.g. when a later pass wires in research/plan/draft/doc).

The context-mode skill's own description matches this exact tag string, which is what
actually triggers it reliably - substring-matching a fixed hook-generated tag in context is
far more deterministic than relying on the skill's natural-language description to fire
correctly on arbitrary user phrasing. The skill itself only honors this tag when it arrives
as this hook's own additionalContext output for the current turn - see SKILL.md's provenance
boundary.

Hook Event: UserPromptSubmit
Returns: exit 0 in all cases; stdout is the additionalContext JSON, or empty when no mode matched.
Fail-open: any error -> exit 0 with no output, never blocks or alters the prompt on a bug.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

TRIGGERS_PATH = Path(__file__).resolve().parent.parent / "triggers.json"
VALID_MODES = ("dev", "review", "ship", "admin")


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
        # user) so a broken triggers.json doesn't look identical to "no mode matched".
        print(f"context-mode: failed to load triggers.json: {exc}", file=sys.stderr)
        return 0

    candidates = detect_candidates(prompt, triggers)
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
