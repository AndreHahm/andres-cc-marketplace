"""Codex review scope derivation and output schema/aggregation.

`derive_review_scope` is purely deterministic — merge-base diff in, a scope
decision out. `validate_review_output`/`aggregate_findings` police the
structured envelope every dispatched reviewer must return; they never parse
or trust reviewer prose beyond that envelope's own typed fields.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from scripts.marketplace_ci.git_state import ChangedPath

STRUCTURAL_CHECK_REF = "scripts.marketplace_ci.validators:run_delta_structural_checks"

# Delta Validate's 3 baseline reviewers, dispatched on every delta PR
# regardless of component type (design v4 amendment 14).
DELTA_VALIDATE = ("plugin-rulebook-checker", "dependency-reviewer", "security-reviewer")

# Delta Audit's launch-time type-specific reviewer, keyed by the plugin
# component-directory name (plugins/<name>/<component-type>/...). Every
# other component type (hooks, commands, rules, scripts, docs) yields an
# empty scope.audit at launch — the other 10 reviewers are added here one
# at a time, alongside Task 9's own routing table, as their type appears in
# a real PR (see design v4 amendment 14 / Global Constraints).
LAUNCH_AUDIT_BY_COMPONENT_TYPE = {
    "skills": "skill-reviewer",
    "agents": "subagent-reviewer",
}

# "Shared marketplace governance" per design's escalation conditions: a
# change to any of these always triggers full review, since their blast
# radius isn't bounded by a single plugin's own delta.
FULL_ESCALATION_PATHS = (
    "plugins/plugin-devkit/skills/plugin-rulebook/SKILL.md",
    ".claude-plugin/marketplace.json",
    ".claude/marketplace-sync.json",
)


@dataclass(frozen=True)
class ReviewScope:
    mode: str  # "light" | "delta" | "full"
    structural_check: str
    validate: tuple[str, ...]
    audit: tuple[str, ...]
    paths: tuple[str, ...]


def _changed_path_set(changes: Sequence[ChangedPath]) -> tuple[str, ...]:
    paths = {p for cp in changes if (p := cp.new_path or cp.old_path) is not None}
    return tuple(sorted(paths))


def _component_type(path: str) -> str | None:
    parts = path.split("/")
    if len(parts) < 3 or parts[0] != "plugins":
        return None
    return parts[2]


def derive_review_scope(
    changes: Sequence[ChangedPath],
    dependency_index: dict[str, tuple[str, ...]],
    *,
    dependency_closure_limit: int = 50,
) -> ReviewScope:
    paths = _changed_path_set(changes)

    if any(p in FULL_ESCALATION_PATHS for p in paths):
        return ReviewScope(
            mode="full", structural_check=STRUCTURAL_CHECK_REF, validate=(), audit=(), paths=paths
        )

    closure: set[str] = set(paths)
    for path in paths:
        closure.update(dependency_index.get(path, ()))
    if len(closure) > dependency_closure_limit:
        return ReviewScope(
            mode="full",
            structural_check=STRUCTURAL_CHECK_REF,
            validate=(),
            audit=(),
            paths=tuple(sorted(closure)),
        )

    if not any(p.startswith("plugins/") for p in paths):
        return ReviewScope(
            mode="light", structural_check=STRUCTURAL_CHECK_REF, validate=(), audit=(), paths=paths
        )

    audit_types = {
        LAUNCH_AUDIT_BY_COMPONENT_TYPE[component]
        for path in paths
        if (component := _component_type(path)) in LAUNCH_AUDIT_BY_COMPONENT_TYPE
    }

    return ReviewScope(
        mode="delta",
        structural_check=STRUCTURAL_CHECK_REF,
        validate=DELTA_VALIDATE,
        audit=tuple(sorted(audit_types)),
        paths=paths,
    )


VALID_SEVERITIES = ("Critical", "Major", "Minor")
_SEVERITY_RANK = {"Minor": 0, "Major": 1, "Critical": 2}

_REQUIRED_TOP_KEYS = {"mode", "reviewed_paths", "reviewers", "coverage_confirmed", "findings"}
_REQUIRED_REVIEWERS_KEYS = {"selected", "completed", "skipped", "failed"}
_REQUIRED_FINDING_KEYS = {"reviewer", "severity", "rule", "path", "evidence", "remediation"}


class ReviewOutputError(ValueError):
    """Raised when a reviewer's structured output envelope is malformed."""


@dataclass(frozen=True)
class Finding:
    reviewer: str
    severity: str
    rule: str
    path: str
    evidence: str
    remediation: str
    line: int | None = None
    reporters: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewResult:
    mode: str
    reviewed_paths: tuple[str, ...]
    selected: tuple[str, ...]
    completed: tuple[str, ...]
    skipped: tuple[str, ...]
    failed: tuple[str, ...]
    coverage_confirmed: bool
    findings: tuple[Finding, ...]

    @property
    def blocking(self) -> bool:
        return any(f.severity in ("Critical", "Major") for f in self.findings)


def validate_review_output(data: dict) -> ReviewResult:
    missing_top = _REQUIRED_TOP_KEYS - set(data)
    if missing_top:
        raise ReviewOutputError(f"missing required field(s): {sorted(missing_top)}")

    reviewers = data["reviewers"]
    if not isinstance(reviewers, dict):
        raise ReviewOutputError("'reviewers' must be an object")
    missing_reviewers = _REQUIRED_REVIEWERS_KEYS - set(reviewers)
    if missing_reviewers:
        raise ReviewOutputError(f"reviewers missing required field(s): {sorted(missing_reviewers)}")

    selected = tuple(reviewers["selected"])
    completed = tuple(reviewers["completed"])
    skipped = tuple(reviewers["skipped"])
    failed = tuple(reviewers["failed"])

    accounted = set(completed) | set(skipped) | set(failed)
    missing_coverage = set(selected) - accounted
    if missing_coverage:
        raise ReviewOutputError(f"incomplete reviewer coverage: {sorted(missing_coverage)}")
    if not data["coverage_confirmed"]:
        raise ReviewOutputError("coverage_confirmed is false")

    findings: list[Finding] = []
    for raw in data["findings"]:
        missing_finding = _REQUIRED_FINDING_KEYS - set(raw)
        if missing_finding:
            raise ReviewOutputError(f"finding missing required field(s): {sorted(missing_finding)}")
        if raw["severity"] not in VALID_SEVERITIES:
            raise ReviewOutputError(f"unknown severity: {raw['severity']!r}")
        findings.append(
            Finding(
                reviewer=raw["reviewer"],
                severity=raw["severity"],
                rule=raw["rule"],
                path=raw["path"],
                evidence=raw["evidence"],
                remediation=raw["remediation"],
                line=raw.get("line"),
            )
        )

    return ReviewResult(
        mode=data["mode"],
        reviewed_paths=tuple(data["reviewed_paths"]),
        selected=selected,
        completed=completed,
        skipped=skipped,
        failed=failed,
        coverage_confirmed=bool(data["coverage_confirmed"]),
        findings=tuple(findings),
    )


def aggregate_findings(reports: Sequence[ReviewResult]) -> tuple[Finding, ...]:
    """Deduplicate only identical (rule, path, line) findings, keeping the
    highest reported severity and every distinct reporting reviewer."""
    grouped: dict[tuple[str, str, int | None], list[Finding]] = {}
    order: list[tuple[str, str, int | None]] = []
    for report in reports:
        for finding in report.findings:
            key = (finding.rule, finding.path, finding.line)
            if key not in grouped:
                grouped[key] = []
                order.append(key)
            grouped[key].append(finding)

    aggregated: list[Finding] = []
    for key in order:
        group = grouped[key]
        highest = max(group, key=lambda f: _SEVERITY_RANK[f.severity])
        reporters = tuple(sorted({f.reviewer for f in group}))
        aggregated.append(replace(highest, reporters=reporters))
    return tuple(aggregated)
