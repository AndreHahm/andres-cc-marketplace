#!/usr/bin/env python3
"""Summarize a finished mutmut 3.8.1 run from its own result files, failing closed.

Reads every `<file>.py.meta` under the mutants directory (JSON; `exit_code_by_key` holds one exit
code per mutant) and maps each code to a status with the table from mutmut 3.8.1's `stats.py`.
It then cross-checks its counts against `mutmut-cicd-stats.json` (written by
`mutmut export-cicd-stats`) and refuses the run when they disagree or when a code is not in the
table, so a changed mutmut never produces a silently wrong summary.

Status classes:
  killed        killed, caught by type check
  survived      the selected tests passed with the mutant in place
  timeout       counted against the score, listed separately
  not measured  no tests, skipped, not checked: no visible test ran the mutant; never a survivor
  unclear       suspicious, segfault, check was interrupted by user

score = killed / (killed + survived + timeout); none when that sum is 0.

Usage:
  qlty-mutation-parse.py [--mutants DIR] [--module PATH] [--label NAME]
      [--format text|json|markdown]

`--module` (the mutated file's path, such as scripts/x/y.py) reads only
`<mutants>/<module>.meta`, the file mutmut wrote for that module. Without it, every `.meta` under
the directory is read, which also picks up `.meta` files that `also_copy` brought along (test
fixtures, for example); a duplicate key is refused either way.

Reads files only; runs no subprocess and opens no network connection.
Exit codes: 0 summary written (survivors never fail it); 2 invalid or inconsistent input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_INPUT = 2

MUTMUT_VERSION = "3.8.1"
# mutmut 3.8.1 stats.status_by_exit_code; None means "not checked".
STATUS_BY_EXIT_CODE: dict[int | None, str] = {
    1: "killed",
    3: "killed",
    0: "survived",
    5: "no tests",
    2: "check was interrupted by user",
    None: "not checked",
    33: "no tests",
    34: "skipped",
    35: "suspicious",
    36: "timeout",
    37: "caught by type check",
    -24: "timeout",
    24: "timeout",
    152: "timeout",
    255: "timeout",
    -11: "segfault",
    -9: "segfault",
}
CLASS_BY_STATUS = {
    "killed": "killed",
    "caught by type check": "killed",
    "survived": "survived",
    "timeout": "timeout",
    "no tests": "not_measured",
    "skipped": "not_measured",
    "not checked": "not_measured",
    "suspicious": "unclear",
    "segfault": "unclear",
    "check was interrupted by user": "unclear",
}
CLASSES = ("killed", "survived", "timeout", "not_measured", "unclear")
STATS_FILE = "mutmut-cicd-stats.json"
# The keys mutmut 3.8.1's save_cicd_stats writes. "not checked" and "caught by type check" have
# no key of their own and are covered by total; "killed" there excludes "caught by type check".
STATS_KEYS = frozenset(
    {
        "killed",
        "survived",
        "total",
        "no_tests",
        "skipped",
        "suspicious",
        "timeout",
        "check_was_interrupted_by_user",
        "segfault",
    }
)
# mutmut 3.8.1 keys (utils/format_utils.py): "<module>.x_<function>__mutmut_<n>" or
# "<module>.xǁ<Class>ǁ<method>__mutmut_<n>". "ǁ" is a Unicode letter, so the class and method
# parts exclude it explicitly.
KEY = re.compile(
    r"^(?P<module>[\w.]+?)\.x(?:ǁ(?P<cls>[^ǁ.]+)ǁ(?P<meth>[^ǁ.]+?)|_(?P<func>[^ǁ.]+?))__mutmut_\d+$"
)


class InputError(Exception):
    """The mutants directory is missing, malformed, or disagrees with mutmut's own totals."""


def load_exit_codes(mutants: Path, module: str | None = None) -> dict[str, int | None]:
    if module is not None:
        if module.startswith(("/", "-")) or ".." in module.split("/") or not module.endswith(".py"):
            raise InputError(
                f"--module must be a relative .py path inside the run tree: {module!r}"
            )
        meta = mutants / f"{module}.meta"
        if not meta.is_file():
            raise InputError(f"{meta} is missing; was {module} mutated in this run?")
        metas = [meta]
    else:
        metas = sorted(mutants.rglob("*.meta"))
    if not metas:
        raise InputError(f"no .meta file under {mutants}; run `mutmut run` first")
    codes: dict[str, int | None] = {}
    for meta in metas:
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputError(f"{meta}: not readable JSON ({exc})") from exc
        by_key = data.get("exit_code_by_key") if isinstance(data, dict) else None
        if not isinstance(by_key, dict):
            raise InputError(f"{meta}: no exit_code_by_key object")
        for key, code in by_key.items():
            if code is not None and (isinstance(code, bool) or not isinstance(code, int)):
                raise InputError(f"{meta}: exit code for {key!r} is not an integer: {code!r}")
            if code not in STATUS_BY_EXIT_CODE:
                raise InputError(
                    f"{meta}: exit code {code} for {key!r} is not in mutmut {MUTMUT_VERSION}'s "
                    "table; "
                    "check the mutmut version before trusting any result"
                )
            if key in codes:
                raise InputError(f"{meta}: mutant {key!r} appears in more than one .meta file")
            codes[key] = code
    return codes


def load_stats(mutants: Path) -> dict[str, int]:
    path = mutants / STATS_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InputError(f"{path} is missing; run `mutmut export-cicd-stats` first") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"{path}: not readable JSON ({exc})") from exc
    if not isinstance(data, dict) or not all(
        isinstance(v, int) and not isinstance(v, bool) for v in data.values()
    ):
        raise InputError(f"{path}: expected an object of integer counts")
    return data


def cross_check(status_counts: dict[str, int], total: int, stats: dict[str, int]) -> None:
    if set(stats) != STATS_KEYS:
        raise InputError(
            f"{STATS_FILE} keys {sorted(stats)} are not mutmut {MUTMUT_VERSION}'s "
            f"{sorted(STATS_KEYS)}; "
            "check the mutmut version before trusting any result"
        )
    expected = {status.replace(" ", "_"): n for status, n in status_counts.items()}
    expected["total"] = total
    mismatches = [
        f"{name}: .meta files {expected.get(name, 0)}, {STATS_FILE} {value}"
        for name, value in sorted(stats.items())
        if expected.get(name, 0) != value
    ]
    if mismatches:
        raise InputError("counts disagree with mutmut's own totals: " + "; ".join(mismatches))


def describe(key: str) -> dict[str, Any]:
    match = KEY.match(key)
    if not match:
        return {"key": key, "module": None, "function": None}
    func = f"{match['cls']}.{match['meth']}" if match["cls"] else match["func"]
    return {"key": key, "module": match["module"], "function": func}


def summarize(mutants: Path, label: str | None, module: str | None = None) -> dict[str, Any]:
    codes = load_exit_codes(mutants, module)
    stats = load_stats(mutants)
    status_counts: dict[str, int] = {status: 0 for status in CLASS_BY_STATUS}
    by_class: dict[str, list[str]] = {name: [] for name in CLASSES}
    for key, code in sorted(codes.items()):
        status = STATUS_BY_EXIT_CODE[code]
        status_counts[status] += 1
        by_class[CLASS_BY_STATUS[status]].append(key)
    cross_check(status_counts, len(codes), stats)
    counts = {name: len(keys) for name, keys in by_class.items()}
    scored = counts["killed"] + counts["survived"] + counts["timeout"]
    return {
        "label": label,
        "mutmut_version": MUTMUT_VERSION,
        "total": len(codes),
        "counts": counts,
        "status_counts": {k: v for k, v in status_counts.items() if v},
        "score": round(counts["killed"] / scored, 4) if scored else None,
        "survivors": [describe(k) for k in by_class["survived"]],
        "timeouts": [describe(k) for k in by_class["timeout"]],
        "not_measured": [describe(k) for k in by_class["not_measured"]],
        "unclear": [
            {**describe(k), "status": STATUS_BY_EXIT_CODE[codes[k]]} for k in by_class["unclear"]
        ],
    }


def score_text(summary: dict[str, Any]) -> str:
    score = summary["score"]
    return "n/a (nothing measured)" if score is None else f"{score:.1%}"


def render_text(summary: dict[str, Any]) -> str:
    c = summary["counts"]
    lines = [
        f"{summary['label'] or 'mutation run'}: score {score_text(summary)}",
        f"  total {summary['total']}, killed {c['killed']}, survived {c['survived']}, "
        f"timeout {c['timeout']}, "
        f"not measured {c['not_measured']}, unclear {c['unclear']}",
    ]
    lines += [f"  survived: {s['key']}" for s in summary["survivors"]]
    lines += [f"  timeout: {s['key']}" for s in summary["timeouts"]]
    lines += [f"  unclear ({s['status']}): {s['key']}" for s in summary["unclear"]]
    return "\n".join(lines) + "\n"


def render_markdown(summary: dict[str, Any]) -> str:
    c = summary["counts"]
    lines = [
        f"### Mutation testing: {summary['label'] or 'run'}",
        "",
        "| Score | Total | Killed | Survived | Timeout | Not measured | Unclear |",
        "|---|---|---|---|---|---|---|",
        f"| {score_text(summary)} | {summary['total']} | {c['killed']} | {c['survived']} "
        f"| {c['timeout']} "
        f"| {c['not_measured']} | {c['unclear']} |",
        "",
        "Not measured means no selected test ran the mutant; it is not a survivor. "
        "Survivors and timeouts never fail this job.",
    ]
    if summary["survivors"]:
        lines += ["", "<details><summary>Survivors</summary>", ""]
        lines += [f"- `{s['key']}`" for s in summary["survivors"]]
        lines += ["", "</details>"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--mutants", type=Path, default=Path("mutants"), help="mutmut's output directory"
    )
    parser.add_argument("--module", help="read only <mutants>/<MODULE>.meta (a relative .py path)")
    parser.add_argument("--label", help="a name for the run, such as the module")
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    args = parser.parse_args(argv)
    try:
        summary = summarize(args.mutants, args.label, args.module)
    except InputError as exc:
        print(f"qlty-mutation-parse: {exc}", file=sys.stderr)
        return EXIT_INPUT
    if args.format == "json":
        sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    elif args.format == "markdown":
        sys.stdout.write(render_markdown(summary))
    else:
        sys.stdout.write(render_text(summary))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
