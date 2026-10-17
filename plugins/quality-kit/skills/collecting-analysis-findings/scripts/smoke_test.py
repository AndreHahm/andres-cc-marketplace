#!/usr/bin/env python3
"""Smoke test for collecting-analysis-findings: adapter on fixtures, frontmatter, links, grants.

Runs the adapter in-process (no subprocess) against synthetic fixtures shaped like the real
Cloud CLI output, then checks this skill's SKILL.md and references. Exit 0 when every check
passes, 1 otherwise.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import re
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
FIXTURES = HERE / "fixtures"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def load_adapter():
    spec = importlib.util.spec_from_file_location("collect_codacy", HERE / "collect_codacy.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load collect_codacy.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["collect_codacy"] = module
    spec.loader.exec_module(module)
    return module


def run_main(
    adapter, *argv: str, stdin: str = "", stdin_bytes: bytes | None = None
) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    real_stdin = sys.stdin
    # A bytes stdin goes through a wrapper with an ASCII locale encoding, like a non-UTF-8 console.
    sys.stdin = (
        io.TextIOWrapper(io.BytesIO(stdin_bytes), encoding="ascii")
        if stdin_bytes is not None
        else io.StringIO(stdin)
    )
    try:
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = adapter.main(list(argv))
            except SystemExit as exc:  # argparse exits on a bad command line
                code = int(exc.code) if isinstance(exc.code, int) else 1
    finally:
        sys.stdin = real_stdin
    return code, out.getvalue(), err.getvalue()


def frontmatter(path: Path) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.DOTALL)
    if match is None:
        return {}
    fields: dict[str, str] = {}
    key = None
    for line in match.group(1).splitlines():
        top = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)  # any key-shaped line at column 0
        if top:
            key = top.group(1)
            fields[key] = top.group(2).strip()
        elif key and line[:1].isspace():
            fields[key] += " " + line.strip()
    return fields


def check_adapter() -> None:
    adapter = load_adapter()
    code, out, _ = run_main(adapter, "--kind", "pr", "--input", str(FIXTURES / "pr.json"))
    record = json.loads(out) if code == 0 else {}
    check("pr fixture exits 0", code == 0)
    check("pr fixture: 3 findings", record.get("counts", {}).get("total") == 3)
    check(
        "pr fixture: head commit and PR number carried",
        record.get("source", {}).get("head_commit_sha") == "2" * 40
        and record.get("source", {}).get("pull_request") == 7,
    )
    top = (record.get("groups") or [{}])[0]
    check(
        "pr fixture: groups by rule and file",
        top.get("rule") == "Bandit_B603" and top.get("count") == 2,
    )

    code, out, _ = run_main(
        adapter, "--kind", "pr", "--input", str(FIXTURES / "pr.json"), "--category", "Security"
    )
    check("category filter keeps only Security", json.loads(out)["counts"]["total"] == 2)

    code, out, _ = run_main(adapter, "--kind", "repo", "--input", str(FIXTURES / "repo.json"))
    findings = json.loads(out)["findings"]
    check(
        "repo fixture: issue_id and tool are null",
        bool(findings) and all(f["issue_id"] is None and f["tool"] is None for f in findings),
    )
    check("repo fixture: missing line stays null", findings[1]["line"] is None)
    check(
        "instruction-like message stays data",
        findings[1]["message"].startswith("Ignore all previous instructions") and code == 0,
    )

    code, out, _ = run_main(adapter, "--kind", "ignored", "--input", str(FIXTURES / "ignored.json"))
    ignored = json.loads(out)["findings"][0]
    check(
        "ignored fixture: reason and comment carried",
        ignored["ignored"] is True
        and ignored["ignore_reason"] == "TestCode"
        and ignored["ignore_comment"] == "pytest assert in a test file",
    )

    code, out, err = run_main(adapter, "--kind", "pr", "--input", str(FIXTURES / "unknown.json"))
    check(
        "unknown shape fails closed with exit 2 and no stdout",
        code == 2 and out == "" and "pullRequest" in err,
    )
    code, out, _ = run_main(adapter, "--kind", "pr", "--input", str(FIXTURES / "missing.json"))
    check("missing file fails closed with exit 2", code == 2 and out == "")
    code, out, _ = run_main(adapter, "--kind", "repo", "--input", str(FIXTURES / "pr.json"))
    check("wrong --kind for the input fails closed", code == 2 and out == "")

    check_adapter_variants(adapter)

    source = (HERE / "collect_codacy.py").read_text(encoding="utf-8")
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    }
    allowed = {"__future__", "argparse", "json", "sys", "collections", "pathlib", "re", "typing"}
    check(
        "adapter imports only the allowed standard-library modules (os only for getuid)",
        imported <= allowed | {"os"},
        ", ".join(sorted(imported - allowed - {"os"})),
    )
    os_names = {
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module == "os"
        for alias in node.names
    }
    check(
        "the only thing imported from os is getuid, and os is never imported whole",
        os_names <= {"getuid"}
        and "os"
        not in {
            a.name
            for n in ast.walk(ast.parse(source))
            if isinstance(n, ast.Import)
            for a in n.names
        },
    )
    calls = re.findall(r"\b(?:eval|exec|__import__|popen|system)\(|(?<!re\.)\bcompile\(", source)
    check(
        "adapter source has no dynamic-execution call (keyword heuristic)",
        not calls,
        ", ".join(calls),
    )


def check_adapter_variants(adapter) -> None:
    pr = json.loads((FIXTURES / "pr.json").read_text(encoding="utf-8"))

    analysing = json.loads(json.dumps(pr))
    analysing["pullRequest"]["isAnalysing"] = True
    code, out, _ = run_main(adapter, "--kind", "pr", "--input", "-", stdin=json.dumps(analysing))
    check(
        "stdin input and is_analysing true are carried",
        code == 0 and json.loads(out)["source"]["is_analysing"] is True,
    )

    path = FIXTURES / "pr.json"
    code, out, _ = run_main(adapter, "--kind", "pr", "--input", str(path), "--group-by", "file")
    groups = json.loads(out)["groups"]
    check("group-by file groups by file only", groups == [{"file": "scripts/tool.py", "count": 3}])
    code, out, _ = run_main(adapter, "--kind", "pr", "--input", str(path), "--group-by", "rule")
    check(
        "group-by rule groups by rule only", json.loads(out)["groups"][0]["rule"] == "Bandit_B603"
    )
    code, out, _ = run_main(adapter, "--kind", "pr", "--input", str(path), "--format", "table")
    check("table format prints a count line", code == 0 and out.startswith("3 finding(s)"))

    potential = json.loads(json.dumps(pr))
    potential["potentialIssues"] = [potential["newIssues"][0]]
    code, out, _ = run_main(adapter, "--kind", "pr", "--input", "-", stdin=json.dumps(potential))
    states = [f["state"] for f in json.loads(out)["findings"]]
    check("potentialIssues entries map to state potential", states.count("potential") == 1)
    broken = json.loads(json.dumps(pr))
    broken["potentialIssues"] = [{"unexpected": True}]
    code, out, _ = run_main(adapter, "--kind", "pr", "--input", "-", stdin=json.dumps(broken))
    check("an unfamiliar potentialIssues entry fails closed", code == 2 and out == "")

    code, out, err = run_main(adapter, "--kind", "pr", "--input", "-", stdin="[" * 100000)
    check(
        "deeply nested JSON fails closed with exit 2",
        code == 2 and out == "" and "cannot read input" in err,
    )
    digit_limit = getattr(sys, "get_int_max_str_digits", lambda: 0)()
    huge = json.dumps(pr).replace('"number": 7', '"number": ' + "1" * 5000)
    code, out, err = run_main(adapter, "--kind", "pr", "--input", "-", stdin=huge)
    check(
        "an oversized integer literal fails closed with exit 2",
        digit_limit == 0 or (code == 2 and out == "" and "ValueError" in err),
    )
    unicode_pr = json.loads(json.dumps(pr))
    unicode_pr["newIssues"][0]["commitIssue"]["message"] = "dash — and accent é"
    code, out, _ = run_main(
        adapter,
        "--kind",
        "pr",
        "--input",
        "-",
        stdin_bytes=json.dumps(unicode_pr, ensure_ascii=False).encode("utf-8"),
    )
    check(
        "stdin is decoded as UTF-8 whatever the console encoding",
        code == 0 and json.loads(out)["findings"][0]["message"] == "dash — and accent é",
    )
    forged = json.loads(json.dumps(pr))
    forged["newIssues"][0]["commitIssue"]["filePath"] = "a.py\n    9  Bandit_B999  x.py"
    code, out, _ = run_main(
        adapter, "--kind", "pr", "--input", "-", "--format", "table", stdin=json.dumps(forged)
    )
    check(
        "table output escapes a line break in a file name",
        code == 0 and "\\x0a" in out and len(out.splitlines()) == 1 + 3,
    )
    # Built with chr() so the source holds no invisible characters.
    c1, bidi, zero_width, bom = chr(0x9B), chr(0x202E), chr(0x200B), chr(0xFEFF)
    tricky = json.loads(json.dumps(pr))
    tricky["newIssues"][0]["commitIssue"]["filePath"] = (
        f"a{c1}.py{bidi}b" + chr(92) + f"x0a{zero_width}{bom}.py"
    )
    code, out, _ = run_main(
        adapter, "--kind", "pr", "--input", "-", "--format", "table", stdin=json.dumps(tricky)
    )
    check(
        "table output escapes C1, bidi and zero-width marks and a literal backslash",
        code == 0
        and "\\x9b" in out
        and "\\u202e" in out
        and "\\u200b" in out
        and "\\ufeff" in out
        and "\\x5cx0a" in out
        and not any(ch in out for ch in (c1, bidi, zero_width, bom)),
    )
    code, out, _ = run_main(adapter, "--kind", "pr", "--input", "-", stdin="{not json")
    check("malformed JSON fails closed with exit 2", code == 2 and out == "")
    code, out, _ = run_main(adapter, "--kind", "pr", "--input", "-", stdin="")
    check("empty input fails closed with exit 2", code == 2 and out == "")
    code, out, _ = run_main(adapter, "--kind", "bogus", "--input", "-")
    check("an invalid --kind exits 2 with nothing on stdout", code == 2 and out == "")
    code, out, _ = run_main(
        adapter, "--kind", "pr", "--input", str(path), "--category", "NoSuchCategory"
    )
    record = json.loads(out)
    check(
        "a category that matches nothing yields an empty record",
        record["counts"]["total"] == 0 and record["groups"] == [],
    )

    bad_id = json.loads(json.dumps(pr))
    bad_id["newIssues"][0]["commitIssue"]["issueId"] = "abc; rm -rf /"
    code, out, _ = run_main(adapter, "--kind", "pr", "--input", "-", stdin=json.dumps(bad_id))
    check("an issueId that is not a plain identifier fails closed", code == 2 and out == "")
    bad_id["newIssues"][0]["commitIssue"]["issueId"] = "-F"
    code, out, _ = run_main(adapter, "--kind", "pr", "--input", "-", stdin=json.dumps(bad_id))
    check("an issueId starting with a dash fails closed", code == 2 and out == "")
    code, out, err = run_main(adapter, "--kind", "pr", "--input", str(FIXTURES))
    check(
        "a directory as --input fails closed",
        code == 2 and out == "" and "not a regular file" in err,
    )
    original = adapter.MAX_INPUT_BYTES
    adapter.MAX_INPUT_BYTES = 10
    try:
        code, out, err = run_main(adapter, "--kind", "pr", "--input", "-", stdin=json.dumps(pr))
    finally:
        adapter.MAX_INPUT_BYTES = original
    check(
        "valid JSON over the size cap fails closed",
        code == 2 and out == "" and "larger than" in err,
    )

    code, out, _ = run_main(adapter, "--kind", "ignored", "--input", str(FIXTURES / "ignored.json"))
    second = json.loads(out)["findings"][1]
    check(
        "ignored item without reason or comment keeps them null",
        second["ignored"] is True
        and second["ignore_reason"] is None
        and second["ignore_comment"] is None,
    )

    check_output_guard(adapter)


def check_output_guard(adapter) -> None:
    """--output writes only inside an owned scratchpad directory, outside any git work tree."""
    pr_path = str(FIXTURES / "pr.json")
    posix = getattr(adapter, "getuid", None) is not None
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        scratch = root / "scratchpad"
        elsewhere = root / "elsewhere"
        scratch.mkdir()
        scratch.chmod(0o700)
        elsewhere.mkdir()
        target = scratch / "record.json"
        code, out, _ = run_main(
            adapter, "--kind", "pr", "--input", pr_path, "--output", str(target)
        )
        written = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {}
        check(
            "--output inside a scratchpad directory writes the record there, not to stdout",
            code == 0
            and "finding(s) written to record.json" in out
            and written.get("counts", {}).get("total") == 3,
        )
        check(
            "the temporary file is gone and the record is private to the owner",
            not (scratch / ".record.json.tmp").exists()
            and (not posix or target.stat().st_mode & 0o077 == 0),
        )
        refused = elsewhere / "record.json"
        code, out, err = run_main(
            adapter, "--kind", "pr", "--input", pr_path, "--output", str(refused)
        )
        check(
            "--output outside a scratchpad directory is refused and writes nothing",
            code == 2
            and out == ""
            and "inside a scratchpad directory" in err
            and not refused.exists(),
        )
        sneaky = scratch / ".." / "elsewhere" / "record.json"
        code, _, _ = run_main(adapter, "--kind", "pr", "--input", pr_path, "--output", str(sneaky))
        check("a .. segment cannot lead out of the scratchpad", code == 2 and not refused.exists())
        if posix:
            open_scratch = root / "open" / "scratchpad"
            open_scratch.mkdir(parents=True)
            open_scratch.chmod(0o777)
            code, _, err = run_main(
                adapter,
                "--kind",
                "pr",
                "--input",
                pr_path,
                "--output",
                str(open_scratch / "r.json"),
            )
            check(
                "a scratchpad that others can write to is refused",
                code == 2
                and "not writable by others" in err
                and not (open_scratch / "r.json").exists(),
            )
            nested = root / "private" / "scratchpad" / "public" / "scratchpad"
            nested.mkdir(parents=True)
            (root / "private" / "scratchpad").chmod(0o700)
            nested.chmod(0o777)
            code, _, err = run_main(
                adapter,
                "--kind",
                "pr",
                "--input",
                pr_path,
                "--output",
                str(nested / "r.json"),
            )
            check(
                "a world-writable scratchpad inside a private one is refused (nearest decides)",
                code == 2 and "not writable by others" in err and not (nested / "r.json").exists(),
            )
        victim = elsewhere / "victim.json"
        link = scratch / "link.json"
        try:
            link.symlink_to(victim)
        except (OSError, NotImplementedError):
            link = None  # symlinks unavailable on this platform: the check below is skipped
        if link is not None:
            code, _, err = run_main(
                adapter, "--kind", "pr", "--input", pr_path, "--output", str(link)
            )
            check(
                "--output through a symlink that leaves the scratchpad is refused",
                code == 2 and not victim.exists(),
            )
        repo_scratch = root / "repo" / "scratchpad"
        repo_scratch.mkdir(parents=True)
        repo_scratch.chmod(0o700)
        (root / "repo" / ".git").mkdir()
        code, _, err = run_main(
            adapter, "--kind", "pr", "--input", pr_path, "--output", str(repo_scratch / "r.json")
        )
        check(
            "--output inside a git work tree is refused",
            code == 2 and "git work tree" in err and not (repo_scratch / "r.json").exists(),
        )
        # The path is resolved again just before writing; a result that differs aborts the write.
        calls = []
        real_resolve = adapter._scratch_output

        def shifting(raw: str) -> Path:
            calls.append(raw)
            return (
                real_resolve(raw) if len(calls) == 1 else real_resolve(str(scratch / "other.json"))
            )

        adapter._scratch_output = shifting
        try:
            code, _, err = run_main(
                adapter, "--kind", "pr", "--input", pr_path, "--output", str(scratch / "race.json")
            )
        finally:
            adapter._scratch_output = real_resolve
        check(
            "a changed output path is caught by the re-check just before writing",
            code == 2 and "changed while" in err and not (scratch / "race.json").exists(),
        )
        subdir = scratch / "sub"
        subdir.mkdir()
        code, _, err = run_main(
            adapter, "--kind", "pr", "--input", pr_path, "--output", str(subdir)
        )
        check("--output naming a directory is refused", code == 2 and "not a directory" in err)
        previous = scratch / "previous.json"
        previous.write_text("older record", encoding="utf-8")
        code, _, _ = run_main(
            adapter,
            "--kind",
            "pr",
            "--input",
            str(FIXTURES / "unknown.json"),
            "--output",
            str(previous),
        )
        check(
            "a failing run leaves an existing output file untouched and creates none",
            code == 2
            and previous.read_text(encoding="utf-8") == "older record"
            and not (scratch / "bad.json").exists(),
        )


def check_skills() -> None:
    for skill_dir in (SKILL_DIR,):
        skill_md = skill_dir / "SKILL.md"
        fm = frontmatter(skill_md)
        check(
            f"{skill_dir.name}: frontmatter name matches directory",
            fm.get("name") == skill_dir.name,
        )
        check(f"{skill_dir.name}: description present", len(fm.get("description", "")) >= 80)
        body = skill_md.read_text(encoding="utf-8")
        refs = set(re.findall(r"`((?:references|scripts)/[A-Za-z0-9_./-]+)`", body))
        missing = sorted(r for r in refs if not (skill_dir / r).exists())
        check(f"{skill_dir.name}: referenced files exist", not missing, ", ".join(missing))

    collecting = frontmatter(SKILL_DIR / "SKILL.md").get("allowed-tools", "")
    collecting_body = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    check("allowed-tools is declared", bool(collecting.strip()))
    check("one-way dependency: collecting grants no Skill()", "Skill(" not in collecting)
    check(
        "one-way dependency: collecting never calls resolving",
        "Skill(resolving" not in collecting_body,
    )
    adapter_ref = (SKILL_DIR / "references" / "codacy-adapter.md").read_text(encoding="utf-8")
    forbidden_section = adapter_ref.split("## Forbidden", 1)[1].split("## Input shapes", 1)[0]
    flags = re.findall(r"`(-{1,2}[A-Za-z][A-Za-z-]*)`", forbidden_section) + re.findall(
        r"`(-[A-Za-z])/`?(--[A-Za-z-]+)`?", forbidden_section
    )
    flat = {f for item in flags for f in ((item,) if isinstance(item, str) else item)}
    required = {
        "--ignore-issue",
        "--unignore-issue",
        "--reanalyze",
        "--reanalyze-and-wait",
        "-F",
        "-I",
        "-R",
        "-m",
        "-y",
    }
    check(
        "forbidden list names every known write flag",
        required <= flat,
        ", ".join(sorted(required - flat)),
    )
    check(
        "allowlist regexes require a letter or digit first (no flag injection)",
        "^[A-Za-z0-9][A-Za-z0-9._-]*$" in collecting_body
        and "^[A-Za-z0-9][A-Za-z0-9._/-]*$" in collecting_body,
    )
    check(
        "collecting pre-approves no codacy command (write flags the grant cannot narrow)",
        not re.search(r"Bash\(codacy", collecting),
        collecting,
    )
    gate = collecting_body.split("**Quality gates:**", 1)[1]
    check(
        "quality gate points at the forbidden list",
        "Forbidden section of `references/codacy-adapter.md`" in gate,
    )


def guarded(name: str, run) -> None:
    """Run a group of checks; a crash inside it reads as a FAIL line, not a bare traceback."""
    try:
        run()
    except Exception as exc:  # noqa: BLE001 - any crash must surface as a failed check
        check(f"{name} ran to completion", False, f"{type(exc).__name__}: {exc}")


def main() -> int:
    guarded("adapter checks", check_adapter)
    guarded("skill checks", check_skills)
    print(f"\n{len(failures)} failure(s)" if failures else "\nall checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
