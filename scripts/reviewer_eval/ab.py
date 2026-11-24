"""Compare two versions of the reviewer prompts on one head (issue #862, related #586).

An arm is a commit: `dispatch_reviewers` reads each reviewer's prompt from `.codex/agents/` at the
SHA it is given, and that SHA is separate from the diff's line ranges, so passing the arm's commit
changes the prompt and nothing else. Nothing in the reviewed checkout is executed: the dispatcher
and the bridge are this checkout's. `plan` and `report` make no model call; `run` does, and only
with the exact number of calls the plan printed.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

from scripts.marketplace_ci import __main__ as ci
from scripts.marketplace_ci import review, review_contract, review_verifiers
from scripts.marketplace_ci.git_state import ChangedPath
from scripts.reviewer_eval.corpus import _HEAD_SHA, CorpusError, load_corpus
from scripts.reviewer_eval.score import _rate, stability

MAX_REPEATS = 10
_ROOT = Path(__file__).resolve().parents[2]
_ARM_NAME = re.compile(r"[a-z][a-z0-9-]{0,30}")


class AbError(ValueError):
    """The experiment cannot run as asked."""


@dataclass(frozen=True)
class Plan:
    repo: Path
    head_sha: str
    base_sha: str
    arms: dict[str, str]
    repeats: int
    scope: review.ReviewScope
    changed: tuple[ChangedPath, ...]
    reviewers: tuple[str, ...]
    prompts: dict[str, dict[str, str]]  # reviewer -> arm -> sha256 of its prompt
    outcomes: tuple[review_verifiers.VerifierOutcome, ...]

    @property
    def calls(self) -> int:
        return len(self.reviewers) * len(self.arms) * self.repeats

    @property
    def identical_prompts(self) -> tuple[str, ...]:
        return tuple(n for n in self.reviewers if len(set(self.prompts[n].values())) == 1)

    def manifest(self) -> dict:
        return {
            "schema_version": 1,
            "head_sha": self.head_sha,
            "base_sha": self.base_sha,
            "arms": self.arms,
            "repeats": self.repeats,
            "planned_calls": self.calls,
            "reviewed_paths": list(self.scope.paths),
            "prompts": self.prompts,
            "identical_prompts": list(self.identical_prompts),
            "configured_model": _configured_model(),
            "pinned_cli_version": review_contract.CODEX_CLI_VERSION,
        }


def _configured_model() -> str:
    model = os.environ.get(review_contract.MODEL_VARIABLE, "").strip()
    if not model:
        raise AbError(f"{review_contract.MODEL_VARIABLE} is not set; a run must record its model")
    return model


def _git_ok(repo: Path, *args: str) -> bool:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True).returncode == 0


def _prompt_digest(repo: Path, reviewer: str, arm: str, sha: str, scratch: Path) -> str:
    try:
        out = review.prepare_reviewer_instruction(
            reviewer, base_sha=sha, out=scratch / f"{arm}-{reviewer}.txt", repo=repo
        )
    except SystemExit as exc:
        raise AbError(f"arm {arm!r} has no usable prompt for {reviewer} at {sha}") from exc
    return hashlib.sha256(out.read_bytes()).hexdigest()


def make_plan(
    *, repo: Path, head_sha: str, base_sha: str, arms: dict[str, str], repeats: int
) -> Plan:
    """Check every input and work out what a run would do, without a model call."""
    _configured_model()
    if len(arms) != 2:
        raise AbError("give exactly two arms")
    for name in arms:
        if not _ARM_NAME.fullmatch(name):
            raise AbError(f"arm name {name!r} must match {_ARM_NAME.pattern}")
    for label, sha in (("head", head_sha), ("base", base_sha), *arms.items()):
        if not _HEAD_SHA.fullmatch(sha):
            raise AbError(f"{label}: {sha!r} must be 40 lowercase hex characters")
    if not 1 <= repeats <= MAX_REPEATS:
        raise AbError(f"repeats must be 1 to {MAX_REPEATS}")
    if ci._git_out(repo, "rev-parse", "HEAD") != head_sha:
        raise AbError(f"{head_sha} is not what is checked out in {repo}")
    # Not `_git_out`: its None means a failed command as well as no output.
    try:
        dirty = review._run_git(repo, "status", "--porcelain") != b""
    except RuntimeError as exc:
        raise AbError(f"git status failed in {repo}") from exc
    if dirty:
        raise AbError(f"the checkout in {repo} is not clean")
    if not _git_ok(repo, "merge-base", "--is-ancestor", base_sha, head_sha):
        raise AbError(f"base {base_sha} is not an ancestor of head {head_sha}")
    try:
        delta = review.compute_pr_delta(repo, base_sha)
        changed = review.collapse_identical_mirrors(repo, delta, base_sha)
    except review.PrDeltaError as exc:
        raise AbError(str(exc)) from exc
    # As CI scopes a later run on a PR: CI's exclusions, no first-run escalation.
    scope = review.derive_review_scope(
        review.exclude_from_ci_review(repo, changed, base_sha), {}, first_run=False
    )
    reviewers = tuple(dict.fromkeys((*scope.validate, *scope.audit)))
    if not reviewers:
        raise AbError("this head starts no reviewer")
    unsafe = [p for p in scope.paths if not review._BRIEFING_SAFE_PATH.fullmatch(p)]
    if unsafe:
        raise AbError(f"the reviewer bridge does not accept the path {unsafe[0]!r}")
    # Here, before a call is paid for, so a verifier that cannot run costs nothing.
    try:
        structural = review.run_delta_structural_checks(repo, tuple(changed))
        outcomes = review_verifiers.run_verifiers(repo, changed, base_sha, structural=structural)
    except Exception as exc:  # fail closed, as run-codex-review does
        raise AbError(f"script verifier failed: {exc!r}") from exc
    with tempfile.TemporaryDirectory(prefix="reviewer-ab-") as scratch:
        prompts = {
            name: {
                arm: _prompt_digest(repo, name, arm, sha, Path(scratch))
                for arm, sha in arms.items()
            }
            for name in reviewers
        }
    return Plan(
        repo=repo,
        head_sha=head_sha,
        base_sha=base_sha,
        arms=dict(arms),
        repeats=repeats,
        scope=scope,
        changed=tuple(changed),
        reviewers=reviewers,
        prompts=prompts,
        outcomes=tuple(outcomes),
    )


@contextmanager
def _own_bridge() -> Generator[None]:
    """Point the dispatcher at this checkout's bridge. It launches `repo / <constant>`, and joining
    an absolute path gives that path, so the reviewed head's bridge is never run. A test pins it."""
    relative = review.BRIDGE_INVOKE_RELATIVE_PATH
    review.BRIDGE_INVOKE_RELATIVE_PATH = _ROOT / relative
    try:
        yield
    finally:
        review.BRIDGE_INVOKE_RELATIVE_PATH = relative


def _run_once(plan: Plan, arm: str, raw: Path) -> dict:
    """One run of every reviewer with `arm`'s prompts, gated as `run-codex-review` gates it. The
    reports go to `raw` first: a failure in the gating must not lose calls already paid for."""
    exceptions = review_contract.load_exceptions(review_contract.EXCEPTIONS_PATH)
    changed_paths = review._changed_path_set(plan.changed)
    ranges = review.compute_changed_line_ranges(plan.repo, plan.base_sha)
    with _own_bridge():
        reports = review.dispatch_reviewers(
            plan.scope,
            base_sha=plan.arms[arm],
            repo=plan.repo,
            changed_ranges=ranges,
            changed_paths=changed_paths,
            exceptions=exceptions,
            # No retries: the planned number is then also the most dispatches this run can make (one
            # dispatch is a Codex session, which makes several model requests).
            max_timeout_retries=0,
            max_empty_retries=0,
        )
    _write(raw, {"reports": [asdict(r) for r in reports]})
    validated: list[review.ReviewResult] = []
    failed: dict[str, str] = {}
    for report in reports:
        if report.status != "completed" or report.output is None:
            failed[report.reviewer] = report.error or "no output"
            continue
        try:
            result = review.validate_review_output(report.output)
        except review.ReviewOutputError as exc:
            failed[report.reviewer] = f"invalid output: {exc}"
            continue
        validated.append(review.relative_citations(result, plan.repo))
    validated = list(review.mark_symlinked(validated, plan.repo))
    models = tuple(validated)  # before the script results, whose names are not reviewers
    validated.extend(
        review.ReviewResult(reviewer=o.name, verdict="script", findings=o.findings)
        for o in plan.outcomes
    )
    coverage = review_verifiers.script_coverage(plan.repo, plan.outcomes)

    def gate(results: Sequence[review.ReviewResult]) -> tuple[list[dict], bool]:
        findings = review.aggregate_findings(results, coverage)
        blocking, in_diff, scoped = ci._diff_scope(
            findings, plan.repo, plan.base_sha, changed_paths, (ranges,), exceptions, coverage
        )
        dicts = [
            ci._finding_to_dict(
                f,
                None if in_diff is None else f in in_diff,
                f in blocking,
                review.gate_decision(
                    f,
                    in_diff=in_diff is None or f in in_diff,
                    exceptions=exceptions,
                    coverage=coverage,
                ),
            )
            for f in findings
        ]
        return dicts, scoped

    findings, diff_scoped = gate(validated)
    provenance = ci._run_provenance(plan.repo, plan.base_sha, reports)
    provenance["head_sha"] = plan.head_sha  # a merge commit's head is itself here, not its parent
    return {
        "arm": arm,
        "arm_sha": plan.arms[arm],
        "reviewed_paths": list(plan.scope.paths),
        "reviewers": [r.reviewer for r in reports if r.reviewer not in failed],
        "failed_reviewers": failed,
        "provenance": provenance,
        "diff_scoped": diff_scoped,
        "findings": findings,
        # Each reviewer gated alone. The merged list above gives every reporter of a finding the
        # highest severity among them, which would credit one reviewer with another's rating.
        "by_reviewer": {r.reviewer: gate([r])[0] for r in models},
    }


def _write(path: Path, data: dict) -> None:
    """Redacted: these files hold model text and are uploaded from a public repository."""
    path.parent.mkdir(parents=True, exist_ok=True)
    redacted = review._redact_json_values(data)
    path.write_text(json.dumps(redacted, indent=2) + "\n", encoding="utf-8")


def run_experiment(plan: Plan, out: Path) -> int:
    """Run every repeat, old and new taking turns so drift over time favors neither arm. Returns 1
    when any reviewer failed. Stops after a run in which all did: the rest would only cost more."""
    if out.resolve().is_relative_to(plan.repo.resolve()):
        raise AbError(f"{out} is inside the reviewed checkout")
    try:
        out.mkdir(parents=True)
    except FileExistsError as exc:
        raise AbError(f"{out} already exists") from exc
    _write(out / "manifest.json", plan.manifest())
    status = 0
    for repeat in range(1, plan.repeats + 1):
        for arm in plan.arms:
            result = _run_once(plan, arm, out / arm / "raw" / f"run{repeat}.json")
            _write(out / arm / f"run{repeat}.json", result)
            for name, error in result["failed_reviewers"].items():
                print(f"{arm} run {repeat}: {name} failed: {error}", file=sys.stderr)
                status = 1
            if not result["reviewers"]:
                print("every reviewer of this run failed; stopping", file=sys.stderr)
                return 1
    return status


def _finding_key(finding: dict) -> tuple:
    return finding["rule"], finding["path"], finding["line"]


def _reported_by(result: dict, reviewer: str) -> list[dict]:
    return result["by_reviewer"].get(reviewer, [])


def _label_of(finding: dict, reviewer: str, labels: dict[tuple, list[tuple]]) -> str | None:
    """The corpus label of `finding`, or None when there is none or the candidates disagree. A label
    with a rule applies to that rule only; one without a rule to any finding on its line."""
    key = (reviewer, finding["path"], finding["line"])
    found = {label for rule, label in labels.get(key, ()) if rule in (None, finding["rule"])}
    return found.pop() if len(found) == 1 else None


def _arm_summary(
    reviewer: str, results: list[dict], labels: dict[tuple, list[tuple]], planned: int
) -> dict:
    runs = [r for r in results if reviewer in r["reviewers"]]
    sets = [
        frozenset((f["path"], f["line"]) for f in _reported_by(r, reviewer) if f["blocking"])
        for r in runs
    ]
    per_run: list[int] = []
    reported: Counter[tuple] = Counter()
    blocked: Counter[tuple] = Counter()
    severities: dict[tuple, Counter[str]] = {}
    judged = correct = 0
    for result in runs:
        mine = _reported_by(result, reviewer)
        per_run.append(sum(f["blocking"] for f in mine))
        for finding in mine:
            key = _finding_key(finding)
            severities.setdefault(key, Counter())[finding["severity"]] += 1
            label = _label_of(finding, reviewer, labels)
            judged += label is not None
            correct += label == "true"
        # Once per run, however often a run repeats a key.
        reported.update({_finding_key(f) for f in mine})
        blocked.update({_finding_key(f) for f in mine if f["blocking"]})
    agreement = stability(sets)
    return {
        "runs": len(runs),
        "failed": len(results) - len(runs),
        # Stopped early, or lost after the calls (raw/ may still hold the reports).
        "missing": planned - len(results),
        "blocking_per_run": per_run,
        "min": min(per_run, default=None),
        "median": statistics.median(per_run) if per_run else None,
        "max": max(per_run, default=None),
        "agree": agreement["agree"] if runs else None,
        "stable": agreement["stable"],
        "labelled": judged,
        "precision": _rate(correct, judged),
        "findings": [
            {
                "rule": key[0],
                "path": key[1],
                "line": key[2],
                "severities": dict(severities[key]),
                "reported": count,
                "blocking": blocked[key],
                "runs": len(runs),
            }
            for key, count in reported.most_common()
        ],
    }


def build_report(out: Path, cases: Sequence[dict]) -> dict:
    """Per reviewer and arm: the spread of blocking findings over the runs. A run the reviewer
    failed in is counted in `failed`, never as a run without findings."""
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    labels: dict[tuple, list[tuple]] = {}
    for case in cases:
        if case["head_sha"] == manifest["head_sha"]:
            for f in case["findings"]:
                key = (f["reviewer"], f["path"], f["line"])
                labels.setdefault(key, []).append((f["rule"], f["label"]))
    results = {
        arm: [
            json.loads(path.read_text(encoding="utf-8"))
            for n in range(1, manifest["repeats"] + 1)
            if (path := out / arm / f"run{n}.json").is_file()
        ]
        for arm in manifest["arms"]
    }
    for arm, sha in manifest["arms"].items():
        if any(r["arm_sha"] != sha for r in results[arm]):
            raise AbError(f"{out / arm} holds a run of another arm commit")
    return {
        "manifest": manifest,
        "reviewers": {
            name: {
                arm: _arm_summary(name, results[arm], labels, manifest["repeats"])
                for arm in manifest["arms"]
            }
            for name in manifest["prompts"]
        },
    }


def _cell(value: object) -> str:
    """Model text is data: no markup, link, reference, table break or line break."""
    text = html.escape(" ".join(str(value).split()), quote=False)
    text = text.replace("#", "&#35;")  # first: the entities below contain one
    for char in "\\`*_[]|@:.$~":
        text = text.replace(char, f"&#{ord(char)};")
    return text


def render_markdown(report: dict) -> str:
    manifest = report["manifest"]
    lines = [
        f"Head `{manifest['head_sha']}`, base `{manifest['base_sha']}`, "
        f"{manifest['repeats']} repeats per arm, {manifest['planned_calls']} planned dispatches.",
        "",
        "Counts of what was observed, not a significance test: a few repeats cannot separate a "
        "prompt's effect from run-to-run variation.",
        "",
        "| Reviewer | Arm | Runs | Failed | Missing | Blocking | Median | Agree | Precision |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name, arms in report["reviewers"].items():
        for arm, s in arms.items():
            precision = "-" if s["precision"] is None else f"{s['precision']:.2f}/{s['labelled']}"
            counts = ", ".join(map(str, s["blocking_per_run"])) or "-"
            cells = (
                name, arm, s["runs"], s["failed"], s["missing"], counts,
                "-" if s["median"] is None else s["median"],
                "-" if s["agree"] is None else s["agree"], precision,
            )  # fmt: skip
            lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")
    if manifest["identical_prompts"]:
        same = ", ".join(_cell(n) for n in manifest["identical_prompts"])
        lines += ["", f"Same prompt in both arms (not a comparison): {same}."]
    lines += [
        "",
        "| Reviewer | Arm | Finding | Severities | Reported | Blocking |",
        "|---|---|---|---|---|---|",
    ]
    for name, arms in report["reviewers"].items():
        for arm, s in arms.items():
            for f in s["findings"]:
                severities = ", ".join(f"{k} {v}" for k, v in f["severities"].items())
                cells = (
                    name, arm, f"{f['rule']} {f['path']}:{f['line']}", severities,
                    f"{f['reported']} of {f['runs']}", f"{f['blocking']} of {f['runs']}",
                )  # fmt: skip
                lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")
    return "\n".join(lines) + "\n"


def _parse_arms(values: list[str]) -> dict[str, str]:
    arms: dict[str, str] = {}
    for value in values:
        name, _, sha = value.partition("=")
        if name in arms:
            raise AbError(f"arm {name!r} is given twice")
        arms[name] = sha
    return arms


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reviewer_eval.ab", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run"):
        sub = commands.add_parser(name)
        sub.add_argument("--repo", required=True, type=Path, help="checkout of --head")
        sub.add_argument("--head", required=True)
        sub.add_argument("--base", required=True, help="the delta is base...head")
        sub.add_argument("--arm", required=True, action="append", metavar="NAME=SHA")
        sub.add_argument("--repeats", required=True, type=int)
        if name == "run":
            sub.add_argument("--approved-calls", required=True, type=int)
            sub.add_argument("--out", required=True, type=Path)
    sub = commands.add_parser("report")
    sub.add_argument("out", type=Path)
    sub.add_argument("--corpus", type=Path, default=Path("reviewer-eval/corpus"))
    sub.add_argument("--markdown", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "report":
            report = build_report(args.out, load_corpus(args.corpus))
            print(render_markdown(report) if args.markdown else json.dumps(report, indent=2))
            return 0
        plan = make_plan(
            repo=args.repo.resolve(),
            head_sha=args.head,
            base_sha=args.base,
            arms=_parse_arms(args.arm),
            repeats=args.repeats,
        )
        if args.command == "plan":
            print(json.dumps(plan.manifest(), indent=2))
            return 0
        if args.approved_calls != plan.calls:
            raise AbError(
                f"{args.approved_calls} calls were approved but this run makes {plan.calls}"
            )
        return run_experiment(plan, args.out)
    except (AbError, CorpusError) as exc:
        print(exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
