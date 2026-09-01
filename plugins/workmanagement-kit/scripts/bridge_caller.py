#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Dispatch work-transition-reviewer / work-intake-classifier live through
codex-kit's codex-review-bridge (see plugins/codex-kit/skills/codex-review-bridge/SKILL.md).

Reads the target agent's .md file, strips its YAML frontmatter, writes the body
to a scratch instruction file outside the repository entirely (an OS temp
directory -- --instruction-file is not repo-root-bound the way --target-paths
is, and this guarantees no --target-paths value, however broad, can ever
contain it), then calls bridge-invoke.mjs and returns the parsed canonical
envelope (or typed failure) as a dict.

Per GitHub issue #251 / plugins/workmanagement-kit/FOUNDATION_CONTRACTS.md.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
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
    # ValueError, not SystemExit -- SystemExit is a BaseException, not an
    # Exception, so it silently bypasses main()'s own
    # except (ValueError, FileNotFoundError, OSError) and crashes with an
    # uncaught traceback instead of the documented typed-failure dict (found
    # by CodeRabbit's PR #278 review).
    raise ValueError(f"could not resolve repo root from {start}")


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

    # A relative target path must resolve against `root`, not the process's
    # actual OS cwd -- Path.resolve() on a relative path resolves against
    # Path.cwd(), which only matches `root` by coincidence unless the caller
    # happens to invoke this script from the repo root itself. A caller using
    # --repo-root from a different directory would otherwise get a target
    # resolved against the wrong base (found by Codex/CodeRabbit/Devin's
    # PR #278 review).
    resolved_targets = [
        (Path(t) if Path(t).is_absolute() else root / t).resolve() for t in target_paths
    ]

    # Scratch instruction file: a fresh OS temp directory, deliberately
    # OUTSIDE the repository entirely. An earlier version put this under
    # `root/.temp/`, reasoning that bridge-invoke.mjs's repo-root containment
    # check required it -- that reasoning was wrong: --instruction-file is
    # explicitly NOT bound by that check (bridge-invoke.mjs's own comment:
    # "instruction-file is deliberately NOT bound by the repo-root
    # containment gate... plugin-auditor's documented Codex path writes the
    # trusted reviewer instructions to the session scratchpad precisely
    # because that directory must live OUTSIDE the repository root"). Being
    # inside root meant a broad --target-paths entry (e.g. the repo root
    # itself, ".") would always contain the scratch dir too, rejecting every
    # such dispatch via the nested-instruction-file check that used to live
    # here (found by Codex's PR #278 full review). A directory outside the
    # repo entirely can never be contained by any --target-paths value, so
    # that check is no longer needed at all.
    scratch_dir = Path(tempfile.mkdtemp(prefix="workmanagement-kit-bridge-"))
    instruction_file = scratch_dir / f"{dispatch_id}-{agent}-instruction.md"
    instruction_file.write_text(body, encoding="utf-8")

    # Everything from here on must run inside the try/finally below --
    # instruction_file now exists on disk, and every remaining precondition
    # check (the bridge_script existence check right below included) can
    # still raise before dispatch ever happens. An earlier version only
    # wrapped the subprocess.run call itself, so a missing bridge_script
    # raised FileNotFoundError before the try block even started, leaking
    # the instruction file on every such failure (found by Devin's PR #278
    # round-2 review).
    try:
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

        # bridge-invoke.mjs validates --target-paths (but NOT
        # --instruction-file -- see the scratch_dir comment above) against
        # ^[A-Za-z0-9._/-]+$ -- no backslash (Windows' native separator) and
        # no colon (a Windows drive letter, e.g. "C:") are in that charset.
        # An absolute Windows path fails this check either way it's
        # rendered, so every --target-paths value handed to the bridge must
        # be relative to --cwd, using forward slashes. --instruction-file
        # carries no such restriction and is passed as an absolute path
        # unchanged, since it now lives outside `root` and has no
        # `root`-relative form to begin with.
        def relposix(p: Path) -> str:
            return p.relative_to(root).as_posix()

        cmd = [
            "node",
            str(bridge_script),
            "--reviewer-type",
            agent,
            "--instruction-file",
            str(instruction_file.resolve()),
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

        # encoding="utf-8" is required explicitly -- subprocess.run's
        # text=True alone decodes with the platform's locale-preferred
        # encoding (cp1252 on a default Windows install, not UTF-8), which
        # silently corrupts any non-ASCII character (e.g. an em dash) the
        # child process writes as UTF-8.
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", cwd=str(root)
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        # bridge-invoke.mjs writes every typed failure via console.error
        # (stderr) and only a real success envelope via console.log
        # (stdout) -- verified directly against its source. Parsing stdout
        # only silently discarded the bridge's own failure category (e.g.
        # isolation_profile_unavailable, cli_unavailable) on every real
        # failure, always falling back to the generic
        # bridge_caller_invocation_error below (found by Codex/Devin's
        # PR #278 review).
        try:
            payload_text = stdout if stdout else stderr
            payload = json.loads(payload_text) if payload_text else None
        except json.JSONDecodeError:
            payload = None

        if payload is None:
            return {
                "ok": False,
                "category": "bridge_caller_invocation_error",
                "detail": {
                    "returncode": result.returncode,
                    "stdout": stdout[-4000:],
                    "stderr": stderr[-4000:],
                },
            }
        return payload
    finally:
        # Otherwise every dispatch -- success or failure -- permanently
        # leaves a file (and now a whole temp directory) behind (found by
        # Devin's PR #278 round-2 review). Runs on every exit path,
        # including a subprocess.run OSError propagating out of this
        # function. rmdir() only removes an empty directory -- since this
        # scratch_dir is a fresh mkdtemp() used for exactly one file, it's
        # always empty immediately after that file is unlinked; ignored if
        # something unexpected leaves it non-empty rather than failing the
        # whole dispatch over cleanup.
        instruction_file.unlink(missing_ok=True)
        try:
            scratch_dir.rmdir()
        except OSError:
            pass


def main() -> None:
    # exit_on_error=False: without it, an invalid --agent choice or a missing
    # required option makes parse_args() print a raw argparse usage message
    # to stderr and call sys.exit(2) directly -- bypassing this script's own
    # documented typed-JSON-failure contract entirely, since that happens
    # before the try/except below ever runs (found by CodeRabbit's PR #278
    # review). With it, parse_args() raises argparse.ArgumentError instead,
    # which is caught below like any other precondition failure. -h/--help
    # is unaffected -- argparse's help action still calls sys.exit(0)
    # directly regardless of this flag, which is the correct, expected
    # behavior for --help, not a failure to convert.
    parser = argparse.ArgumentParser(description=__doc__, exit_on_error=False)
    parser.add_argument("--agent", required=True, choices=sorted(AGENTS))
    parser.add_argument("--target-paths", required=True, help="comma-separated evidence paths")
    parser.add_argument("--dispatch-id", required=True)
    parser.add_argument("--execution-profile", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repo-root")
    parser.add_argument("--cwd")

    # Every one of dispatch()'s own precondition checks, argument-parsing
    # failures (see exit_on_error above), and subprocess.run's own OSError
    # (e.g. node missing/unlaunchable), previously propagated as an uncaught
    # traceback or a bare non-JSON exit instead of this script's documented
    # dict/typed-failure return -- found live during this session's own
    # C1-fix verification, by cross-model review, and by CodeRabbit's PR #278
    # review (GitHub issue #251's finalize session). Caught here so every
    # failure path returns the same shape.
    try:
        args = parser.parse_args()
        result = dispatch(
            agent=args.agent,
            target_paths=[p for p in args.target_paths.split(",") if p],
            dispatch_id=args.dispatch_id,
            execution_profile=args.execution_profile,
            dry_run=args.dry_run,
            repo_root=args.repo_root,
            cwd=args.cwd,
        )
    except (ValueError, FileNotFoundError, OSError, argparse.ArgumentError) as exc:
        result = {
            "ok": False,
            "category": "bridge_caller_precondition_error",
            "detail": str(exc),
        }
    print(json.dumps(result, indent=2))
    sys.exit(1 if isinstance(result, dict) and result.get("ok") is False else 0)


if __name__ == "__main__":
    main()
