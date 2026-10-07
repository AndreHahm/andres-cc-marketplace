#!/usr/bin/env python3
"""Persisted smoke test for skill-tester: frontmatter validity, referenced-file
existence, Bash-scope grant consistency, declared-tool usage, and a fixture run
of scripts/aggregate_benchmark.py against known-good numbers, plus its rejection of a
contaminated or ungraded baseline."""

import contextlib
import importlib.util
import io
import json
import pathlib
import re
import runpy
import sys
import tempfile

sys.dont_write_bytecode = (
    True  # importing the aggregation script must not write a .pyc into the skill folder
)

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
AGGREGATE = SKILL_DIR / "scripts" / "aggregate_benchmark.py"


def _split_frontmatter(text):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    return text[4:end], text[end + 5 :]


def _frontmatter_value(frontmatter, key):
    """Value of a top-level frontmatter key, with any block-scalar indicator removed."""
    match = re.search(rf"^{key}:[ \t]*(.*(?:\n[ \t]+.*)*)", frontmatter, re.MULTILINE)
    if not match:
        return None
    return re.sub(r"^[>|][+-]?\s*", "", match.group(1).strip()).strip()


def check_frontmatter():
    frontmatter, _ = _split_frontmatter(SKILL_MD.read_text(encoding="utf-8"))
    if frontmatter is None:
        return False, "SKILL.md has no frontmatter block, or it is never closed"
    for key in ("name", "description"):
        if not _frontmatter_value(frontmatter, key):
            return False, f"required frontmatter field '{key}' is missing or empty"
    return True, "frontmatter present and closed, name and description non-empty"


def check_referenced_files():
    pattern = re.compile(
        r"`(\$\{CLAUDE_SKILL_DIR\}/(?:\.\./\.\./)?(?:references|scripts|assets)/[\w./-]+"
        r"|references/[\w.-]+\.md|scripts/[\w./-]+|assets/[\w.-]+)`"
    )
    sources = [SKILL_MD, *sorted((SKILL_DIR / "references").glob("*.md"))]
    checked = 0
    missing = []
    for source in sources:
        for match in pattern.finditer(source.read_text(encoding="utf-8")):
            raw = match.group(1)
            if raw.startswith("${CLAUDE_SKILL_DIR}/"):
                target = SKILL_DIR / raw[len("${CLAUDE_SKILL_DIR}/") :]
            else:
                target = SKILL_DIR / raw
            checked += 1
            if not target.exists():
                missing.append(f"{source.name}: {raw}")
    if checked == 0:
        return (
            False,
            "no referenced file paths found at all (the extraction pattern matched nothing)",
        )
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, f"all {checked} referenced paths exist"


def check_no_orphans():
    body = SKILL_MD.read_text(encoding="utf-8")
    orphans = []
    for folder in ("references", "scripts"):
        for path in sorted((SKILL_DIR / folder).glob("*")):
            if path.name in {"smoke_test.py", "__pycache__"}:
                continue
            if f"{folder}/{path.name}" not in body:
                orphans.append(f"{folder}/{path.name}")
    if orphans:
        return False, "files not referenced from SKILL.md: " + ", ".join(orphans)
    return True, "every references/ and scripts/ file is referenced from SKILL.md"


def _allowed_tools(frontmatter):
    """Tool tokens from `allowed-tools` (space, comma, block-scalar and indented-list forms)."""
    match = re.search(r"^allowed-tools:[ \t]*(.*(?:\n[ \t]+.*)*)", frontmatter or "", re.MULTILINE)
    if not match:
        return None
    return re.findall(r"[A-Za-z]\w*(?:\([^)]*\))?", match.group(1))


def _granted_bash_commands(tools):
    """First token of every `Bash(<command>:*)` grant, e.g. `python` for `Bash(python:*)`."""
    granted = []
    for tool in tools:
        if tool.startswith("Bash(") and tool.endswith(")"):
            scope = tool[len("Bash(") : -1].rsplit(":", 1)[0].split()
            if scope:
                granted.append(scope[0])
    return granted


def check_bash_grants():
    frontmatter, body = _split_frontmatter(SKILL_MD.read_text(encoding="utf-8"))
    tools = _allowed_tools(frontmatter)
    if tools is None:
        return False, "no allowed-tools line in frontmatter"
    granted = _granted_bash_commands(tools)
    invoked = set()
    for block in re.findall(r"```bash\n(.*?)```", body, re.DOTALL):
        # Join trailing-backslash continuations so a wrapped command is one command.
        joined = re.sub(r"\\\s*\n\s*", " ", block)
        for line in joined.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if re.search(r"&&|\|\||[;|`]|\$\(", line):
                return False, (
                    "fenced bash blocks must use one simple command per line "
                    f"(compound shell syntax found: {line!r})"
                )
            invoked.add(line.split()[0])
    if not invoked:
        return False, "no commands found in fenced bash blocks (extraction matched nothing)"
    uncovered = [cmd for cmd in invoked if cmd not in granted]
    if uncovered:
        return False, "body invokes command(s) not covered by any granted Bash scope: " + ", ".join(
            sorted(uncovered)
        )
    return (
        True,
        f"every invoked command ({', '.join(sorted(invoked))}) is covered by a granted Bash scope",
    )


def check_declared_tools_used():
    frontmatter, body = _split_frontmatter(SKILL_MD.read_text(encoding="utf-8"))
    tools = _allowed_tools(frontmatter)
    if tools is None:
        return False, "no allowed-tools line in frontmatter"
    declared = list(dict.fromkeys(tool.split("(")[0] for tool in tools))
    evidence = {
        "Read": r"\bRead\b",
        "Write": r"\bWrite\b",
        "Edit": r"or direct edits",
        "Agent": r"\bAgent tool\b",
        "Skill": r"^Skill: ",
        "Bash": r"```bash",
        "Glob": r"\bGlob\b",
        "Grep": r"\bGrep\b",
    }
    unused = []
    for tool in declared:
        pattern = evidence.get(tool)
        if pattern is None:
            return False, f"declared tool {tool!r} has no usage pattern in this smoke test; add one"
        if not re.search(pattern, body, re.MULTILINE):
            unused.append(tool)
    if not declared:
        return False, "allowed-tools declares no tools (extraction matched nothing)"
    if unused:
        return False, "declared but never used in the body: " + ", ".join(unused)
    return True, f"every declared tool is used in the body ({', '.join(declared)})"


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _run_aggregate(path):
    """Run aggregate_benchmark.py in-process as __main__; return (exit code, stdout)."""
    stdout = io.StringIO()
    saved_argv = sys.argv
    sys.argv = [str(AGGREGATE), str(path)]
    code = 0
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            runpy.run_path(str(AGGREGATE), run_name="__main__")
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.argv = saved_argv
    return code, stdout.getvalue()


def check_aggregate_fixture():
    """Known-good run: two evals whose averages are exact in binary floating point."""
    assets = SKILL_DIR / "assets"
    with_example = json.loads(
        (assets / "grading-with-skill-example.json").read_text(encoding="utf-8")
    )
    base_example = json.loads(
        (assets / "grading-baseline-example.json").read_text(encoding="utf-8")
    )
    if with_example["summary"]["pass_rate"] != 1.0 or base_example["summary"]["pass_rate"] != 0.4:
        return False, "assets grading examples no longer have the pass rates this fixture assumes"

    def grading(example, pass_rate):
        data = json.loads(json.dumps(example))
        data["summary"]["pass_rate"] = pass_rate
        return data

    # eval-2 and eval-10 (not eval-1/eval-2) so a lexicographic sort would reverse them.
    runs = {
        "eval-2": (
            (with_example, 1.0, 2500, 8000),
            (base_example, 0.5, 1800, 5000),
        ),
        "eval-10": (
            (with_example, 0.75, 2100, 7000),
            (base_example, 0.25, 1900, 4000),
        ),
    }
    with tempfile.TemporaryDirectory() as tmp:
        iteration = pathlib.Path(tmp) / "evals" / "fixture-skill" / "workspace" / "iteration-1"
        for eval_dir, (with_run, base_run) in runs.items():
            for config, (example, pass_rate, tokens, duration) in (
                ("with_skill", with_run),
                ("baseline", base_run),
            ):
                _write_json(
                    iteration / eval_dir / config / "grading.json", grading(example, pass_rate)
                )
                _write_json(
                    iteration / eval_dir / config / "timing.json",
                    {"total_tokens": tokens, "duration_ms": duration, "model": "<model-id>"},
                )
        (iteration / "eval-backup").mkdir()  # stray sibling the script must skip
        code, output = _run_aggregate(iteration)
        if code != 0:
            return False, f"aggregate_benchmark.py exited {code}: {output[-200:]}"
        benchmark = json.loads((iteration / "benchmark.json").read_text(encoding="utf-8"))
        missing_code, _ = _run_aggregate(pathlib.Path(tmp) / "does-not-exist")

    problems = []
    if [e["eval_id"] for e in benchmark["evals"]] != [2, 10]:
        problems.append(
            f"eval order {[e['eval_id'] for e in benchmark['evals']]} (want numeric [2, 10])"
        )
    if benchmark["skill_name"] != "fixture-skill":
        problems.append(f"skill_name {benchmark['skill_name']!r}")
    expected_summary = json.loads(
        """
        {
            "with_skill_avg_pass_rate": 0.875,
            "baseline_avg_pass_rate": 0.375,
            "improvement": 0.5,
            "avg_tokens_with_skill": 2300,
            "avg_tokens_baseline": 1850,
            "token_cost": 450,
            "avg_duration_ms_with_skill": 7500,
            "avg_duration_ms_baseline": 4500,
            "duration_cost_ms": 3000
        }
        """
    )
    for key, want in expected_summary.items():
        if benchmark["summary"].get(key) != want:
            problems.append(f"summary.{key}={benchmark['summary'].get(key)!r} (want {want!r})")
    expected_delta = json.loads('{"pass_rate": 0.5, "tokens": 700, "duration_ms": 3000}')
    if benchmark["evals"][0]["delta"] != expected_delta:
        problems.append(f"eval-2 delta {benchmark['evals'][0]['delta']!r}")
    if missing_code != 1:
        problems.append(f"nonexistent iteration path exited {missing_code} (want 1)")

    spec = importlib.util.spec_from_file_location("aggregate_benchmark", AGGREGATE)
    if spec is None or spec.loader is None:
        return False, "could not load aggregate_benchmark.py as a module"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if (module.ruby_round(2.5), module.ruby_round(-2.5), module.ruby_round(0.5)) != (3, -3, 1):
        problems.append("ruby_round no longer rounds half away from zero")

    if problems:
        return False, "; ".join(problems)
    return True, "fixture run matches known-good benchmark.json values and ruby_round boundaries"


def check_negative_improvement_output():
    """A skill that scores below baseline must print a signed '-', never '+-'."""
    assets = SKILL_DIR / "assets"
    with_example = json.loads(
        (assets / "grading-with-skill-example.json").read_text(encoding="utf-8")
    )
    base_example = json.loads(
        (assets / "grading-baseline-example.json").read_text(encoding="utf-8")
    )
    with_example["summary"]["pass_rate"] = 0.25
    base_example["summary"]["pass_rate"] = 0.75
    with tempfile.TemporaryDirectory() as tmp:
        iteration = pathlib.Path(tmp) / "evals" / "fixture-skill" / "workspace" / "iteration-1"
        for config, example in (("with_skill", with_example), ("baseline", base_example)):
            _write_json(iteration / "eval-1" / config / "grading.json", example)
            _write_json(
                iteration / "eval-1" / config / "timing.json",
                {"total_tokens": 1000, "duration_ms": 1000, "model": "<model-id>"},
            )
        code, output = _run_aggregate(iteration)
    if code != 0:
        return False, f"aggregate_benchmark.py exited {code}"
    if "Improvement: -50.0 percentage points" not in output:
        return False, f"negative improvement not printed as '-50.0': {output[-160:]!r}"
    if "+-" in output:
        return False, "output contains '+-'"
    return True, "negative improvement prints as -50.0 percentage points"


def check_unusable_baseline_rejected():
    """A contaminated baseline, or a baseline directory with no grading, must stop aggregation."""
    example = json.loads(
        (SKILL_DIR / "assets" / "grading-baseline-example.json").read_text(encoding="utf-8")
    )
    timing = {"total_tokens": 1000, "duration_ms": 1000, "model": "<model-id>"}
    problems = []
    for label, graded_baseline in (
        ("contaminated", {**example, "contaminated": True}),
        ("ungraded", None),
    ):
        with tempfile.TemporaryDirectory() as tmp:
            iteration = pathlib.Path(tmp) / "evals" / "fixture-skill" / "workspace" / "iteration-1"
            eval_dir = iteration / "eval-1"
            _write_json(eval_dir / "with_skill" / "grading.json", example)
            _write_json(eval_dir / "with_skill" / "timing.json", timing)
            _write_json(eval_dir / "baseline" / "timing.json", timing)
            if graded_baseline is not None:
                _write_json(eval_dir / "baseline" / "grading.json", graded_baseline)
            code, _ = _run_aggregate(iteration)
            if code != 1:
                problems.append(f"{label} baseline exited {code} (want 1)")
    if problems:
        return False, "; ".join(problems)
    return True, "a contaminated or ungraded baseline stops aggregation with exit 1"


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_no_orphans,
    check_bash_grants,
    check_declared_tools_used,
    check_aggregate_fixture,
    check_negative_improvement_output,
    check_unusable_baseline_rejected,
]


def main():
    failed = False
    for check in CHECKS:
        try:
            ok, message = check()
        except Exception as exc:  # a crashing check is a failing check, not an aborted run
            ok, message = False, f"check raised {type(exc).__name__}: {exc}"
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
