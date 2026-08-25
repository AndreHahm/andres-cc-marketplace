"""Shared record fields and cross-record invariants for plugin-inventory and
marketplace-inventory that JSON Schema alone can't express: stable ID
generation, the status enum, and history-period continuity (exactly one
open period, the valid_to three-state sentinel, array-order-is-authoritative
non-overlap checking). Contains no file I/O and no grading logic -- see
json_store.py and grading.py for those.
"""

import secrets

STATUS_VALUES = {"planned", "active", "deprecated", "superseded", "retired"}
FUNCTIONAL_ROLE_VALUES = {
    "workflow",
    "reviewer",
    "validator",
    "reference",
    "integration",
    "infrastructure",
    "mixed",
}
COMPATIBILITY_LEVEL_VALUES = {"native", "compatible", "partial", "incompatible", "unknown"}

ID_HEX_LENGTH = 8
ID_MAX_COLLISION_RETRIES = 5


def generate_id(type_prefix, existing_ids):
    """Generate a new stable opaque ID: '<type_prefix>_<8-hex-lowercase>'.

    `type_prefix` is 'plugin' or 'component'. `existing_ids` is every ID
    already assigned at this ID's scope (marketplace-wide for `plugin_*`,
    plugin-wide for `component_*`) -- checked before assignment, never
    recomputed later. Raises ValueError after ID_MAX_COLLISION_RETRIES
    consecutive collisions (a report-worthy anomaly at 32 bits of entropy,
    per the concept's own collision-handling note).
    """
    if type_prefix not in ("plugin", "component"):
        raise ValueError(f"type_prefix must be 'plugin' or 'component', got {type_prefix!r}")
    for _ in range(ID_MAX_COLLISION_RETRIES + 1):
        candidate = f"{type_prefix}_{secrets.token_hex(ID_HEX_LENGTH // 2)}"
        if candidate not in existing_ids:
            return candidate
    raise ValueError(
        f"could not generate a unique {type_prefix} ID after "
        f"{ID_MAX_COLLISION_RETRIES + 1} attempts -- report-worthy anomaly, not a retry-forever bug"
    )


def validate_status(status):
    if status not in STATUS_VALUES:
        raise ValueError(f"invalid status {status!r}; must be one of {sorted(STATUS_VALUES)}")


def validate_functional_role(role):
    if role not in FUNCTIONAL_ROLE_VALUES:
        raise ValueError(
            f"invalid functional_role {role!r}; must be one of {sorted(FUNCTIONAL_ROLE_VALUES)}"
        )


def validate_compatibility_level(level):
    if level not in COMPATIBILITY_LEVEL_VALUES:
        raise ValueError(
            f"invalid compatibility level {level!r}; "
            f"must be one of {sorted(COMPATIBILITY_LEVEL_VALUES)}"
        )


def validate_history_periods(periods, entity_label):
    """Validate a naming_history- or status_history-shaped list of periods.

    Enforces: at least one period; exactly one period has `valid_to is None`
    (the open period) and it is last in array order; every other period's
    `valid_to` is a real ISO date string or the literal sentinel
    `"unknown"` (never bare `null`, which is reserved for the open period);
    `valid_from` is `null` or a real ISO date string (no third state).
    Non-overlap is checked only between adjacent periods whose relevant
    boundary dates are *both* known (neither `None` nor `"unknown"`) --
    array position, not a re-derived date comparison, is what establishes
    which period is earlier in every other case.
    """
    if not periods:
        raise ValueError(f"{entity_label}: history must have at least one period")

    open_periods = [p for p in periods if p.get("valid_to") is None]
    if len(open_periods) != 1:
        raise ValueError(
            f"{entity_label}: exactly one period must have valid_to == null "
            f"(the open period); found {len(open_periods)}"
        )
    if periods[-1].get("valid_to") is not None:
        raise ValueError(
            f"{entity_label}: the open period (valid_to == null) must be last in array order"
        )

    for period in periods:
        valid_to = period.get("valid_to")
        if valid_to is not None and valid_to != "unknown" and not _looks_like_date(valid_to):
            raise ValueError(
                f"{entity_label}: valid_to must be null, 'unknown', or an ISO date "
                f"string; got {valid_to!r}"
            )
        valid_from = period.get("valid_from")
        if valid_from is not None and not _looks_like_date(valid_from):
            raise ValueError(
                f"{entity_label}: valid_from must be null or an ISO date string; got {valid_from!r}"
            )

    for earlier, later in zip(periods, periods[1:], strict=False):
        earlier_end = earlier.get("valid_to")
        later_start = later.get("valid_from")
        if _is_real_date(earlier_end) and _is_real_date(later_start) and later_start < earlier_end:
            raise ValueError(
                f"{entity_label}: period order violation -- '{later_start}' starts "
                f"before the preceding period's own end '{earlier_end}'"
            )


def open_period_value(periods, value_key):
    """Return the value_key field (e.g. 'status' or 'name') of the one open period."""
    for period in periods:
        if period.get("valid_to") is None:
            return period.get(value_key)
    raise ValueError("no open period found -- call validate_history_periods first")


def _is_real_date(value):
    return value is not None and value != "unknown" and _looks_like_date(value)


def _looks_like_date(value):
    if not isinstance(value, str) or len(value) != 10:
        return False
    parts = value.split("-")
    return len(parts) == 3 and all(part.isdigit() for part in parts)
