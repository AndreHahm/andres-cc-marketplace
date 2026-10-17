"""Labelled corpus for the reviewer eval (Phase 4 of #568, issue #586).

One JSON file per (PR, head) under `reviewer-eval/corpus/`, named
`pr-<pr>-<first 8 of head_sha>.json`. This module only validates and loads; scoring
reads the loaded cases. The labelling rule is in `reviewer-eval/README.md`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = 1
KINDS = ("findings", "clean")
LABELS = ("true", "false_positive", "pre_existing", "out_of_scope")
SOURCES = ("ledger", "thread", "owner")

_CASE_KEYS = {"schema_version", "pr", "head_sha", "kind", "findings", "known_issues"}
_FINDING_KEYS = {
    "id",
    "reviewer",
    "path",
    "line",
    "rule",
    "label",
    "source",
    "note",
    "known_issue",
}
_KNOWN_ISSUE_KEYS = {"id", "path", "description"}
_HEAD_SHA = re.compile(r"[0-9a-f]{40}")


class CorpusError(Exception):
    """A corpus directory or file that cannot be loaded; the message lists every problem."""


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _check_keys(item: dict, allowed: set[str], where: str) -> list[str]:
    errors = [f"{where}: unknown key {key!r}" for key in sorted(set(item) - allowed)]
    errors += [f"{where}: missing key {key!r}" for key in sorted(allowed - set(item))]
    return errors


def _non_empty_str(item: dict, key: str, where: str) -> list[str]:
    value = item.get(key)
    if isinstance(value, str) and value:
        return []
    return [f"{where}: {key} must be a non-empty string"]


def _validate_findings(case: dict, known_ids: set[str]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, finding in enumerate(case["findings"]):
        where = f"findings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{where}: must be an object")
            continue
        errors += _check_keys(finding, _FINDING_KEYS, where)
        errors += _non_empty_str(finding, "id", where)
        errors += _non_empty_str(finding, "reviewer", where)
        errors += _non_empty_str(finding, "path", where)
        finding_id = finding.get("id")
        if isinstance(finding_id, str):
            if finding_id in seen:
                errors.append(f"{where}: duplicate id {finding_id!r}")
            seen.add(finding_id)
        line = finding.get("line")
        if line is not None and not _is_positive_int(line):
            errors.append(f"{where}: line must be a positive integer or null")
        rule = finding.get("rule")
        if rule is not None and not isinstance(rule, str):
            errors.append(f"{where}: rule must be a string or null")
        if finding.get("label") not in LABELS:
            errors.append(f"{where}: label must be one of {', '.join(LABELS)}")
        if finding.get("source") not in SOURCES:
            errors.append(f"{where}: source must be one of {', '.join(SOURCES)}")
        if not isinstance(finding.get("note"), str):
            errors.append(f"{where}: note must be a string")
        link = finding.get("known_issue")
        if link is not None:
            if not isinstance(link, str):
                errors.append(f"{where}: known_issue must be a string or null")
            elif link not in known_ids:
                errors.append(f"{where}: known_issue {link!r} is not a known issue of this case")
            elif finding.get("label") != "true":
                errors.append(f"{where}: a finding linked to a known_issue must be labelled true")
    return errors


def _validate_known_issues(case: dict) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    ids: set[str] = set()
    for index, issue in enumerate(case["known_issues"]):
        where = f"known_issues[{index}]"
        if not isinstance(issue, dict):
            errors.append(f"{where}: must be an object")
            continue
        errors += _check_keys(issue, _KNOWN_ISSUE_KEYS, where)
        errors += _non_empty_str(issue, "id", where)
        errors += _non_empty_str(issue, "path", where)
        if not isinstance(issue.get("description"), str):
            errors.append(f"{where}: description must be a string")
        issue_id = issue.get("id")
        if isinstance(issue_id, str):
            if issue_id in ids:
                errors.append(f"{where}: duplicate id {issue_id!r}")
            ids.add(issue_id)
    return errors, ids


def validate_case(case: object) -> list[str]:
    """Every problem with one corpus case, or an empty list when it is valid."""
    if not isinstance(case, dict):
        return ["case must be a JSON object"]
    errors = [f"case: unknown key {key!r}" for key in sorted(set(case) - _CASE_KEYS)]
    if case.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"case: schema_version must be {SCHEMA_VERSION}")
    pr = case.get("pr")
    if not _is_positive_int(pr):
        errors.append("case: pr must be a positive integer")
    head_sha = case.get("head_sha")
    if not (isinstance(head_sha, str) and _HEAD_SHA.fullmatch(head_sha)):
        errors.append("case: head_sha must be 40 lowercase hex characters")
    kind = case.get("kind")
    if kind not in KINDS:
        errors.append(f"case: kind must be one of {', '.join(KINDS)}")
    for key in ("findings", "known_issues"):
        if not isinstance(case.get(key), list):
            errors.append(f"case: {key} must be a list")
    if errors and any("must be a list" in error for error in errors):
        return errors
    issue_errors, known_ids = _validate_known_issues(case)
    errors += issue_errors
    errors += _validate_findings(case, known_ids)
    if kind == "clean":
        if case["known_issues"]:
            errors.append("case: a clean case must have no known_issues")
        if any(isinstance(f, dict) and f.get("label") == "true" for f in case["findings"]):
            errors.append("case: a clean case cannot have a finding labelled true")
    return errors


def expected_filename(case: dict) -> str:
    return f"pr-{case['pr']}-{case['head_sha'][:8]}.json"


def load_corpus(directory: Path) -> list[dict]:
    """Every case in `directory`, in filename order. Raises `CorpusError` listing all problems."""
    directory = Path(directory)
    if not directory.is_dir():
        raise CorpusError(f"{directory}: not a directory")
    cases: list[dict] = []
    problems: list[str] = []
    for path in sorted(directory.glob("*.json")):
        try:
            case = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(f"{path.name}: cannot read as JSON ({exc})")
            continue
        errors = validate_case(case)
        if not errors and path.name != expected_filename(case):
            errors = [f"filename must be {expected_filename(case)}"]
        if errors:
            problems += [f"{path.name}: {error}" for error in errors]
        else:
            cases.append(case)
    if problems:
        raise CorpusError("\n".join(problems))
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reviewer_eval.corpus", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="check every case in a corpus directory")
    validate.add_argument("directory", nargs="?", default="reviewer-eval/corpus")
    args = parser.parse_args(argv)
    try:
        cases = load_corpus(Path(args.directory))
    except CorpusError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"{len(cases)} case{'s' if len(cases) != 1 else ''} valid in {args.directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
