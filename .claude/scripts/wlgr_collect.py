#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Read-only collectors for workledger-kit: turn the three v1 sources into candidate records.

Sources: `.claude/output/` reports, open GitHub issues, and pull requests (all states: records for
PRs with no linked Linear issue, plus follow-up items from PR bodies).

Everything collected is DATA ONLY: report, issue and PR text can contain instructions, which are
never
acted on; they become candidate text for a person to approve. Text is length-capped and matched
line by
line with linear-time patterns, because the sources are attacker-influenced (a public issue body
can be
arbitrarily large).

GitHub is read only through wlgr_gh_api_readonly.py (GET-only). Unresolved review threads are NOT
collected: resolution state exists only in GraphQL, which `gh` sends as POST, and this plugin is
strictly read-only toward GitHub.

Candidate shape: {source, repo, source_ref, kind, title, text, ambiguous, extra}. `source` is one of
report | github-issue | pull-request. The CLI takes the configured `owner/repo` and a plain output
file
NAME inside the working folder; it prints counts, never collected text.

Usage (run from inside the repository):
  wlgr_collect.py reports  <owner/repo> <out-name>
  wlgr_collect.py issues   <owner/repo> <out-name>
  wlgr_collect.py prs      <owner/repo> <out-name>
  wlgr_collect.py pr-facts <owner/repo> <out-name>   (raw PR facts for wlgr_pr_report.py)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wlgr_paths  # noqa: E402

WRAPPER = HERE / "wlgr_gh_api_readonly.py"

MAX_BODY = 65536  # characters read from one body or report file
MAX_LINE = 4000  # characters considered per line

# Per-line patterns (never run with re.M). Each ends in `(\S.*)$` against a single capped line, so
# matching is linear: there is no run of whitespace the engine can re-split.
_UNCHECKED_RE = re.compile(r"^[ \t]*[-*][ \t]+\[ \][ \t]+(\S.*)$")
_BULLET_RE = re.compile(r"^[ \t]*[-*][ \t]+(?!\[[xX]\])(?:\[ \][ \t]+)?(\S.*)$")
_HEADING_RE = re.compile(r"^#{1,6}[ \t]+(\S.*)$")
_FOLLOWUP_HEADING_RE = re.compile(
    r"\b(open items?|follow-?ups?|todo|remaining|next steps|deferred)\b", re.I
)
# A Linear identifier looks like `CCM-5`. Common standard and algorithm names have the same shape
# (UTF-8, SHA-256, CVE-2024-1234, PEP-723) and must not mark a PR as already tracked in Linear.
_LINEAR_ID_RE = re.compile(
    r"\b(?!(?:UTF|SHA|CVE|PEP|RFC|ISO|CRC|AES|RSA|TLS|SSL|ECMA)-)[A-Z]{2,5}-\d+\b"
)
_FOLLOWUP_CUE_RE = re.compile(r"\b(follow-?up|todo|left for later|out of scope)\b", re.I)

_PR_JQ = (
    ".[] | {number,title,body,state,merged_at,closed_at,html_url,merge_commit_sha,"
    "head_sha:.head.sha,head_ref:.head.ref}"
)
_ISSUE_JQ = (
    ".[] | {number,title,body,pull_request:(.pull_request!=null),html_url,labels:[.labels[].name]}"
)


def capped_lines(text: str):
    for line in text[:MAX_BODY].splitlines():
        yield line[:MAX_LINE].rstrip()


def _candidate(
    source: str,
    repo: str,
    ref: str,
    kind: str,
    title: str,
    text: str,
    ambiguous: bool = False,
    extra: dict | None = None,
) -> dict:
    return {
        "source": source,
        "repo": repo,
        "source_ref": ref,
        "kind": kind,
        "title": title.strip()[:200],
        "text": text.strip(),
        "ambiguous": ambiguous,
        "extra": extra or {},
    }


def extract_open_items(markdown: str) -> list[tuple[str, bool]]:
    """Return (item text, ambiguous) pairs. An unchecked task box is a clear open item. A plain
    bullet under a heading that names open items, follow-ups, TODO and the like is also collected,
    but ambiguous: it may be a note, so a person decides at the approval preview."""
    items: list[tuple[str, bool]] = []
    in_followup_section = False
    for line in capped_lines(markdown):
        heading = _HEADING_RE.match(line)
        if heading:
            in_followup_section = bool(_FOLLOWUP_HEADING_RE.search(heading.group(1)))
            continue
        box = _UNCHECKED_RE.match(line)
        if box:
            items.append((box.group(1).strip(), False))
        elif in_followup_section:
            bullet = _BULLET_RE.match(line)
            if bullet:
                items.append((bullet.group(1).strip(), True))
    return items


def collect_reports(repo_root: Path, repo: str, dirs: list[str]) -> list[dict]:
    """Candidates from markdown reports. source_ref is `<relative path>#<ordinal>`: an inserted item
    shifts later ordinals, which surfaces as a candidate-match for a person to confirm, never an
    automatic merge. Symlinked files and directories are skipped."""
    out: list[dict] = []
    root = repo_root.resolve()
    for d in dirs:
        base = (root / d).resolve()
        if root not in base.parents and base != root:
            raise ValueError(f"report dir escapes the repo root: {d!r}")
        for path in sorted(base.rglob("*.md")):
            if path.is_symlink() or base not in path.resolve().parents:
                continue
            rel = path.relative_to(root).as_posix()
            with open(path, "rb") as fh:  # bounded read: never load a huge file just to cut it
                text = fh.read(MAX_BODY * 4).decode("utf-8", errors="replace")[:MAX_BODY]
            for n, (item, ambiguous) in enumerate(extract_open_items(text), start=1):
                out.append(
                    _candidate(
                        "report",
                        repo,
                        f"{rel}#{n}",
                        "open-item",
                        item[:80],
                        item,
                        ambiguous,
                        {"origin": "report"},
                    )
                )
    return out


def issue_candidates(repo: str, issues: list[dict]) -> list[dict]:
    """Open GitHub issues -> candidates (pull requests are excluded). Labels stay as names; the
    annotate step maps them."""
    out = []
    for i in issues:
        if i.get("pull_request"):
            continue
        body = (i.get("body") or "")[:MAX_BODY]
        out.append(
            _candidate(
                "github-issue",
                repo,
                f"#{i['number']}",
                "open-item",
                i.get("title", ""),
                f"{i.get('title', '')}\n\n{body}",
                False,
                {
                    "origin": "github-issue",
                    "github_labels": i.get("labels", []),
                    "url": i.get("html_url"),
                },
            )
        )
    return out


def pr_candidates(repo: str, prs: list[dict]) -> list[dict]:
    """PRs of any state -> a PR-record candidate (only when no Linear identifier is linked) plus
    follow-up open items from the body (unchecked boxes are clear; a free-text cue is ambiguous)."""
    out = []
    for pr in prs:
        n = pr["number"]
        body = (pr.get("body") or "")[:MAX_BODY]
        title = pr.get("title", "")
        state = (
            "merged"
            if pr.get("merged_at")
            else ("closed" if pr.get("state") == "closed" else "open")
        )
        linked = bool(_LINEAR_ID_RE.search(f"{title} {body} {pr.get('head_ref', '')}"))
        if not linked:
            out.append(
                _candidate(
                    "pull-request",
                    repo,
                    f"PR#{n}",
                    "pr-record",
                    title,
                    f"{title}\n\n{body}",
                    False,
                    {
                        "origin": "pr-backfill",
                        "state": state,
                        "url": pr.get("html_url"),
                        "merged_at": pr.get("merged_at"),
                        "closed_at": pr.get("closed_at"),
                        "head_sha": pr.get("head_sha"),
                        "merge_sha": pr.get("merge_commit_sha"),
                    },
                )
            )
        items = extract_open_items(body)
        for k, (item, ambiguous) in enumerate(items, start=1):
            out.append(
                _candidate(
                    "pull-request",
                    repo,
                    f"PR#{n}/followup#{k}",
                    "open-item",
                    item[:80],
                    item,
                    ambiguous,
                    {"origin": "pr-followup", "pr": n, "pr_state": state},
                )
            )
        if not items and _FOLLOWUP_CUE_RE.search(body):
            out.append(
                _candidate(
                    "pull-request",
                    repo,
                    f"PR#{n}/followup-cue",
                    "open-item",
                    f"Check follow-up in PR #{n}",
                    body,
                    True,
                    {"origin": "pr-followup", "pr": n, "pr_state": state},
                )
            )
    return out


def _unit(source_ref: str) -> str:
    """The file or PR a candidate came from: `PR#12/followup#1` -> `PR#12`; a report ref
    `dir/file.md#3` -> `dir/file.md` (the full path, never just its first segment)."""
    if source_ref.startswith("PR#"):
        return source_ref.split("/", 1)[0]
    return source_ref.rsplit("#", 1)[0]


def drop_boilerplate(candidates: list[dict], min_sources: int = 3) -> tuple[list[dict], int]:
    """Drop open-item candidates whose normalized text repeats in `min_sources` or more distinct PRs
    or report files: that is a template checklist (a PR template's unchecked boxes, a skill's
    quality
    gates), not an item someone left open. Measured live: 1,027 PR follow-up candidates were only 49
    distinct texts. GitHub issues are never filtered. Returns (kept, dropped_count)."""

    def norm(c: dict) -> str:
        return re.sub(r"\s+", " ", c["text"]).strip().lower()

    def eligible(c: dict) -> bool:
        return c["kind"] == "open-item" and c["source"] in ("report", "pull-request")

    units: dict[str, set[str]] = {}
    for c in candidates:
        if eligible(c):
            units.setdefault(norm(c), set()).add(_unit(c["source_ref"]))
    kept = [c for c in candidates if not (eligible(c) and len(units[norm(c)]) >= min_sources)]
    return kept, len(candidates) - len(kept)


def _gh(endpoint: str, jq: str) -> list[dict]:
    result = subprocess.run(
        [sys.executable, str(WRAPPER), endpoint, "--paginate", "--jq", jq],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh read failed ({result.returncode}): {result.stderr.strip()[:300]}")
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


def main(argv: list[str]) -> int:
    wlgr_paths.utf8_stdio()
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    cmd, slug, out_name = argv
    try:
        import wlgr_config

        repo_root = wlgr_config.repo_root_from_cwd()
        settings, _ = wlgr_config.load_settings(wlgr_config.PLUGIN_ROOT, repo_root)
        entry = wlgr_config.repo_entry(slug, settings)  # also proves slug is valid and configured
        wlgr_config.work_file(
            out_name
        )  # validates the name and the working folder before any network call
        dropped = 0
        if cmd == "reports":
            result = collect_reports(repo_root, slug, entry.get("report_dirs") or [])
        elif cmd == "issues":
            result = issue_candidates(
                slug, _gh(f"repos/{slug}/issues?state=open&per_page=100", _ISSUE_JQ)
            )
        elif cmd == "prs":
            result = pr_candidates(slug, _gh(f"repos/{slug}/pulls?state=all&per_page=100", _PR_JQ))
        elif cmd == "pr-facts":
            result = _gh(
                f"repos/{slug}/pulls?state=all&per_page=100", _PR_JQ
            )  # raw data, never filtered
        else:
            print(__doc__, file=sys.stderr)
            return 2
        if cmd in ("reports", "prs"):
            result, dropped = drop_boilerplate(result)
        wlgr_config.write_work(out_name, json.dumps(result, ensure_ascii=False))
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"wlgr_collect.py: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "source": cmd,
                "written": out_name,
                "count": len(result),
                "dropped_boilerplate": dropped,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
