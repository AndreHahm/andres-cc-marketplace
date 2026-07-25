#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
# PostToolUse hook (matcher: Agent|Skill|Bash): best-effort, log-only detection of a
# subset of plugin-rulebook R26 (Expensive-Action Opt-In) violations at
# runtime. R26 is otherwise a text-only rule checked by plugin-rulebook (does
# a SKILL.md *say* it asks before an expensive action) -- this hook cannot
# verify R26 compliance in general, only flag the small, explicit set of
# known expensive-action signatures below when they fire with no
# AskUserQuestion tool_use found anywhere earlier in the same transcript.
# R25 (Unplanned-Overhead Disclosure) is deliberately NOT attempted here --
# whether overhead was verbally disclosed in response text is a semantic
# judgment call this static, pattern-matching hook cannot approximate.
#
# LOG-ONLY: this hook never blocks (PostToolUse cannot block regardless of
# what this script does). It surfaces a systemMessage only. False positives
# are expected -- the "was there a prior AskUserQuestion" check is a
# whole-transcript text search, not a precise causal link to this specific
# dispatch, and the signature registry below is deliberately small and
# explicit. Extend EXPENSIVE_ACTIONS as new R26-gated steps ship; don't try
# to generalize this into a whole-plugin static analyzer.
#
# Matcher assumption verified against a real session transcript (not just
# claude --debug synthetic input): PostToolUse tool_name is literally "Agent"
# for Agent() dispatches, "Skill" for Skill() dispatches, and "Bash" for
# Bash() calls, and AskUserQuestion tool_use entries serialize as
# `"name":"AskUserQuestion"` -- confirmed via
# `grep -o '"name":"[A-Za-z_]*"' <session>.jsonl` against this plugin-devkit
# repo's own ~/.claude/projects/ transcript during this hook's own build (and
# re-confirmed for "Bash" when the test-agent-trigger.sh signature below was
# moved from an Agent dispatch to a direct scoped-Bash call).

import json
import re
import sys
from pathlib import Path

# Only tail this many bytes of transcript.jsonl -- a session-long transcript
# can grow into the tens of MB, and a full read_text() on every matching
# dispatch risks the hook's own 10s timeout on long sessions (exactly the
# sessions where an R26 gate matters most). AskUserQuestion calls relevant to
# the CURRENT dispatch are always recent, so a tail is sufficient.
TRANSCRIPT_TAIL_BYTES = 2_000_000

EXPENSIVE_ACTIONS = [
    {
        "tool_name": "Agent",
        "target_pattern": re.compile(r"human-doc-reviewer", re.IGNORECASE),
        "expensive_mode_pattern": re.compile(r"\bfull mode\b", re.IGNORECASE),
        "label": "human-doc-reviewer dispatched in full mode (R26 Document-step gate)",
    },
    {
        # test-agent-trigger.sh is called directly via a scoped Bash tool now
        # (plugin-lifecycle-upstream's bounded Phase-5 check and
        # plugin-lifecycle-downstream's exhaustive Deep Test battery both
        # dispatch it this way, not via an Agent), so there is no descriptive
        # prose in tool_input to pattern-match against -- just a shell
        # command line. The script's own auto-derive mode (no phrases-file
        # argument) only ever emits "+" (should-trigger) phrases; there is no
        # code path for it to produce "-" (should-not-trigger) cases. So an
        # explicit phrases-file 2nd positional argument is the only way to
        # get should-not-trigger coverage or a hand-curated exhaustive list --
        # its presence is what actually distinguishes Deep Test's full
        # battery from the bounded single-call auto-derive check, which never
        # passes one. This is a heuristic (see module docstring): it doesn't
        # parse the shell command, just checks token shape after the script
        # name and can be fooled by unusual quoting or argument order.
        "tool_name": "Bash",
        "target_pattern": re.compile(r"test-agent-trigger\.sh"),
        "expensive_mode_pattern": re.compile(
            r"test-agent-trigger\.sh\s+\S+\s+(?!--timeout\b)\S+"
        ),
        "label": (
            "test-agent-trigger.sh invoked with an explicit phrases-file argument "
            "-- full battery, not the bounded auto-derive check (R26 Deep Test gate)"
        ),
    },
    {
        "tool_name": "Skill",
        "target_pattern": re.compile(r"skill-tester", re.IGNORECASE),
        "expensive_mode_pattern": re.compile(r"full baseline-comparison benchmark", re.IGNORECASE),
        "label": "skill-tester full benchmark dispatched (R26 Deep Test gate)",
    },
]


def transcript_has_ask_user_question(transcript_path_str):
    if not transcript_path_str:
        return None  # unknown -- can't verify either way, don't flag

    # Reject path traversal and anything that isn't shaped like a transcript
    # file, per this plugin's own hook security checklist -- transcript_path
    # is event data from the hook's stdin, even though it's platform-set
    # rather than attacker-influenced tool_input text.
    path = Path(transcript_path_str)
    if ".." in path.parts or path.suffix != ".jsonl":
        return None

    try:
        if not path.is_file():
            return None
        size = path.stat().st_size
        with path.open("rb") as f:
            if size > TRANSCRIPT_TAIL_BYTES:
                f.seek(size - TRANSCRIPT_TAIL_BYTES)
            data = f.read()
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        return None
    return bool(re.search(r'"name"\s*:\s*"AskUserQuestion"', text))


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    serialized = json.dumps(tool_input, ensure_ascii=False)

    matched_label = None
    for action in EXPENSIVE_ACTIONS:
        if action["tool_name"] != tool_name:
            continue
        if action["target_pattern"].search(serialized) and action["expensive_mode_pattern"].search(serialized):
            matched_label = action["label"]
            break

    if matched_label is None:
        sys.exit(0)

    has_gate = transcript_has_ask_user_question(payload.get("transcript_path"))
    if has_gate is not False:
        # True (gate found) or None (couldn't verify) -- nothing to flag
        sys.exit(0)

    print(json.dumps({
        "systemMessage": (
            "r26-expensive-action-check (log-only, best-effort, does not block): "
            f"{matched_label} with no AskUserQuestion call found earlier in this "
            "transcript. May be a false positive -- this heuristic only pattern-matches "
            "tool_input text, it does not verify the gate actually preceded this "
            "specific dispatch. Verify manually whether the delta/full or opt-in "
            "choice was actually offered before this action ran."
        ),
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
