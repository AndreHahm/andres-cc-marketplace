"""Score the reviewers against the labelled corpus (Phase 4 of #568, issue #586).

Precision and recall come from `reviewer-eval/corpus/`; stability comes from repeated archived runs
of one head. This only measures: it never changes a reviewer prompt, pin or weight.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from scripts.reviewer_eval.corpus import CorpusError, load_corpus

OVERALL = "overall"
STABILITY_REPEATS = 5
STABILITY_MIN_AGREE = 4


def _is_int(value: object) -> bool:
    """A real integer: `bool` is an `int` subclass and would otherwise pass as line 1 or 0."""
    return isinstance(value, int) and not isinstance(value, bool)


def _rate(part: int, whole: int) -> float | None:
    return part / whole if whole else None


def score_corpus(cases: list[dict]) -> dict[str, dict]:
    """Precision per reviewer and recall against the corpus's known issues.

    Only a finding labelled `true` is correct. A known issue counts as found by a reviewer when one
    of that reviewer's findings links to it; `overall` counts it found when any reviewer's does.
    """
    known_total = sum(len(case["known_issues"]) for case in cases)
    reported: Counter[str] = Counter()
    correct: Counter[str] = Counter()
    found: dict[str, set[tuple[int, str, str]]] = {OVERALL: set()}
    for case in cases:
        for finding in case["findings"]:
            reviewer = finding["reviewer"]
            for name in (reviewer, OVERALL):
                reported[name] += 1
                correct[name] += finding["label"] == "true"
            if finding["known_issue"] is not None:
                key = (case["pr"], case["head_sha"], finding["known_issue"])
                found.setdefault(reviewer, set()).add(key)
                found[OVERALL].add(key)
    names = sorted(set(reported) - {OVERALL}) + [OVERALL]
    return {
        name: {
            "reported": reported[name],
            "true": correct[name],
            "precision": _rate(correct[name], reported[name]),
            "known_found": len(found.get(name, ())),
            "known_total": known_total,
            "recall": _rate(len(found.get(name, ())), known_total),
        }
        for name in names
    }


def blocking_set(result: dict, reviewer: str) -> frozenset[tuple[str, int | None]]:
    """The (path, line) of every finding `reviewer` reported as blocking in one archived result.

    The result is untrusted CI output, so a missing or mistyped field is a clear `ValueError`.
    """
    if not isinstance(result, dict):
        raise ValueError("archived result: must be a JSON object")
    findings = result.get("findings")
    if not isinstance(findings, list):
        raise ValueError("archived result: findings must be a list")
    blocking = set()
    for finding in findings:
        if not (
            isinstance(finding, dict)
            and isinstance(finding.get("reviewer"), str)
            and isinstance(finding.get("path"), str)
            and isinstance(finding.get("blocking"), bool)
            and (finding.get("line") is None or _is_int(finding["line"]))
        ):
            raise ValueError("archived result: a finding has a missing or mistyped field")
        if finding["reviewer"] == reviewer and finding["blocking"]:
            blocking.add((finding["path"], finding["line"]))
    return frozenset(blocking)


def stability(blocking_sets: list[frozenset]) -> dict:
    """How many repeats of one head gave the same blocking set; stable means at least 4 of 5.

    With more than 5 repeats the same 4-in-5 share applies (8 of 10, not 4 of 10). `stable` is None
    until the full number of repeats exists, since fewer say nothing about it.
    """
    agree = max(Counter(blocking_sets).values(), default=0)
    stable = None
    if len(blocking_sets) >= STABILITY_REPEATS:
        stable = agree * STABILITY_REPEATS >= len(blocking_sets) * STABILITY_MIN_AGREE
    return {"repeats": len(blocking_sets), "agree": agree, "stable": stable}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reviewer_eval.score", description=__doc__)
    parser.add_argument("directory", nargs="?", default="reviewer-eval/corpus")
    args = parser.parse_args(argv)
    try:
        cases = load_corpus(Path(args.directory))
    except CorpusError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(json.dumps(score_corpus(cases), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
