"""Append-only naming/status/scoring/security-scoring history maintenance.

Only ordinary appends: close the currently-open period and add the next
one. Never rewrites or deletes an existing period -- that's explicit
repair-history mode's job, which lives in the calling skill (it shows the
exact destructive rewrite and gets human approval before touching anything
this module would otherwise protect).
"""

from .models import validate_history_periods  # ty: ignore[unresolved-import]


def close_and_append_status_period(
    status_history, new_status, valid_from, reason, evidence, closed_valid_to=None
):
    """Close the currently-open status period and append the next one.

    `closed_valid_to` is the real date the prior status ended, or left as
    `"unknown"` (the default) if genuinely undocumented -- never bare
    `None`, which is reserved for the new, now-open period this function
    appends.
    """
    if not status_history:
        raise ValueError(
            "status_history must already contain a bootstrap period before transitioning"
        )
    updated = [dict(p) for p in status_history]
    if updated[-1].get("valid_to") is not None:
        raise ValueError(
            "the last status period is already closed -- nothing open to transition from"
        )
    updated[-1]["valid_to"] = closed_valid_to if closed_valid_to is not None else "unknown"
    updated.append(
        {
            "status": new_status,
            "valid_from": valid_from,
            "valid_to": None,
            "reason": reason,
            "evidence": list(evidence),
        }
    )
    validate_history_periods(updated, "status_history")
    return updated


def close_and_append_naming_period(
    naming_history, new_name, valid_from, reason, evidence, closed_valid_to=None
):
    """Close the currently-open naming period and append the next one. See
    `close_and_append_status_period` for the `closed_valid_to` convention.
    """
    if not naming_history:
        raise ValueError("naming_history must already contain a bootstrap period before a rename")
    updated = [dict(p) for p in naming_history]
    if updated[-1].get("valid_to") is not None:
        raise ValueError("the last naming period is already closed -- nothing open to rename from")
    updated[-1]["valid_to"] = closed_valid_to if closed_valid_to is not None else "unknown"
    updated.append(
        {
            "name": new_name,
            "valid_from": valid_from,
            "valid_to": None,
            "reason": reason,
            "evidence": list(evidence),
        }
    )
    validate_history_periods(updated, "naming_history")
    return updated


SCORING_EVENT_REQUIRED_FIELDS = {
    "score",
    "graded_at",
    "imported_on",
    "target",
    "target_type",
    "report_path",
    "report_sha256",
    "grader_schema_version",
    "gates_applied",
}

SECURITY_SCORING_EVENT_REQUIRED_FIELDS = {
    "security_score",
    "graded_at",
    "imported_on",
    "target",
    "target_type",
    "report_path",
    "report_sha256",
    "grader_schema_version",
    "source_field",
    "is_na",
}


def append_scoring_event(scoring_history, event):
    """Append a quality `scoring_history` event. Returns `(updated_history,
    appended)` -- `appended` is `False` (a no-op) when the event's report
    hash + target already exists in the history, per the concept's dedup
    rule. Backfilling an older report appends it in chronological array
    position but the caller decides whether that changes the record's
    *current* `score` (it doesn't, unless it's the newest by `graded_at`).
    """
    missing = SCORING_EVENT_REQUIRED_FIELDS - event.keys()
    if missing:
        raise ValueError(f"scoring event missing required fields: {sorted(missing)}")
    for existing in scoring_history:
        if (
            existing["report_sha256"] == event["report_sha256"]
            and existing["target"] == event["target"]
        ):
            return scoring_history, False
    updated = list(scoring_history) + [event]
    updated.sort(key=lambda e: e["graded_at"])
    return updated, True


def append_security_scoring_event(security_scoring_history, event):
    """Append a `security_scoring_history` event. Deduplicates independently
    by target, report hash, *and* source field (a component's quality and
    security events may legitimately cite the same report).
    """
    missing = SECURITY_SCORING_EVENT_REQUIRED_FIELDS - event.keys()
    if missing:
        raise ValueError(f"security scoring event missing required fields: {sorted(missing)}")
    for existing in security_scoring_history:
        if (
            existing["report_sha256"] == event["report_sha256"]
            and existing["target"] == event["target"]
            and existing["source_field"] == event["source_field"]
        ):
            return security_scoring_history, False
    updated = list(security_scoring_history) + [event]
    updated.sort(key=lambda e: e["graded_at"])
    return updated, True


def current_score_from_history(scoring_history):
    """The current `score` equals the chronologically newest valid entry by
    `graded_at` -- never the most recently *imported* item. Returns `None`
    for an empty history (the invariant: `score` is null exactly when
    `scoring_history` is empty).
    """
    if not scoring_history:
        return None
    return max(scoring_history, key=lambda e: e["graded_at"])["score"]


def current_security_score_from_history(security_scoring_history):
    """Same rule as `current_score_from_history`, for the security lane."""
    if not security_scoring_history:
        return None
    return max(security_scoring_history, key=lambda e: e["graded_at"])["security_score"]
