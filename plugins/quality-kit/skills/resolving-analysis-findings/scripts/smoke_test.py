#!/usr/bin/env python3
"""Smoke test for resolving-analysis-findings: structure, grants and decision-rule invariants.

This skill is prose plus one small head-read script, so the test runs that script against a fake
`gh` and checks what can drift: frontmatter,
every referenced file, the tool grants against what the body uses, the five-rung ladder and the
decision-rights table, the one-way dependency on collecting-analysis-findings, and that the inline
suppression syntax is the same in this skill's references, docs/ci.md and the git-kit scripts it
documents. Checks that need the repository are skipped, not failed, when the plugin runs elsewhere.
Exit 0 when every check passes, 1 otherwise.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
COLLECTING = SKILL_DIR.parent / "collecting-analysis-findings"
ALLOWED_FIELDS = {"name", "description", "argument-hint", "allowed-tools"}

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def skip(name: str, why: str) -> None:
    print(f"SKIP: {name} -- {why}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    fields: dict[str, str] = {}
    key = None
    for line in (match.group(1) if match else "").splitlines():
        top = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)  # any key-shaped line at column 0
        if top:
            key = top.group(1)
            fields[key] = top.group(2).strip()
        elif key and line[:1].isspace():
            fields[key] += " " + line.strip()
    return fields


def find_repo_root() -> Path | None:
    for parent in HERE.parents:
        if (
            (parent / "docs" / "ci.md").is_file()
            and (parent / "plugins" / "git-kit").is_dir()
            and (parent / "plugins" / "quality-kit").is_dir()
            and (parent / ".claude-plugin" / "marketplace.json").is_file()
        ):
            return parent
    return None


def check_structure(text: str, fm: dict[str, str], body: str) -> None:
    check("frontmatter name matches directory", fm.get("name") == SKILL_DIR.name)
    check("description present", len(fm.get("description", "")) >= 80)
    extra = sorted(set(fm) - ALLOWED_FIELDS)
    check("frontmatter uses only allowed fields", not extra, ", ".join(extra))
    for heading in (
        "## Quick Start",
        "## When to Use",
        "## When NOT to Use",
        "## Testing & Validation",
        "## Reference Guide",
    ):
        check(
            f"section present: {heading}",
            re.search(rf"^{re.escape(heading)}$", text, re.MULTILINE) is not None,
        )

    refs = set(re.findall(r"`(references/[A-Za-z0-9_.-]+)`", body))
    missing = sorted(r for r in refs if not (SKILL_DIR / r).is_file())
    check("referenced files exist", not missing, ", ".join(missing))
    on_disk = {f"references/{p.name}" for p in (SKILL_DIR / "references").glob("*.md")}
    check("every reference file is referenced", on_disk <= refs, ", ".join(sorted(on_disk - refs)))


def check_grants(fm: dict[str, str], body: str) -> None:
    grants = fm.get("allowed-tools", "")
    check("grants the collecting skill", "Skill(collecting-analysis-findings)" in grants)
    check("grants are declared", bool(grants.strip()))
    check(
        "does not grant AskUserQuestion or Write",
        not re.search(r"\b(AskUserQuestion|Write)\b", grants),
    )
    check(
        "grants only the pinned head read and the issue-state wrapper form in Bash"
        " (no gh, codacy or sonar command)",
        re.findall(r"(?<![\w(])Bash(?:\([^)]*\))?", grants)
        == [
            "Bash(python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/resolving-analysis-findings"
            "/scripts/read_pr_head.py:*)",
            "Bash(python3 -I ${CLAUDE_PLUGIN_ROOT}/scripts/qlty-sonar-read.py issue-state:*)",
        ],
    )
    check(
        "boundaries tell the user never to choose don't ask again",
        'never choose "don\'t ask again"' in body.replace("\n", " "),
    )
    check("body calls the collecting skill", "Skill(collecting-analysis-findings)" in body)


def check_read_pr_head() -> None:
    path = SKILL_DIR / "scripts" / "read_pr_head.py"
    spec = importlib.util.spec_from_file_location("read_pr_head", path)
    check("read_pr_head.py loads", spec is not None and spec.loader is not None)
    if spec is None or spec.loader is None:
        return
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    sha = "a" * 40
    repo = "github.com/acme/repo"
    options: dict[str, object] = {}

    def outcome(
        argv: list[str], stdout: str = "", code: int = 0
    ) -> tuple[int, list[list[str]], str]:
        calls: list[list[str]] = []
        printed = io.StringIO()

        def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
            calls.append(command)
            options.update(kwargs)
            return SimpleNamespace(returncode=code, stdout=stdout)

        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(io.StringIO()):
            return module.main(argv, run=fake_run), calls, printed.getvalue()

    for name, value in {"a SHA-1": sha, "a SHA-256": "b" * 64}.items():
        status, calls, printed = outcome(["acme/repo", "12"], json.dumps({"headRefOid": value}))
        check(
            f"read_pr_head prints only {name} from the one fixed command",
            status == 0
            and printed == value + "\n"
            and calls == [["gh", "pr", "view", "12", "--repo", repo, "--json", "headRefOid"]],
        )
    check(
        "read_pr_head leaves the working directory before running gh",
        "os.chdir(Path(__file__).resolve().parent)" in read(path),
    )
    check(
        "read_pr_head tolerates undecodable gh output and closes stdin",
        options.get("errors") == "replace" and "stdin" in options,
    )
    for name, argv in {
        "an option as the number": ["acme/repo", "--web"],
        "an option as the repository": ["--repo", "12"],
        "a repository with no owner": ["repo", "12"],
        "a dot repository": ["acme/.", "12"],
        "a dot-dot repository": ["acme/..", "12"],
        "a repository with a trailing newline": ["acme/repo\n", "12"],
        "a zero number": ["acme/repo", "0"],
        "a leading zero": ["acme/repo", "012"],
        "an overlong number": ["acme/repo", "1" * 11],
        "a number with a trailing newline": ["acme/repo", "12\n"],
        "an extra argument": ["acme/repo", "12", "--web"],
        "a missing argument": ["acme/repo"],
    }.items():
        status, calls, printed = outcome(argv)
        check(
            f"read_pr_head refuses {name} before running gh",
            status == 2 and not calls and not printed,
        )
    for name, stdout, code in (
        ("a failed gh", "", 1),
        ("output that is not JSON", "not json", 0),
        ("a JSON list", "[]", 0),
        ("JSON null", "null", 0),
        ("a null SHA", json.dumps({"headRefOid": None}), 0),
        ("a numeric SHA", json.dumps({"headRefOid": 5}), 0),
        ("a branch name", json.dumps({"headRefOid": "main"}), 0),
        ("an uppercase SHA", json.dumps({"headRefOid": "A" * 40}), 0),
        ("a short SHA", json.dumps({"headRefOid": sha[:39]}), 0),
        ("a long SHA", json.dumps({"headRefOid": sha + "a"}), 0),
        ("a SHA with a trailing newline", json.dumps({"headRefOid": sha + "\n"}), 0),
    ):
        status, calls, printed = outcome(["acme/repo", "12"], stdout, code)
        check(f"read_pr_head refuses {name}", status == 2 and bool(calls) and not printed)


def check_rules(body: str) -> None:
    rungs = re.findall(r"^\| ([1-5])\. ", body, re.MULTILINE)
    check(
        "ladder has rungs 1 to 5", sorted(set(rungs)) == ["1", "2", "3", "4", "5"], ",".join(rungs)
    )
    _, found, after = body.partition("## Decision rights")
    check("a Decision rights section exists", bool(found))
    rights = after.split("\n## ", 1)[0]
    rows = [line for line in rights.splitlines() if line.startswith("| ")]

    def row(prefix: str) -> str:
        return next((line for line in rows if line.startswith(f"| {prefix}")), "")

    rung3, rung4, rung5 = row("Rung 3"), row("Rung 4"), row("Rung 5")
    quiet = row("Rung 2 on `Minor`")
    asks = row("Rung 2 on any other finding")
    check("decision rights have rows for rungs 3, 4 and 5", all((rung3, rung4, rung5)))
    check(
        "decision rights name the other remote writes",
        all(k in row("`--unignore-issue`") for k in ("--reanalyze", "--reanalyze-and-wait"))
        and "`-F`" in row("Bulk flags"),
    )
    check(
        "rung 3 is a per-command approval for a remote write",
        "per command" in rung3 and "remote write" in rung3,
    )
    check("rung 5 is handed over, never run", "Not run here" in rung5)
    check(
        "Warning/Medium is decided only on an accepted shape; elsewhere it asks first",
        bool(quiet)
        and "docs/ci.md" in quiet
        and "outside the `Security` category" in quiet
        and "`Security` finding" in asks
        and "Critical" not in quiet
        and "outside an accepted shape" in asks
        and "AskUserQuestion" in asks,
    )
    check("bulk flags are handed over, not run", "Not run here, like rung 5" in row("Bulk flags"))
    flat = " ".join(body.split())
    check(
        "an edit target must be a relative path inside the repository",
        "no `..` segment" in flat and "no leading `/`" in flat and "`.git/`" in flat,
    )
    check(
        "an edit outside the finding's file is asked about first, and the symlink gap is disclosed",
        "`AskUserQuestion` naming that file" in flat
        and "nothing granted here can detect one" in flat,
    )
    check(
        "issue_id is validated before a command is built",
        "^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$" in body,
    )
    check(
        "edits and remote writes re-collect for the current head first",
        "after the fresh re-collect" in rung3,
    )
    stale = [
        p.name
        for p in (SKILL_DIR / "references").glob("*.md")
        if any(
            old in p.read_text(encoding="utf-8")
            for old in ("`Critical`, `High` or `Error`", "`Minor`, `Info` or `Warning`")
        )
    ]
    check("references do not restate a shorter approval severity list", not stale, ", ".join(stale))
    check(
        "the re-collect and the local scan are each asked about first",
        "ask via `AskUserQuestion` whether to re-collect now" in flat
        and "after asking via `AskUserQuestion` whether to run it now" in flat,
    )
    check("init is never run unprompted", "never run `codacy-analysis init`" in body)
    check(
        "init is handed to the user, never run here",
        "`codacy-analysis init` is never run here" in body.replace("\n", " "),
    )


def check_sonar(body: str) -> None:
    section = body.split("## Sonar mechanisms", 1)[1].split("## Real or false positive", 1)[0]
    check(
        "a provider switch keeps one provider per run",
        "**One provider per run.**" in body and "never edits `.codacy.yml`" in body,
    )
    check("Sonar's rung 2 uses the rule-key form", "# NOSONAR(S5655)" in section)
    check(
        "Sonar's rung 3 asks per command, and bulk transitions are not run",
        "`AskUserQuestion` per command" in section and "bulk transitions" in section,
    )
    check(
        "Sonar's rung 4 is a UI setting handed to the user",
        "Ignore Issues on Multiple Criteria" in section
        and "not `.sonarcloud.properties`" in section,
    )
    check(
        "a security or high impact always asks before rung 2",
        "`SECURITY` impact or a `HIGH` or `BLOCKER` impact" in section,
    )
    check(
        "the Sonar project key comes from the record and is validated",
        "`source.repository`" in body
        and "Sonar project-key pattern in that same paragraph" in body
        and "^[A-Za-z0-9][A-Za-z0-9._:-]{0,399}$"
        in (SKILL_DIR.parent / "collecting-analysis-findings" / "SKILL.md").read_text(
            encoding="utf-8"
        ),
    )
    check(
        ".sonar-config.json is denied, .codacy.yml stays at rung 4, .sonarcloud.properties never",
        "`.sonar-config.json`" in body
        and "`.codacy.yml` is edited only at rung 4 and `.sonarcloud.properties` never"
        in " ".join(body.split()),
    )
    scan = (SKILL_DIR / "references" / "local-scan.md").read_text(encoding="utf-8")
    check(
        "the Sonar scan's question says files are sent and retention is undocumented",
        "sends project files" in body and "undocumented" in body and "sends project" in scan,
    )
    check(
        "no sonar command is pre-approved",
        "Bash(sonar" not in frontmatter(body).get("allowed-tools", ""),
    )


def check_dependency() -> None:
    collecting = read(COLLECTING / "SKILL.md") if (COLLECTING / "SKILL.md").is_file() else ""
    if not collecting:
        skip("one-way dependency", "collecting-analysis-findings not found beside this skill")
        return
    grants = frontmatter(collecting).get("allowed-tools", "")
    check("collecting grants no Skill()", "Skill(" not in grants)
    check("collecting never calls this skill", "Skill(resolving" not in collecting)


def check_syntax_consistency() -> None:
    formats_path = SKILL_DIR / "references" / "suppression-formats.md"
    formats = read(formats_path) if formats_path.is_file() else ""
    check(
        "suppression-formats recommends the trailing-comment form",
        "# nosec B603 B607  # " in formats,
    )
    root = find_repo_root()
    if root is None:
        skip(
            "nosec form in docs/ci.md and git-kit scripts", "not inside the marketplace repository"
        )
        return
    ci = read(root / "docs" / "ci.md")
    check("docs/ci.md B404 row uses the trailing-comment form", "`# nosec B404  # <reason>`" in ci)
    bad = []
    for name in ("git-verify-fix-diff.py", "git-review-ledger.py"):
        text = read(root / "plugins" / "git-kit" / "scripts" / name)
        if not re.search(r"^import subprocess  # nosec B404  # \S", text, re.MULTILINE):
            bad.append(f"{name}: import line")
        if re.search(r"# nosec B\d+ -- ", text):
            bad.append(f"{name}: old -- form")
        bare = [
            str(number)
            for number, line in enumerate(text.splitlines(), 1)
            if "subprocess.run(" in line and not re.search(r"# nosec B603 B607  # \S", line)
        ]
        if bare:
            bad.append(f"{name}: subprocess.run without a reason on line(s) {', '.join(bare)}")
    check("git-kit scripts use the trailing-comment form", not bad, ", ".join(bad))


def check_skill_file() -> None:
    text = read(SKILL_DIR / "SKILL.md")
    fm = frontmatter(text)
    _, separator, body = text.partition("\n---\n")
    check("SKILL.md has a frontmatter block", bool(separator))
    check_structure(text, fm, body)
    check_grants(fm, body)
    check_read_pr_head()
    check_rules(body)


def guarded(name: str, run) -> None:
    """Run a group of checks; a crash inside it reads as a FAIL line, not a bare traceback."""
    try:
        run()
    except Exception as exc:  # noqa: BLE001 - any crash must surface as a failed check
        check(f"{name} ran to completion", False, f"{type(exc).__name__}: {exc}")


def main() -> int:
    guarded("SKILL.md checks", check_skill_file)
    guarded("Sonar checks", lambda: check_sonar(read(SKILL_DIR / "SKILL.md")))
    guarded("dependency checks", check_dependency)
    guarded("syntax consistency checks", check_syntax_consistency)
    print(f"\n{len(failures)} failure(s)" if failures else "\nall checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
