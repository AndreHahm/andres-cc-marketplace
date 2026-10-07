#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Deterministic core for workledger-kit: open-item identity, dedup, plan hashing, issue proposals,
GitHub label mapping, digest bookkeeping and Notion-safe chunking.

The library functions are pure (no network, no connector). The CLI reads and writes only plain file
NAMES inside the validated working folder (see wlgr_config.workdir): it never takes a path, and
collected text never travels on stdin or argv, so nothing collected can reach a shell. It prints
counts
only, never collected text.

Why exact comparison in code: Linear's text search is fuzzy (a wrong fingerprint still returned the
right issue; `#99` matched `#999`), so a search hit is never proof of identity. A candidate's
`dedup_key` is parsed from the first line of each existing description and compared by equality.

Usage (all names are files in the working folder):
  wlgr_open_items.py annotate   <candidates.json> <annotated.json>
  wlgr_open_items.py folder-counts <annotated.json>
  wlgr_open_items.py filter-folders <annotated.json> <folders.json> <filtered.json>
      (the output name may be the same as the input name)
  wlgr_open_items.py classify   <annotated.json> <existing-issues.json> <classified.json>
  wlgr_open_items.py apply-classification <annotated.json> <classified.json>
                                          [<confirmed-keys.json>] <selected.json>
  wlgr_open_items.py describe   <annotated.json> <proposals.json>
  wlgr_open_items.py plan-hash  <items.json>
  wlgr_open_items.py chunk      <text-file> <chunks.json> [limit 100-2000]
  wlgr_open_items.py new-since  <annotated.json> <seen-keys.json> <new.json>
  wlgr_open_items.py mark-seen  <annotated.json> <seen-keys.json>
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wlgr_paths  # noqa: E402

MASTER_LABEL = "meta: master"
MASTER_TITLE_PREFIX = "[MASTER"
DEDUP_PREFIX = "dedup_key: "
TRACKING_HEADING = "## Tracking data"
NOTION_TEXT_LIMIT = 2000
CONTEXT_EXCERPT = 1500

_REPO_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_TYPE_MAP = {"enhancement": "improvement"}  # t: -> type:, enhancement becomes improvement
_PRIORITY_MAP = {"critical": "Urgent", "high": "High", "medium": "Medium", "low": "Low"}
_PR_STATUS = {"open": "In Review", "merged": "Done", "closed": "Canceled"}


def normalize_text(text: str) -> str:
    """Collapse whitespace and case so cosmetic edits do not change the fingerprint."""
    return re.sub(r"\s+", " ", text).strip().lower()


def fingerprint(text: str) -> str:
    """Short, stable content fingerprint: 8 hex chars of sha256 over the normalized text."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()[:8]


def make_dedup_key(repo: str, source_ref: str, text: str) -> str:
    """`<owner/repo>|<source-ref>|<content fingerprint>`. The source ref may not contain `|`."""
    if not _REPO_RE.fullmatch(repo):
        raise ValueError(f"repo must look like owner/repo, got {repo!r}")
    if not source_ref or "|" in source_ref or "\n" in source_ref:
        raise ValueError("source_ref must be non-empty and contain no '|' or newline")
    return f"{repo}|{source_ref}|{fingerprint(text)}"


def split_key(key: str) -> tuple[str, str, str]:
    parts = key.split("|")
    if len(parts) != 3 or not all(parts):
        raise ValueError(f"malformed dedup key: {key!r}")
    return parts[0], parts[1], parts[2]


def read_dedup_key(description: str | None) -> str | None:
    """The dedup key is the single first line of the description. None means missing or malformed:
    the caller flags that as drift and never silently repairs it."""
    if not description:
        return None
    first = description.split("\n", 1)[0].rstrip("\r")
    if not first.startswith(DEDUP_PREFIX):
        return None
    key = first[len(DEDUP_PREFIX) :].strip()
    try:
        split_key(key)
    except ValueError:
        return None
    return key


def is_master(issue: dict) -> bool:
    """Masters are copy sources for people; the plugin skips them everywhere."""
    labels = [str(x).strip().lower() for x in (issue.get("labels") or [])]
    title = str(issue.get("title") or "")
    return MASTER_LABEL in labels or title.startswith(MASTER_TITLE_PREFIX)


def index_existing(existing_issues: list[dict]) -> tuple[dict, dict, list]:
    """Parse each existing issue's first-line key ONCE: (exact key -> id, (repo, ref) -> id, drift
    ids).
    Masters are skipped; issues with a missing or malformed key go to drift and are never
    repaired."""
    exact: dict[str, object] = {}
    by_ref: dict[tuple[str, str], object] = {}
    drift: list = []
    for issue in existing_issues:
        if is_master(issue):
            continue
        key = read_dedup_key(issue.get("description"))
        if key is None:
            drift.append(issue.get("id"))
            continue
        exact.setdefault(key, issue.get("id"))
        e_repo, e_ref, _ = split_key(key)
        by_ref.setdefault((e_repo, e_ref), issue.get("id"))
    return exact, by_ref, drift


def classify_with_index(candidate_key: str, index: tuple[dict, dict, list]) -> dict:
    """Return {"result": "duplicate"|"candidate-match"|"new", "issue": id-or-None, "drift": [ids]}.

    duplicate        exact key equality -> skip, never write
    candidate-match  same repo and source ref, changed fingerprint -> a person confirms, never an
    auto-merge
    new              no match
    """
    exact, by_ref, drift = index
    if candidate_key in exact:
        return {"result": "duplicate", "issue": exact[candidate_key], "drift": drift}
    repo, ref, _fp = split_key(candidate_key)
    if (repo, ref) in by_ref:
        return {"result": "candidate-match", "issue": by_ref[(repo, ref)], "drift": drift}
    return {"result": "new", "issue": None, "drift": drift}


def classify_candidate(candidate_key: str, existing_issues: list[dict]) -> dict:
    """One-off form of classify_with_index (the CLI indexes once and reuses the index)."""
    return classify_with_index(candidate_key, index_existing(existing_issues))


def select_for_plan(
    annotated: list[dict], classified: list[dict], confirmed_keys: set[str]
) -> tuple[list[dict], dict]:
    """The candidates that may be proposed: every `new` one, plus a `candidate-match` only if a
    person
    confirmed its key. Duplicates and unconfirmed matches are dropped, so they can never reach the
    proposals file, its plan hash or a submission. A candidate missing from `classified` is
    dropped too
    (nothing may be proposed that was not classified)."""
    result_by_key = {c["dedup_key"]: c["result"] for c in classified}
    kept: list[dict] = []
    counts = {
        "new": 0,
        "confirmed-match": 0,
        "dropped-duplicate": 0,
        "dropped-unconfirmed-match": 0,
        "dropped-unclassified": 0,
    }
    for c in annotated:
        r = result_by_key.get(c["dedup_key"])
        if r == "new":
            kept.append(c)
            counts["new"] += 1
        elif r == "candidate-match" and c["dedup_key"] in confirmed_keys:
            kept.append(c)
            counts["confirmed-match"] += 1
        elif r == "duplicate":
            counts["dropped-duplicate"] += 1
        elif r == "candidate-match":
            counts["dropped-unconfirmed-match"] += 1
        else:
            counts["dropped-unclassified"] += 1
    return kept, counts


def folder_counts(candidates: list[dict], depth: int = 3) -> dict[str, int]:
    """Report candidates per folder (the first `depth` path components of the file the item came
    from),
    most numerous first. Counts only: lets a person choose real report folders without reading the
    text."""
    counts: dict[str, int] = {}
    for c in candidates:
        if c["source"] == "report":
            folder = "/".join(c["source_ref"].rsplit("#", 1)[0].split("/")[:depth])
            counts[folder] = counts.get(folder, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def plan_hash(items: list[dict]) -> str:
    """Hash binding an approval to exactly the previewed set: order-independent over items, so any
    added, removed or edited item changes the hash and forces a re-preview."""
    canon = sorted(
        json.dumps(i, sort_keys=True, ensure_ascii=False, separators=(",", ":")) for i in items
    )
    return hashlib.sha256("\n".join(canon).encode("utf-8")).hexdigest()


def map_github_labels(labels: list[str]) -> dict:
    """`t:` -> type label (enhancement -> improvement); `i:` -> impact label; `p:` -> Linear
    priority
    (no label); `a:`, `s:`, `auto:` dropped. Every original label is also returned in
    `github_labels`
    so nothing is lost."""
    out: dict = {"type": None, "impact": None, "priority": None, "github_labels": list(labels)}
    for raw in labels:
        low = raw.strip().lower()
        if low.startswith("t:"):
            v = low[2:].strip()
            out["type"] = f"type: {_TYPE_MAP.get(v, v)}"
        elif low.startswith("i:"):
            out["impact"] = f"impact: {low[2:].strip().replace('minor change', 'minor')}"
        elif low.startswith("p:"):
            out["priority"] = _PRIORITY_MAP.get(low[2:].strip())
    return out


def annotate_keys(candidates: list[dict]) -> tuple[list[dict], list[dict]]:
    """Add `dedup_key` (and mapped GitHub labels) to each collected candidate. A candidate whose
    reference cannot form a valid key (for example a file name containing '|') is returned in the
    second list with its reason instead of aborting the whole batch."""
    kept, skipped = [], []
    for c in candidates:
        try:
            key = make_dedup_key(c["repo"], c["source_ref"], c["text"])
        except (ValueError, KeyError) as exc:
            skipped.append({"source_ref": c.get("source_ref"), "reason": str(exc)})
            continue
        extra = dict(c.get("extra") or {})
        if extra.get("github_labels") is not None:
            extra["mapped"] = map_github_labels(list(extra["github_labels"]))
        kept.append({**c, "dedup_key": key, "extra": extra})
    return kept, skipped


def filter_report_folders(candidates: list[dict], folders: list[str]) -> list[dict]:
    """Keep every non-report candidate, and only the report candidates under one of `folders`
    (each a
    repo-relative folder such as `.claude/output/plugin-conception`). Used after a person has chosen
    which report folders hold real open items; the rest are generated working output."""
    prefixes = [f.strip().replace(chr(92), "/").rstrip("/") + "/" for f in folders if f.strip()]
    return [
        c
        for c in candidates
        if c["source"] != "report" or any(c["source_ref"].startswith(p) for p in prefixes)
    ]


def new_since(annotated: list[dict], seen_keys: set[str]) -> list[dict]:
    """Annotated candidates whose key is not in `seen_keys`. Local only: used by the read-only
    digest, which cannot consult Linear (intake re-asks for approval on every read)."""
    return [c for c in annotated if c["dedup_key"] not in seen_keys]


def build_description(
    dedup_key: str, summary: str, context: str, done_when: list[str], tracking: dict
) -> str:
    """First line `dedup_key: ...`, human sections, then one fenced yaml block under a fixed heading
    at the end. Tracking values are JSON-quoted so the block stays flat text."""
    split_key(dedup_key)
    lines = [
        f"{DEDUP_PREFIX}{dedup_key}",
        "",
        "## Summary",
        summary.strip(),
        "",
        "## Context",
        context.strip(),
        "",
    ]
    lines.append("## Done when")
    lines.extend(f"- [ ] {c}" for c in done_when)
    lines += ["", TRACKING_HEADING, "```yaml", "schema: 1"]
    for k in sorted(tracking):
        lines.append(f"{k}: {json.dumps(tracking[k], ensure_ascii=False)}")
    lines.append("```")
    return "\n".join(lines) + "\n"


def propose_issue(c: dict) -> dict:
    """The Linear issue this annotated candidate would become (a proposal, never a write)."""
    extra = c.get("extra") or {}
    kind = c["kind"]
    mapped = extra.get("mapped") or {}
    status = (
        "Triaged"
        if kind == "open-item"
        else _PR_STATUS.get(extra.get("state", "open"), "In Review")
    )
    tracking = {
        "kind": kind,
        "repo": c["repo"],
        "origin": extra.get("origin"),
        "source_ref": c["source_ref"],
    }
    for k in ("url", "state", "merged_at", "closed_at", "head_sha", "merge_sha", "pr"):
        if extra.get(k) is not None:
            tracking[k] = extra[k]
    if extra.get("github_labels") is not None:
        tracking["github_labels"] = extra["github_labels"]
    done = (
        ["The item is resolved, or declined with the reason recorded"]
        if kind == "open-item"
        else ["The record matches the pull request's final state"]
    )
    context = f"Collected from {c['source']} {c['source_ref']}.\n\n" + c["text"][:CONTEXT_EXCERPT]
    labels = [f"kind: {kind}"] + [
        x
        for x in (
            f"origin: {extra['origin']}" if extra.get("origin") else None,
            mapped.get("type"),
            mapped.get("impact"),
        )
        if x
    ]
    return {
        "dedup_key": c["dedup_key"],
        "title": c["title"] or c["source_ref"],
        "status": status,
        "labels": labels,
        "priority": mapped.get("priority"),
        "ambiguous": c.get("ambiguous", False),
        "description": build_description(
            c["dedup_key"], c["title"] or c["source_ref"], context, done, tracking
        ),
    }


MIN_CHUNK = 100


def chunk_text(text: str, limit: int = NOTION_TEXT_LIMIT) -> list[str]:
    """Split into blocks of at most `limit` characters (Notion's 2,000-character limit is
    user-stated,
    not independently verified). `limit` must be 100..2000. Prefers paragraph, then line, then hard
    splits, and cuts by index, so the cost is linear in the text."""
    if not MIN_CHUNK <= limit <= NOTION_TEXT_LIMIT:
        raise ValueError(f"limit must be between {MIN_CHUNK} and {NOTION_TEXT_LIMIT}")
    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current:
            chunks.append(current)
            current = ""

    for para in text.split("\n\n"):
        sep = "\n\n" if current else ""
        if len(current) + len(sep) + len(para) <= limit:
            current += sep + para
            continue
        flush()
        pos = 0
        while len(para) - pos > limit:
            cut = para.rfind("\n", pos, pos + limit)
            cut = cut if cut > pos else pos + limit
            chunks.append(para[pos:cut])
            pos = cut
            while pos < len(para) and para[pos] == "\n":
                pos += 1
        current = para[pos:]
    flush()
    return [c for c in chunks if c]


# ---- CLI: plain file names inside the validated working folder ---------------------------------


def _load(name: str):
    import wlgr_config

    return json.loads(wlgr_config.read_work(name))


def _save(name: str, data) -> None:
    import wlgr_config

    wlgr_config.write_work(name, json.dumps(data, ensure_ascii=False, indent=1))


def _seen(name: str) -> tuple[set[str], bool]:
    """(keys, existed). A missing seen-keys file is a first run."""
    import wlgr_config

    path = wlgr_config.work_file(name)
    if not path.is_file():
        return set(), False
    return set(json.loads(wlgr_config.read_work(name))), True


def main(argv: list[str]) -> int:
    wlgr_paths.utf8_stdio()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    cmd, a = argv[0], argv[1:]
    try:
        if cmd == "annotate" and len(a) == 2:
            kept, skipped = annotate_keys(_load(a[0]))
            _save(a[1], {"candidates": kept, "skipped": skipped})
            print(json.dumps({"annotated": len(kept), "skipped": len(skipped)}))
        elif cmd == "folder-counts" and len(a) == 1:
            counts = folder_counts(_load(a[0])["candidates"])
            top = dict(list(counts.items())[:40])
            rest = sum(list(counts.values())[40:])
            print(json.dumps({"folders": top, "other_folders_total": rest}))
        elif cmd == "filter-folders" and len(a) == 3:
            data = _load(a[0])
            folders = _load(a[1])
            if not isinstance(folders, list) or not all(isinstance(f, str) for f in folders):
                raise ValueError("folders file must be a JSON list of folder names")
            kept = filter_report_folders(data["candidates"], folders)
            _save(a[2], {**data, "candidates": kept})
            print(json.dumps({"kept": len(kept), "removed": len(data["candidates"]) - len(kept)}))
        elif cmd == "classify" and len(a) == 3:
            cands = _load(a[0])["candidates"]
            index = index_existing(_load(a[1]))
            results = [
                {"dedup_key": c["dedup_key"], **classify_with_index(c["dedup_key"], index)}
                for c in cands
            ]
            _save(a[2], results)
            counts = {
                r: sum(x["result"] == r for x in results)
                for r in ("duplicate", "candidate-match", "new")
            }
            counts["drift"] = len(index[2])
            print(json.dumps(counts))
        elif cmd == "apply-classification" and len(a) in (3, 4):
            confirmed = set(_load(a[2])) if len(a) == 4 else set()
            kept, counts = select_for_plan(_load(a[0])["candidates"], _load(a[1]), confirmed)
            _save(a[-1], {"candidates": kept, "skipped": []})
            print(json.dumps(counts))
        elif cmd == "describe" and len(a) == 2:
            proposals = [propose_issue(c) for c in _load(a[0])["candidates"]]
            _save(a[1], proposals)
            print(json.dumps({"proposals": len(proposals)}))
        elif cmd == "plan-hash" and len(a) == 1:
            print(plan_hash(_load(a[0])))
        elif cmd == "chunk" and len(a) in (2, 3):
            import wlgr_config

            chunks = chunk_text(
                wlgr_config.read_work(a[0]), int(a[2]) if len(a) == 3 else NOTION_TEXT_LIMIT
            )
            _save(a[1], chunks)
            print(
                json.dumps(
                    {"chunks": len(chunks), "max_len": max((len(c) for c in chunks), default=0)}
                )
            )
        elif cmd == "new-since" and len(a) == 3:
            seen, existed = _seen(a[1])
            fresh = new_since(_load(a[0])["candidates"], seen)
            _save(a[2], fresh)
            print(json.dumps({"new": len(fresh), "first_run": not existed}))
        elif cmd == "mark-seen" and len(a) == 2:
            import wlgr_config

            seen, _ = _seen(a[1])
            keys = seen | {c["dedup_key"] for c in _load(a[0])["candidates"]}
            wlgr_config.write_work(a[1], json.dumps(sorted(keys)))
            print(json.dumps({"seen": len(keys)}))
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"wlgr_open_items.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
