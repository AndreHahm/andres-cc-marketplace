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

# Full mode, governance-path trigger: a small, fixed reviewer set targeted at
# the changed governance file itself and its direct consumers -- never a
# marketplace-wide fan-out (unbounded cost). Keyed by the exact
# FULL_ESCALATION_PATHS entry that triggered escalation; if a change touches
# more than one, the union of their reviewer sets is dispatched.
FULL_MODE_GOVERNANCE_REVIEWERS: dict[str, tuple[str, ...]] = {
    # The rulebook's own correctness, plus a check for stale duplicate-fact
    # drift the edit may have introduced elsewhere (R20-style).
    "plugins/plugin-devkit/skills/plugin-rulebook/SKILL.md": (
        "plugin-rulebook-checker",
        "consistency-reviewer",
    ),
    # Manifest/registration structural correctness -- not a rule-compliance
    # sweep, since these files aren't rulebook-scoped components themselves.
    ".claude-plugin/marketplace.json": ("plugin-validator",),
    ".claude/marketplace-sync.json": ("plugin-validator",),
}


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

    triggering_governance_paths = [p for p in paths if p in FULL_ESCALATION_PATHS]

    closure: set[str] = set(paths)
    for path in paths:
        closure.update(dependency_index.get(path, ()))
    closure_overflow = len(closure) > dependency_closure_limit

    if triggering_governance_paths or closure_overflow:
        # A large dependency closure is "delta, but big" -- not a different
        # kind of risk -- so both triggers reuse delta's own scoping, over
        # the escalated path set (the full closure, when that's what
        # triggered escalation; otherwise the raw diff).
        #
        # Escalation is additive, never a replacement: DELTA_VALIDATE's own
        # baseline is always included, so a governance-path or
        # closure-overflow trigger can never dispatch *fewer* reviewers than
        # the equivalent non-escalated delta scope would have for the same
        # raw diff -- an earlier version of this function returned only the
        # governance-specific set, letting an author touch a governance path
        # alongside an unrelated risky change to strip delta's own baseline
        # reviewers (security-reviewer, dependency-reviewer) off the diff.
        # See the "escalation is never a subset of delta" test below.
        scoped_paths = closure if closure_overflow else set(paths)
        audit_types = {
            LAUNCH_AUDIT_BY_COMPONENT_TYPE[component]
            for p in scoped_paths
            if (component := _component_type(p)) in LAUNCH_AUDIT_BY_COMPONENT_TYPE
        }
        governance_reviewers = {
            name
            for p in triggering_governance_paths
            for name in FULL_MODE_GOVERNANCE_REVIEWERS.get(p, ())
        }
        if any(p not in FULL_MODE_GOVERNANCE_REVIEWERS for p in triggering_governance_paths):
            # Invariant violation: a path is in FULL_ESCALATION_PATHS but has
            # no entry in FULL_MODE_GOVERNANCE_REVIEWERS. Fail closed rather
            # than silently dispatching only DELTA_VALIDATE for a governance
            # path whose own targeted reviewer was never actually added --
            # this is exactly the gap run-codex-review's own defensive guard
            # exists to catch, so route it there deliberately instead of
            # raising a bare KeyError before that guard ever runs.
            return ReviewScope(
                mode="full",
                structural_check=STRUCTURAL_CHECK_REF,
                validate=(),
                audit=(),
                paths=paths,
            )
        validate = tuple(sorted(set(DELTA_VALIDATE) | governance_reviewers))
        return ReviewScope(
            mode="full",
            structural_check=STRUCTURAL_CHECK_REF,
            validate=validate,
            audit=tuple(sorted(audit_types)),
            paths=tuple(sorted(scoped_paths)),
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

# The envelope's own severity enum is lowercase (codex-review-bridge/references/
# envelope-schema.md); Finding.severity stays capitalized internally so
# aggregate_findings/blocking checks below don't need to change.
_ENVELOPE_SEVERITY_TO_CANONICAL = {"critical": "Critical", "major": "Major", "minor": "Minor"}

# Matches the single reviewer envelope bridge-invoke.mjs's dispatch_reviewers()
# call actually returns per dispatch (codex-review-bridge/references/
# envelope-schema.md) -- NOT a whole-run coverage summary. There is no
# mode/reviewed_paths/reviewers/coverage_confirmed concept at this layer: a
# single reviewer's own response can't report which OTHER reviewers ran.
# run-codex-review builds that whole-run payload itself, directly from
# ReviewScope and the ReviewerReport list dispatch_reviewers() returns.
_REQUIRED_TOP_KEYS = {
    "contract_version",
    "dispatch",
    "provenance",
    "findings",
    "verdict",
    "inspection_limits",
}
_REQUIRED_DISPATCH_KEYS = {"id", "reviewer", "backend", "target_paths"}
_REQUIRED_FINDING_KEYS = {
    "id",
    "severity",
    "axis",
    "location",
    "evidence",
    "finding",
    "fix",
    "confidence",
}

# Strips a trailing ":line" or ":line:col" suffix off a finding's `location`
# -- mirrors bridge-invoke.mjs's own locateInSemanticScope regex exactly, so
# the two layers agree on where the path ends and the line number begins.
_LOCATION_LINE_SUFFIX = re.compile(r":(\d+)(?::\d+)?$")


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
    reviewer: str
    verdict: str
    findings: tuple[Finding, ...]

    @property
    def blocking(self) -> bool:
        return any(f.severity in ("Critical", "Major") for f in self.findings)


def _split_location(location: str) -> tuple[str, int | None]:
    match = _LOCATION_LINE_SUFFIX.search(location)
    if not match:
        return location, None
    return location[: match.start()], int(match.group(1))


def validate_review_output(data: dict) -> ReviewResult:
    """Validate a single reviewer's canonical findings envelope -- the exact
    shape codex-review-bridge's bridge-invoke.mjs returns from one
    dispatch_reviewers() call, per codex-review-bridge/references/
    envelope-schema.md. Called once per ReviewerReport in
    _handle_run_codex_review; that caller assembles the whole-run
    mode/reviewed_paths/reviewers payload itself and does not read those
    fields from this function's return value."""
    missing_top = _REQUIRED_TOP_KEYS - set(data)
    if missing_top:
        raise ReviewOutputError(f"missing required field(s): {sorted(missing_top)}")

    dispatch = data["dispatch"]
    if not isinstance(dispatch, dict):
        raise ReviewOutputError("'dispatch' must be an object")
    missing_dispatch = _REQUIRED_DISPATCH_KEYS - set(dispatch)
    if missing_dispatch:
        raise ReviewOutputError(f"dispatch missing required field(s): {sorted(missing_dispatch)}")
    reviewer = dispatch["reviewer"]

    findings: list[Finding] = []
    for raw in data["findings"]:
        missing_finding = _REQUIRED_FINDING_KEYS - set(raw)
        if missing_finding:
            raise ReviewOutputError(f"finding missing required field(s): {sorted(missing_finding)}")
        severity = _ENVELOPE_SEVERITY_TO_CANONICAL.get(raw["severity"])
        if severity is None:
            raise ReviewOutputError(f"unknown severity: {raw['severity']!r}")
        path, line = _split_location(raw["location"])
        findings.append(
            Finding(
                reviewer=reviewer,
                severity=severity,
                rule=raw["axis"],
                path=path,
                evidence=raw["evidence"],
                remediation=raw["fix"],
                line=line,
            )
        )

    return ReviewResult(reviewer=reviewer, verdict=data["verdict"], findings=tuple(findings))


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
