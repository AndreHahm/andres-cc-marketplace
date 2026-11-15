#!/usr/bin/env python3
"""Compute a pull request's coverage tier from a coverage report and a unified diff.

The report is a coverage.py JSON report, a Cobertura XML report or an LCOV tracefile, detected
from its content (`--report-format` forces one). Report paths are matched to the diff's
repository-relative paths: an absolute path under `--root` (default: the current directory) is made
relative to it, and a path that still matches no diff file falls back to a unique suffix match on a
`/` boundary.

Patch coverage is the share of changed lines that coverage can measure and that ran. The tier comes
from the thresholds in quality-kit's `assets/qlty-coverage-tiers.yml`, overridden key by key by a
repository's `.github/coverage-tiers.yml` when it exists:

  green   >= green    informational, passes
  yellow  >= yellow   minor, passes with a warning
  orange  >= orange   major, fails
  red     below       critical, fails

A diff with no measurable changed line is green ("nothing to measure").

Usage:
  git diff --unified=0 BASE...HEAD | qlty-coverage-tier.py --coverage REPORT [--override F]
      [--defaults F] [--report-format auto|coveragepy|cobertura|lcov] [--root DIR]
      [--format text|json|markdown] [--github-annotations]

Reads files only; runs no subprocess and opens no network connection. Needs PyYAML, and defusedxml
for a Cobertura report (run it with `uv run --with pyyaml --with defusedxml` where they are not
installed).
Exit codes: 0 green or yellow; 1 orange or red; 2 invalid input (a bad report, diff or thresholds
file); 3 PyYAML or defusedxml is missing.
"""

from __future__ import annotations

import argparse
import html
import json
import posixpath
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_INPUT = 2
EXIT_NO_PACKAGE = 3

DEFAULTS = Path(__file__).resolve().parent.parent / "assets" / "qlty-coverage-tiers.yml"
TIER_KEYS = ("green", "yellow", "orange")
TOP_KEYS = {"version", "tiers"}
HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
LABELS = {
    "green": "informational",
    "yellow": "minor",
    "orange": "major",
    "red": "critical",
}
COMMENT_MARKER = "<!-- quality-kit:coverage-tier -->"
REPORT_FORMATS = ("auto", "coveragepy", "cobertura", "lcov")
DTD = re.compile(r"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)

# A report maps each file to (executed lines, measurable lines).
Report = dict[str, tuple[set[int], set[int]]]


class InputError(Exception):
    """Raised for any input this script refuses; the message is printed and the exit is 2."""


def _load_yaml(path: Path) -> Any:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        print(
            "qlty-coverage-tier: PyYAML is needed; run with `uv run --with pyyaml`",
            file=sys.stderr,
        )
        sys.exit(EXIT_NO_PACKAGE)
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise InputError(f"{path}: cannot read thresholds ({error.__class__.__name__})") from None


def _tiers(document: Any, path: Path, *, partial: bool) -> dict[str, float]:
    if not isinstance(document, dict):
        raise InputError(f"{path}: expected a mapping")
    unknown = set(document) - TOP_KEYS
    if unknown:
        raise InputError(f"{path}: unknown keys {sorted(unknown)}")
    if document.get("version", 1) != 1:
        raise InputError(f"{path}: version must be 1")
    tiers = document.get("tiers", {})
    if not isinstance(tiers, dict):
        raise InputError(f"{path}: tiers must be a mapping")
    unknown = set(tiers) - set(TIER_KEYS)
    if unknown:
        raise InputError(f"{path}: unknown tiers {sorted(unknown)}")
    if not partial and set(tiers) != set(TIER_KEYS):
        raise InputError(f"{path}: defaults must set {list(TIER_KEYS)}")
    result: dict[str, float] = {}
    for key, value in tiers.items():
        if isinstance(value, bool) or not isinstance(value, int | float) or not 0 <= value <= 100:
            raise InputError(f"{path}: tiers.{key} must be a number from 0 to 100")
        result[key] = float(value)
    return result


def thresholds(defaults: Path, override: Path | None) -> dict[str, float]:
    """Return the merged thresholds, failing closed on any malformed or out-of-order value."""
    merged = _tiers(_load_yaml(defaults), defaults, partial=False)
    if override is not None and override.exists():
        merged.update(_tiers(_load_yaml(override), override, partial=True))
    if not merged["green"] >= merged["yellow"] >= merged["orange"]:
        raise InputError("thresholds must satisfy green >= yellow >= orange")
    return merged


_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


def _unquote(target: str) -> str:
    """Decode git's C-style quoted path (`"b/q\\"t\\tb"`, octal bytes such as `\\303\\251`)."""
    if not (len(target) >= 2 and target[0] == target[-1] == '"'):
        return target
    body, out, i = target[1:-1], bytearray(), 0
    while i < len(body):
        char = body[i]
        if char != "\\":
            out += char.encode("utf-8")
            i += 1
            continue
        nxt = body[i + 1 : i + 2]
        if nxt in _ESCAPES:
            out.append(_ESCAPES[nxt])
            i += 2
        elif len(body[i + 1 : i + 4]) == 3 and all(c in "01234567" for c in body[i + 1 : i + 4]):
            out.append(int(body[i + 1 : i + 4], 8) & 0xFF)
            i += 4
        else:
            raise InputError(f"unexpected escape in diff path {target!r}")
    return out.decode("utf-8", errors="replace")


def changed_lines(diff: str) -> dict[str, set[int]]:
    """Map each file in a unified diff to the line numbers its new side adds or changes.

    Hunk bodies are read by the line counts in their @@ header, so a changed line whose content
    starts with "++ " or "-- " (the diff lines "+++ ..." and "--- ...") is content, never a header.
    """
    files: dict[str, set[int]] = {}
    current: set[int] | None = None
    line = old_left = new_left = 0
    # git ends diff lines with \n only; str.splitlines() would also split on \r, \x0c and other
    # characters a binary or text line may hold, and break the hunk counts.
    for text in diff.split("\n"):
        if old_left > 0 or new_left > 0:
            marker = text[:1]
            if marker == "+":
                new_left -= 1
                if current is not None:
                    current.add(line)
                line += 1
            elif marker == "-":
                old_left -= 1
            elif marker == " ":
                old_left -= 1
                new_left -= 1
                line += 1
            elif marker != "\\":
                raise InputError(f"diff hunk ends early before {text[:40]!r}")
            continue
        if text.startswith("+++ "):
            raw = text[4:]
            # A literal tab never sits inside git's quotes (it is escaped there), so a trailing tab
            # after a name with a space is stripped before decoding.
            target = _unquote(raw.rstrip("\t")) if raw.startswith('"') else raw.split("\t", 1)[0]
            if target == "/dev/null":
                current = None
            elif target.startswith("b/"):
                current = files.setdefault(target[2:], set())
            else:
                raise InputError(f"unexpected diff target {target!r}; use `git diff`")
            continue
        match = HUNK.match(text)
        if match:
            old_left = int(match.group(1)) if match.group(1) is not None else 1
            line = int(match.group(2))
            new_left = int(match.group(3)) if match.group(3) is not None else 1
    return files


def _add(report: Report, name: str, executed: set[int], measurable: set[int]) -> None:
    old_executed, old_measurable = report.setdefault(name, (set(), set()))
    old_executed |= executed
    old_measurable |= measurable | executed


def _lines(values: Any, path: Path, name: str) -> set[int]:
    if not isinstance(values, list) or not all(type(v) is int for v in values):
        raise InputError(f"{path}: {name!r}: line lists must hold integers")
    return set(values)


def _coveragepy(text: str, path: Path) -> Report:
    try:
        document = json.loads(text)
    except ValueError:
        raise InputError(f"{path}: not valid JSON") from None
    files = document.get("files") if isinstance(document, dict) else None
    if not isinstance(files, dict):
        raise InputError(f"{path}: not a coverage.py JSON report (no files mapping)")
    report: Report = {}
    for name, entry in files.items():
        if not isinstance(entry, dict):
            raise InputError(f"{path}: {name!r}: expected a mapping")
        executed = _lines(entry.get("executed_lines", []), path, name)
        _add(report, name, executed, _lines(entry.get("missing_lines", []), path, name))
    return report


def _cobertura(text: str, path: Path, root: PurePosixPath) -> Report:
    try:
        from defusedxml import DefusedXmlException, ElementTree
    except ImportError:
        print(
            "qlty-coverage-tier: defusedxml is needed for a Cobertura report; run with"
            " `uv run --with defusedxml`",
            file=sys.stderr,
        )
        sys.exit(EXIT_NO_PACKAGE)
    # A coverage report never needs a DTD: refusing one gives a clear message, and defusedxml
    # blocks entity expansion and external entities in any case.
    if DTD.search(text):
        raise InputError(
            f"{path}: a DTD or entity declaration is not allowed in a Cobertura report"
        )
    try:
        document = ElementTree.fromstring(text)
    except DefusedXmlException:
        raise InputError(f"{path}: entities are not allowed in a Cobertura report") from None
    except ElementTree.ParseError:
        raise InputError(f"{path}: not valid XML") from None
    if document.tag != "coverage":
        raise InputError(f"{path}: not a Cobertura report (root element is not <coverage>)")
    sources = [s.text.strip() for s in document.iter("source") if s.text and s.text.strip()]
    report: Report = {}
    for cls in document.iter("class"):
        filename = cls.get("filename")
        if not filename:
            raise InputError(f"{path}: a <class> has no filename")
        executed: set[int] = set()
        measurable: set[int] = set()
        for line in cls.iter("line"):
            try:
                number, hits = int(line.get("number", "")), int(line.get("hits", ""))
            except ValueError:
                raise InputError(
                    f"{path}: {filename!r}: a <line> needs integer number and hits"
                ) from None
            measurable.add(number)
            if hits > 0:
                executed.add(number)
        # A relative filename is relative to one of the <source> directories; the first joined path
        # that exists under the root is the file, else the filename is kept for suffix matching.
        name = filename
        if not posixpath.isabs(filename.replace("\\", "/")):
            for source in sources:
                joined = _relative(posixpath.join(source.replace("\\", "/"), filename), root)
                if not posixpath.isabs(joined) and Path(str(root), joined).is_file():
                    name = joined
                    break
        _add(report, name, executed, measurable)
    return report


def _lcov(text: str, path: Path) -> Report:
    report: Report = {}
    name: str | None = None
    executed: set[int] = set()
    measurable: set[int] = set()
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line.startswith("SF:"):
            if name is not None:
                raise InputError(f"{path}:{number}: SF before the previous record's end_of_record")
            name, executed, measurable = line[3:], set(), set()
        elif line.startswith("DA:"):
            if name is None:
                raise InputError(f"{path}:{number}: DA before SF")
            fields = line[3:].split(",")
            try:
                line_number, hits = int(fields[0]), int(fields[1])
            except (IndexError, ValueError):
                raise InputError(
                    f"{path}:{number}: DA needs a line number and a hit count"
                ) from None
            measurable.add(line_number)
            if hits > 0:
                executed.add(line_number)
        elif line == "end_of_record":
            if name is None:
                raise InputError(f"{path}:{number}: end_of_record before SF")
            _add(report, name, executed, measurable)
            name = None
    if name is not None:
        raise InputError(f"{path}: the last record has no end_of_record")
    if not report and "SF:" not in text:
        raise InputError(f"{path}: not an LCOV tracefile (no SF record)")
    return report


def _detect(text: str) -> str:
    head = text.lstrip()[:200]
    if head.startswith("{"):
        return "coveragepy"
    if head.startswith("<"):
        return "cobertura"
    if re.match(r"(TN|SF):", head):
        return "lcov"
    raise InputError("cannot tell the report format; pass --report-format")


def _relative(name: str, root: PurePosixPath) -> str:
    """Return a report path as a normalized, root-relative POSIX path where possible."""
    normal = posixpath.normpath(name.replace("\\", "/"))
    if posixpath.isabs(normal):
        try:
            return str(PurePosixPath(normal).relative_to(root))
        except ValueError:
            return normal
    return normal.removeprefix("./")


def load_report(path: Path, report_format: str = "auto", root: Path | None = None) -> Report:
    """Read a coverage report of any supported format into repository-relative paths."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise InputError(
            f"{path}: cannot read coverage report ({error.__class__.__name__})"
        ) from None
    chosen = _detect(text) if report_format == "auto" else report_format
    base = PurePosixPath(str((root or Path.cwd()).resolve()).replace("\\", "/"))
    if chosen == "cobertura":
        parsed = _cobertura(text, path, base)
    else:
        parsed = {"coveragepy": _coveragepy, "lcov": _lcov}[chosen](text, path)
    report: Report = {}
    for name, (executed, measurable) in parsed.items():
        _add(report, _relative(name, base), executed, measurable)
    return report


def _match(name: str, report: Report) -> tuple[set[int], set[int]] | None:
    """Find a diff file's report entry: an exact path, else one unique suffix match."""
    if name in report:
        return report[name]
    hits = [
        entry
        for key, entry in report.items()
        if name.endswith("/" + key) or key.endswith("/" + name)
    ]
    return hits[0] if len(hits) == 1 else None


def tier_for(percent: float | None, limits: dict[str, float]) -> str:
    """Return the tier name for a patch coverage percentage (None means nothing to measure)."""
    if percent is None or percent >= limits["green"]:
        return "green"
    if percent >= limits["yellow"]:
        return "yellow"
    if percent >= limits["orange"]:
        return "orange"
    return "red"


def evaluate(report: Report, diff: dict[str, set[int]], limits: dict[str, float]) -> dict:
    """Intersect the changed lines with the report and return the tier result."""
    rows = []
    covered_total = measurable_total = 0
    for name in sorted(diff):
        entry = _match(name, report)
        if entry is None:
            continue
        executed, measurable_lines = entry
        measurable = measurable_lines & diff[name]
        if not measurable:
            continue
        covered = measurable & executed
        covered_total += len(covered)
        measurable_total += len(measurable)
        rows.append(
            {
                "file": name,
                "covered": len(covered),
                "measurable": len(measurable),
                "missed_lines": sorted(measurable - covered),
            }
        )
    percent = round(100 * covered_total / measurable_total, 2) if measurable_total else None
    tier = tier_for(percent, limits)
    return {
        "tier": tier,
        "label": LABELS[tier],
        "passes": tier in ("green", "yellow"),
        "patch_coverage": percent,
        "covered": covered_total,
        "measurable": measurable_total,
        "thresholds": limits,
        "files": rows,
    }


def _summary(result: dict) -> str:
    percent = result["patch_coverage"]
    shown = "nothing to measure" if percent is None else f"{percent:.2f} %"
    return (
        f"Coverage tier: {result['tier']} ({result['label']}), patch coverage {shown} "
        f"({result['covered']} of {result['measurable']} changed lines)"
    )


def markdown(result: dict) -> str:
    """Render the sticky PR comment body, starting with the marker the workflow looks for."""
    limits = result["thresholds"]
    lines = [
        COMMENT_MARKER,
        f"### {_summary(result)}",
        "",
        f"Tiers on patch coverage: green ≥ {limits['green']:g} %, yellow ≥ {limits['yellow']:g} %, "
        f"orange ≥ {limits['orange']:g} %, red below. "
        "Orange and red fail this check; it is not required.",
    ]
    missed = [row for row in result["files"] if row["missed_lines"]]
    if missed:
        lines += ["", "| File | Covered | Missed lines |", "|---|---|---|"]
        for row in missed:
            spans = ", ".join(str(n) for n in row["missed_lines"][:20])
            more = " …" if len(row["missed_lines"]) > 20 else ""
            lines.append(
                f"| {_code(row['file'])} | {row['covered']}/{row['measurable']} | {spans}{more} |"
            )
    return "\n".join(lines) + "\n"


_MARKDOWN = set("|@.:*_[]#~&<>\"'")


def _code(name: str) -> str:
    """Render a file name from the PR as inert inline code in the comment.

    HTML-escaped, with the characters GitHub still reads as markdown inside <code> (table
    separator, mention, autolink, emphasis, link) as entities, so no name can end the cell, start
    a link or tag, or mention anyone.
    """
    # One pass over the raw name, so no entity is ever encoded twice (every entity holds a "#").
    escaped = "".join(
        f"&#{ord(c)};" if c in _MARKDOWN or ord(c) < 32 or ord(c) == 127 else html.escape(c)
        for c in name
    )
    return "<code>" + escaped + "</code>"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--coverage",
        type=Path,
        required=True,
        help="coverage.py JSON, Cobertura XML or LCOV report",
    )
    parser.add_argument("--report-format", choices=REPORT_FORMATS, default="auto")
    parser.add_argument(
        "--root", type=Path, help="repository root for absolute report paths (default: .)"
    )
    parser.add_argument("--diff", type=Path, help="unified diff file (default: stdin)")
    parser.add_argument("--defaults", type=Path, default=DEFAULTS)
    parser.add_argument("--override", type=Path, default=Path(".github/coverage-tiers.yml"))
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    parser.add_argument("--github-annotations", action="store_true")
    args = parser.parse_args(argv)
    try:
        limits = thresholds(args.defaults, args.override)
        try:
            # git diff --text prints a binary or non-UTF-8 file's raw bytes; they are replaced, not
            # refused: such files are in no report, so evaluate() skips them.
            raw = args.diff.read_bytes() if args.diff else sys.stdin.buffer.read()
            diff_text = raw.decode("utf-8", errors="replace")
        except OSError as error:
            raise InputError(f"cannot read the diff ({error.__class__.__name__})") from None
        report = load_report(args.coverage, args.report_format, args.root)
        result = evaluate(report, changed_lines(diff_text), limits)
    except InputError as error:
        print(f"qlty-coverage-tier: {error}", file=sys.stderr)
        return EXIT_INPUT
    except Exception as error:  # noqa: BLE001  # any other crash is an input the script cannot judge
        # Exit 2, not Python's default 1: the workflow reads 1 as an orange or red tier.
        print(f"qlty-coverage-tier: unexpected {error.__class__.__name__}", file=sys.stderr)
        return EXIT_INPUT
    if args.format == "json":
        print(json.dumps(result, indent=2))
    elif args.format == "markdown":
        print(markdown(result), end="")
    else:
        print(_summary(result))
    if args.github_annotations and result["tier"] != "green":
        level = "warning" if result["tier"] == "yellow" else "error"
        print(f"::{level} title=Coverage tier {result['tier']}::{_summary(result)}")
    return EXIT_PASS if result["passes"] else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
