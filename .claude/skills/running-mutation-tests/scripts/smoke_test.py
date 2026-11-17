#!/usr/bin/env python3
"""Smoke test for running-mutation-tests: the plugin-root mutation runner and parser, offline.

Loads `scripts/qlty-mutation-parse.py` (plugin root) in-process and checks it against real mutmut
3.8.1 output saved under `fixtures/` (the 2026-11-15 design runs on trust_boundary and
validators), then against tampered copies: an unknown exit code, counts that disagree with
mutmut's totals, a missing totals file, no `.meta` file. Loads `scripts/qlty-mutation-run.py`
and checks its input refusals, module list parsing and the configuration it writes, without
running mutmut or pytest. Checks SKILL.md's grants against the scripts. Needs PyYAML (in this
repository's dev group; elsewhere run it with `uv run --with pyyaml`). Exit 0 when every check
passes, 1 otherwise.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parents[2]
PARSE_SCRIPT = PLUGIN_ROOT / "scripts" / "qlty-mutation-parse.py"
RUN_SCRIPT = PLUGIN_ROOT / "scripts" / "qlty-mutation-run.py"
FIXTURES = HERE / "fixtures"
SKILL = HERE.parent / "SKILL.md"
_SCRATCH = tempfile.TemporaryDirectory()
SCRATCH = Path(_SCRATCH.name)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def load(path: Path, name: str):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def guarded(name: str, fn) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - a crash is a failing check, reported by name
        check(f"{name}: no crash", False, f"{type(exc).__name__}: {exc}")


def call(main, argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def copy_fixture(name: str) -> Path:
    target = SCRATCH / f"{name}-{len(list(SCRATCH.iterdir()))}"
    shutil.copytree(FIXTURES / name, target)
    return target


def meta_path(root: Path) -> Path:
    return next(root.rglob("*.meta"))


def check_parse_real(parse) -> None:
    tb = parse.summarize(FIXTURES / "trust_boundary", "trust_boundary")
    check(
        "trust_boundary totals",
        (tb["total"], tb["counts"]["killed"], tb["counts"]["survived"]) == (25, 22, 3),
    )
    check("trust_boundary score", tb["score"] == 0.88, str(tb["score"]))
    check(
        "trust_boundary survivors are find_tier1_touches",
        {s["function"] for s in tb["survivors"]} == {"find_tier1_touches"},
    )
    va = parse.summarize(FIXTURES / "validators", "validators")
    check(
        "validators totals",
        (va["total"], va["counts"]["killed"], va["counts"]["survived"]) == (313, 253, 60),
    )
    check("validators: every key parsed", all(s["function"] for s in va["survivors"]))
    code, out, _ = call(
        parse.main, ["--mutants", str(FIXTURES / "trust_boundary"), "--format", "markdown"]
    )
    check("markdown exit 0", code == 0)
    check("markdown explains not measured", "Not measured means" in out and "| 88.0% |" in out)
    code, out, _ = call(parse.main, ["--mutants", str(FIXTURES / "validators"), "--format", "json"])
    check("json output parses", code == 0 and json.loads(out)["total"] == 313)


def check_parse_refusals(parse) -> None:
    root = copy_fixture("trust_boundary")
    meta = meta_path(root)
    data = json.loads(meta.read_text(encoding="utf-8"))
    first = next(iter(data["exit_code_by_key"]))
    data["exit_code_by_key"][first] = 99
    meta.write_text(json.dumps(data), encoding="utf-8")
    code, _, err = call(parse.main, ["--mutants", str(root)])
    check("unknown exit code refused", code == 2 and "not in mutmut 3.8.1" in err, err)

    root = copy_fixture("trust_boundary")
    stats = root / "mutmut-cicd-stats.json"
    totals = json.loads(stats.read_text(encoding="utf-8"))
    totals["killed"] += 1
    stats.write_text(json.dumps(totals), encoding="utf-8")
    code, _, err = call(parse.main, ["--mutants", str(root)])
    check("totals mismatch refused", code == 2 and "disagree" in err, err)

    root = copy_fixture("trust_boundary")
    (root / "mutmut-cicd-stats.json").unlink()
    code, _, err = call(parse.main, ["--mutants", str(root)])
    check("missing totals refused", code == 2 and "export-cicd-stats" in err, err)

    root = copy_fixture("trust_boundary")
    stats = root / "mutmut-cicd-stats.json"
    totals = json.loads(stats.read_text(encoding="utf-8"))
    del totals["killed"]
    stats.write_text(json.dumps(totals), encoding="utf-8")
    code, _, err = call(parse.main, ["--mutants", str(root)])
    check("missing totals key refused", code == 2 and "check the mutmut version" in err, err)

    root = copy_fixture("trust_boundary")
    stray = root / "plugins" / "fixtures" / "scripts" / "marketplace_ci"
    stray.mkdir(parents=True)
    shutil.copy(meta_path(root), stray / "trust_boundary.py.meta")
    code, _, err = call(parse.main, ["--mutants", str(root)])
    check(
        "stray copied .meta: duplicate refused without --module",
        code == 2 and "more than one" in err,
        err,
    )
    module = "scripts/marketplace_ci/trust_boundary.py"
    code, out, err = call(parse.main, ["--mutants", str(root), "--module", module])
    check(
        "stray copied .meta: --module reads only the module", code == 0 and "total 25" in out, err
    )
    code, _, err = call(parse.main, ["--mutants", str(root), "--module", "../x.py"])
    check("--module outside the tree refused", code == 2, err)

    empty = SCRATCH / "empty-mutants"
    empty.mkdir()
    code, _, err = call(parse.main, ["--mutants", str(empty)])
    check("no .meta refused", code == 2 and "mutmut run" in err, err)


def check_parse_classes(parse) -> None:
    root = SCRATCH / "synthetic"
    (root / "pkg").mkdir(parents=True)
    codes = {
        "pkg.mod.x_f__mutmut_1": 1,
        "pkg.mod.x_f__mutmut_2": 0,
        "pkg.mod.xǁKǁ__init____mutmut_3": 33,
        "pkg.mod.x_g__mutmut_4": None,
        "pkg.mod.x_g__mutmut_5": 36,
        "pkg.mod.x_g__mutmut_6": -11,
    }
    (root / "pkg" / "mod.py.meta").write_text(
        json.dumps({"exit_code_by_key": codes}), encoding="utf-8"
    )
    totals = {
        "killed": 1,
        "survived": 1,
        "total": 6,
        "no_tests": 1,
        "skipped": 0,
        "suspicious": 0,
        "timeout": 1,
        "check_was_interrupted_by_user": 0,
        "segfault": 1,
    }
    (root / "mutmut-cicd-stats.json").write_text(json.dumps(totals), encoding="utf-8")
    s = parse.summarize(root, None)
    check(
        "not measured counts no tests and not checked",
        s["counts"]["not_measured"] == 2,
        str(s["counts"]),
    )
    check(
        "not measured never in survivors", all("mutmut_3" not in x["key"] for x in s["survivors"])
    )
    check("method key described", any(x["function"] == "K.__init__" for x in s["not_measured"]))
    check("score excludes not measured and unclear", s["score"] == round(1 / 3, 4), str(s["score"]))
    check(
        "segfault is unclear",
        s["counts"]["unclear"] == 1 and s["unclear"][0]["status"] == "segfault",
    )


def make_root(name: str, pyproject: str = "[project]\nname = 'x'\n") -> Path:
    root = SCRATCH / name
    (root / "scripts" / "pkg").mkdir(parents=True)
    (root / "scripts" / "pkg" / "mod.py").write_text("X = 1\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_mod.py").write_text("def test_x():\n    pass\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return root


def write_list(root: Path, text: str) -> Path:
    path = root / "modules.yml"
    path.write_text(text, encoding="utf-8")
    return path


def check_run(run) -> None:
    for bad in ("/abs.py", "a/../b.py", "a\\b.py", ""):
        try:
            run.checked_relative(bad, "x")
            check(f"path refused: {bad!r}", False)
        except run.InputError:
            check(f"path refused: {bad!r}", True)

    root = make_root("run-ok")
    good = "version: 1\nmodules:\n  - module: scripts/pkg/mod.py\n    tests: [tests/test_mod.py]\n"
    entries = run.load_list(write_list(root, good))
    check(
        "list loads", entries == [{"module": "scripts/pkg/mod.py", "tests": ["tests/test_mod.py"]}]
    )
    check("pick by stem", run.pick(entries, "mod")["module"] == "scripts/pkg/mod.py")
    for name, text in {
        "extra key": good + "extra: 1\n",
        "duplicate module": good
        + "  - module: scripts/pkg/mod.py\n    tests: [tests/test_mod.py]\n",
        "empty tests": "version: 1\nmodules:\n  - module: scripts/pkg/mod.py\n    tests: []\n",
        "wrong version": good.replace("version: 1", "version: 2"),
    }.items():
        try:
            run.load_list(write_list(root, text))
            check(f"list refused: {name}", False)
        except run.InputError:
            check(f"list refused: {name}", True)

    run.check_root(root, "scripts/pkg/mod.py", ["tests/test_mod.py"])
    config = run.write_config(root, "scripts/pkg/mod.py", ["tests/test_mod.py"])
    text = config.read_text(encoding="utf-8")
    check("config: source path", "source_paths =\n    scripts\n" in text, text)
    check("config: only this module", "only_mutate =\n    *scripts/pkg/mod.py\n" in text, text)
    check(
        "config: also_copy has tests, not scripts or .git",
        "\n    tests" in text.split("also_copy =")[1].split("pytest_add")[0]
        and "\n    scripts" not in text.split("also_copy =")[1].split("pytest_add")[0]
        and ".git" not in text,
        text,
    )
    check("config: git change detection off", "use_git_change_detection = false" in text)
    try:
        run.check_root(root, "scripts/pkg/mod.py", ["tests/test_mod.py"])
        check("existing setup.cfg refused", False)
    except run.InputError:
        check("existing setup.cfg refused", True)
    config.unlink()

    tool_root = make_root("run-tool", "[tool.mutmut]\nsource_paths = ['scripts']\n")
    try:
        run.check_root(tool_root, "scripts/pkg/mod.py", ["tests/test_mod.py"])
        check("[tool.mutmut] refused", False)
    except run.InputError:
        check("[tool.mutmut] refused", True)

    link_root = make_root("run-link")
    outside = SCRATCH / "outside-target.cfg"
    (link_root / "setup.cfg").symlink_to(outside)
    try:
        run.check_root(link_root, "scripts/pkg/mod.py", ["tests/test_mod.py"])
        check("dangling setup.cfg symlink refused", False)
    except run.InputError:
        check("dangling setup.cfg symlink refused", True)
    check("nothing written through the link", not outside.exists())
    (link_root / "setup.cfg").unlink()
    (link_root / "mutants").symlink_to(SCRATCH)
    try:
        run.check_root(link_root, "scripts/pkg/mod.py", ["tests/test_mod.py"])
        check("symlinked mutants/ refused", False)
    except run.InputError:
        check("symlinked mutants/ refused", True)
    (link_root / "mutants").unlink()
    elsewhere = SCRATCH / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "out.py").write_text("X = 2\n", encoding="utf-8")
    (elsewhere / "test_out.py").write_text("def test_y():\n    pass\n", encoding="utf-8")
    (link_root / "scripts" / "pkg" / "out.py").symlink_to(elsewhere / "out.py")
    (link_root / "tests" / "test_out.py").symlink_to(elsewhere / "test_out.py")
    (link_root / "tests2").symlink_to(elsewhere)
    (link_root / "tests" / "test_in.py").symlink_to(link_root / "tests" / "test_mod.py")
    for name, module, tests in (
        ("module", "scripts/pkg/out.py", ["tests/test_mod.py"]),
        ("test", "scripts/pkg/mod.py", ["tests/test_out.py"]),
        ("test under a linked directory", "scripts/pkg/mod.py", ["tests2/test_out.py"]),
    ):
        try:
            run.check_root(link_root, module, tests)
            check(f"{name} symlinked outside the root refused", False)
        except run.InputError as exc:
            check(f"{name} symlinked outside the root refused", "outside" in str(exc), str(exc))
    run.check_root(link_root, "scripts/pkg/mod.py", ["tests/test_mod.py", "tests/test_in.py"])
    check("plain paths and a link inside the root still accepted", True)
    for bad in ("tests/-p.py", "tests/a\nb.py", "-x"):
        try:
            run.checked_relative(bad, "x")
            check(f"unsafe name refused: {bad!r}", False)
        except run.InputError:
            check(f"unsafe name refused: {bad!r}", True)

    code, _, err = call(
        run.main,
        ["--root", str(root), "--source", "scripts/pkg/missing.py", "--tests", "tests/test_mod.py"],
    )
    check("missing module: exit 2", code == 2 and "not a .py file" in err, err)
    code, _, err = call(run.main, ["--root", str(root), "--module", "mod"])
    check("no list file: exit 2", code == 2, err)
    code, _, err = call(
        run.main,
        [
            "--root",
            str(root),
            "--list",
            str(write_list(root, good)),
            "--module",
            "mod",
            "--show",
            "bad;key",
        ],
    )
    check("bad --show key: exit 2", code == 2 and "not a mutant key" in err, err)
    (root / "mutants").mkdir()
    code, _, err = call(
        run.main, ["--root", str(root), "--list", str(write_list(root, good)), "--module", "mod"]
    )
    check("leftover mutants/ refused: exit 2", code == 2 and "already holds mutants" in err, err)
    (root / "mutants").rmdir()
    check(
        "real key accepted",
        bool(
            run.is_mutant_key(
                "scripts.marketplace_ci.trust_boundary.x_find_tier1_touches__mutmut_8"
            )
        ),
    )
    check("method key accepted", run.is_mutant_key("a.b.xǁFooǁ__init____mutmut_3"))
    for bad_key in (
        "a.x_f__mutmut_",
        "a.x_f",
        ".x_f__mutmut_1",
        "a.x_f g__mutmut_1",
        "a.xǁFooǁ__mutmut_1",
    ):
        check(f"key rejected: {bad_key!r}", not run.is_mutant_key(bad_key))
    long_key = "a" * 50000 + ".x_" + "_" * 50000 + "__mutmut_"
    started = time.perf_counter()
    rejected = not run.is_mutant_key(long_key)
    check("long key rejected in linear time", rejected and time.perf_counter() - started < 1.0)
    check("python3 found next to this interpreter", run.python_env() is not None)
    planted = {
        "QLTY_SMOKE_TOKEN": "s3cr3t",
        "PYTHON_SMOKE_TOKEN": "s3cr3t",
        "PYTHON_SMOKE_INDEX_URL": "https://u:pw@example.invalid/simple",
        "LC_SMOKE": "x",
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "HOME": "/h",
    }
    saved_env = {name: os.environ.get(name) for name in planted}
    try:
        os.environ.update(planted)
        child = run.python_env() or {}
        check("secret variable not passed to tests", "QLTY_SMOKE_TOKEN" not in child)
        check("secret-like PYTHON* name not passed to tests", "PYTHON_SMOKE_TOKEN" not in child)
        check("unlisted PYTHON* name not passed to tests", "PYTHON_SMOKE_INDEX_URL" not in child)
        check("unlisted LC_* name not passed to tests", "LC_SMOKE" not in child)
        check(
            "HOME, a listed LC_* and a listed PYTHON* name passed to tests",
            child.get("HOME") == "/h"
            and child.get("LC_ALL") == "C.UTF-8"
            and child.get("PYTHONHASHSEED") == "0",
        )
    finally:
        for name, value in saved_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    # An unknown interpreter (empty sys.executable) is refused, even with a python3 in the cwd.
    decoy = Path(tempfile.mkdtemp())
    (decoy / "python3").write_text("#!/bin/sh\n", encoding="utf-8")
    (decoy / "python3").chmod(0o700)
    saved_exe, saved_cwd = sys.executable, Path.cwd()
    try:
        sys.executable = ""
        os.chdir(decoy)
        check("empty sys.executable refused", run.python_env() is None)
    finally:
        sys.executable = saved_exe
        os.chdir(saved_cwd)
        shutil.rmtree(decoy)
    code, out, _ = call(
        run.main, ["--root", str(root), "--list", str(write_list(root, good)), "--list-modules"]
    )
    check("--list-modules", code == 0 and json.loads(out) == ["scripts/pkg/mod.py"], out)
    check("no setup.cfg left behind", not (root / "setup.cfg").exists())


def check_skill() -> None:
    text = SKILL.read_text(encoding="utf-8")
    header = text.split("---", 2)[1]
    check("grant: list modules", 'qlty-mutation-run.py" --list-modules' in header)
    check("parser not pre-approved (the agent runs it)", "qlty-mutation-parse.py" not in header)
    grants = header.split("allowed-tools:")[1]
    check("Edit and Write pre-approved", "Edit" in grants and "Write" in grants)
    check(
        "writes gated on the user's approval of the exact text",
        "after the user approved its exact text in Step 4" in text
        and "after the user\napproved its exact text in Step 5" in text,
    )
    check(
        "a module is added to the weekly list only after a finished run",
        "## Step 5: Add to the weekly run" in text and "runner status\nwas `0`" in text,
    )


def main() -> int:
    try:
        import yaml  # noqa: F401  # type: ignore[import-untyped]
    except ImportError:
        print("SKIP: PyYAML is not installed; run with `uv run --with pyyaml`")
        return 1
    parse = load(PARSE_SCRIPT, "qlty_mutation_parse")
    guarded("parser on real output", lambda: check_parse_real(parse))
    guarded("parser refusals", lambda: check_parse_refusals(parse))
    guarded("parser classes", lambda: check_parse_classes(parse))
    run = load(RUN_SCRIPT, "qlty_mutation_run")
    guarded("runner", lambda: check_run(run))
    guarded("skill", check_skill)
    print(f"\n{'FAILED' if failures else 'OK'}: {len(failures)} failing check(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
