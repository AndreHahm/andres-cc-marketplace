#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""Dispatch work-transition-reviewer / work-intake-classifier live through
codex-kit's codex-review-bridge (see plugins/codex-kit/skills/codex-review-bridge/SKILL.md).

Reads the target agent's .md file, strips its YAML frontmatter, writes the body
to a scratch instruction file outside --target-paths (the bridge's own
containment check rejects a nested/equal path), then calls bridge-invoke.mjs
and returns the parsed canonical envelope (or typed failure) as a dict.

Per GitHub issue #251 / plugins/workmanagement-kit/FOUNDATION_CONTRACTS.md.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

AGENTS = {"work-transition-reviewer", "work-intake-classifier"}

# Same charset/length bridge-invoke.mjs's own isValidToken enforces on
# --dispatch-id (^[A-Za-z0-9._-]{1,64}$) -- mirrored here deliberately so this
# script never constructs a filesystem path from an unvalidated dispatch_id
# before handing off to a separate process that would reject it anyway.
_DISPATCH_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def repo_root_from(start: Path) -> Path:
    cur = start.resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".git").exists():
            return parent
    raise SystemExit(f"could not resolve repo root from {start}")


def strip_frontmatter(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[i + 1 :]).lstrip("\n")
    return text


def dispatch(
    agent: str,
    target_paths: list[str],
    dispatch_id: str,
    execution_profile: str,
    dry_run: bool,
    repo_root: str | None = None,
    cwd: str | None = None,
) -> dict:
    if agent not in AGENTS:
        raise ValueError(f"unknown agent {agent!r}, expected one of {sorted(AGENTS)}")
    if not target_paths:
        raise ValueError("target_paths must be non-empty")
    # bridge-invoke.mjs itself refuses danger-full-access -- rejected here too,
    # as a local, no-cost defense-in-depth check across the process boundary,
    # not a replacement for the bridge's own authoritative refusal.
    if execution_profile == "danger-full-access":
        raise ValueError(
            "execution_profile 'danger-full-access' is always refused by "
            "codex-review-bridge -- use codex-windows-guardrails instead for that profile"
        )
    # Validated before any path is constructed from it -- dispatch_id is
    # caller-supplied and was previously interpolated straight into a
    # filesystem path with no check, letting a value like "../../foo" write
    # the agent body outside the intended scratch directory (found by
    # security-reviewer, see GitHub issue #251's finalize session).
    if not _DISPATCH_ID_RE.match(dispatch_id):
        raise ValueError(
            f"dispatch_id {dispatch_id!r} does not match {_DISPATCH_ID_RE.pattern} "
            "-- refusing to use it in a filesystem path"
        )

    plugin_root = Path(__file__).resolve().parent.parent
    root = Path(repo_root).resolve() if repo_root else repo_root_from(plugin_root)
    cwd_path = Path(cwd).resolve() if cwd else root
    # relposix() below computes every path relative to `root`, but --cwd is
    # what the dispatched Node process actually resolves relative paths
    # against -- an independently-supplied --cwd that diverges from root
    # would silently make every --target-paths/--instruction-file value
    # wrong from that process's own perspective (found by cross-model review,
    # GitHub issue #251's finalize session). Rejected here rather than
    # supporting two independent roots, which nothing currently needs.
    if cwd_path != root:
        raise ValueError(
            f"--cwd {cwd_path} must equal the resolved repo root {root} -- "
            "every path this script computes is relative to root, not an "
            "independently-configurable --cwd"
        )

    agent_file = plugin_root / "agents" / f"{agent}.md"
    if not agent_file.is_file():
        raise FileNotFoundError(agent_file)
    body = strip_frontmatter(agent_file.read_text(encoding="utf-8"))

    # Scratch instruction file: gitignored (**/.temp/), inside the repo root
    # (bridge-invoke.mjs's repo-root containment check requires this), and
    # deliberately outside any realistic --target-paths (evidence files),
    # never nested inside them. Path is computed and containment-checked
    # BEFORE any write happens -- every check below must pass first.
    scratch_dir = root / ".temp" / "workmanagement-kit-bridge"
    instruction_file = scratch_dir / f"{dispatch_id}-{agent}-instruction.md"

    resolved_targets = [Path(t).resolve() for t in target_paths]
    instr_resolved = scratch_dir.resolve() / instruction_file.name
    for tp in resolved_targets:
        if instr_resolved == tp or instr_resolved in tp.parents or tp in instr_resolved.parents:
            raise ValueError(
                f"instruction file {instr_resolved} is nested in/equal to target path {tp} "
                "-- codex-review-bridge's own containment check would reject this dispatch"
            )

    scratch_dir.mkdir(parents=True, exist_ok=True)
    instruction_file.write_text(body, encoding="utf-8")

    bridge_script = (
        root
        / "plugins"
        / "codex-kit"
        / "skills"
        / "codex-review-bridge"
        / "scripts"
        / "bridge-invoke.mjs"
    )
    if not bridge_script.is_file():
        raise FileNotFoundError(bridge_script)

    # bridge-invoke.mjs validates --target-paths/--instruction-file against
    # ^[A-Za-z0-9._/-]+$ -- no backslash (Windows' native separator) and no
    # colon (a Windows drive letter, e.g. "C:") are in that charset. An
    # absolute Windows path fails this check either way it's rendered, so
    # every path handed to the bridge must be relative to --cwd, using
    # forward slashes.
    def relposix(p: Path) -> str:
        return p.relative_to(root).as_posix()

    cmd = [
        "node",
        str(bridge_script),
        "--reviewer-type",
        agent,
        "--instruction-file",
        relposix(instruction_file.resolve()),
        "--target-paths",
        ",".join(relposix(tp) for tp in resolved_targets),
        "--execution-profile",
        execution_profile,
        "--dispatch-id",
        dispatch_id,
        "--cwd",
        cwd_path.as_posix(),
    ]
    if dry_run:
        cmd += ["--dry-run", "true"]

    # encoding="utf-8" is required explicitly -- subprocess.run's text=True
    # alone decodes with the platform's locale-preferred encoding (cp1252 on
    # a default Windows install, not UTF-8), which silently corrupts any
    # non-ASCII character (e.g. an em dash) the child process writes as UTF-8.
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=str(root))
    stdout = result.stdout.strip()
    try:
        payload = json.loads(stdout) if stdout else None
    except json.JSONDecodeError:
        payload = None

    if payload is None:
        return {
            "ok": False,
            "category": "bridge_caller_invocation_error",
            "detail": {
                "returncode": result.returncode,
                "stdout": stdout[-4000:],
                "stderr": result.stderr.strip()[-4000:],
            },
        }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", required=True, choices=sorted(AGENTS))
    parser.add_argument("--target-paths", required=True, help="comma-separated evidence paths")
    parser.add_argument("--dispatch-id", required=True)
    parser.add_argument("--execution-profile", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repo-root")
    parser.add_argument("--cwd")
    args = parser.parse_args()

    # Every one of dispatch()'s own precondition checks, and subprocess.run's
    # own OSError (e.g. node missing/unlaunchable), previously propagated as
    # an uncaught traceback instead of this script's documented dict/typed-
    # failure return -- found live during this session's own C1-fix
    # verification and by cross-model review (GitHub issue #251's finalize
    # session). Caught here so every failure path returns the same shape.
    try:
        result = dispatch(
            agent=args.agent,
            target_paths=[p for p in args.target_paths.split(",") if p],
            dispatch_id=args.dispatch_id,
            execution_profile=args.execution_profile,
            dry_run=args.dry_run,
            repo_root=args.repo_root,
            cwd=args.cwd,
        )
    except (ValueError, FileNotFoundError, OSError) as exc:
        result = {
            "ok": False,
            "category": "bridge_caller_precondition_error",
            "detail": str(exc),
        }
    print(json.dumps(result, indent=2))
    sys.exit(1 if isinstance(result, dict) and result.get("ok") is False else 0)


if __name__ == "__main__":
    main()
