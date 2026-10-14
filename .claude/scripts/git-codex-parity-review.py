#!/usr/bin/env python3
"""Run this repository's CI `Codex delta review` locally, with CI's own settings.

`create-pr` calls this before the first push so blocking findings the CI job would raise
surface locally instead of one CI round at a time (issue #540). It wraps the exact entry
point the workflow uses (`python -m scripts.marketplace_ci run-codex-review`) and reads the
settings that must match CI from the workflow file itself, so they cannot drift:

  - CODEX_KIT_REVIEW_TIMEOUT_MS: the repository variable of that name when it is set to a valid
    number (as in CI, where the workflow takes `vars.CODEX_KIT_REVIEW_TIMEOUT_MS || '<fallback>'`),
    else the fallback parsed from .github/workflows/marketplace-ci.yml.
  - Codex CLI pin: parsed from the same file; a differing local version only warns.
  - Warns when the branch changed a Tier-1 file (list read from the base-tip copy).
  - Base: `origin/main` is fetched first (best effort); its tip SHA, used as CI's base.sha, is
    printed.
  - CODEX_KIT_REVIEW_MODEL: a repository variable (vars.*), not a workflow value, so it is
    read with `gh variable list --json`; when unset or unreadable the local Codex default is used
    and that is stated in the output.

Exit codes: 0 clean, 1 blocking findings, 2 could not run (never a pass; this includes a missing,
malformed or contradictory result file, and a pre-existing or unwritable --output path), 3 not
applicable (this checkout has no marketplace CI to mirror).

This repository's own convention only.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

WORKFLOW = Path(".github/workflows/marketplace-ci.yml")
ENTRY_POINT = Path("scripts/marketplace_ci/__main__.py")
TRUST_BOUNDARY = "scripts/marketplace_ci/trust_boundary.py"
MODEL_VARIABLE = "CODEX_KIT_REVIEW_MODEL"
TIMEOUT_VARIABLE = "CODEX_KIT_REVIEW_TIMEOUT_MS"
# The CI job's own timeout-minutes is 45; stay under it so a hung run can't outlive CI's budget.
RUN_TIMEOUT_SECONDS = 45 * 60
# Bound for every helper call (git, gh, codex --version): a stalled network or a credential prompt
# must fall through to the documented warning / exit 2 path instead of hanging the gate.
_HELPER_TIMEOUT_SECONDS = 60
# A model slug is data from a repository variable; pass it on only if the bridge would accept it.
_MODEL_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")  # identical to bridge-invoke.mjs
# Group 1: a literal value. Group 2: the fallback N in the workflow's `vars.<NAME> || 'N'` form.
_TIMEOUT_RE = re.compile(
    r"CODEX_KIT_REVIEW_TIMEOUT_MS:\s*"
    r"(?:\"?(\d+)\"?|\$\{\{[^}]*\|\|\s*'(\d+)'\s*\}\})"
)
# A timeout variable is data too: positive, no leading zero, at most 9 digits (about 11 days).
_TIMEOUT_VALUE_RE = re.compile(r"^[1-9][0-9]{0,8}$")
_PIN_RE = re.compile(r"npm install -g @openai/codex@(\d+\.\d+\.\d+)")
_VERSION_RE = re.compile(r"\d+\.\d+\.\d+")
_SLUG_RE = re.compile(r"^(?:https://github\.com/|git@github\.com:)([\w.-]+/[\w.-]+?)(?:\.git)?$")


_STEP_RE = re.compile(r"^\s*- name:", re.MULTILINE)


def _step_block(workflow_text: str, name_prefix: str) -> str:
    """The text of the workflow step whose `- name:` starts with `name_prefix` ("" if absent)."""
    start = re.search(rf"^\s*- name: {re.escape(name_prefix)}", workflow_text, re.MULTILINE)
    if not start:
        return ""
    following = _STEP_RE.search(workflow_text, start.end())
    return workflow_text[start.start() : following.start() if following else len(workflow_text)]


def parse_ci_settings(workflow_text: str) -> tuple[str, str] | None:
    """Return (timeout_ms, codex_pin) from the codex-review job's own steps, or None if missing.

    Anchored to the named steps so a comment or another job elsewhere in the file can't match.
    """
    timeout = _TIMEOUT_RE.search(_step_block(workflow_text, "Dispatch reviewers directly"))
    pin = _PIN_RE.search(_step_block(workflow_text, "Install Codex CLI"))
    if not timeout or not pin:
        return None
    return timeout.group(1) or timeout.group(2), pin.group(1)


def _run(argv: list[str], **kwargs) -> subprocess.CompletedProcess[str] | None:
    kwargs.setdefault("timeout", _HELPER_TIMEOUT_SECONDS)
    try:
        return subprocess.run(argv, capture_output=True, text=True, check=False, **kwargs)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _run_in_group(
    argv: list[str], *, env: dict[str, str], timeout: float
) -> subprocess.CompletedProcess[str] | None:
    """Run `argv` in its own session so a timeout kills the whole tree (uv, node, codex)."""
    try:
        proc = subprocess.Popen(
            argv,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=os.name == "posix",
        )
    except FileNotFoundError:
        return None
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            # Without /T only the direct child dies; a surviving descendant keeps the pipes open.
            _run(["taskkill", "/F", "/T", "/PID", str(proc.pid)])
            proc.kill()
        try:
            proc.communicate(timeout=_HELPER_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            pass  # a descendant still holds the pipes; the run is already abandoned
        return None
    return subprocess.CompletedProcess(argv, proc.returncode, stdout, stderr)


def _origin_slug() -> str | None:
    """`owner/repo` of `origin`, so the variable lookup targets where this branch is pushed."""
    result = _run(["git", "remote", "get-url", "origin"])
    if result is None or result.returncode != 0:
        return None
    match = _SLUG_RE.match(result.stdout.strip())
    return match.group(1) if match else None


def _read_variable(name: str, pattern: re.Pattern[str]) -> str | None:
    """A repository variable's value if it is set and matches `pattern`, else None."""
    slug = _origin_slug()
    repo_args = ["--repo", slug] if slug else []
    # `gh variable get` only exists in newer gh releases (absent in 2.45.0); `list --json` is older.
    selector = f'.[] | select(.name == "{name}") | .value'
    result = _run(["gh", "variable", "list", "--json", "name,value", "--jq", selector, *repo_args])
    if result is None or result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value if pattern.match(value) else None


def resolve_model() -> str | None:
    return _read_variable(MODEL_VARIABLE, _MODEL_RE)


def resolve_timeout_ms(fallback: str) -> tuple[str, bool]:
    """(timeout_ms, from_variable): the repository variable when valid, as CI does, else the
    workflow's fallback."""
    value = _read_variable(TIMEOUT_VARIABLE, _TIMEOUT_VALUE_RE)
    return (value, True) if value else (fallback, False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", required=True, metavar="PATH", help="result JSON (scratch dir)")
    args = parser.parse_args()
    # abspath, not resolve(): never follow a final-component symlink, so the existence check below
    # sees the path the caller named (a symlink is refused), not its target. (Before the chdir.)
    output = Path(os.path.abspath(args.output))

    # Resolve paths against the checkout root, not the cwd: a session sitting in a subdirectory
    # must not look like "no marketplace CI here", the one outcome the caller treats as a skip.
    top = _run(["git", "rev-parse", "--show-toplevel"])
    if top is not None and top.returncode == 0 and top.stdout.strip():
        os.chdir(top.stdout.strip())

    if not WORKFLOW.is_file() or not ENTRY_POINT.is_file():
        print("PARITY: no marketplace CI in this checkout; nothing to run.")
        return 3

    settings = parse_ci_settings(WORKFLOW.read_text(encoding="utf-8"))
    if settings is None:
        print(f"PARITY: could not read the timeout and Codex pin from {WORKFLOW}.", file=sys.stderr)
        return 2
    timeout_ms, pin = settings

    codex = _run(["codex", "--version"])
    if codex is None or codex.returncode != 0:
        print("PARITY: the Codex CLI is not available locally; cannot run.", file=sys.stderr)
        return 2
    found = _VERSION_RE.search(codex.stdout)
    local_version = found.group(0) if found else "unknown"
    if local_version != pin:
        print(f"PARITY WARNING: local Codex CLI {local_version} differs from CI's pin {pin}.")

    # CI reviews against the PR's current base tip; a stale local origin/main would mean older
    # reviewer instructions.
    # The explicit refspec updates the tracking ref this script reads next, whatever the remote's
    # configured fetch refspec is (a plain `git fetch origin main` only does so under the default).
    fetch = _run(
        ["git", "fetch", "--quiet", "origin", "+refs/heads/main:refs/remotes/origin/main"],
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if fetch is None or fetch.returncode != 0:
        print("PARITY WARNING: could not fetch origin/main; the local ref may be stale.")

    # CI passes the PR's base *tip* (github.event.pull_request.base.sha), and the entry point reads
    # each reviewer's .codex/agents/<name>.toml from exactly that SHA, so a merge-base would run
    # stale reviewer instructions on a long-lived branch. The entry point takes its own three-dot
    # diff.
    tip = _run(["git", "rev-parse", "--verify", "origin/main^{commit}"])
    base_sha = tip.stdout.strip() if tip and tip.returncode == 0 else ""
    if not base_sha:
        print("PARITY: could not resolve origin/main.", file=sys.stderr)
        return 2
    print(f"PARITY: base {base_sha[:12]} (tip of origin/main, as CI's base.sha).")

    touched = tier1_touches(base_sha)
    if touched is None:
        print("PARITY WARNING: could not check whether review-dispatch files changed.")
    elif touched:
        print(
            "PARITY WARNING: this branch changes review-dispatch-critical files "
            f"({', '.join(touched)}). CI hard-refuses to dispatch on these, and this local run "
            "executes the branch's own copy of that code with your Codex credentials; treat a "
            "clean result as non-authoritative."
        )

    if (output.parent.resolve() / output.name).is_relative_to(Path.cwd().resolve()):
        print(f"PARITY: --output {output} is inside the checkout; use a scratch directory.")
        return 2
    # The child writes its result only after the whole (10 to 40 minute) review, so a missing or
    # unwritable directory must be caught here, not at the end of an expensive run.
    if not output.parent.is_dir() or not os.access(output.parent, os.W_OK):
        print(f"PARITY: the directory for --output ({output.parent}) is missing or not writable.")
        return 2
    # Never delete or overwrite anything: a pre-existing path (file, directory or symlink, even a
    # dangling one) is refused. The caller names a fresh file per run, so no stale result exists.
    if output.is_symlink():
        print(f"PARITY: --output is a symlink ({output}); pass a new path (nothing is followed).")
        return 2
    if output.exists():
        print(f"PARITY: {output} already exists; pass a new --output path (nothing is deleted).")
        return 2
    # Beside --output, so the per-reviewer instruction files never touch the checkout. Refused when
    # it already exists (symlinks included): the child would write through it.
    instructions_dir = output.with_name(f"{output.stem}-instructions")
    if instructions_dir.is_symlink() or instructions_dir.exists():
        print(f"PARITY: {instructions_dir} already exists; pass a new --output path.")
        return 2

    timeout_ms, timeout_from_variable = resolve_timeout_ms(timeout_ms)
    env: dict[str, str] = {**os.environ, TIMEOUT_VARIABLE: timeout_ms}
    print(
        f"PARITY: timeout {timeout_ms} ms "
        + (
            f"(from repository variable {TIMEOUT_VARIABLE})."
            if timeout_from_variable
            else f"(workflow fallback; {TIMEOUT_VARIABLE} unset or unreadable)."
        )
    )
    model = resolve_model()
    if model:
        env[MODEL_VARIABLE] = model
        print(f"PARITY: model {model} (from repository variable {MODEL_VARIABLE}).")
    else:
        env.pop(MODEL_VARIABLE, None)
        print(f"PARITY WARNING: {MODEL_VARIABLE} unset or unreadable; using the local default.")

    argv = [
        "uv", "run", "python", "-m", "scripts.marketplace_ci", "run-codex-review",
        "--base-sha", base_sha, "--instructions-dir", str(instructions_dir),
        "--output", str(output),
    ]  # fmt: skip
    result = _run_in_group(argv, env=env, timeout=RUN_TIMEOUT_SECONDS)
    if result is None:
        print("PARITY: run-codex-review could not be started or timed out.", file=sys.stderr)
        return 2
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode not in (0, 1):
        return 2
    # Fail closed: an exit status alone is not evidence that a review ran and what it concluded.
    blocking = _read_blocking(output)
    if blocking is None:
        print(f"PARITY: exit {result.returncode} but no valid result at {output}; cannot run.")
        return 2
    if blocking != (result.returncode == 1):
        print(f"PARITY: exit {result.returncode} contradicts the result (blocking={blocking}).")
        return 2
    return result.returncode


# Keys every completed run-codex-review result carries (scripts/marketplace_ci/__main__.py
# builds the payload; a drift test checks each is still written there).
_RESULT_LIST_KEYS = ("reviewed_paths", "reviewers", "structural_findings", "findings")


def _read_blocking(output: Path) -> bool | None:
    """`blocking` of a completed run-codex-review result, or None if the file isn't one.

    Completed means the payload `_handle_run_codex_review` writes: a non-empty string `mode`, the
    list fields above, and a boolean `blocking`. Anything else (missing, unreadable, truncated, or
    the entry point's `error` payload) is not evidence that a review ran.
    """
    try:
        data = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    mode, blocking = data.get("mode"), data.get("blocking")
    if not (isinstance(mode, str) and mode and isinstance(blocking, bool)):
        return None
    if not all(isinstance(data.get(key), list) for key in _RESULT_LIST_KEYS):
        return None
    return blocking


def tier1_touches(base_sha: str) -> list[str] | None:
    """Tier-1 (review-dispatch-critical) files this branch changed since `base_sha`, or None.

    CI hard-refuses to dispatch when a PR changes these, because the PR would control the code
    that runs with the review credentials. The file list is read from the `base_sha` copy of
    trust_boundary.py, never the branch's own copy, so the branch cannot shrink it.
    """
    shown = _run(["git", "show", f"{base_sha}:{TRUST_BOUNDARY}"])
    if shown is None or shown.returncode != 0:
        return None
    try:
        for node in ast.parse(shown.stdout).body:
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and any(isinstance(t, ast.Name) and t.id == "TIER1_FILES" for t in node.targets)
            ):
                paths = sorted(ast.literal_eval(node.value.args[0]))  # frozenset({...})
                break
        else:
            return None
    except (
        SyntaxError,
        ValueError,
        AttributeError,
        IndexError,
        TypeError,
        RecursionError,
        MemoryError,
    ):
        return None
    diff = _run(["git", "diff", "--name-only", f"{base_sha}...HEAD", "--", *paths])
    if diff is None or diff.returncode != 0:
        return None
    return [line for line in diff.stdout.splitlines() if line]


def _guarded_main() -> int:
    # An uncaught exception would exit 1, which the caller reads as "blocking findings".
    try:
        return main()
    except Exception as exc:
        print(f"PARITY: unexpected failure: {exc!r}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(_guarded_main())
