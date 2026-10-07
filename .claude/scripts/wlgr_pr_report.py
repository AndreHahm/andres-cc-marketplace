#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Assemble the PR timeline report from raw PR facts: a baseline over all PRs, or a delta of
PRs changed since a date. Pure and offline; the facts come from `wlgr_collect.py pr-facts`.

Four views plus a per-plugin breakdown:
  1. Timeline by merge (or close) date
  2. PR -> referenced issues and items (explicit references only; inferred links need the
     classification capability and are never shown as facts)
  3. Issues closed by merged PRs (closing keywords only)
  4. Follow-up PRs and tasks (follow-up cues and unchecked boxes)
  + per plugin: PR counts and follow-ups, attributed from the PR title's conventional-commit scope,
    e.g. `feat(git-kit): ...`. A PR with no scope is counted under `(no scope)`.

Usage (run inside the repository; names are plain files in the working folder):
  wlgr_pr_report.py <facts.json> <report.md> [--since YYYY-MM-DD] [--repo owner/repo]
  --repo names the repository in the report title; without it the name is read from the first PR,
  so pass it whenever the repository may have no pull requests yet.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wlgr_paths  # noqa: E402
from wlgr_collect import MAX_BODY, capped_lines  # noqa: E402

# Linear-time: after the keyword, either "blanks, colon, blanks" or one run of blanks; no
# overlapping
# quantifiers, so a long run of spaces cannot be re-split many ways.
_CLOSES_RE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)(?:[ \t]*:[ \t]*|[ \t]+)#(\d+)", re.I
)
_CUE_RE = re.compile(
    r"\b(?:follow-?ups?\s+(?:to|of|for)|continues|builds on|supersedes|part of)\s+#(\d+)", re.I
)
_MENTION_RE = re.compile(r"(?<![\w/])#(\d+)\b")
_SCOPE_RE = re.compile(r"^\s*\w+\(([^)]+)\)")
_UNCHECKED_RE = re.compile(
    r"^[ \t]*[-*][ \t]+\[ \][ \t]+(\S.*)$"
)  # applied per capped line, never re.M
BOILERPLATE_MIN_PRS = 3


def _unchecked(body: str) -> list[str]:
    return [m.group(1).strip() for line in capped_lines(body) if (m := _UNCHECKED_RE.match(line))]


def parse_refs(number: int, text: str) -> dict[str, list[int]]:
    """Explicit references in a PR's title and body. Each number appears in one group only, in the
    order closes > cue > mention, and a PR never references itself. Text is length-capped first."""
    text = text[:MAX_BODY]
    closes = {int(n) for n in _CLOSES_RE.findall(text)} - {number}
    cue = {int(n) for n in _CUE_RE.findall(text)} - {number} - closes
    mention = {int(n) for n in _MENTION_RE.findall(text)} - {number} - closes - cue
    return {"closes": sorted(closes), "cue": sorted(cue), "mention": sorted(mention)}


def plugin_scopes(title: str) -> list[str]:
    """Plugin names from the title's conventional-commit scope; `|` is replaced so a scope cannot
    break the markdown table it is printed in."""
    m = _SCOPE_RE.match(title[:300])
    return (
        [s.strip().replace("|", "/") for s in m.group(1).split(",") if s.strip()]
        if m
        else ["(no scope)"]
    )


def _date(pr: dict) -> str:
    return (pr.get("merged_at") or pr.get("closed_at") or "")[:10]


def _state(pr: dict) -> str:
    return (
        "merged" if pr.get("merged_at") else ("closed" if pr.get("state") == "closed" else "open")
    )


def real_boxes(prs: list[dict]) -> dict[int, list[str]]:
    """Unchecked task boxes per PR, minus template boilerplate: a box whose normalized text
    appears in
    BOILERPLATE_MIN_PRS or more PRs is the PR template's own checklist, not a left-open task."""
    per_pr = {
        p["number"]: [re.sub(r"\s+", " ", t).lower() for t in _unchecked(p.get("body") or "")]
        for p in prs
    }
    seen_in = Counter(t for texts in per_pr.values() for t in set(texts))
    return {
        n: [t for t in texts if seen_in[t] < BOILERPLATE_MIN_PRS] for n, texts in per_pr.items()
    }


def select(prs: list[dict], since: str | None) -> list[dict]:
    """Baseline (since is None): every PR. Delta: open PRs plus PRs merged or closed on/after
    `since`."""
    if since is None:
        return list(prs)
    return [p for p in prs if _state(p) == "open" or _date(p) >= since]


def build_report(prs: list[dict], repo: str, today: str, since: str | None = None) -> str:
    chosen = sorted(select(prs, since), key=lambda p: (_date(p), p["number"]))
    kind = f"delta since {since}" if since else "baseline"
    out = [
        f"# PR history ({kind}): {repo}",
        "",
        f"Generated {today}. Dated snapshot, not live. {len(chosen)} PR(s).",
        "Links below are explicit GitHub references only. Inferred links are not shown: they "
        "need the "
        "classification capability and would be marked as inferred with their evidence.",
        "",
    ]

    out += ["## Timeline", "", "| Date | PR | State | Title |", "|---|---|---|---|"]
    for p in chosen:
        out.append(
            f"| {_date(p) or '-'} | #{p['number']} | {_state(p)} | {p['title'].replace('|', '/')} |"
        )

    refs = {
        p["number"]: parse_refs(p["number"], f"{p['title']}\n{p.get('body') or ''}") for p in chosen
    }
    out += ["", "## PR to referenced issues and items", ""]
    any_ref = False
    for p in chosen:
        r = refs[p["number"]]
        parts = [
            f"{label} {', '.join('#' + str(n) for n in r[key])}"
            for key, label in (
                ("closes", "closes"),
                ("cue", "follow-up/continues"),
                ("mention", "mentions"),
            )
            if r[key]
        ]
        if parts:
            any_ref = True
            out.append(f"- #{p['number']}: " + "; ".join(parts))
    if not any_ref:
        out.append("- none")

    out += ["", "## Issues closed by merged PRs", ""]
    closed = defaultdict(list)
    for p in chosen:
        if _state(p) == "merged":
            for n in refs[p["number"]]["closes"]:
                closed[n].append(p["number"])
    out += [
        f"- #{n}: closed by " + ", ".join(f"#{x}" for x in prs_)
        for n, prs_ in sorted(closed.items())
    ] or ["- none"]

    out += ["", "## Follow-up PRs and tasks", ""]
    follow = []
    box_texts = real_boxes(
        prs
    )  # frequency is judged over ALL PRs, so a delta stays consistent with the baseline
    for p in chosen:
        boxes = len(box_texts[p["number"]])
        cue = refs[p["number"]]["cue"]
        if boxes or cue:
            bits = ([f"{boxes} unchecked task(s)"] if boxes else []) + (
                [f"follow-up/continues {', '.join('#' + str(n) for n in cue)}"] if cue else []
            )
            follow.append((p, boxes, "; ".join(bits)))
    out += [f"- #{p['number']}: {text}" for p, _, text in follow] or ["- none"]

    out += [
        "",
        "## Per plugin (from the PR title scope)",
        "",
        "| Plugin | PRs | PRs with follow-ups |",
        "|---|---|---|",
    ]
    prs_per, follow_per = Counter(), Counter()
    followed = {p["number"] for p, _, _ in follow}
    for p in chosen:
        for s in plugin_scopes(p["title"]):
            prs_per[s] += 1
            follow_per[s] += p["number"] in followed
    out += [
        f"| {s} | {n} | {follow_per[s]} |"
        for s, n in sorted(prs_per.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    wlgr_paths.utf8_stdio()
    args: list[str] = []
    opts: dict[str, str] = {}
    it = iter(argv)
    for arg in it:
        if arg in ("--since", "--repo"):
            value = next(it, None)
            if value is None or arg in opts:
                print(__doc__, file=sys.stderr)
                return 2
            opts[arg] = value
        else:
            args.append(arg)
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    since = opts.get("--since")
    if since and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", since):
        print("wlgr_pr_report.py: --since must be YYYY-MM-DD", file=sys.stderr)
        return 2
    try:
        import wlgr_config

        if "--repo" in opts and not wlgr_config.valid_slug(opts["--repo"]):
            print("wlgr_pr_report.py: --repo must be owner/repo", file=sys.stderr)
            return 2
        prs = json.loads(wlgr_config.read_work(args[0]))
        # An explicit --repo names the report even when the repository has no PRs; otherwise the
        # name comes from the first PR's URL.
        if "--repo" in opts:
            repo = opts["--repo"]
        elif prs:
            repo = prs[0].get("html_url", "").split("/pull/")[0].split("github.com/")[-1]
        else:
            repo = "unknown"
        from datetime import date

        text = build_report(prs, repo, date.today().isoformat(), since)
        wlgr_config.write_work(args[1], text)
    except (ValueError, OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"wlgr_pr_report.py: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"written": args[1], "prs": len(select(prs, since)), "characters": len(text)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
