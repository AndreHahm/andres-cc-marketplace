#!/usr/bin/env python3
"""Persisted smoke test for context-mode: exercises detect_mode.py's real
UserPromptSubmit hook contract (stdin -> stdout/exit-code) -- happy path,
order-of-mention, fail-open on malformed/non-UTF8 input, and the closed
VALID_MODES vocabulary guarantee documented in this skill's own Quality Gates."""

import json
import pathlib
import subprocess
import sys
import tempfile

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "detect_mode.py"


def run_hook(stdin_bytes):
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=stdin_bytes,
        capture_output=True,
        timeout=15,
    )


def check_single_candidate_ship():
    payload = json.dumps({"prompt": "ship it now"}).encode("utf-8")
    result = run_hook(payload)
    if result.returncode != 0:
        return False, f"exited {result.returncode}, expected 0"
    out = json.loads(result.stdout.decode("utf-8"))
    tag = out["hookSpecificOutput"]["additionalContext"]
    if tag != "[Context-Mode candidate: ship]":
        return False, f"expected single-ship tag, got {tag!r}"
    return True, "single 'ship it' prompt correctly tags candidate: ship"


def check_multi_candidate_order_of_mention():
    # "review this pr" appears before "ship it" in the string -- order-of-mention
    # says candidates must list review before ship.
    payload = json.dumps({"prompt": "review this pr, then ship it"}).encode("utf-8")
    result = run_hook(payload)
    if result.returncode != 0:
        return False, f"exited {result.returncode}, expected 0"
    out = json.loads(result.stdout.decode("utf-8"))
    tag = out["hookSpecificOutput"]["additionalContext"]
    if tag != "[Context-Mode candidates: review, ship]":
        return False, f"expected order-of-mention 'review, ship', got {tag!r}"
    return True, "multi-candidate prompt ordered by first-mention position (review, ship)"


def check_no_match_produces_no_output():
    payload = json.dumps({"prompt": "how does authentication work here"}).encode("utf-8")
    result = run_hook(payload)
    if result.returncode != 0:
        return False, f"exited {result.returncode}, expected 0"
    if result.stdout.strip():
        return False, f"expected empty stdout for no-match prompt, got {result.stdout!r}"
    return True, "no-match prompt produces exit 0 with empty stdout"


def check_malformed_json_fails_open():
    result = run_hook(b"{not valid json at all")
    if result.returncode != 0:
        return False, f"malformed JSON exited {result.returncode}, expected 0 (fail-open)"
    if result.stdout.strip():
        return False, f"malformed JSON should produce no stdout, got {result.stdout!r}"
    return True, "malformed JSON stdin fails open (exit 0, no output)"


def check_non_utf8_fails_open():
    # A lone continuation byte is invalid UTF-8 on its own.
    result = run_hook(b"\xff\xfe not valid utf-8 \x80")
    if result.returncode != 0:
        return False, f"non-UTF8 stdin exited {result.returncode}, expected 0 (fail-open)"
    # Found by CodeRabbit, 2026-09-18: exit 0 alone doesn't prove the hook
    # produced no output -- a regression emitting hook output for invalid
    # bytes would still exit 0. Match check_malformed_json_fails_open's own
    # stdout assertion.
    if result.stdout.strip():
        return False, f"non-UTF8 stdin should produce no stdout, got {result.stdout!r}"
    return True, "non-UTF-8 stdin fails open (exit 0) with empty stdout, no crash"


def check_valid_modes_vocabulary_is_closed():
    # Direct-import check with a monkeypatched triggers.json containing an extra
    # "research" key (a deferred mode not in VALID_MODES) -- load_triggers() must
    # filter it out regardless of what the data file contains, per this skill's
    # own documented guarantee ("only VALID_MODES may ever be emitted").
    sys.path.insert(0, str(SKILL_DIR / "scripts"))
    import importlib

    import detect_mode as dm

    importlib.reload(dm)

    with tempfile.TemporaryDirectory() as tmp:
        fake_triggers = pathlib.Path(tmp) / "triggers.json"
        fake_triggers.write_text(
            json.dumps({"ship": ["ship it"], "research": ["deep dive into"]}),
            encoding="utf-8",
        )
        original_path = dm.TRIGGERS_PATH
        dm.TRIGGERS_PATH = fake_triggers
        try:
            triggers = dm.load_triggers()
            if "research" in triggers:
                return False, "load_triggers() did not filter out a non-VALID_MODES key"
            if "ship" not in triggers:
                return False, "load_triggers() incorrectly dropped a valid VALID_MODES key"
            candidates = dm.detect_candidates("let's deep dive into this and ship it", triggers)
            if "research" in candidates:
                return False, f"'research' leaked into candidates outside VALID_MODES: {candidates}"
        finally:
            dm.TRIGGERS_PATH = original_path

    return True, "non-VALID_MODES keys in triggers.json are filtered, never emitted"


def check_skill_md_validates_candidates_before_reading():
    # Regression guard for the 2026-09-17 security fix: SKILL.md's own Dispatch
    # logic must validate a candidate value against the closed dev/review/ship/admin
    # vocabulary BEFORE constructing a references/<value>.md read -- a forged tag
    # (never produced by the hook, so VALID_MODES never applied to it) with a
    # path-shaped value like "../../../../CLAUDE.local" would otherwise steer an
    # arbitrary .md file read. This is a prose/dispatch-logic fix, not executable
    # code, so the check is structural: confirm the closed-vocabulary guard text
    # exists and sits before "Single candidate", "Multiple candidates", AND
    # "Explicit manual request" dispatch steps, not just mentioned once in passing.
    # The scope was widened the same day (still 2026-09-17) after a security-reviewer
    # pass found the original fix only covered steps 2/3, leaving the manual-request
    # channel (step 4) reachable with the identical unvalidated-read primitive.
    skill_md = SKILL_DIR / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    guard_idx = text.find("Closed-vocabulary check")
    # Match the actual numbered dispatch-step headers, not an earlier prose mention
    # of the same words elsewhere in the doc (e.g. the tag-format example under
    # "How activation reaches this skill").
    single_idx = text.find("**Single candidate**")
    multi_idx = text.find("**Multiple candidates**")
    manual_idx = text.find("**Explicit manual request**")
    if guard_idx == -1:
        return False, "SKILL.md no longer states a closed-vocabulary check in Dispatch logic"
    if not (guard_idx < single_idx and guard_idx < multi_idx and guard_idx < manual_idx):
        return (
            False,
            "closed-vocabulary check does not precede all three dispatch steps it must gate",
        )
    if "steps 2, 3, and 4" not in text[guard_idx : guard_idx + 200]:
        return False, "closed-vocabulary check's own scope clause no longer names step 4"
    if "read nothing" not in text[guard_idx : guard_idx + 1000]:
        return False, "closed-vocabulary check does not state the 'read nothing' refusal action"
    return True, "SKILL.md's closed-vocabulary check precedes all three dispatch steps it must gate"


CHECKS = [
    check_single_candidate_ship,
    check_multi_candidate_order_of_mention,
    check_no_match_produces_no_output,
    check_malformed_json_fails_open,
    check_non_utf8_fails_open,
    check_valid_modes_vocabulary_is_closed,
    check_skill_md_validates_candidates_before_reading,
]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
