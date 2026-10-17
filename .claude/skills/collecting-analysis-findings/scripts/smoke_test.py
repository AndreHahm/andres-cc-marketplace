#!/usr/bin/env python3
"""Smoke test for the quality-kit skills: adapter behavior on fixtures, frontmatter, links, grants.

Runs the adapter in-process (no subprocess) against synthetic fixtures shaped like the real
Cloud CLI output, then checks the two SKILL.md files against each other. Exit 0 when every check
passes, 1 otherwise.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import re
import sys
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


def run_main(adapter, *argv: str, stdin: str = "") -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    real_stdin = sys.stdin
    sys.stdin = io.StringIO(stdin)
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
        top = re.match(r"^([a-z][a-z-]*):\s*(.*)$", line)
        if top:
            key = top.group(1)
            fields[key] = top.group(2).strip()
        elif key:
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
        all(f["issue_id"] is None and f["tool"] is None for f in findings),
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
        "adapter imports only the allowed standard-library modules",
        imported <= allowed,
        ", ".join(sorted(imported - allowed)),
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

    code, out, _ = run_main(adapter, "--kind", "pr", "--input", "-", stdin="[" * 100000)
    check("deeply nested JSON fails closed with exit 2", code == 2 and out == "")
    code, out, _ = run_main(
        adapter, "--kind", "pr", "--input", "-", stdin='{"a": ' + "1" * 5000 + "}"
    )
    check("an oversized integer literal fails closed with exit 2", code == 2 and out == "")
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
    code, out, _ = run_main(adapter, "--kind", "pr", "--input", str(FIXTURES))
    check("a directory as --input fails closed", code == 2 and out == "")
    original = adapter.MAX_INPUT_BYTES
    adapter.MAX_INPUT_BYTES = 10
    try:
        code, out, _ = run_main(adapter, "--kind", "pr", "--input", "-", stdin="x" * 50)
    finally:
        adapter.MAX_INPUT_BYTES = original
    check("input over the size cap fails closed", code == 2 and out == "")

    code, out, _ = run_main(adapter, "--kind", "ignored", "--input", str(FIXTURES / "ignored.json"))
    second = json.loads(out)["findings"][1]
    check(
        "ignored item without reason or comment keeps them null",
        second["ignored"] is True
        and second["ignore_reason"] is None
        and second["ignore_comment"] is None,
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


def main() -> int:
    check_adapter()
    check_skills()
    print(f"\n{len(failures)} failure(s)" if failures else "\nall checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
