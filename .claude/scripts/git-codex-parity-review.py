#!/usr/bin/env python3
"""Run this repository's CI `Codex delta review` locally, with CI's own settings.

`create-pr` calls this before the first push so blocking findings the CI job would raise
surface locally instead of one CI round at a time (issue #540). It wraps the exact entry
point the workflow uses (`python -m scripts.marketplace_ci run-codex-review`) and reads the
settings that must match CI from the workflow file itself, so they cannot drift:

  - CODEX_KIT_REVIEW_TIMEOUT_MS: parsed from .github/workflows/marketplace-ci.yml.
  - Codex CLI pin: parsed from the same file; a differing local version only warns.
  - CODEX_KIT_REVIEW_MODEL: a repository variable (vars.*), not a workflow value, so it is
    read with `gh variable get`; when unset or unreadable the local Codex default is used and
    that is stated in the output.

Exit codes: 0 clean, 1 blocking findings, 2 could not run (never a pass), 3 not applicable
(this checkout has no marketplace CI to mirror).

This repository's own convention only.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

WORKFLOW = Path(".github/workflows/marketplace-ci.yml")
ENTRY_POINT = Path("scripts/marketplace_ci/__main__.py")
MODEL_VARIABLE = "CODEX_KIT_REVIEW_MODEL"
# The CI job's own timeout-minutes is 45; stay under it so a hung run can't outlive CI's budget.
RUN_TIMEOUT_SECONDS = 45 * 60
# A model slug is data from a repository variable; only pass it on if it looks like one.
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}$")
_TIMEOUT_RE = re.compile(r'CODEX_KIT_REVIEW_TIMEOUT_MS:\s*"?(\d+)"?')
_PIN_RE = re.compile(r"npm install -g @openai/codex@(\d+\.\d+\.\d+)")
_VERSION_RE = re.compile(r"\d+\.\d+\.\d+")


def parse_ci_settings(workflow_text: str) -> tuple[str, str] | None:
    """Return (timeout_ms, codex_pin) from the workflow text, or None if either is missing."""
    timeout = _TIMEOUT_RE.search(workflow_text)
    pin = _PIN_RE.search(workflow_text)
    if not timeout or not pin:
        return None
    return timeout.group(1), pin.group(1)


def _run(argv: list[str], **kwargs) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(argv, capture_output=True, text=True, check=False, **kwargs)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def resolve_model() -> str | None:
    result = _run(["gh", "variable", "get", MODEL_VARIABLE])
    if result is None or result.returncode != 0:
        return None
    model = result.stdout.strip()
    return model if _MODEL_RE.match(model) else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", required=True, metavar="PATH", help="result JSON (scratch dir)")
    args = parser.parse_args()

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

    merge_base = _run(["git", "merge-base", "origin/main", "HEAD"])
    base_sha = merge_base.stdout.strip() if merge_base and merge_base.returncode == 0 else ""
    if not base_sha:
        print("PARITY: could not resolve the merge base with origin/main.", file=sys.stderr)
        return 2

    # A stale result from an earlier run must never be mistaken for this run's findings.
    Path(args.output).unlink(missing_ok=True)

    env = {**os.environ, "CODEX_KIT_REVIEW_TIMEOUT_MS": timeout_ms}
    model = resolve_model()
    if model:
        env[MODEL_VARIABLE] = model
        print(f"PARITY: model {model} (from repository variable {MODEL_VARIABLE}).")
    else:
        env.pop(MODEL_VARIABLE, None)
        print(f"PARITY WARNING: {MODEL_VARIABLE} unset or unreadable; using the local default.")

    argv = [
        "uv", "run", "python", "-m", "scripts.marketplace_ci", "run-codex-review",
        "--base-sha", base_sha, "--output", args.output,
    ]  # fmt: skip
    result = _run(argv, env=env, timeout=RUN_TIMEOUT_SECONDS)
    if result is None:
        print("PARITY: run-codex-review could not be started or timed out.", file=sys.stderr)
        return 2
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode if result.returncode in (0, 1) else 2


def _guarded_main() -> int:
    # An uncaught exception would exit 1, which the caller reads as "blocking findings".
    try:
        return main()
    except Exception as exc:
        print(f"PARITY: unexpected failure: {exc!r}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(_guarded_main())
