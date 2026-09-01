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

# Paths plugin-rulebook-checker's own R1-R27 rules never review, per its
# documented scope (plugin-rulebook/SKILL.md's R1 "Scope" line covers
# SKILL.md/agent/command/hook/rule files and references/*.md; R23's own
# scope note explicitly excludes README/CONTRIBUTING/CHANGELOG, mirroring
# claudemd-reviewer's exception). evals/ fixtures are test-run output, not
# plugin components, and are outside every R-rule's stated scope entirely.
# Dispatching plugin-rulebook-checker against these wastes its review
# budget on files it was never going to have an opinion on -- confirmed
# live on PR #41: a 100-path delta (33 evals/ fixtures + 5 plugin-root
# docs) caused two consecutive dispatch failures for exactly this reviewer,
# a malformed response under strain and then a hard timeout, while the
# other DELTA_VALIDATE reviewers on the same oversized scope did not fail.
_RULEBOOK_OUT_OF_SCOPE_PREFIXES = ("evals/",)
_RULEBOOK_OUT_OF_SCOPE_BASENAMES = frozenset(
    {
        "README.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "KNOWN_ISSUES.md",
        "LICENSE",
        "NOTICE",
        "INSTALLATION.md",
    }
)


def _is_plugin_or_repo_root_doc(path: str) -> bool:
    """True only for a bare repo-root file (`KNOWN_ISSUES.md`) or a file
    directly at a plugin's own root (`plugins/<name>/README.md`) -- never a
    same-named file nested inside a component directory. A security review
    of the reviewer-scope bypass (this predicate's second caller, added
    below) found that without this check, `plugins/<name>/commands/README.md`
    -- a real, invocable command file, since Claude Code loads every .md in
    a plugin's commands/ directory -- matched the same basename exclusion
    and could smuggle a component change past every reviewer."""
    parts = path.split("/")
    return len(parts) == 1 or (len(parts) == 3 and parts[0] == "plugins")


def _is_rulebook_scoped_path(path: str) -> bool:
    if path.startswith(_RULEBOOK_OUT_OF_SCOPE_PREFIXES):
        return False
    name = Path(path).name
    if name in _RULEBOOK_OUT_OF_SCOPE_BASENAMES and _is_plugin_or_repo_root_doc(path):
        return False
    return True


# Reviewer-scope-bypass eligibility uses its own, deliberately narrower
# exclusion than plugin-rulebook-checker's target-path narrowing above.
# evals/ fixtures and these three basenames are genuinely inert text with
# no dependency-graph or security signal for any reviewer to look at.
# README.md/CONTRIBUTING.md/CHANGELOG.md/INSTALLATION.md do NOT get the
# same pass here (a security review flagged this as a real gap): a
# README's install step can pipe a script to a shell, and a
# CHANGELOG/CONTRIBUTING can newly document a dependency -- exactly what
# dependency-reviewer/security-reviewer exist to catch, even though
# plugin-rulebook-checker's own R1-R27 rules never had an opinion on them.
_BYPASS_OUT_OF_SCOPE_PREFIXES = ("evals/",)
_BYPASS_OUT_OF_SCOPE_BASENAMES = frozenset({"LICENSE", "NOTICE", "KNOWN_ISSUES.md"})


def _is_bypass_scoped_path(path: str) -> bool:
    if path.startswith(_BYPASS_OUT_OF_SCOPE_PREFIXES):
        return False
    name = Path(path).name
    if name in _BYPASS_OUT_OF_SCOPE_BASENAMES and _is_plugin_or_repo_root_doc(path):
        return False
    return True


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

# The rulebook-content files a reviewer agent's own instructions Glob/Read
# live from whatever checkout it's running in -- never base-SHA-pinned the
# way the instructions text itself is. Listed once here and reused to build
# both the canonical plugins/ set and the .claude/ in-development-mirror set
# below, so the two can never drift apart by one being updated without the
# other (a security review found the .claude/ mirror copy, tracked and
# git-editable independently of the canonical copy, was getting zero
# reviewers dispatched at all when it was the only thing a PR touched --
# worse than the original gap, since even an ordinary delta dispatch never
# ran against it).
#
# Scoped to files whose consuming reviewer is actually in today's live
# CI dispatch path (DELTA_VALIDATE's baseline, or LAUNCH_AUDIT_BY_COMPONENT_TYPE's
# skill-reviewer/subagent-reviewer) -- a second security review pass also
# named references/argument-consistency.md (command-reviewer),
# references/language-rules.md (language-reviewer), and
# references/compliance-report-example.md (external-references-reviewer) as
# the same live-read pattern, but none of those three reviewers is
# currently launch-dispatched by derive_review_scope at all, so there is no
# live self-judging path through them today. Deliberately not added here;
# add them (and their consumer to LAUNCH_AUDIT_BY_COMPONENT_TYPE / the
# governance dispatch, as appropriate) together, in the same change, if
# that reviewer is ever wired into automatic dispatch.
_RULEBOOK_GOVERNANCE_RELATIVE_PATHS = (
    "SKILL.md",
    "assets/settings.json",
    "references/compact-rule-checklist.md",
    # Explicitly named as the live-read "source of truth" in
    # external-references-reviewer's own instructions, and applied
    # (never re-derived) by plugin-rulebook-checker's own Step 1.5.
    "references/external-reference-policy.md",
    # Live-read by every reviewer agent that excludes gitignored paths from
    # its own scope -- a broadened exclusion pattern here could make every
    # dispatched reviewer skip the very PR that broadened it.
    "references/gitignore-exclusion.md",
    # Controls the severity tier definitions skill-reviewer uses to grade
    # its own findings -- a sharper self-judging surface than the others
    # here, since it decides how severely a finding scores, not just what
    # gets looked at. skill-reviewer is launch-dispatched today.
    "references/size-rules.md",
    # The shared Plugin-scope/CWD-scope file-enumeration definition
    # consistency-reviewer (part of the rulebook governance dispatch
    # itself) and completeness-reviewer/scripts-reviewer/language-reviewer
    # use to decide which files are even in bounds for their own review.
    "references/plugin-file-surface.md",
)

_RULEBOOK_GOVERNANCE_ROOTS = (
    "plugins/plugin-devkit/skills/plugin-rulebook/",
    ".claude/skills/plugin-rulebook/",
)

# "Shared marketplace governance" per design's escalation conditions: a
# change to any of these always triggers full review, since their blast
# radius isn't bounded by a single plugin's own delta.
FULL_ESCALATION_PATHS = (
    *(
        root + rel
        for root in _RULEBOOK_GOVERNANCE_ROOTS
        for rel in _RULEBOOK_GOVERNANCE_RELATIVE_PATHS
    ),
    ".claude/plugin-rulebook.config.json",
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
    # drift the edit may have introduced elsewhere (R20-style). Same set for
    # every one of the 5 governance files, in both the canonical plugins/
    # copy and the .claude/ in-development mirror -- see
    # _RULEBOOK_GOVERNANCE_RELATIVE_PATHS/_RULEBOOK_GOVERNANCE_ROOTS above
    # for why a PR editing only one of these, in only one of the two
    # locations, needs the identical dispatch.
    **{
        root + rel: ("plugin-rulebook-checker", "consistency-reviewer")
        for root in _RULEBOOK_GOVERNANCE_ROOTS
        for rel in _RULEBOOK_GOVERNANCE_RELATIVE_PATHS
    },
    # Same live-read gap, for the repo-specific R23 override plugin-rulebook-checker's
    # own Step 1.4 merges on top of the plugin defaults.
    ".claude/plugin-rulebook.config.json": (
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
    """Both sides of a rename, not just the new path -- a rename FROM a
    reviewer-scoped path TO a bypass-excluded one (e.g. `skills/x/SKILL.md`
    -> a plugin-root `LICENSE`) must still count as touching the old,
    reviewer-scoped path, or the whole diff looks reviewer-empty and
    silently skips Codex even though it deletes a loadable component.
    Flagged live by the external Codex connector reviewer on this
    feature's own first PR (#50) -- `git diff --name-only`'s default
    rename detection reports only the destination, and the earlier
    `new_path or old_path` here then discarded the source entirely."""
    paths: set[str] = set()
    for cp in changes:
        if cp.new_path is not None:
            paths.add(cp.new_path)
        if cp.old_path is not None:
            paths.add(cp.old_path)
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

    # A diff touching only the gate's own code (BYPASS_INELIGIBLE_PREFIXES,
    # defined below) must still fall through to a real reviewer dispatch,
    # not just avoid the bypass flag -- a security review found that
    # forcing bypass_eligible=False alone still let mode stay "light" here
    # (no plugins/ path), which dispatches zero reviewers regardless of the
    # flag. Falling through to the delta branch below is enough on its own:
    # `_is_bypass_scoped_path` never excludes these prefixes, so
    # has_reviewer_scoped_path comes out True and the baseline three
    # dispatch for real.
    if not any(p.startswith("plugins/") for p in paths) and not any(
        p.startswith(BYPASS_INELIGIBLE_PREFIXES) for p in paths
    ):
        return ReviewScope(
            mode="light", structural_check=STRUCTURAL_CHECK_REF, validate=(), audit=(), paths=paths
        )

    audit_types = {
        LAUNCH_AUDIT_BY_COMPONENT_TYPE[component]
        for path in paths
        if (component := _component_type(path)) in LAUNCH_AUDIT_BY_COMPONENT_TYPE
    }

    # Reviewer-scope bypass: a plugins/ change whose every path is an evals/
    # fixture (see _is_bypass_scoped_path -- deliberately narrower than
    # plugin-rulebook-checker's own target-path exclusion above) has nothing
    # for the baseline reviewers to look at either. `or bool(audit_types)`
    # keeps the baseline tied to the audit set: whenever a type-specific
    # audit reviewer would dispatch, the baseline three dispatch alongside
    # it too.
    has_reviewer_scoped_path = any(_is_bypass_scoped_path(p) for p in paths) or bool(audit_types)

    return ReviewScope(
        mode="delta",
        structural_check=STRUCTURAL_CHECK_REF,
        validate=DELTA_VALIDATE if has_reviewer_scoped_path else (),
        audit=tuple(sorted(audit_types)),
        paths=paths,
    )


# Paths whose own content decides whether Codex review runs at all, or that
# feed a separate privilege/policy decision (check-pr's CODEOWNERS
# matching, the PR template, uv's own dependency resolution) -- a change to
# any of these must never be able to bypass its own review, or a diff
# touching only these (plus otherwise-bypass-eligible files) could silently
# weaken Codex review, merge-privilege checks, or the dependency supply
# chain for itself and every PR after it. `scripts/` (not just
# `scripts/marketplace_ci/`) also covers scripts/__init__.py, which
# `python -m scripts.marketplace_ci` imports before any restored module
# runs (see below); `.github/` (not just `.github/workflows/`) also covers
# `.github/pull_request_template.md` and `.github/marketplace-validators.json`.
#
# Enforced twice, not just here: derive_review_scope's own light-mode gate
# above also falls through to a real delta dispatch (DELTA_VALIDATE) for any
# path under one of these prefixes, rather than relying on this function
# alone to withhold the bypass flag with zero reviewers actually running --
# a security review found the first version of this list only did the
# latter, so the diff was never bypass-eligible but also never reviewed.
#
# Trust boundary, honestly stated: `compute-scope` restores
# `scripts/`+`pyproject.toml`+`uv.lock` from the trusted base SHA before
# scoring (see marketplace-ci.yml's `compute-scope` job), so an *unaware*
# edit to this list or `is_bypass_eligible` doesn't defeat itself. That
# restore is not an adversarial-proof boundary, and this list doesn't
# either: a same-repo PR author can edit `.github/workflows/marketplace-ci.yml`
# itself (GitHub runs a `pull_request` workflow using the PR's own copy of
# the workflow file for a same-repo PR), which is a pre-existing property
# of every check in this workflow, not something this bypass introduces or
# could close from inside `review.py`.
BYPASS_INELIGIBLE_PREFIXES = (
    ".github/",  # also covers .github/CODEOWNERS, one of 3 candidates below
    "scripts/",
    ".codex/agents/",
    ".claude/rules/",
    # The .claude/ in-development mirror of the rulebook skill is a real,
    # independently git-editable copy -- not under plugins/, so it was
    # falling through to light-mode/bypass-eligible (zero reviewers) if a PR
    # touched only it. FULL_ESCALATION_PATHS above already forces mode="full"
    # for its 5 specific governance files; this prefix is the belt-and-
    # suspenders floor for every *other* file under this directory (e.g. a
    # reference file not in that governance list), guaranteeing at least an
    # ordinary delta dispatch rather than none.
    ".claude/skills/plugin-rulebook/",
    "pyproject.toml",
    "uv.lock",
    # The other 2 of pr_policy.py's 3 _CODEOWNERS_CANDIDATES -- a PR adding
    # or editing either one changes who check_merge_rights lets merge for
    # every subsequent PR (a CODEOWNERS match is terminal: it both grants
    # merge rights by listing and denies them to a non-listed author, even
    # with write permission, never falling through to the permission
    # check), so this is exactly the kind of policy-weakening file the
    # rest of this list already exists to keep out of the bypass path.
    "CODEOWNERS",
    "docs/CODEOWNERS",
)


def is_bypass_eligible(scope: ReviewScope) -> bool:
    """True when there is nothing for any Codex reviewer to look at --
    covers today's mode="light" (no plugins/ path touched) and the new
    reviewer-scope-empty delta case above. Never true for mode="full":
    escalation (a shared-governance path, or an oversized dependency
    closure) is inherently high-risk regardless of what reviewer set it
    resolves to, including the fail-closed empty-scope gap case
    derive_review_scope itself returns when an escalation trigger has no
    defined reviewer set -- that gap must keep failing closed, never read as
    bypass-eligible. Never true either when any changed path is under
    BYPASS_INELIGIBLE_PREFIXES -- belt-and-suspenders alongside
    derive_review_scope's own light-mode gate, which is what actually
    guarantees a real reviewer set dispatches for these paths."""
    if any(p.startswith(BYPASS_INELIGIBLE_PREFIXES) for p in scope.paths):
        return False
    return scope.mode != "full" and not scope.validate and not scope.audit


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


def rebase_onto_base_absorbed(*, base_sha: str, before: str, after: str, repo: Path) -> bool:
    """True when this push absorbed new commits from the PR's base branch --
    `after` newly contains `base_sha` as an ancestor that `before` did not.
    Used to force full Codex review even when the diff's own scope would
    otherwise qualify for the reviewer-scope bypass: a rebase can change how
    already-reviewed code interacts with what the base branch now contains,
    which a bare changed-file-list diff doesn't capture. An ordinary commit
    returns False. Also returns True (fails closed) if `before` or `after`
    can't be resolved in this checkout -- notably, this is the *expected*
    outcome for a force-pushed-over `before` SHA in CI's own shallow-refs
    checkout, not a rare edge case, since the pre-push commit is generally
    unreachable there once superseded. Logs the unresolvable ref's git
    stderr for diagnosis rather than resolving silently."""

    def is_ancestor(ancestor: str, descendant: str) -> bool | None:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=repo,
            capture_output=True,
        )
        if result.returncode in (0, 1):
            return result.returncode == 0
        print(
            f"rebase_onto_base_absorbed: cannot resolve ancestry of {ancestor!r}/{descendant!r}: "
            f"{result.stderr.decode('utf-8', errors='replace').strip()}",
            file=sys.stderr,
        )
        return None

    after_has_base = is_ancestor(base_sha, after)
    before_has_base = is_ancestor(base_sha, before)
    if after_has_base is None or before_has_base is None:
        return True
    return after_has_base and not before_has_base


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

    reports: list[ReviewerReport] = []
    for name in (*scope.validate, *scope.audit):
        reviewer_scope = scope.paths
        if name == "plugin-rulebook-checker":
            # Narrow to only what R1-R27 actually reviews -- see
            # _is_rulebook_scoped_path's own comment for why. Fall back to
            # the full scope if filtering would leave nothing: a caller
            # dispatches this reviewer whenever mode requires DELTA_VALIDATE's
            # baseline regardless of whether any in-scope file happens to
            # remain, and an empty --target-paths is worse than a widened
            # (but real) one.
            scoped = tuple(p for p in scope.paths if _is_rulebook_scoped_path(p))
            reviewer_scope = scoped or scope.paths
        target_paths = ",".join(reviewer_scope)

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
