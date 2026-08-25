"""Reads and validates a completed plugin-grader JSON report for import into
an inventory's `scoring_history`/`security_scoring_history`. Contains no
grading formula, security rollup, or score transformation of its own --
plugin-grader is the sole quality- and security-scoring authority; this
module only verifies target identity, schema shape, and required fields,
then copies the resulting value unchanged.
"""

import datetime

from .json_store import compute_hash, read_json  # ty: ignore[unresolved-import]


class GradingReportError(ValueError):
    """Raised when a plugin-grader report can't be used for import: malformed,
    unsupported target type, target/type mismatch, or a required field absent.
    """


def load_and_validate_report(report_path, expected_target, expected_target_type):
    """Read a plugin-grader report and verify target/type/shape.

    Returns the parsed report dict. Raises `GradingReportError` on any
    mismatch or malformed JSON -- never silently substitutes a default.
    """
    try:
        report = read_json(report_path)
    except (OSError, ValueError) as exc:
        raise GradingReportError(f"could not read/parse report at {report_path}: {exc}") from exc

    for field in ("target", "target_type", "graded_at"):
        if field not in report:
            raise GradingReportError(f"report {report_path} is missing required field {field!r}")

    if report["target"] != expected_target:
        raise GradingReportError(
            f"report target {report['target']!r} does not match expected {expected_target!r}"
        )
    if report["target_type"] != expected_target_type:
        raise GradingReportError(
            f"report target_type {report['target_type']!r} does not match "
            f"expected {expected_target_type!r}"
        )
    return report


def extract_quality_score(report):
    """Return `(score, grader_schema_version)` for import into
    `scoring_history`. Component-mode -> `final_score`; plugin-mode ->
    `plugin_final_score`. `weighted_total`/`plugin_score_raw` are never
    substituted -- this raises if the authoritative field is absent rather
    than falling back to a pre-gate value.
    """
    if report["target_type"] == "plugin":
        if "plugin_final_score" not in report:
            raise GradingReportError("plugin-mode report has no plugin_final_score")
        return report["plugin_final_score"], report.get("grader_schema_version")
    if "final_score" not in report:
        raise GradingReportError("component-mode report has no final_score")
    return report["final_score"], report.get("grader_schema_version")


def extract_security_score(report):
    """Return `(security_score, source_field, is_na, grader_schema_version)`.

    Both modes treat "no security dimension in this report" the same way -- a graceful
    `security_score: None`, never an exception that would also abort the caller's
    unrelated quality-score import (`build_scoring_event`/`extract_quality_score` are
    entirely independent of this function and never see its result).

    Component-mode: `dimensions.safety_risk_handling.score`/`is_na` when the dimension is
    present; `None` when it's entirely absent (an unsupported target type, or a report
    that predates this dimension) -- this is not distinguished from plugin-mode's
    pre-prerequisite case below, since both mean the same thing to a caller: nothing to
    import, quality import unaffected.
    Plugin-mode: an explicit `plugin_security_score`, distinguishing two `None` cases the
    caller must not conflate -- `grader_schema_version` absent entirely means the report
    predates the security-score prerequisite (a different case from the field being
    present-and-`null` with a stated `notes.security_score_unavailable_reason`, which this
    function surfaces as `security_score: None` with a real `grader_schema_version`,
    letting the caller tell the two apart).
    """
    grader_schema_version = report.get("grader_schema_version")
    if report["target_type"] == "plugin":
        if grader_schema_version is None:
            return None, "plugin_security_score", None, None
        return (
            report.get("plugin_security_score"),
            "plugin_security_score",
            None,
            grader_schema_version,
        )

    dimensions = report.get("dimensions", {})
    safety = dimensions.get("safety_risk_handling")
    if safety is None:
        return None, "dimensions.safety_risk_handling.score", None, grader_schema_version
    return (
        safety.get("score"),
        "dimensions.safety_risk_handling.score",
        safety.get("is_na", False),
        grader_schema_version,
    )


def _imported_on_today():
    return datetime.datetime.now(datetime.UTC).date().isoformat()


def build_scoring_event(report, report_path, target, target_type):
    """Build a `scoring_history`-shaped event dict, ready for
    `history.append_scoring_event`. Raises `GradingReportError` if the
    report has no usable quality score.

    `report_path` typically points into a gitignored `.claude/output/` report and is a
    best-effort provenance breadcrumb, not a durable reference -- it can become
    unresolvable at any time without that being a breaking change. `report_sha256` is
    the durable identity a consumer should actually trust.
    """
    score, grader_schema_version = extract_quality_score(report)
    gates_applied = report.get(
        "plugin_gates_applied" if target_type == "plugin" else "gates_applied", []
    )
    if not isinstance(gates_applied, list) or not all(
        isinstance(g, dict) and isinstance(g.get("gate"), str) for g in gates_applied
    ):
        raise GradingReportError(
            "report's gates_applied is not a list of {'gate': <str>, ...} objects"
        )
    return {
        "score": score,
        "graded_at": report["graded_at"],
        "imported_on": _imported_on_today(),
        "target": target,
        "target_type": target_type,
        "report_path": report_path,
        "report_sha256": compute_hash(report),
        "grader_schema_version": grader_schema_version,
        "gates_applied": gates_applied,
    }


def build_security_scoring_event(report, report_path, target, target_type):
    """Build a `security_scoring_history`-shaped event dict. Returns `None`
    when there is nothing to append -- a `None` security score with no
    `grader_schema_version` at all (pre-prerequisite report) never appends a
    history event, matching the invariant that a `null` score is not a
    score-bearing event.
    """
    security_score, source_field, is_na, grader_schema_version = extract_security_score(report)
    if security_score is None:
        return None
    return {
        "security_score": security_score,
        "graded_at": report["graded_at"],
        "imported_on": _imported_on_today(),
        "target": target,
        "target_type": target_type,
        "report_path": report_path,
        "report_sha256": compute_hash(report),
        "grader_schema_version": grader_schema_version,
        "source_field": source_field,
        "is_na": is_na,
    }
