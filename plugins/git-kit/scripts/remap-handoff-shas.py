#!/usr/bin/env python3
"""Remap build-handoff-writer report SHAs after a rebase/squash merge.

A PR merged via GitHub's rebase-merge or squash-merge rewrites every commit
hash. build-handoff-writer reports under .claude/output/ record the
pre-merge SHAs, which then silently point at commits unreachable from the
default branch. This script detects that for a given merged PR and remaps
any stale SHA reference it can resolve, via exact commit-message match first
and patch-id (diff-content) match as a fallback. Anything it can't resolve
is reported, never guessed.

This repository's own convention only - a no-op if .claude/output/ doesn't
exist (e.g. run against a repo that doesn't use build-handoff-writer).
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import typing
from pathlib import Path

SHA_TOKEN_RE = re.compile(r"`([0-9a-f]{7,40})`")


def run(*args: str, cwd: str, input_text: str | None = None) -> tuple[int, str, str]:
    r = subprocess.run(
        list(args), capture_output=True, text=True, encoding="utf-8", cwd=cwd, input=input_text
    )
    return r.returncode, r.stdout, r.stderr


def is_ancestor(sha: str, base: str, repo: str) -> bool:
    rc, _, _ = run("git", "merge-base", "--is-ancestor", sha, base, cwd=repo)
    return rc == 0


def find_by_message(msg: str, base: str, repo: str) -> list[str]:
    rc, out, _ = run("git", "log", base, "--format=%H\x01%s", cwd=repo)
    if rc != 0:
        return []
    return [h for line in out.splitlines() for h, _, s in [line.partition("\x01")] if s == msg]


def patch_id(sha: str, repo: str) -> str | None:
    rc, diff, _ = run("git", "show", sha, cwd=repo)
    if rc != 0 or not diff:
        return None
    rc2, pid_out, _ = run("git", "patch-id", "--stable", cwd=repo, input_text=diff)
    if rc2 != 0 or not pid_out.strip():
        return None
    return pid_out.split()[0]


def build_patchid_index(base: str, repo: str) -> dict[str, list[str]]:
    rc, out, _ = run("git", "log", base, "--format=%H", cwd=repo)
    index: dict[str, list[str]] = {}
    for h in out.split():
        pid = patch_id(h, repo)
        if pid:
            index.setdefault(pid, []).append(h)
    return index


def short_sha(oid: str, length: int, repo: str) -> str:
    rc, out, _ = run("git", "rev-parse", f"--short={length}", oid, cwd=repo)
    return out.strip() if rc == 0 and out.strip() else oid[:length]


def apply_remap_to_file(path: Path, remap: dict[str, str], repo: str) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    if "## Commits" not in text:
        return False

    def repl(m: re.Match[str]) -> str:
        token = m.group(1)
        for old_oid, new_oid in remap.items():
            if old_oid.startswith(token):
                return f"`{short_sha(new_oid, len(token), repo)}`"
        return m.group(0)

    new_text = SHA_TOKEN_RE.sub(repl, text)
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    # Commit subject lines can contain non-ASCII characters; the default Windows
    # console encoding (cp1252) chokes on them otherwise.
    typing.cast(io.TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8", errors="replace")
    typing.cast(io.TextIOWrapper, sys.stderr).reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pr", required=True, help="Merged PR number")
    ap.add_argument("--repo-root", default=".", help="Repository root (default: cwd)")
    ap.add_argument("--base", default="main", help="Branch the PR merged into")
    args = ap.parse_args()

    repo = str(Path(args.repo_root).resolve())
    output_dir = Path(repo) / ".claude" / "output"
    if not output_dir.is_dir():
        print("No .claude/output/ directory here; nothing to remap.")
        return 0

    rc, out, err = run("gh", "pr", "view", args.pr, "--json", "commits", cwd=repo)
    if rc != 0:
        print(f"Could not fetch PR #{args.pr} commits: {err.strip()}", file=sys.stderr)
        return 1
    commits = json.loads(out).get("commits") or []
    if not commits:
        print(f"PR #{args.pr} has no recorded commits; nothing to do.")
        return 0

    stale = [
        (c["oid"], c["messageHeadline"])
        for c in commits
        if not is_ancestor(c["oid"], args.base, repo)
    ]
    if not stale:
        print(
            f"All {len(commits)} commit(s) from PR #{args.pr} are ancestors of {args.base}; "
            "no remap needed."
        )
        return 0

    print(
        f"{len(stale)} of {len(commits)} commit(s) from PR #{args.pr} "
        f"are unreachable from {args.base} (rebase/squash merge) - resolving replacements..."
    )

    patchid_index: dict[str, list[str]] | None = None
    remap: dict[str, str] = {}
    unresolved: list[tuple[str, str]] = []
    for oid, msg in stale:
        matches = find_by_message(msg, args.base, repo)
        if len(matches) == 1:
            remap[oid] = matches[0]
            continue
        if patchid_index is None:
            patchid_index = build_patchid_index(args.base, repo)
        pid = patch_id(oid, repo)
        pid_matches = patchid_index.get(pid, []) if pid else []
        if len(pid_matches) == 1:
            remap[oid] = pid_matches[0]
            continue
        unresolved.append((oid, msg))

    changed: list[Path] = []
    if remap:
        for path in sorted(output_dir.rglob("*.md")):
            if apply_remap_to_file(path, remap, repo):
                changed.append(path.relative_to(repo))

    print(f"\nRemapped {len(remap)} commit SHA(s) across {len(changed)} report file(s):")
    for f in changed:
        print(f"  - {f}")

    if unresolved:
        print(
            f"\n{len(unresolved)} commit(s) could not be automatically remapped "
            f"(no unique commit-message or patch-id match on {args.base}):"
        )
        for oid, msg in unresolved:
            print(f"  - {oid[:7]} {msg!r}")
        print("Any report referencing these SHAs was left untouched - annotate manually if needed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
