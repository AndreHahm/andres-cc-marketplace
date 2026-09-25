#!/usr/bin/env python3
"""Remap build-handoff-writer report SHAs after a rebase/squash merge.

A PR merged via GitHub's rebase-merge or squash-merge rewrites every commit
hash. build-handoff-writer reports under .claude/output/ record the
pre-merge SHAs, which then silently point at commits unreachable from the
default branch. This script detects that for a given merged PR and remaps
any stale SHA reference it can resolve, via patch-id (diff-content) match
first -- the higher-confidence signal, since it compares actual content, not
text -- and an exact commit-message match as a fallback, scoped to commits at
or after the PR's own merge time so an unrelated older commit that happens to
share the same subject line can never be mistaken for the real replacement.
Anything it can't resolve is reported, never guessed.

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
from datetime import datetime, timedelta
from pathlib import Path

# Buffer subtracted from the PR's mergedAt before scoping the commit-message
# fallback search -- generous enough to absorb any clock skew between
# GitHub's recorded merge time and the merged commits' own committer dates,
# without meaningfully widening the window a same-subject false positive
# could hide in.
MESSAGE_SEARCH_BUFFER = timedelta(hours=1)

SHA_TOKEN_RE = re.compile(r"`([0-9a-f]{7,40})`")


def run(*args: str, cwd: str, input_text: str | None = None) -> tuple[int, str, str]:
    r = subprocess.run(
        list(args), capture_output=True, text=True, encoding="utf-8", cwd=cwd, input=input_text
    )
    return r.returncode, r.stdout, r.stderr


def is_ancestor(sha: str, base_ref: str, repo: str) -> bool:
    rc, _, _ = run("git", "merge-base", "--is-ancestor", sha, base_ref, cwd=repo)
    return rc == 0


def find_by_message(msg: str, base_ref: str, since: str | None, repo: str) -> list[str]:
    # Scoped to commits at/after the PR's own merge time (with a generous
    # buffer for clock skew) so an unrelated older commit sharing the exact
    # same subject line can never be mistaken for the real replacement.
    args = ["git", "log", base_ref, "--format=%H\x01%s"]
    if since:
        args.append(f"--since={since}")
    rc, out, _ = run(*args, cwd=repo)
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


def build_patchid_index(base_ref: str, repo: str) -> dict[str, list[str]]:
    rc, out, _ = run("git", "log", base_ref, "--format=%H", cwd=repo)
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
        matches = [new_oid for old_oid, new_oid in remap.items() if old_oid.startswith(token)]
        if len(matches) == 1:
            return f"`{short_sha(matches[0], len(token), repo)}`"
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

    # Refresh the local view of the base branch before trusting it for
    # ancestry/replacement lookups -- a stale local ref (never independently
    # re-synced by this script) would otherwise search pre-merge history and
    # either miss the true replacement or, worse, silently leave every
    # commit unresolved while reporting success. Operate against the
    # refreshed origin/<base>, never the bare local branch name.
    rc, _, err = run("git", "fetch", "origin", args.base, cwd=repo)
    if rc != 0:
        print(f"Could not fetch origin/{args.base}: {err.strip()}", file=sys.stderr)
        return 1
    base_ref = f"origin/{args.base}"

    rc, out, err = run("gh", "pr", "view", args.pr, "--json", "commits,mergedAt", cwd=repo)
    if rc != 0:
        print(f"Could not fetch PR #{args.pr} commits: {err.strip()}", file=sys.stderr)
        return 1
    pr_data = json.loads(out)
    commits = pr_data.get("commits") or []
    merged_at = pr_data.get("mergedAt")
    since = None
    if merged_at:
        merged_dt = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
        since = (merged_dt - MESSAGE_SEARCH_BUFFER).isoformat()
    if not commits:
        print(f"PR #{args.pr} has no recorded commits; nothing to do.")
        return 0

    stale = [
        (c["oid"], c["messageHeadline"])
        for c in commits
        if not is_ancestor(c["oid"], base_ref, repo)
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
        # Patch-id (actual diff content) is tried first -- it's the
        # high-confidence signal. Commit-message match is only a fallback,
        # and scoped to commits at/after the merge so an unrelated older
        # commit sharing the same subject text can never be mistaken for
        # the real replacement.
        if patchid_index is None:
            patchid_index = build_patchid_index(base_ref, repo)
        pid = patch_id(oid, repo)
        pid_matches = patchid_index.get(pid, []) if pid else []
        if len(pid_matches) == 1:
            remap[oid] = pid_matches[0]
            continue
        matches = find_by_message(msg, base_ref, since, repo)
        if len(matches) == 1:
            remap[oid] = matches[0]
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
