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


def check_analyze_context_structure_risk_bands():
    # Covers the recently-reworked degradation_risk banding and its
    # spillover-vs-local-header distinction -- previously untested
    # (completeness-reviewer finding, 2026-09-18).
    # A header exactly at the middle band's own start means no section that
    # starts before the band spills into it -- the low-risk case.
    low_context = "# Header A\n" + "contentA\n" * 5 + "# Header B\n" + "contentB\n" * 13
    low = dd.analyze_context_structure(low_context)
    if low["degradation_risk"] != "low":
        return (
            False,
            f"expected low risk for a local header, got {low['degradation_risk']!r} "
            f"(spillover={low['middle_spillover_ratio']})",
        )
    high = dd.analyze_context_structure("line\n" * 100)
    if high["degradation_risk"] not in ("medium", "high"):
        risk = high["degradation_risk"]
        return False, f"expected medium/high risk for an undifferentiated blob, got {risk!r}"
    if high["middle_spillover_ratio"] <= low["middle_spillover_ratio"]:
        return False, "spillover_ratio did not increase for the no-local-header blob case"
    return True, "risk banding and spillover computation both behave correctly on real inputs"


def check_extract_claims_and_analyze_agent_context():
    detector = dd.PoisoningDetector()
    claims = detector.extract_claims("Revenue increased. The API failed to respond.")
    if not claims or "text" not in claims[0] or "id" not in claims[0]:
        return False, f"extract_claims did not return the documented claim-dict shape: {claims}"
    result = dd.analyze_agent_context("short clean context", context_limit=1000)
    if "status" not in result or "health_score" not in result:
        return (
            False,
            f"analyze_agent_context did not return the documented health-analysis shape: {result}",
        )
    return True, "extract_claims and analyze_agent_context both return their documented shapes"


def check_patterns_snippets_match_real_signatures():
    # Backs quality gate 2 mechanically (completeness-reviewer finding,
    # 2026-09-18): patterns.md must never document a pseudocode API that
    # doesn't match the real script's signatures.
    #
    # inspect.signature(fn) alone only proves fn is introspectable -- it does
    # NOT validate that the documented call shape (argument names, count,
    # positional vs. keyword) actually matches the real signature (found by
    # CodeRabbit, 2026-09-18). Bind each documented example call's own
    # argument shape against the real signature via Signature.bind(), which
    # raises TypeError on a mismatched name/count/keyword -- this is what
    # actually proves the documented call would work.
    import inspect

    patterns_md = (SKILL_DIR / "references" / "patterns.md").read_text(encoding="utf-8")
    # Each entry's args/kwargs mirror patterns.md's own documented example
    # call exactly (see that file's "Core Concepts"/"Composite Health
    # Scoring" sections) -- dummy values only, never executed, just bound.
    documented_calls = {
        "measure_attention_distribution": ((["tok"],), {"query": "quarterly revenue"}),
        "detect_lost_in_middle": ((), {"critical_positions": [0, 1], "attention_distribution": []}),
        "classify_critical_positions": (([0, 1], 10), {}),
        "analyze_context_structure": (("context text",), {}),
        "analyze_agent_context": (
            ("context text",),
            {"context_limit": 80_000, "critical_positions": None},
        ),
    }
    missing = [name for name in documented_calls if name not in patterns_md]
    if missing:
        return False, f"patterns.md never documents these real functions: {missing}"
    for name, (args, kwargs) in documented_calls.items():
        fn = getattr(dd, name, None)
        if fn is None or not callable(fn):
            return (
                False,
                f"patterns.md documents {name!r} but it does not exist in degradation_detector.py",
            )
        try:
            inspect.signature(fn).bind(*args, **kwargs)
        except TypeError as exc:
            return (
                False,
                f"patterns.md's documented call shape for {name}(*{args}, **{kwargs}) "
                f"does not match the real signature: {exc}",
            )
    return (
        True,
        "every function patterns.md documents exists with a signature matching its "
        "documented call shape",
    )


CHECKS = [
    check_beginning_and_end_are_favored,
    check_lost_in_middle_flags_middle_positions,
    check_negative_position_rejected_not_silently_safe,
    check_poisoning_detects_known_indicators,
    check_clean_text_not_flagged,
    check_health_analyzer_rejects_nonpositive_limit,
    check_health_analyzer_status_in_known_set,
    check_analyze_context_structure_risk_bands,
    check_extract_claims_and_analyze_agent_context,
    check_patterns_snippets_match_real_signatures,
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
