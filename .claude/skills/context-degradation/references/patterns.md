# Context Degradation Patterns: Technical Reference

This document provides technical background on diagnosing and measuring context degradation, and points
at `scripts/degradation_detector.py` — the real, runnable implementation of the detection functions
described below. Where a section below has a working implementation, its usage snippet calls that
script's actual functions/classes directly rather than restating pseudocode with a different, drifted
signature.

## Attention Distribution Analysis

`degradation_detector.py`'s `measure_attention_distribution()` simulates the U-shaped attention curve
(beginning/end positions favored, middle positions degraded) documented in lost-in-middle research — it's
a simulation for demonstration, not a real model forward pass; see the script's own module docstring.
`detect_lost_in_middle()` then checks whether specific critical positions fall in the degraded region:

```python
from degradation_detector import measure_attention_distribution, detect_lost_in_middle

attention = measure_attention_distribution(context_tokens, query="quarterly revenue")
result = detect_lost_in_middle(critical_positions=[0, 1, 25, 48, 49], attention_distribution=attention)
# result: {"at_risk": [...], "safe": [...], "recommendations": [...], "degradation_score": 0.0-1.0}
```

Also available: `analyze_context_structure(context: str)`, which assesses structural degradation risk
(how much content sits in the low-attention middle third) from a context string's own section layout —
returns `total_lines`, `sections`, `middle_content_ratio`, and a `degradation_risk` level
(`low`/`medium`/`high`).

## Context Poisoning Detection

`degradation_detector.py`'s `PoisoningDetector` class checks for error accumulation, contradiction
patterns, and hallucination-marker phrases via pattern matching — a proxy heuristic, not a fine-tuned
classifier (see the script's own module docstring):

```python
from degradation_detector import PoisoningDetector

detector = PoisoningDetector()
report = detector.detect_poisoning(context_string)
# report: {"poisoning_risk": bool, "indicators": [...], "overall_risk": "low"|"medium"|"high"}
```

`extract_claims(text)` is also available on the same class, for building a claim-provenance list to
track separately from the aggregate poisoning check above.

## Distraction: Relevance Scoring

No implementation in `degradation_detector.py` — this is conceptual guidance only. The idea: score each
context element's relevance to the current task (e.g. via embedding similarity), sort descending, and
flag elements below a relevance threshold as candidate distractors to remove. Even a single distractor
document measurably degrades performance on relevant tasks (see the SKILL.md's Core Concepts) — the goal
of this scoring is to catch that case before it happens, not just after.

## Composite Health Scoring

`degradation_detector.py`'s `ContextHealthAnalyzer` combines attention distribution, poisoning detection,
and context-limit utilization into one composite score:

```python
from degradation_detector import ContextHealthAnalyzer

analyzer = ContextHealthAnalyzer(context_limit=100_000)
result = analyzer.analyze(context_string, critical_positions=[0, 1, 2, 3, 4])
# result: {"health_score": 0.0-1.0, "status": "healthy"|"warning"|"degraded"|"critical",
#          "metrics": {...}, "issues": {...}, "recommendations": [...]}
```

For a one-call convenience wrapper that also prints a summary, use `analyze_agent_context(context,
context_limit=80_000, critical_positions=None)` — see the script's own CLI demo (`if __name__ ==
"__main__"` block) for a full worked example against synthetic context.

### Alert Thresholds

Reference thresholds to configure monitoring against (not read from `degradation_detector.py` directly —
apply these to its `metrics`/`health_score` output):

```python
CONTEXT_ALERTS = {
    "utilization_warning": 0.7,      # 70% of context limit
    "utilization_critical": 0.9,     # 90% of context limit
    "attention_degraded_ratio": 0.3, # 30% in middle region
    "relevance_threshold": 0.3,      # Below 30% relevance
    "consecutive_warnings": 3        # Three warnings triggers alert
}
```

## Recovery Procedures

No implementation in `degradation_detector.py` — this is conceptual guidance only, for when a diagnosed
degradation (poisoning, confusion, clash) needs the context truncated rather than just flagged. Priority
order when truncating:

1. Preserve critical system elements (system prompt, tool definitions) always.
2. Preserve recent conversation turns — more of these than older ones.
3. Preserve critical retrieved documents/context the task still needs.
4. If still over budget, summarize the oldest preserved documents before truncating turns.
5. Only as a last resort, truncate the oldest conversation turns, keeping the most recent ones intact.

This mirrors `context-engineering`'s **Write**/**Compress** operations (see that skill) applied
specifically to a poisoning/clash recovery, rather than routine context management.
