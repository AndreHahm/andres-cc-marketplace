#!/usr/bin/env python3
"""Run mutmut on one module with its own test selection, in a run tree that may be changed.

The module and its tests come from a module list file (`--list`, default
`.github/mutation-modules.yml`) or from `--source` plus `--tests`. The list file is YAML:

  version: 1
  modules:
    - module: scripts/marketplace_ci/pr_policy.py
      tests:
        - tests/marketplace_ci/test_pr_policy.py

Steps, all inside `--root` (default: the current directory):
  1. Baseline: run pytest on the selection; a red baseline stops the run (exit 4).
  2. Write mutmut's configuration to a new `setup.cfg` (`[mutmut]`): the module's top directory as
     `source_paths`, the module as `only_mutate`, every other top-level path as `also_copy` (the
     tests read repository files), the selection, and `use_git_change_detection = false`.
  3. `mutmut run`, then `mutmut export-cicd-stats`; remove the `setup.cfg` again.

The run tree gets `mutants/` and, for the run's length, `setup.cfg`: use a CI checkout or an
isolated copy, never a working tree with changes you want to keep. It refuses a root whose
`setup.cfg` exists or whose `pyproject.toml` already has `[tool.mutmut]`, a run in a root that
already holds `mutants/` (mutmut would keep the old verdicts), and a module or test path that
resolves outside the root (a symbolic link pointing elsewhere).

Usage (mutmut and PyYAML come from uv):
  uv run --with mutmut==3.8.1 --with pyyaml python qlty-mutation-run.py --module pr_policy
  uv run --with mutmut==3.8.1 python qlty-mutation-run.py --source scripts/x/y.py \
      --tests tests/test_y.py
  qlty-mutation-run.py --list-modules        print the list file's module paths as JSON, then exit
  ... --module pr_policy --show KEY [KEY...]   after a run: print those mutants' diffs (mutmut show
                                               needs the same configuration, so it is written again)

Exit codes: mutmut's own exit status from `mutmut run` (0 when it finished, whatever survived), or
that of `export-cicd-stats` when the run returned 0; 2 invalid input; 3 PyYAML or mutmut missing, or
no python3 next to the running interpreter that is that interpreter; 4 red baseline.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess  # nosec B404  # runs pytest and mutmut with fixed argument lists, never a shell
import sys
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

EXIT_INPUT = 2
EXIT_NO_PACKAGE = 3
EXIT_RED_BASELINE = 4

DEFAULT_LIST = ".github/mutation-modules.yml"
NEVER_COPY = {".git", ".venv", "node_modules", "mutants", "setup.cfg"}
# Control characters would add lines to setup.cfg; a leading "-" would reach pytest as an option.
UNSAFE_NAME = re.compile(r"[\x00-\x1f\x7f]|^-")
# A mutmut 3.8.1 mutant key: "<module>.x_<function>__mutmut_<n>" or
# "<module>.xǁ<Class>ǁ<method>__mutmut_<n>". Checked piecewise in is_mutant_key, because one regex
# for the whole key backtracks super-linearly (Sonar S8786).
KEY_MODULE = re.compile(r"[\w.]+")
KEY_NAME = re.compile(r"[^\sǁ]+")


class InputError(Exception):
    """The list file, the selection or the run tree is not usable."""


def is_mutant_key(key: str) -> bool:
    head, sep, number = key.rpartition("__mutmut_")
    if not (sep and number.isdecimal()):
        return False
    parts = head.split("ǁ")
    if len(parts) == 3:  # <module>.xǁ<Class>ǁ<method>
        module, cls, name = parts
        return (
            module.endswith(".x")
            and KEY_MODULE.fullmatch(module[:-2]) is not None
            and KEY_NAME.fullmatch(cls) is not None
            and KEY_NAME.fullmatch(name) is not None
        )
    # <module>.x_<function>: the first ".x_" gives the longest valid function name, and a module
    # part failing [\w.]+ there fails for every later ".x_" too.
    cut = head.find(".x_", 1)
    return (
        len(parts) == 1
        and cut > 0
        and KEY_MODULE.fullmatch(head[:cut]) is not None
        and KEY_NAME.fullmatch(head[cut + 3 :]) is not None
    )


def checked_relative(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise InputError(f"{what} must be a non-empty string")
    if any(UNSAFE_NAME.search(part) for part in value.split("/")):
        raise InputError(f"{what} has a control character or a leading '-': {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise InputError(f"{what} must be a relative path inside the run tree: {value!r}")
    return path.as_posix()


def load_list(path: Path) -> list[dict[str, Any]]:
    try:
        import yaml
    except ImportError as exc:
        raise ModuleNotFoundError(
            "PyYAML is not installed; run with `uv run --with pyyaml`"
        ) from exc
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise InputError(f"{path}: not readable YAML ({exc})") from exc
    if (
        not isinstance(data, dict)
        or data.get("version") != 1
        or set(data) != {"version", "modules"}
    ):
        raise InputError(f"{path}: expected exactly the keys version (1) and modules")
    modules = data["modules"]
    if not isinstance(modules, list) or not modules:
        raise InputError(f"{path}: modules must be a non-empty list")
    entries = []
    for index, entry in enumerate(modules):
        if not isinstance(entry, dict) or set(entry) != {"module", "tests"}:
            raise InputError(f"{path}: modules[{index}] must have exactly module and tests")
        tests = entry["tests"]
        if not isinstance(tests, list) or not tests:
            raise InputError(f"{path}: modules[{index}].tests must be a non-empty list")
        entries.append(
            {
                "module": checked_relative(entry["module"], f"modules[{index}].module"),
                "tests": [checked_relative(t, f"modules[{index}].tests") for t in tests],
            }
        )
    seen = [e["module"] for e in entries]
    if len(seen) != len(set(seen)):
        raise InputError(f"{path}: a module is listed twice")
    return entries


def pick(entries: list[dict[str, Any]], name: str) -> dict[str, Any]:
    matches = [e for e in entries if e["module"] == name or PurePosixPath(e["module"]).stem == name]
    if len(matches) != 1:
        raise InputError(f"{name!r} matches {len(matches)} modules in the list file")
    return matches[0]


def check_root(root: Path, module: str, tests: list[str]) -> None:
    for name in ("setup.cfg", "mutants"):
        if (root / name).is_symlink():
            raise InputError(f"{root / name} is a symbolic link; refusing to write through it")
    if os.path.lexists(root / "setup.cfg"):
        raise InputError(
            f"{root / 'setup.cfg'} exists; this runner writes its own and will not replace it"
        )
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise InputError(f"{pyproject}: not readable TOML ({exc})") from exc
        if "mutmut" in data.get("tool", {}):
            raise InputError(
                f"{pyproject} has [tool.mutmut], which mutmut would read instead of setup.cfg"
            )
    if not module.endswith(".py") or not (root / module).is_file():
        raise InputError(f"module {module} is not a .py file under {root}")
    if len(PurePosixPath(module).parts) < 2:
        raise InputError(
            f"module {module} must sit in a directory, which becomes mutmut's source path"
        )
    missing = [t for t in tests if not (root / t).exists()]
    if missing:
        raise InputError(f"test paths not found under {root}: {', '.join(missing)}")
    # A symbolic link may point anywhere; pytest and mutmut would follow it out of the run tree.
    # This covers the listed paths (any link along them), not links inside a test directory.
    base = root.resolve()
    outside = [p for p in (module, *tests) if not (root / p).resolve().is_relative_to(base)]
    if outside:
        raise InputError(f"paths resolve outside {root}: {', '.join(outside)}")


def cfg_list(values: list[str]) -> str:
    return "".join(f"\n    {v}" for v in values)


def write_config(root: Path, module: str, tests: list[str]) -> Path:
    source = PurePosixPath(module).parts[0]
    also_copy = sorted(
        p.name
        for p in root.iterdir()
        if p.name not in NEVER_COPY and p.name != source and not UNSAFE_NAME.search(p.name)
    )
    text = (
        "# Written by quality-kit's qlty-mutation-run.py for one run; removed when the run ends.\n"
        "[mutmut]\n"
        f"source_paths ={cfg_list([source])}\n"
        f"only_mutate ={cfg_list(['*' + module])}\n"
        f"also_copy ={cfg_list(also_copy)}\n"
        f"pytest_add_cli_args_test_selection ={cfg_list(tests)}\n"
        f"pytest_add_cli_args ={cfg_list(['-p', 'no:cacheprovider', '-q'])}\n"
        "use_git_change_detection = false\n"
    )
    path = root / "setup.cfg"
    # "x": create only, never through a file or symbolic link planted since check_root.
    with open(path, "x", encoding="utf-8") as handle:
        handle.write(text)
    return path


def python_env() -> dict[str, str] | None:
    # The subprocess calls below start a literal "python3" (Semgrep's subprocess audit flags any
    # computed command, sys.executable included). Putting the running interpreter's own folder first
    # on PATH makes that "python3" the same environment, so pytest and mutmut stay importable. None
    # when that folder holds no python3 that is this interpreter: never fall back further down PATH.
    if not sys.executable:  # unknown interpreter: abspath("") would mean the current directory
        return None
    folder = os.path.abspath(os.path.dirname(sys.executable))
    found = shutil.which("python3", path=folder)
    if found is None or not os.path.samefile(found, sys.executable):
        return None
    return {**os.environ, "PATH": folder + os.pathsep + os.environ.get("PATH", "")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="the run tree (default: cwd)")
    parser.add_argument(
        "--list", type=Path, help=f"module list file (default: <root>/{DEFAULT_LIST})"
    )
    parser.add_argument("--module", help="a module path or file stem from the list file")
    parser.add_argument(
        "--source", help="a module path, used with --tests instead of the list file"
    )
    parser.add_argument("--tests", nargs="+", help="the test selection for --source")
    parser.add_argument(
        "--list-modules", action="store_true", help="print the list's modules as JSON"
    )
    parser.add_argument(
        "--show",
        nargs="+",
        metavar="KEY",
        help="after a run: print these mutants' diffs (mutmut show) instead of running",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    list_path = args.list or root / DEFAULT_LIST
    try:
        if args.list_modules:
            print(json.dumps([e["module"] for e in load_list(list_path)]))
            return 0
        if args.source and args.tests and not args.module:
            module = checked_relative(args.source, "--source")
            tests = [checked_relative(t, "--tests") for t in args.tests]
        elif args.module and not (args.source or args.tests):
            entry = pick(load_list(list_path), args.module)
            module, tests = entry["module"], entry["tests"]
        else:
            raise InputError("give either --module, or --source with --tests")
        bad = [k for k in args.show or [] if not is_mutant_key(k)]
        if bad:
            raise InputError(f"not a mutant key: {', '.join(bad)}")
        check_root(root, module, tests)
        # mutmut keeps an existing mutants/ verdict unless the function's source changed, so a
        # re-run after a test was strengthened would report old survivors as freshly measured.
        if not args.show and os.path.lexists(root / "mutants"):
            raise InputError(f"{root} already holds mutants/ from a run; use a fresh run tree")
    except InputError as exc:
        print(f"qlty-mutation-run: {exc}", file=sys.stderr)
        return EXIT_INPUT
    except ModuleNotFoundError as exc:
        print(f"qlty-mutation-run: {exc}", file=sys.stderr)
        return EXIT_NO_PACKAGE
    if importlib.util.find_spec("mutmut") is None:
        print(
            "qlty-mutation-run: mutmut is not installed; run with `uv run --with mutmut==3.8.1`",
            file=sys.stderr,
        )
        return EXIT_NO_PACKAGE
    env = python_env()
    if env is None:
        print(
            f"qlty-mutation-run: no python3 next to {sys.executable} that is the same interpreter;"
            " run it from a venv",
            file=sys.stderr,
        )
        return EXIT_NO_PACKAGE

    if args.show:
        if not (root / "mutants").is_dir():
            print(f"qlty-mutation-run: no mutants/ under {root}; run first", file=sys.stderr)
            return EXIT_INPUT
        config = write_config(root, module, tests)
        try:
            for key in args.show:
                status = subprocess.run(  # nosec B603 B607  # literal python3 from python_env, checked key
                    ["python3", "-m", "mutmut", "show", key], cwd=root, env=env, check=False
                ).returncode
                if status != 0:
                    print(f"qlty-mutation-run: mutmut show {key} exited {status}", file=sys.stderr)
                    return status
            return 0
        finally:
            config.unlink(missing_ok=True)

    print(f"qlty-mutation-run: baseline for {module}: pytest {' '.join(tests)}", file=sys.stderr)
    baseline = subprocess.run(  # nosec B603 B607  # literal python3 from python_env, checked paths
        ["python3", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--", *tests],
        cwd=root,
        env=env,
        check=False,
    ).returncode
    if baseline != 0:
        print(
            f"qlty-mutation-run: the baseline is red (pytest exit {baseline}); no mutation run",
            file=sys.stderr,
        )
        return EXIT_RED_BASELINE

    config = write_config(root, module, tests)
    try:
        status = subprocess.run(  # nosec B603 B607  # literal command, python3 from python_env
            ["python3", "-m", "mutmut", "run"], cwd=root, env=env, check=False
        ).returncode
        if status != 0:
            print(f"qlty-mutation-run: mutmut run exited {status}", file=sys.stderr)
            return status
        status = subprocess.run(  # nosec B603 B607  # literal command, python3 from python_env
            ["python3", "-m", "mutmut", "export-cicd-stats"], cwd=root, env=env, check=False
        ).returncode
        if status != 0:
            print(f"qlty-mutation-run: mutmut export-cicd-stats exited {status}", file=sys.stderr)
        return status
    finally:
        config.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
