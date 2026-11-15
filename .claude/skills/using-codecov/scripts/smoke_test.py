#!/usr/bin/env python3
"""Smoke test for using-codecov: both plugin-root scripts on synthetic inputs, offline.

Loads `scripts/qlty-coverage-tier.py` (plugin root) in-process and checks the diff parser, the
tier boundaries, the three report formats (coverage.py JSON, Cobertura XML, LCOV) and their path
matching, the threshold merge and its fail-closed refusals, and the exit codes. Loads
`scripts/qlty-codecov-read.py` with its HTTP layer replaced (no network) and checks argument
validation, the projection, the error mapping, the redirect refusal and that the token never
reaches the output. Checks SKILL.md's grants against the scripts. Needs PyYAML, as the
tier script does; run it with `uv run --with pyyaml` where PyYAML is not installed. Exit 0 when
every check passes, 1 otherwise.
"""

from __future__ import annotations

import email.message
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parents[2]
TIER_SCRIPT = PLUGIN_ROOT / "scripts" / "qlty-coverage-tier.py"
READ_SCRIPT = PLUGIN_ROOT / "scripts" / "qlty-codecov-read.py"
SKILL = HERE.parent / "SKILL.md"
TOKEN = "smoke-token-must-not-leak-0123456789"
_SCRATCH = tempfile.TemporaryDirectory()
SCRATCH = Path(_SCRATCH.name)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(name: str, text: str) -> Path:
    path = SCRATCH / name
    path.write_text(text, encoding="utf-8")
    return path


def run(tier, *argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = tier.main(list(argv))
    return code, out.getvalue(), err.getvalue()


# Ten changed lines in a.py (1-10), of which lines 1-8 are measurable; b.py is not in the report.
REPORT = {
    "meta": {"version": "7.17.0"},
    "files": {
        "a.py": {"executed_lines": [1, 2, 3, 4, 5, 6], "missing_lines": [7, 8]},
        "c.py": {"executed_lines": [1], "missing_lines": [2]},
    },
}
DIFF = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -0,0 +1,10 @@
+one
+two
+three
+four
+five
+six
+seven
+eight
+nine
+ten
diff --git a/b.py b/b.py
--- /dev/null
+++ b/b.py
@@ -0,0 +1,2 @@
+x
+y
diff --git a/gone.py b/gone.py
--- a/gone.py
+++ /dev/null
@@ -1,2 +0,0 @@
-x
-y
"""


def check_diff_parser(tier) -> None:
    files = tier.changed_lines(DIFF)
    check("diff: added lines map to new-side numbers", files.get("a.py") == set(range(1, 11)))
    check("diff: a new file is read", files.get("b.py") == {1, 2})
    check("diff: a deleted file has no entry", "gone.py" not in files)
    context = """--- a/c.py
+++ b/c.py
@@ -1,3 +1,4 @@
 keep
+added
 keep
-removed
+changed
"""
    check(
        "diff: context lines advance, removed lines do not",
        tier.changed_lines(context) == {"c.py": {2, 4}},
    )
    tricky = "--- a/n.md\n+++ b/n.md\n@@ -1,2 +1,3 @@\n x\n+++ b/evil.py\n+++ added\n---- gone\n"
    check(
        "diff: content lines starting with '++ ' or '-- ' stay content, not headers",
        tier.changed_lines(tricky) == {"n.md": {2, 3}},
        repr(tier.changed_lines(tricky)),
    )
    try:
        tier.changed_lines("--- a/t.py\n+++ b/t.py\n@@ -0,0 +1,3 @@\n+a\ndiff --git a/u b/u\n")
        check("diff: a hunk shorter than its header is refused", False, "accepted")
    except tier.InputError:
        check("diff: a hunk shorter than its header is refused", True)
    binary = SCRATCH / "binary.diff"
    binary.write_bytes(
        b"--- a/a.py\n+++ b/a.py\n@@ -0,0 +1,2 @@\n+one\n+two\n"
        b"--- a/i.png\n+++ b/i.png\n@@ -0,0 +1 @@\n+\x89PNG\xff\xfe\n"
    )
    report = write("binary.json", json.dumps(REPORT))
    code, out, err = run(
        tier,
        "--coverage",
        str(report),
        "--diff",
        str(binary),
        "--override",
        str(SCRATCH / "none.yml"),
        "--format",
        "json",
    )
    check(
        "diff: binary bytes in a --text diff are tolerated (the file is skipped)",
        code == 0 and json.loads(out)["measurable"] == 2,
        f"{code} {err}",
    )
    quoted = (
        '--- "a/q\\"t\\tb\\\\\\303\\251.py"\n'
        '+++ "b/q\\"t\\tb\\\\\\303\\251.py"\n'
        "@@ -0,0 +1 @@\n+a\n"
        "--- a/plain \u00e9.py\t\n+++ b/plain \u00e9.py\t\n@@ -0,0 +1 @@\n+a\n"
        '--- "a/sp \\303\\251.py"\t\n+++ "b/sp \\303\\251.py"\t\n@@ -0,0 +1 @@\n+a\n'
    )
    names = set(tier.changed_lines(quoted))
    check(
        "diff: a quoted path (escapes, octal bytes) and a tab-suffixed path decode",
        names == {'q"t\tb\\\u00e9.py', "plain \u00e9.py", "sp \u00e9.py"},
        repr(names),
    )
    check(
        "diff: a decoded newline cannot end the comment row",
        "\n" not in tier._code("a\nb.py") and "&#10;" in tier._code("a\nb.py"),
    )
    try:
        tier.changed_lines("--- x\n+++ x\n@@ -0,0 +1 @@\n+a\n")
        check("diff: a non-git target is refused", False, "no error")
    except tier.InputError:
        check("diff: a non-git target is refused", True)


def check_tiers(tier) -> None:
    limits = {"green": 80.0, "yellow": 70.0, "orange": 50.0}
    cases = [
        (None, "green"),
        (100, "green"),
        (80, "green"),
        (79.99, "yellow"),
        (70, "yellow"),
        (69.99, "orange"),
        (50, "orange"),
        (49.99, "red"),
        (0, "red"),
    ]
    for percent, expected in cases:
        check(f"tier: {percent} is {expected}", tier.tier_for(percent, limits) == expected)
    report = tier.load_report(write("tiers.json", json.dumps(REPORT)), root=SCRATCH)
    result = tier.evaluate(report, tier.changed_lines(DIFF), limits)
    check(
        "evaluate: 6 of 8 measurable lines is 75 % yellow, and it passes",
        (result["patch_coverage"], result["tier"], result["passes"]) == (75.0, "yellow", True),
        json.dumps(result),
    )
    check("evaluate: missed lines are listed", result["files"][0]["missed_lines"] == [7, 8])
    check(
        "evaluate: a file outside the report is skipped",
        [r["file"] for r in result["files"]] == ["a.py"],
    )


def check_thresholds(tier) -> None:
    defaults = tier.DEFAULTS
    check("defaults: the shipped file exists", defaults.is_file())
    check(
        "defaults: 80 / 70 / 50",
        tier.thresholds(defaults, None) == {"green": 80.0, "yellow": 70.0, "orange": 50.0},
    )
    override = write("override.yml", "tiers:\n  green: 90\n")
    check(
        "override: a partial override keeps the other defaults",
        tier.thresholds(defaults, override) == {"green": 90.0, "yellow": 70.0, "orange": 50.0},
    )
    check(
        "override: a missing override file is ignored",
        tier.thresholds(defaults, SCRATCH / "none.yml")["green"] == 80.0,
    )
    refused = {
        "unknown top-level key": "colour: red\n",
        "unknown tier": "tiers:\n  purple: 10\n",
        "value above 100": "tiers:\n  green: 101\n",
        "boolean value": "tiers:\n  green: true\n",
        "string value": "tiers:\n  green: '80'\n",
        "out of order": "tiers:\n  orange: 75\n",
        "wrong version": "version: 2\n",
        "not a mapping": "- 80\n",
        "invalid YAML": "tiers: [\n",
    }
    for name, text in refused.items():
        path = write(f"bad-{len(name)}.yml", text)
        try:
            tier.thresholds(defaults, path)
            check(f"override: {name} is refused", False, "accepted")
        except tier.InputError:
            check(f"override: {name} is refused", True)
    partial_defaults = write("partial-defaults.yml", "tiers:\n  green: 80\n")
    try:
        tier.thresholds(partial_defaults, None)
        check("defaults: a file missing a tier is refused", False, "accepted")
    except tier.InputError:
        check("defaults: a file missing a tier is refused", True)


def refused(tier, name: str, step, needle: str) -> None:
    try:
        step()
        check(name, False, "accepted")
    except tier.InputError as error:
        check(name, needle in str(error), str(error))


def check_formats(tier) -> None:
    """The same a.py coverage as REPORT, written as Cobertura and as LCOV, gives the same tier."""
    limits = {"green": 80.0, "yellow": 70.0, "orange": 50.0}
    diff = tier.changed_lines(DIFF)
    root = SCRATCH / "repo"
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "a.py").write_text("x\n", encoding="utf-8")
    hits = "".join(f'<line number="{n}" hits="{1 if n <= 6 else 0}"/>' for n in range(1, 9))
    cobertura = (
        '<?xml version="1.0" ?><coverage><sources><source>/elsewhere</source>'
        f"<source>{root}</source></sources><packages><package><classes>"
        f'<class filename="src/a.py"><lines>{hits}</lines></class>'
        "</classes></package></packages></coverage>"
    )
    path = write("coverage.xml", cobertura)
    report = tier.load_report(path, root=root)
    check(
        "cobertura: auto-detected, filename joined with the source that exists",
        "src/a.py" in report,
        str(report),
    )
    src_diff = {"src/a.py": diff["a.py"]}
    result = tier.evaluate(report, src_diff, limits)
    check(
        "cobertura: 6 of 8 is 75 % yellow",
        (result["patch_coverage"], result["tier"]) == (75.0, "yellow"),
        json.dumps(result),
    )
    check(
        "cobertura: forced format reads the same",
        tier.load_report(path, "cobertura", root) == report,
    )
    refused(
        tier,
        "cobertura: a DTD is refused",
        lambda: tier.load_report(
            write("dtd.xml", '<?xml version="1.0"?><!DOCTYPE c [<!ENTITY x "y">]><coverage/>'),
            root=root,
        ),
        "DTD",
    )
    refused(
        tier,
        "cobertura: another root element is refused",
        lambda: tier.load_report(write("other.xml", "<report/>"), root=root),
        "not a Cobertura",
    )
    refused(
        tier,
        "cobertura: a non-integer hit count is refused",
        lambda: tier.load_report(
            write(
                "hits.xml",
                '<coverage><class filename="a.py"><line number="1" hits="x"/></class></coverage>',
            ),
            root=root,
        ),
        "integer",
    )

    da = "".join(f"DA:{n},{1 if n <= 6 else 0}\n" for n in range(1, 9))
    lcov = write("lcov.info", f"TN:\nSF:{root}/src/a.py\n{da}end_of_record\n")
    report = tier.load_report(lcov, root=root)
    check(
        "lcov: auto-detected, an absolute path under the root is made relative",
        "src/a.py" in report,
        str(report),
    )
    result = tier.evaluate(report, src_diff, limits)
    check(
        "lcov: 6 of 8 is 75 % yellow",
        (result["patch_coverage"], result["tier"]) == (75.0, "yellow"),
        json.dumps(result),
    )
    refused(
        tier,
        "lcov: DA before SF is refused",
        lambda: tier.load_report(write("bad1.info", "TN:\nDA:1,1\n"), "lcov", root),
        "DA before SF",
    )
    refused(
        tier,
        "lcov: a missing end_of_record is refused",
        lambda: tier.load_report(write("bad2.info", "SF:a.py\nDA:1,1\n"), "lcov", root),
        "end_of_record",
    )
    refused(
        tier,
        "lcov: a malformed DA is refused",
        lambda: tier.load_report(
            write("bad3.info", "SF:a.py\nDA:x\nend_of_record\n"), "lcov", root
        ),
        "DA needs",
    )

    # Suffix matching: a path outside the root still matches one diff file, never two.
    outside = {"/other/runner/src/a.py": ({1}, {1, 2})}
    check(
        "match: a unique suffix matches",
        tier.evaluate(outside, {"src/a.py": {1, 2}}, limits)["measurable"] == 2,
    )
    twice = {"x/a.py": ({1}, {1}), "y/a.py": ({1}, {1})}
    check(
        "match: an ambiguous suffix matches nothing",
        tier.evaluate(twice, {"a.py": {1}}, limits)["measurable"] == 0,
    )
    check(
        "match: no partial-name match",
        tier.evaluate({"ba.py": ({1}, {1})}, {"a.py": {1}}, limits)["measurable"] == 0,
    )
    refused(
        tier,
        "detect: an unknown format is refused",
        lambda: tier.load_report(write("unknown.txt", "hello"), root=root),
        "--report-format",
    )


def check_main(tier) -> None:
    report = write("coverage.json", json.dumps(REPORT))
    diff = write("change.diff", DIFF)
    none = str(SCRATCH / "no-override.yml")
    code, out, _ = run(
        tier,
        "--coverage",
        str(report),
        "--diff",
        str(diff),
        "--override",
        none,
        "--github-annotations",
    )
    check(
        "main: yellow exits 0 with a warning annotation",
        code == 0 and "::warning title=Coverage tier yellow::" in out,
        out,
    )
    strict = write("strict.yml", "tiers:\n  green: 95\n  yellow: 90\n  orange: 80\n")
    code, out, _ = run(
        tier,
        "--coverage",
        str(report),
        "--diff",
        str(diff),
        "--override",
        str(strict),
        "--github-annotations",
    )
    check(
        "main: red exits 1 with an error annotation",
        code == 1 and "::error title=Coverage tier red::" in out,
        out,
    )
    code, out, _ = run(
        tier,
        "--coverage",
        str(report),
        "--diff",
        str(diff),
        "--override",
        none,
        "--format",
        "markdown",
    )
    check(
        "main: markdown starts with the sticky-comment marker",
        out.startswith(tier.COMMENT_MARKER),
        out[:80],
    )
    check(
        "main: markdown lists the missed lines",
        "| <code>a&#46;py</code> | 6/8 | 7, 8 |" in out,
        out,
    )
    hostile = tier.markdown(
        {
            **json.loads(
                run(
                    tier,
                    "--coverage",
                    str(report),
                    "--diff",
                    str(diff),
                    "--override",
                    none,
                    "--format",
                    "json",
                )[1]
            ),
            "files": [
                {"file": "x`|@org/team<b>.py", "covered": 0, "measurable": 1, "missed_lines": [1]}
            ],
        }
    )
    check(
        "main: a hostile file name cannot break the cell, mention or tag",
        "@org" not in hostile
        and "<b>" not in hostile
        and "x`&#124;&#64;org/team&#60;b&#62;&#46;py" in hostile
        and "&amp;#" not in hostile
        and "www.example" not in tier._code("www.example.com_x*.py")
        and "#123" not in tier._code("owner/repo#123.py"),
        hostile,
    )
    deep = write("deep.json", "[" * 100000 + "]" * 100000)
    code, _, err = run(tier, "--coverage", str(deep), "--diff", str(diff), "--override", none)
    check("main: a crash (deep JSON) exits 2, not 1", code == 2, f"{code} {err}")
    code, out, _ = run(
        tier, "--coverage", str(report), "--diff", str(diff), "--override", none, "--format", "json"
    )
    check("main: json output parses", code == 0 and json.loads(out)["tier"] == "yellow")
    bad = write("bad.json", "{}")
    code, _, err = run(tier, "--coverage", str(bad), "--diff", str(diff), "--override", none)
    check(
        "main: a report with no files mapping exits 2", code == 2 and "no files mapping" in err, err
    )
    code, _, err = run(
        tier, "--coverage", str(SCRATCH / "absent.json"), "--diff", str(diff), "--override", none
    )
    check("main: a missing report exits 2", code == 2, err)


class _Response:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def read(self, limit: int = -1) -> bytes:
        return self.body


class _Opener:
    """Stands in for urllib's opener: records the request, then answers or raises."""

    def __init__(self, answer) -> None:
        self.answer = answer
        self.requests: list = []

    def open(self, request, timeout: float):
        self.requests.append(request)
        if isinstance(self.answer, Exception):
            raise self.answer
        return _Response(json.dumps(self.answer).encode())


def _http_error(code: int, detail: str) -> urllib.error.HTTPError:
    body = io.BytesIO(json.dumps({"detail": detail}).encode())
    return urllib.error.HTTPError(
        "https://api.codecov.io/x", code, "x", email.message.Message(), body
    )


def read_with(read, answer, *argv: str) -> tuple[int, str, str, _Opener]:
    opener = _Opener(answer)
    original = read.urllib.request.build_opener
    read.urllib.request.build_opener = lambda *handlers: opener
    try:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = read.main(list(argv))
    finally:
        read.urllib.request.build_opener = original
    return code, out.getvalue(), err.getvalue(), opener


def check_read(read) -> None:
    base = ("--owner", "pallets", "--repo", "flask")
    pull = {
        "pullid": 12,
        "title": "secret title",
        "author": {"username": "someone"},
        "state": "open",
        "ci_passed": True,
        "updatestamp": "2026-11-15T00:00:00Z",
        "base_totals": {"coverage": 90.0, "files": 3},
        "head_totals": {"coverage": 91.0, "files": 3},
        "patch": {"coverage": 75.0, "hits": 3, "misses": 1, "partials": 0},
    }
    code, out, _, opener = read_with(read, pull, "pull", *base, "--pull", "12")
    shown = json.loads(out) if code == 0 else {}
    check(
        "read: pull projects the patch totals", shown.get("patch", {}).get("coverage") == 75.0, out
    )
    check(
        "read: pull drops author and title", "someone" not in out and "secret title" not in out, out
    )
    check(
        "read: pull reads the fixed endpoint",
        opener.requests[0].full_url
        == "https://api.codecov.io/api/v2/github/pallets/repos/flask/pulls/12/",
        opener.requests[0].full_url,
    )
    for name, argv in [
        ("an owner with a slash", ("totals", "--owner", "a/b", "--repo", "r", "--branch", "main")),
        ("a short SHA", ("totals", *base, "--sha", "abc1234")),
        ("a PR number of 0", ("pull", *base, "--pull", "0")),
        ("totals with both branch and SHA", ("totals", *base, "--branch", "m", "--sha", "a" * 40)),
        ("repo with a branch", ("repo", *base, "--branch", "main")),
    ]:
        code, _, _, opener = read_with(read, {}, *argv)
        check(f"read: {name} exits 2 before any request", code == 2 and not opener.requests)
    for name, error, expected in [
        ("401 maps to exit 4", _http_error(401, "Invalid token."), 4),
        (
            "a no-report 404 maps to exit 5",
            _http_error(404, "No coverage report found for commit"),
            5,
        ),
        ("another 404 maps to exit 1", _http_error(404, "Not found."), 1),
        ("a timeout maps to exit 1", TimeoutError(), 1),
    ]:
        code, _, err, _ = read_with(read, error, "totals", *base, "--branch", "main")
        check(f"read: {name}", code == expected, f"{code} {err}")
    code, _, _, _ = read_with(read, ["not", "an", "object"], "repo", *base)
    check("read: an unexpected shape exits 2", code == 2)
    try:
        read._NoRedirect().redirect_request(
            None, None, 302, "Found", {}, "https://elsewhere.example/"
        )
        check("read: a redirect is refused", False, "followed")
    except read.ReadError as error:
        check("read: a redirect is refused", error.code == 1)
    os.environ[read.TOKEN_ENV] = TOKEN
    try:
        code, out, err, opener = read_with(read, _http_error(401, "Invalid token."), "repo", *base)
        sent = opener.requests[0].unredirected_hdrs.get("Authorization")
        check("read: the token is sent as an unredirected bearer header", sent == f"Bearer {TOKEN}")
        check("read: the token never reaches stdout or stderr", TOKEN not in out + err)
    finally:
        del os.environ[read.TOKEN_ENV]
    code, _, _, opener = read_with(read, {"name": "flask"}, "repo", *base)
    check(
        "read: no token, no Authorization header",
        code == 0 and "Authorization" not in opener.requests[0].unredirected_hdrs,
    )


def check_skill() -> None:
    text = SKILL.read_text(encoding="utf-8")
    grants = re.search(r"^allowed-tools: (.+)$", text, re.MULTILINE)
    scripts = re.findall(
        r"\$\{CLAUDE_PLUGIN_ROOT\}/(scripts/[\w.-]+)", grants.group(1) if grants else ""
    )
    check(
        "skill: grants exactly the two plugin-root scripts",
        sorted(scripts) == ["scripts/qlty-codecov-read.py", "scripts/qlty-coverage-tier.py"],
        str(scripts),
    )
    check("skill: every granted script exists", all((PLUGIN_ROOT / s).is_file() for s in scripts))
    refs = re.findall(r"`(references/[\w.-]+\.md)`", text)
    check("skill: the Reference Guide names the three references", len(set(refs)) == 3, str(refs))
    for ref in refs:
        check(f"skill: {ref} exists", (HERE.parent / ref).is_file())


def guarded(name: str, step) -> None:
    """Run a group of checks; a crash inside it reads as a FAIL line, not a bare traceback."""
    try:
        step()
    except Exception as error:  # noqa: BLE001  # report any crash as a failed group
        check(f"{name} ran without crashing", False, f"{error.__class__.__name__}: {error}")


def main() -> int:
    try:
        import yaml  # noqa: F401  # type: ignore[import-untyped]
    except ImportError:
        print("SKIP: PyYAML is not installed; run with `uv run --with pyyaml`")
        return 1
    tier = load(TIER_SCRIPT, "qlty_coverage_tier")
    guarded("diff parser", lambda: check_diff_parser(tier))
    guarded("tiers", lambda: check_tiers(tier))
    guarded("formats", lambda: check_formats(tier))
    guarded("thresholds", lambda: check_thresholds(tier))
    guarded("main", lambda: check_main(tier))
    read = load(READ_SCRIPT, "qlty_codecov_read")
    guarded("read wrapper", lambda: check_read(read))
    guarded("skill", check_skill)
    print(f"\n{'FAILED' if failures else 'OK'}: {len(failures)} failing check(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
