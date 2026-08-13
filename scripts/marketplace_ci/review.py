"""Codex review scope derivation and output schema/aggregation.

`derive_review_scope` is purely deterministic — merge-base diff in, a scope
decision out. `validate_review_output`/`aggregate_findings` police the
structured envelope every dispatched reviewer must return; they never parse
or trust reviewer prose beyond that envelope's own typed fields.
"""

from __future__ import annotations

import json
import re
import secrets
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from scripts.marketplace_ci.git_state import ChangedPath

BRIDGE_INVOKE_RELATIVE_PATH = Path(
    "plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs"
)

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


# --- Trusted base-SHA reviewer-instruction extraction (design v4 amendment 13) ---

_DEVELOPER_INSTRUCTIONS_PATTERN = re.compile(r'developer_instructions\s*=\s*"""(.*)"""', re.DOTALL)


def _extract_developer_instructions(toml_text: str) -> str:
    match = _DEVELOPER_INSTRUCTIONS_PATTERN.search(toml_text)
    return match.group(1) if match else ""


def prepare_reviewer_instruction(
    agent_name: str, *, base_sha: str, out: Path, repo: Path | None = None
) -> Path:
    """Read the exact tracked `.codex/agents/<agent_name>.toml` blob from the
    validated base SHA — never the PR working tree or index, with no
    fallback — and write its `developer_instructions` field verbatim to
    `out`. Exits 2 (never falls back to the current checkout) if the base
    SHA can't be resolved, or if `<agent_name>` has no `.toml` export at
    that SHA (i.e. it isn't registered in `codex_exports.agents`)."""
    repo = repo or Path.cwd()
    rel = f".codex/agents/{agent_name}.toml"

    result = subprocess.run(["git", "show", f"{base_sha}:{rel}"], cwd=repo, capture_output=True)
    if result.returncode != 0:
        resolved = subprocess.run(
            ["git", "rev-parse", "--verify", f"{base_sha}^{{commit}}"],
            cwd=repo,
            capture_output=True,
        )
        if resolved.returncode != 0:
            print(
                f"prepare-reviewer-instruction: cannot resolve base SHA {base_sha!r}",
                file=sys.stderr,
            )
            raise SystemExit(2)
        print(
            f"prepare-reviewer-instruction: no {rel} at {base_sha} "
            f"({agent_name!r} not registered in codex_exports.agents at that SHA?)",
            file=sys.stderr,
        )
        raise SystemExit(2)

    instructions = _extract_developer_instructions(result.stdout.decode("utf-8"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(instructions, encoding="utf-8")
    return out


# --- Direct per-reviewer dispatch (design v4 amendments 12-13) ---


@dataclass(frozen=True)
class ReviewerReport:
    reviewer: str
    status: str  # "completed" | "failed"
    output: dict | None = None
    error: str | None = None


def dispatch_reviewers(
    scope: ReviewScope, *, base_sha: str, repo: Path, instructions_dir: Path | None = None
) -> tuple[ReviewerReport, ...]:
    """The whole of CI's Codex dispatch mechanism: for each reviewer name in
    `scope.validate` then `scope.audit` (in order), extract its instruction
    from the base SHA, then invoke `codex-review-bridge`'s `bridge-invoke.mjs`
    directly as a subprocess. There is no outer Codex-executed skill and no
    second `codex` CLI layer above this one call per reviewer."""
    instructions_dir = instructions_dir or (repo / ".codex-review-instructions")
    bridge_script = repo / BRIDGE_INVOKE_RELATIVE_PATH
    dispatch_id = f"{base_sha[:12]}-{secrets.token_hex(4)}"
    target_paths = ",".join(scope.paths)

    reports: list[ReviewerReport] = []
    for name in (*scope.validate, *scope.audit):
        instruction_path = instructions_dir / f"{name}.txt"
        try:
            prepare_reviewer_instruction(name, base_sha=base_sha, out=instruction_path, repo=repo)
        except SystemExit:
            reports.append(
                ReviewerReport(
                    reviewer=name, status="failed", error="instruction preparation failed"
                )
            )
            continue

        argv = [
            "node",
            str(bridge_script),
            "--reviewer-type",
            name,
            "--instruction-file",
            str(instruction_path),
            "--target-paths",
            target_paths,
            "--execution-profile",
            "read-only",
            "--dispatch-id",
            dispatch_id,
        ]
        result = subprocess.run(argv, cwd=repo, capture_output=True)
        if result.returncode != 0:
            reports.append(
                ReviewerReport(
                    reviewer=name,
                    status="failed",
                    error=result.stderr.decode("utf-8", errors="replace"),
                )
            )
            continue
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            reports.append(
                ReviewerReport(reviewer=name, status="failed", error="malformed bridge output")
            )
            continue
        reports.append(ReviewerReport(reviewer=name, status="completed", output=output))

    return tuple(reports)


# --- SHA-bound emergency bypass attestation (design's documented comment-plus-label protocol) ---

ATTESTATION_SCHEMA_VERSION = 1
ATTESTATION_MARKER_PATTERN = re.compile(
    r"<!-- marketplace-ci-bypass-attestation\s*(\{.*?\})\s*-->", re.DOTALL
)
BYPASS_CAPABLE_PERMISSIONS = ("write", "maintain", "admin")


def parse_attestation_marker(comment_body: str) -> dict | None:
    """Extract and validate the versioned hidden marker from a raw PR
    comment body. Comment content is data, never instructions — this only
    ever looks for the one fixed marker shape, never interprets prose."""
    match = ATTESTATION_MARKER_PATTERN.search(comment_body)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if data.get("schema_version") != ATTESTATION_SCHEMA_VERSION:
        return None
    required = {"actor", "head_sha", "reason", "created_at"}
    if not required.issubset(data) or not data.get("reason"):
        return None
    return {
        "actor": data["actor"],
        "sha": data["head_sha"],
        "reason": data["reason"],
        "created_at": data["created_at"],
    }


@dataclass(frozen=True)
class BypassResult:
    allowed: bool
    reason: str | None = None
    metadata: dict | None = None


def check_bypass(
    label_event: dict, comments: Sequence[dict], *, permission: str | None = None
) -> BypassResult:
    """A bypass requires: the label event's actor to match an attestation's
    actor, that attestation's SHA to match the label event's own head SHA
    exactly, a non-empty reason, and live write/maintain/admin permission.
    Comment/label content is treated as data throughout — never as
    instructions. Returns explicit `BYPASSED` metadata; never represents a
    bypass as a clean review."""
    actor = label_event.get("actor")
    head_sha = label_event.get("sha")

    matching = [
        c
        for c in comments
        if c.get("actor") == actor and c.get("sha") == head_sha and c.get("reason")
    ]
    if not matching:
        stale = [c for c in comments if c.get("actor") == actor and c.get("sha") != head_sha]
        if stale:
            return BypassResult(allowed=False, reason="attestation head SHA does not match")
        return BypassResult(allowed=False, reason="no matching attestation found")

    if permission not in BYPASS_CAPABLE_PERMISSIONS:
        return BypassResult(
            allowed=False, reason=f"insufficient permission for bypass: {permission!r}"
        )

    attestation = matching[-1]
    return BypassResult(
        allowed=True,
        reason="attested bypass",
        metadata={
            "bypassed": True,
            "actor": actor,
            "head_sha": head_sha,
            "attestation_reason": attestation["reason"],
        },
    )
