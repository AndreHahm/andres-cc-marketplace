#!/usr/bin/env python3
"""Persisted smoke test for skill-development: frontmatter validity, referenced-file
existence, and Bash-scope grant usage consistency."""

import contextlib
import importlib.util
import io
import os
import pathlib
import queue
import re
import subprocess
import sys
import tempfile

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


def check_frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False, "SKILL.md does not start with a frontmatter block"
    end = text.find("\n---\n", 4)
    if end == -1:
        return False, "frontmatter block is never closed"
    fm = text[4:end]
    if "name:" not in fm or "description:" not in fm:
        return False, "missing required frontmatter field ('name' or 'description')"
    return True, "frontmatter present and closed"


def check_referenced_files():
    # This skill's body cites paths both as bare `references/foo.md` and as
    # `${CLAUDE_SKILL_DIR}/references/foo.md` — both forms must be checked, or the
    # majority of this file's real references silently go unverified.
    text = SKILL_MD.read_text(encoding="utf-8")
    pattern = r"`(?:\$\{CLAUDE_SKILL_DIR\}/)?(references/[\w.-]+\.md|scripts/[\w./-]+)`"
    missing = []
    for match in re.finditer(pattern, text):
        path = SKILL_DIR / match.group(1)
        if not path.exists():
            missing.append(match.group(1))
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def check_bash_grants():
    # This skill doesn't use the "scoped `Bash(...)`" invocation phrasing the lifecycle
    # skills use — its body cites commands as literal invocation examples instead
    # (e.g. "python -m scripts.aggregate_benchmark", "mkdir -p ..."). So the meaningful
    # check here is: does each granted Bash(<cmd>:*) scope's <cmd> actually appear as a
    # word-boundary command mention in the body? An unused grant is an R6 least-privilege
    # smell even when nothing in the body's own phrasing names the grant explicitly.
    text = SKILL_MD.read_text(encoding="utf-8")
    end = text.find("\n---\n", 4)
    if end == -1:
        return False, "frontmatter block is never closed"
    frontmatter, body = text[:end], text[end + 5 :]
    # Single-line value, or a YAML block scalar (>- / |) whose indented lines continue it.
    fm_line_match = re.search(
        r"^allowed-tools:[ \t]*((?:[>|][+-]?)?[ \t]*.*(?:\n[ \t]+.*)*)", frontmatter, re.MULTILINE
    )
    if not fm_line_match or not fm_line_match.group(1).strip():
        return True, "no allowed-tools line found (skip)"
    granted_cmds = re.findall(r"Bash\(([\w.-]+):", fm_line_match.group(1))
    unused = [cmd for cmd in granted_cmds if not re.search(rf"\b{re.escape(cmd)}\b", body)]
    if unused:
        return False, "Bash grant(s) never invoked anywhere in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, "every granted Bash command is invoked somewhere in the body"


def _load_script(name):
    """Import a sibling script by file path (repair_skill.py imports quick_validate bare)."""
    # scripts/ itself (bare sibling imports) and the skill dir (`from scripts.utils import`)
    for path in (str(SKILL_DIR / "scripts"), str(SKILL_DIR)):
        if path not in sys.path:
            sys.path.insert(0, path)
    spec = importlib.util.spec_from_file_location(name, SKILL_DIR / "scripts" / f"{name}.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_scan_skills_parses_block_scalar():
    scan = _load_script("scan_skills")
    text = "---\nname: demo\ndescription: >-\n  Folded text.\n  Second line.\n---\n# Body\n"
    description = scan.parse_frontmatter(text).get("description")
    if description != "Folded text. Second line.":
        return False, f"block-scalar description parsed as {description!r}"
    return True, "block-scalar description is parsed by a real YAML parser"


def check_similarity_without_registry():
    sim = _load_script("analyze_similarity")
    if sim.jaccard_similarity(set(), set()) != 0.0:
        return False, "two empty sets must not count as identical"
    same = "Parse structured application logs for error triage and incident correlation"
    skills = [
        {"name": "alpha", "frontmatter": {"name": "alpha", "description": same}},
        {"name": "beta", "frontmatter": {"name": "beta", "description": "Render sales charts"}},
        {"name": "gamma", "frontmatter": {"name": "gamma", "description": same}},
    ]
    if sim.find_obsolete_skills(skills, {}):
        return False, "registry-less skills must not all be reported obsolete (bold != old)"
    report = sim.generate_simple_report({"skills": skills}, 0.65)
    # Merge headings use the title-cased display name; skills are alphabetical pairs
    if "### Alpha + Gamma" not in report:
        return False, "identical registry-less descriptions were not flagged (positive control)"
    if "Beta" in report.split("## Medium Priority")[0].split("## High Priority")[1]:
        return False, "a dissimilar registry-less skill was flagged as a merge pair"
    return True, "no registry: no KeyError; duplicates flagged, dissimilar and unused not"


def check_obsolete_handles_naive_timestamp():
    sim = _load_script("analyze_similarity")
    skills = [{"name": "alpha", "frontmatter": {"description": "Parse logs"}}]
    for stamp in ("2020-01-01T00:00:00", "2020-01-01T00:00:00Z"):
        registry = {"skills": {"alpha": {"activation_count": 3, "last_used": stamp}}}
        reasons = sim.find_obsolete_skills(skills, registry)[0]["reasons"]
        if not any(r.startswith("Not used in") for r in reasons):
            return False, f"last_used {stamp!r} was not compared: {reasons}"
    return True, "naive and timezone-aware last_used timestamps are both compared"


def check_obsolete_lists_high_urgency_first():
    sim = _load_script("analyze_similarity")
    skills = [
        {"name": f"stale-{i}", "frontmatter": {"description": "Parse logs"}} for i in range(11)
    ]
    skills.append({"name": "never-used", "frontmatter": {"description": "Parse logs"}})
    entries = {
        f"stale-{i}": {"activation_count": 3, "last_used": "2020-01-01T00:00:00Z"}
        for i in range(11)
    }
    entries["never-used"] = {"activation_count": 0}
    names = [item["name"] for item in sim.find_obsolete_skills(skills, {"skills": entries})]
    if "never-used" not in names[:10]:
        return False, f"high-urgency skill would be cut by the report's first-10 limit: {names}"
    return True, "high-urgency obsolete skills sort ahead of the report's first-10 cut"


def check_frontmatter_close_is_line_anchored():
    validate = _load_script("quick_validate")
    text = (
        "---\nname: dash-skill\n"
        'description: "Handles jobs --- including retries. Use when jobs stall."\n'
        "---\n# Body\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        skill = pathlib.Path(tmp) / "dash-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(text, encoding="utf-8")
        ok, message = validate.validate_skill_frontmatter(skill)
    if not ok:
        return False, f"a '---' inside a frontmatter value ended the block early: {message}"
    return True, "a '---' inside a frontmatter value does not end the block"


def check_repair_preserves_frontmatter():
    repair = _load_script("repair_skill")
    original = "---\ndescription: >-\n  Zażółć gęślą.\nz-key: 1\na-key: 2\n---\n# Body\n"
    with tempfile.TemporaryDirectory() as tmp:
        skill = pathlib.Path(tmp) / "demo-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(original, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            repair.fix_frontmatter_format(skill)
        result = (skill / "SKILL.md").read_text(encoding="utf-8")
    expected = '---\nname: "demo-skill"\n' + original[4:]
    if result != expected:
        return False, f"existing frontmatter was rewritten: {result!r}"
    return True, "repair inserts only the missing key and leaves the rest byte-identical"


def check_repair_keeps_dashes_inside_values():
    repair = _load_script("repair_skill")
    original = '---\ndescription: "Handles jobs --- including retries."\n---\n# Body\n'
    with tempfile.TemporaryDirectory() as tmp:
        skill = pathlib.Path(tmp) / "demo-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(original, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            repair.fix_frontmatter_format(skill)
        result = (skill / "SKILL.md").read_text(encoding="utf-8")
    expected = '---\nname: "demo-skill"\n' + original[4:]
    if result != expected:
        return False, f"a '---' inside a value was treated as the closing delimiter: {result!r}"
    return True, "repair does not treat a '---' inside a value as the closing delimiter"


def check_init_rejects_path_traversal_name():
    script = SKILL_DIR / "scripts" / "init_skill.py"
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp) / "base"
        base.mkdir()
        proc = subprocess.run(
            [sys.executable, str(script), "../escape", "--path", str(base)],
            capture_output=True,
            text=True,
            check=False,
        )
        escaped = (pathlib.Path(tmp) / "escape").exists()
    if proc.returncode == 0 or escaped:
        return False, "init_skill.py accepted a name containing '..'"
    return True, "init_skill.py rejects a non-hyphen-case skill name"


def check_run_eval_reads_pipe_without_select():
    run_eval = _load_script("run_eval")
    if hasattr(run_eval, "select"):
        return False, "run_eval still imports select (POSIX-only on pipes)"
    child = subprocess.Popen(
        [sys.executable, "-c", "print('ok')"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    chunks = queue.Queue()
    run_eval._pump_stdout(child.stdout, chunks)  # returns at EOF
    child.wait()
    first = chunks.get(timeout=5)
    if b"ok" not in first or chunks.get(timeout=5) != b"":
        return False, f"pump did not deliver the output then EOF: {first!r}"
    return True, "run_eval reads the child's stdout through a portable pump and sees EOF"


def check_package_skill_imports_as_script():
    script = SKILL_DIR / "scripts" / "package_skill.py"
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            [sys.executable, str(script)], capture_output=True, text=True, cwd=tmp, check=False
        )
    if "ModuleNotFoundError" in proc.stderr or "ImportError" in proc.stderr:
        return False, "package_skill.py cannot import quick_validate when run as a script"
    return True, "package_skill.py imports its validator when run as `python .../package_skill.py`"


def check_report_icons_differ():
    text = (SKILL_DIR / "scripts" / "generate_report.py").read_text(encoding="utf-8")
    pairs = re.findall(r'icon = "([^"]*)" if did_pass else "([^"]*)"', text)
    if not pairs or any(ok == bad for ok, bad in pairs):
        return False, f"pass and fail icons must differ: {pairs}"
    return True, "report pass and fail icons are distinct"


def check_improve_description_call_is_contained():
    if os.name == "nt":
        return True, "POSIX-only fake `claude` shim (skip)"
    improve = _load_script("improve_description")
    with tempfile.TemporaryDirectory() as tmp:
        shim = pathlib.Path(tmp) / "claude"
        shim.write_text('#!/bin/sh\nif [ -n "$SLOW" ]; then sleep 5; fi\npwd\n', encoding="utf-8")
        shim.chmod(0o755)
        old_path, old_cwd = os.environ["PATH"], os.getcwd()
        os.environ["PATH"] = f"{tmp}{os.pathsep}{old_path}"
        try:
            reply = improve._call_claude("prompt", None, timeout=5).strip()
            os.environ["SLOW"] = "1"
            try:
                improve._call_claude("prompt", None, timeout=1)
            except RuntimeError as exc:
                timed_out = "timed out" in str(exc)
            else:
                timed_out = False
        finally:
            os.environ["PATH"] = old_path
            os.environ.pop("SLOW", None)
    if os.path.realpath(reply) == os.path.realpath(old_cwd):
        return False, "claude -p ran in the caller's cwd instead of a neutral one"
    if not timed_out:
        return False, "a claude -p timeout did not surface as RuntimeError"
    return True, "claude -p runs in a neutral cwd and a timeout becomes a RuntimeError"


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_scan_skills_parses_block_scalar,
    check_similarity_without_registry,
    check_obsolete_handles_naive_timestamp,
    check_obsolete_lists_high_urgency_first,
    check_frontmatter_close_is_line_anchored,
    check_repair_preserves_frontmatter,
    check_repair_keeps_dashes_inside_values,
    check_init_rejects_path_traversal_name,
    check_run_eval_reads_pipe_without_select,
    check_package_skill_imports_as_script,
    check_report_icons_differ,
    check_improve_description_call_is_contained,
]


def main():
    failed = False
    for check in CHECKS:
        try:
            ok, message = check()
        except Exception as exc:  # a crashing check is a FAIL, not an aborted run
            ok, message = False, f"raised {type(exc).__name__}: {exc}"
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
