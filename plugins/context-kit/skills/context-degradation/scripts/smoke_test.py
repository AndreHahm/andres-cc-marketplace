#!/usr/bin/env python3
"""Persisted smoke test for context-degradation: exercises degradation_detector.py's
real public API with real assertions on the attention/lost-in-middle/poisoning logic
this skill's own reference material documents."""

import pathlib
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import degradation_detector as dd  # noqa: E402


def check_beginning_and_end_are_favored():
    tokens = [f"tok{i}" for i in range(100)]
    dist = dd.measure_attention_distribution(tokens, "query")
    if dist[0]["region"] != "attention_favored":
        return False, "position 0 (beginning) not classified attention_favored"
    if dist[99]["region"] != "attention_favored":
        return False, "position 99 (last token) not attention_favored -- the >= 90th-pct fix"
    if dist[50]["region"] != "attention_degraded":
        return False, "position 50 (middle) not classified attention_degraded"
    return True, "beginning/end favored, middle degraded (100-token distribution)"


def check_lost_in_middle_flags_middle_positions():
    tokens = [f"tok{i}" for i in range(100)]
    dist = dd.measure_attention_distribution(tokens, "query")
    result = dd.detect_lost_in_middle([0, 50, 99], dist)
    if 50 not in result["at_risk"]:
        return False, "middle position 50 not flagged at_risk"
    if 0 not in result["safe"] or 99 not in result["safe"]:
        return False, "beginning/end positions not flagged safe"
    if not (0 < result["degradation_score"] < 1):
        return (
            False,
            f"degradation_score {result['degradation_score']} not in (0, 1) for a mixed set",
        )
    return True, "middle position correctly flagged at_risk, edges safe"


def check_negative_position_rejected_not_silently_safe():
    # Regression check for the documented bug class: a negative pos satisfies
    # `pos < len(...)` and would silently index from the end of the list if both
    # bounds weren't checked -- must be reported as invalid, never as "safe".
    tokens = [f"tok{i}" for i in range(20)]
    dist = dd.measure_attention_distribution(tokens, "query")
    result = dd.detect_lost_in_middle([-1, 500], dist)
    if result.get("invalid_positions") != [-1, 500]:
        return False, f"expected invalid_positions [-1, 500], got {result.get('invalid_positions')}"
    if result["at_risk"] or result["safe"]:
        return False, "out-of-range positions leaked into at_risk/safe instead of invalid_positions"
    return (
        True,
        "negative and overflow positions correctly rejected as invalid, not silently 'safe'",
    )


def check_poisoning_detects_known_indicators():
    detector = dd.PoisoningDetector()
    poisoned = (
        "The API returned an error. However, the system reportedly recovered. "
        "But the error persisted and the request failed. Unable to parse the "
        "response. Sources suggest the endpoint may have been deprecated."
    )
    result = detector.detect_poisoning(poisoned)
    if not result["poisoning_risk"]:
        return False, "known-poisoned text not flagged poisoning_risk=True"
    if result["overall_risk"] not in ("medium", "high"):
        return False, f"overall_risk {result['overall_risk']!r} unexpectedly low for poisoned text"
    return True, f"poisoned text correctly flagged (overall_risk={result['overall_risk']})"


def check_clean_text_not_flagged():
    detector = dd.PoisoningDetector()
    clean = "Revenue increased fifteen percent year over year across all regions."
    result = detector.detect_poisoning(clean)
    if result["poisoning_risk"]:
        return False, f"clean text incorrectly flagged poisoning_risk=True: {result['indicators']}"
    return True, "clean text correctly not flagged"


def check_health_analyzer_rejects_nonpositive_limit():
    try:
        dd.ContextHealthAnalyzer(context_limit=0)
    except ValueError:
        return True, "context_limit=0 correctly raises ValueError"
    return False, "context_limit=0 did not raise ValueError"


def check_health_analyzer_status_in_known_set():
    analyzer = dd.ContextHealthAnalyzer(context_limit=1000)
    result = analyzer.analyze("short clean context with no issues at all")
    if result["status"] not in ("healthy", "warning", "degraded", "critical"):
        return False, f"unexpected status value: {result['status']!r}"
    if not (0.0 <= result["health_score"] <= 1.0):
        return False, f"health_score {result['health_score']} out of [0, 1] range"
    return True, f"health analysis returns a known status ({result['status']}) and score in [0,1]"


CHECKS = [
    check_beginning_and_end_are_favored,
    check_lost_in_middle_flags_middle_positions,
    check_negative_position_rejected_not_silently_safe,
    check_poisoning_detects_known_indicators,
    check_clean_text_not_flagged,
    check_health_analyzer_rejects_nonpositive_limit,
    check_health_analyzer_status_in_known_set,
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
