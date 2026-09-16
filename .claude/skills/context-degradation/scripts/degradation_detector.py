"""
Context Degradation Detection — Public API
============================================

Detect, measure, and diagnose context degradation patterns in LLM agent systems.

Public API:
    measure_attention_distribution  — Map attention weight across context positions.
    detect_lost_in_middle           — Flag critical information in degraded-attention regions.
    analyze_context_structure       — Assess structural degradation risk factors.
    PoisoningDetector               — Detect context poisoning indicators (error accumulation,
                                      contradictions, hallucination markers).
    ContextHealthAnalyzer           — Run composite health analysis combining attention,
                                      poisoning, and utilization metrics.
    analyze_agent_context           — One-call convenience function for agent sessions.

PRODUCTION NOTES:
- The attention estimation functions simulate U-shaped attention curves for demonstration
  purposes. Production systems should extract actual attention weights from model internals
  when available (e.g., via TransformerLens or model-specific APIs).
- Token estimation uses simplified heuristics (~1 token per whitespace-split word).
  Production systems should use model-specific tokenizers for accurate counts.
- Poisoning and hallucination detection uses pattern matching as a proxy. Production
  systems may benefit from fine-tuned classifiers or model-based detection.
"""

import random
import re
from collections.abc import Sequence
from typing import Any

__all__ = [
    "measure_attention_distribution",
    "detect_lost_in_middle",
    "analyze_context_structure",
    "PoisoningDetector",
    "ContextHealthAnalyzer",
    "analyze_agent_context",
]


# ---------------------------------------------------------------------------
# Attention Distribution Analysis
# ---------------------------------------------------------------------------


def measure_attention_distribution(
    context_tokens: Sequence[str],
    query: str,
) -> list[dict[str, Any]]:
    """Map simulated attention weight to each context position.

    Use when: diagnosing whether critical information sits in the
    low-attention middle region of a long context.

    Args:
        context_tokens: Whitespace-split tokens (or chunks) of the context.
        query: The query or task description the context is meant to support.

    Returns:
        List of dicts, one per position, each containing:
            position (int), attention (float), region (str), tokens (str | None).
    """
    n = len(context_tokens)
    attention_by_position: list[dict[str, Any]] = []

    for position in range(n):
        is_beginning = position < n * 0.1
        is_end = position > n * 0.9

        attention = _estimate_attention(position, n, is_beginning, is_end)

        attention_by_position.append(
            {
                "position": position,
                "attention": attention,
                "region": "attention_favored" if (is_beginning or is_end) else "attention_degraded",
                "tokens": context_tokens[position][:50]
                if position < 5 or position > n - 5
                else None,
            }
        )

    return attention_by_position


def _estimate_attention(
    position: int,
    total: int,
    is_beginning: bool,
    is_end: bool,
) -> float:
    """Estimate attention weight for a single position.

    Simulates the U-shaped attention curve documented in lost-in-middle research:
    - Beginning tokens receive high attention (primacy / attention-sink effect).
    - End tokens receive high attention (recency effect).
    - Middle tokens receive degraded attention.

    IMPORTANT: This is a simulation for demonstration. Production systems should
    extract actual attention weights from model forward passes or use
    interpretability libraries (e.g., TransformerLens).
    """
    if is_beginning:
        return 0.8 + random.random() * 0.2
    elif is_end:
        return 0.7 + random.random() * 0.3
    else:
        middle_progress = (position - total * 0.1) / (total * 0.8)
        base_attention = 0.3 * (1 - middle_progress) + 0.1 * middle_progress
        return base_attention + random.random() * 0.1


# ---------------------------------------------------------------------------
# Lost-in-Middle Detection
# ---------------------------------------------------------------------------


def detect_lost_in_middle(
    critical_positions: list[int],
    attention_distribution: list[dict[str, Any]],
) -> dict[str, Any]:
    """Check if critical information sits in attention-degraded positions.

    Use when: context has been assembled and you need to verify that
    high-priority content is not buried in the low-attention middle zone.

    Args:
        critical_positions: Indices into the context that hold critical info.
        attention_distribution: Output of ``measure_attention_distribution``.

    Returns:
        Dict with keys: at_risk (list[int]), safe (list[int]),
        recommendations (list[str]), degradation_score (float 0-1),
        invalid_positions (list[int], only present if any were out of range).
    """
    results: dict[str, Any] = {
        "at_risk": [],
        "safe": [],
        "recommendations": [],
        "degradation_score": 0.0,
    }

    at_risk_count = 0
    valid_count = 0
    invalid_positions: list[int] = []

    for pos in critical_positions:
        # A negative pos satisfies `pos < len(...)` and would silently index
        # from the end of the list (a different, wrong position) rather than
        # being rejected -- both bounds must be checked explicitly.
        if 0 <= pos < len(attention_distribution):
            valid_count += 1
            region = attention_distribution[pos]["region"]
            if region == "attention_degraded":
                results["at_risk"].append(pos)
                at_risk_count += 1
            else:
                results["safe"].append(pos)
        else:
            invalid_positions.append(pos)

    if invalid_positions:
        results["invalid_positions"] = invalid_positions

    if valid_count > 0:
        results["degradation_score"] = at_risk_count / valid_count

    if results["at_risk"]:
        results["recommendations"].extend(
            [
                "Move critical information to attention-favored positions",
                "Use explicit markers to highlight critical information",
                "Consider splitting context to reduce middle section",
                f"{at_risk_count}/{valid_count} critical items are in degraded region",
            ]
        )

    if invalid_positions:
        results["recommendations"].append(
            f"{len(invalid_positions)} critical position(s) out of range and excluded: "
            f"{invalid_positions}"
        )

    return results


# ---------------------------------------------------------------------------
# Context Structure Analysis
# ---------------------------------------------------------------------------


def analyze_context_structure(context: str) -> dict[str, Any]:
    """Assess structural degradation risk factors in a context string.

    Use when: evaluating whether a context layout puts too much content
    in the low-attention middle zone before sending it to a model.

    Args:
        context: The full context string to analyze.

    Returns:
        Dict with total_lines, sections list, middle_content_ratio (fraction of
        all lines that fall in the middle band -- close to constant, ~30%-70% of
        any document by construction, since sections always tile the full input;
        kept for reference, not the risk signal), middle_spillover_ratio
        (fraction of the middle band's own content coming from a section that
        *starts* outside the band -- an undifferentiated blob spanning through
        the middle, vs. content organized with headers local to it; this is
        what degradation_risk is actually based on), and degradation_risk level
        (low / medium / high).
    """
    lines = context.split("\n")
    sections: list[dict[str, Any]] = []

    current_section: dict[str, Any] = {"start": 0, "type": "unknown", "length": 0}

    for i, line in enumerate(lines):
        if line.startswith("#"):
            if current_section["length"] > 0:
                sections.append(current_section)
            current_section = {
                "start": i,
                "type": "header",
                "length": 1,
                "header": line.lstrip("#").strip(),
            }
        else:
            current_section["length"] += 1

    sections.append(current_section)

    n = len(lines)
    middle_start = int(n * 0.3)
    middle_end = int(n * 0.7)
    band_width = middle_end - middle_start + 1

    def band_overlap(section: dict[str, Any]) -> int:
        # Overlap between the section's [start, start+length) span and the
        # middle band, not just whether the section *starts* in the band -- a
        # section that starts before the band and runs through it (including
        # the common single-section, no-headers case) still occupies it.
        return max(
            0,
            min(section["start"] + section["length"], middle_end + 1)
            - max(section["start"], middle_start),
        )

    # middle_content_ratio is a near-constant ~30%-70% of any document by
    # construction (sections always exactly tile the full input, so this is
    # really just "band width / n"), kept only for reference/debugging.
    middle_content = sum(band_overlap(s) for s in sections)
    middle_ratio = middle_content / n if n > 0 else 0

    # middle_spillover_ratio is the actual signal: how much of the band is an
    # undifferentiated blob spilling in from a section that started before it,
    # vs. content that's cleanly organized with a header local to the band.
    spillover_content = sum(band_overlap(s) for s in sections if s["start"] < middle_start)
    spillover_ratio = spillover_content / band_width if band_width > 0 else 0

    return {
        "total_lines": n,
        "sections": sections,
        "middle_content_ratio": middle_ratio,
        "middle_spillover_ratio": spillover_ratio,
        "degradation_risk": (
            "high" if spillover_ratio > 0.7 else "medium" if spillover_ratio > 0.3 else "low"
        ),
    }


# ---------------------------------------------------------------------------
# Context Poisoning Detection
# ---------------------------------------------------------------------------


class PoisoningDetector:
    """Detect context poisoning indicators via pattern matching.

    Use when: context quality is suspect — outputs degrade on previously
    successful tasks, tool calls misalign, or hallucinations persist
    despite corrections.
    """

    def __init__(self) -> None:
        self.claims: list[dict[str, Any]] = []
        self.error_patterns: list[str] = [
            r"error",
            r"failed",
            r"exception",
            r"cannot",
            r"unable",
            r"invalid",
            r"not found",
        ]

    def extract_claims(self, text: str) -> list[dict[str, Any]]:
        """Extract claims from text for verification tracking.

        Use when: building a provenance chain to trace which claims
        entered context and whether they have been verified.

        Args:
            text: Raw text to extract claims from.

        Returns:
            List of claim dicts with id, text, verified status, and
            error indicator flag.
        """
        sentences = text.split(".")
        claims: list[dict[str, Any]] = []

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue

            claims.append(
                {
                    "id": i,
                    "text": sentence,
                    "verified": None,
                    "has_error_indicator": any(
                        re.search(pattern, sentence, re.IGNORECASE)
                        for pattern in self.error_patterns
                    ),
                }
            )

        self.claims.extend(claims)
        return claims

    def detect_poisoning(self, context: str) -> dict[str, Any]:
        """Detect potential context poisoning indicators.

        Use when: agent output quality has degraded and context
        contamination is suspected. Checks for error accumulation,
        contradictions, and hallucination markers.

        Args:
            context: The full context string to analyze.

        Returns:
            Dict with poisoning_risk (bool), indicators (list),
            and overall_risk level (low / medium / high).
        """
        indicators: list[dict[str, Any]] = []

        # Check for error accumulation -- count total occurrences per pattern,
        # not just how many distinct patterns matched at least once, or a
        # single repeated error (the normal form of accumulation) can never
        # cross the threshold below no matter how many times it recurs.
        error_count = sum(
            len(re.findall(pattern, context, re.IGNORECASE)) for pattern in self.error_patterns
        )

        if error_count > 3:
            indicators.append(
                {
                    "type": "error_accumulation",
                    "count": error_count,
                    "severity": "high" if error_count > 5 else "medium",
                    "message": f"Found {error_count} error indicators in context",
                }
            )

        # Check for contradiction patterns
        contradictions = self._detect_contradictions(context)
        if contradictions:
            indicators.append(
                {
                    "type": "contradictions",
                    "count": len(contradictions),
                    "examples": contradictions[:3],
                    "severity": "high",
                    "message": f"Found {len(contradictions)} potential contradictions",
                }
            )

        # Check for hallucination markers
        hallucination_markers = self._detect_hallucination_markers(context)
        if hallucination_markers:
            indicators.append(
                {
                    "type": "hallucination_markers",
                    "count": len(hallucination_markers),
                    "severity": "medium",
                    "message": (
                        f"Found {len(hallucination_markers)} phrases associated with "
                        "uncertain claims"
                    ),
                }
            )

        return {
            "poisoning_risk": len(indicators) > 0,
            "indicators": indicators,
            "overall_risk": (
                "high" if len(indicators) > 2 else "medium" if len(indicators) > 0 else "low"
            ),
        }

    # Common words that establish no "same topic" overlap on their own --
    # excluded from _detect_contradictions' topic-word comparison.
    _CONTRADICTION_STOPWORDS = frozenset(
        {
            "however",
            "although",
            "despite",
            "nevertheless",
            "instead",
            "other",
            "hand",
            "that",
            "this",
            "with",
            "from",
            "have",
            "does",
            "changes",
            "behavior",
            "preserves",
            "compatibility",
        }
    )

    def _detect_contradictions(self, text: str) -> list[str]:
        """Detect potential contradictions in text."""
        contradictions: list[str] = []

        conflict_patterns = [
            (r"however", r"but"),
            (r"on the other hand", r"instead"),
            (r"although", r"yet"),
            (r"despite", r"nevertheless"),
        ]

        sentences = [s.strip() for s in text.split(".") if s.strip()]

        def topic_words(sentence: str) -> set[str]:
            return {
                w
                for w in re.findall(r"[a-zA-Z]{4,}", sentence.lower())
                if w not in self._CONTRADICTION_STOPWORDS
            }

        for pattern1, pattern2 in conflict_patterns:
            idx_with_1 = [
                i for i, s in enumerate(sentences) if re.search(pattern1, s, re.IGNORECASE)
            ]
            idx_with_2 = [
                i for i, s in enumerate(sentences) if re.search(pattern2, s, re.IGNORECASE)
            ]
            for i1 in idx_with_1:
                for i2 in idx_with_2:
                    # A single sentence containing both connectors (e.g. "X
                    # describes alternatives; however, it preserves Y, but
                    # changes nothing") is ordinary explanatory prose, not a
                    # contradiction -- only cross-sentence pairs that share an
                    # overlapping topic word count as a candidate conflict.
                    if i1 == i2:
                        continue
                    s1, s2 = sentences[i1], sentences[i2]
                    if topic_words(s1) & topic_words(s2):
                        for sentence in (s1, s2):
                            if len(sentence) < 200 and sentence not in contradictions:
                                contradictions.append(sentence[:100])

        return contradictions[:5]

    def _detect_hallucination_markers(self, text: str) -> list[str]:
        """Detect phrases associated with uncertain or hallucinated claims."""
        markers = [
            "may have been",
            "might have",
            "could potentially",
            "possibly",
            "apparently",
            "reportedly",
            "it is said that",
            "sources suggest",
            "believed to be",
            "thought to be",
        ]

        return [marker for marker in markers if marker in text.lower()]


# ---------------------------------------------------------------------------
# Context Health Analyzer
# ---------------------------------------------------------------------------


class ContextHealthAnalyzer:
    """Run composite health analysis on a context string.

    Use when: performing routine health checks on agent context during
    long-running sessions, or when setting up automated monitoring that
    triggers compaction or isolation before degradation hits.

    Combines attention distribution, poisoning detection, and utilization
    metrics into a single 0-1 health score with status interpretation.
    """

    def __init__(self, context_limit: int = 100_000) -> None:
        if context_limit <= 0:
            raise ValueError(f"context_limit must be a positive integer, got {context_limit}")
        self.context_limit: int = context_limit
        self.metrics_history: list[dict[str, Any]] = []

    def analyze(
        self,
        context: str,
        critical_positions: list[int] | None = None,
    ) -> dict[str, Any]:
        """Perform comprehensive context health analysis.

        Use when: a single health-check call is needed that covers
        attention, poisoning, and utilization in one pass.

        Args:
            context: The full context string to analyze.
            critical_positions: Indices of tokens holding critical info.
                Defaults to the first 10 positions if not provided.

        Returns:
            Dict with health_score (float 0-1), status (str),
            metrics (dict), issues (dict), and recommendations (list[str]).
        """
        tokens = context.split()

        token_count = len(tokens)
        utilization = token_count / self.context_limit

        # Analyze the full token sequence -- critical_positions indexes into the
        # untruncated `tokens` list, so sampling a prefix here would silently drop
        # any critical position beyond the sample from both at_risk and safe while
        # still counting it in degradation_score's denominator (falsely "safe").
        attention_dist = measure_attention_distribution(
            tokens,
            "current_task",
        )

        # `or` would also replace an explicitly-supplied empty list (a caller
        # deliberately asserting "no critical positions") with the range(10)
        # default -- only an unset (None) argument should fall back to it.
        degradation = detect_lost_in_middle(
            list(range(10)) if critical_positions is None else critical_positions,
            attention_dist,
        )

        poisoning = PoisoningDetector().detect_poisoning(context)

        health_score = self._calculate_health_score(
            utilization=utilization,
            degradation=degradation["degradation_score"],
            poisoning_risk=1.0 if poisoning["poisoning_risk"] else 0.0,
        )

        result: dict[str, Any] = {
            "health_score": health_score,
            "status": self._interpret_score(health_score),
            "metrics": {
                "token_count": token_count,
                "utilization": utilization,
                "degradation_score": degradation["degradation_score"],
                "poisoning_risk": poisoning["overall_risk"],
            },
            "issues": {
                "lost_in_middle": degradation,
                "poisoning": poisoning,
            },
            "recommendations": self._generate_recommendations(utilization, degradation, poisoning),
        }

        self.metrics_history.append(result)
        return result

    def _calculate_health_score(
        self,
        utilization: float,
        degradation: float,
        poisoning_risk: float,
    ) -> float:
        """Calculate composite health score (0-1, higher is healthier)."""
        utilization_penalty = min(utilization * 0.5, 0.3)
        degradation_penalty = degradation * 0.3
        poisoning_penalty = poisoning_risk * 0.2

        score = 1.0 - utilization_penalty - degradation_penalty - poisoning_penalty
        return max(0.0, min(1.0, score))

    def _interpret_score(self, score: float) -> str:
        """Map numeric score to human-readable status."""
        if score > 0.8:
            return "healthy"
        elif score > 0.6:
            return "warning"
        elif score > 0.4:
            return "degraded"
        else:
            return "critical"

    def _generate_recommendations(
        self,
        utilization: float,
        degradation: dict[str, Any],
        poisoning: dict[str, Any],
    ) -> list[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations: list[str] = []

        if utilization > 0.8:
            recommendations.append("Context near limit - consider compaction")
            recommendations.append("Implement observation masking for tool outputs")

        if degradation.get("at_risk"):
            recommendations.append("Critical information in degraded attention region")
            recommendations.append("Move key information to beginning or end of context")

        if poisoning["poisoning_risk"]:
            recommendations.append("Context poisoning indicators detected")
            recommendations.append("Review and remove potentially erroneous information")

        if not recommendations:
            recommendations.append("Context appears healthy - continue monitoring")

        return recommendations


# ---------------------------------------------------------------------------
# Convenience Function
# ---------------------------------------------------------------------------


def analyze_agent_context(
    context: str,
    context_limit: int = 80_000,
    critical_positions: list[int] | None = None,
) -> dict[str, Any]:
    """One-call health analysis for an agent session.

    Use when: a quick health check is needed without manually configuring
    an analyzer instance. Prints a summary and returns the full result dict.

    Args:
        context: The full context string to analyze.
        context_limit: Maximum token budget for this agent's context window.
        critical_positions: Indices of critical tokens. Defaults to [0..4].

    Returns:
        Full health analysis dict from ``ContextHealthAnalyzer.analyze``.
    """
    analyzer = ContextHealthAnalyzer(context_limit=context_limit)

    if critical_positions is None:
        critical_positions = list(range(5))

    result = analyzer.analyze(context, critical_positions)

    print(f"Health Score: {result['health_score']:.2f}")
    print(f"Status: {result['status']}")
    print("Recommendations:")
    for rec in result["recommendations"]:
        print(f"  - {rec}")

    return result


# ---------------------------------------------------------------------------
# CLI Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Demonstrate the public API with synthetic context
    print("=" * 60)
    print("Context Degradation Detector — Demo")
    print("=" * 60)

    # Build a synthetic context with identifiable sections
    intro = "System prompt: Analyze quarterly revenue data and produce a report. "
    middle = "Background information. " * 200  # Filler to simulate long context
    conclusion = "Key finding: Revenue increased 15% year-over-year. "
    sample_context = intro + middle + conclusion

    print(f"\nSample context length: {len(sample_context.split())} tokens")

    # 1. Structure analysis
    print("\n--- Structure Analysis ---")
    structure = analyze_context_structure(sample_context)
    print(f"  Lines: {structure['total_lines']}")
    print(f"  Middle content ratio: {structure['middle_content_ratio']:.2f}")
    print(f"  Middle spillover ratio: {structure['middle_spillover_ratio']:.2f}")
    print(f"  Degradation risk: {structure['degradation_risk']}")

    # 2. Attention distribution (first 50 tokens for brevity)
    print("\n--- Attention Distribution (first 50 tokens) ---")
    tokens = sample_context.split()[:50]
    attention = measure_attention_distribution(tokens, "quarterly revenue")
    favored = sum(1 for a in attention if a["region"] == "attention_favored")
    degraded = sum(1 for a in attention if a["region"] == "attention_degraded")
    print(f"  Favored positions: {favored}")
    print(f"  Degraded positions: {degraded}")

    # 3. Lost-in-middle detection
    print("\n--- Lost-in-Middle Detection ---")
    critical = [0, 1, 2, 25, 26, 48, 49]  # Start, middle, end
    lim_result = detect_lost_in_middle(critical, attention)
    print(f"  At risk: {lim_result['at_risk']}")
    print(f"  Safe: {lim_result['safe']}")
    print(f"  Degradation score: {lim_result['degradation_score']:.2f}")

    # 4. Poisoning detection
    print("\n--- Poisoning Detection ---")
    poisoned_context = (
        "The API returned an error. However, the system reportedly "
        "recovered. But the error persisted and the request failed. "
        "Unable to parse the response. Sources suggest the endpoint "
        "may have been deprecated. Although retries succeeded, yet "
        "the invalid token caused an exception."
    )
    detector = PoisoningDetector()
    poisoning = detector.detect_poisoning(poisoned_context)
    print(f"  Poisoning risk: {poisoning['poisoning_risk']}")
    print(f"  Overall risk: {poisoning['overall_risk']}")
    for indicator in poisoning["indicators"]:
        print(f"    [{indicator['severity']}] {indicator['message']}")

    # 5. Full health analysis
    print("\n--- Full Health Analysis ---")
    result = analyze_agent_context(sample_context)
    print(f"\n  Full result keys: {list(result.keys())}")
