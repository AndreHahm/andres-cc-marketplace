#!/usr/bin/env python3
"""Check that a PR-body edit leaves CI's waiver sections unchanged (merge-pr step 1.6).

    git-pr-body-waiver-check.py <base-from-jq> <new-body>

`<base-from-jq>` is the live body saved with `gh pr view <pr> --json body --jq .body`, which adds
one final newline; that newline is dropped before comparing. `<new-body>` is the body the edit
would send, exactly as `gh api -F body=@<file>` sends it.

Each protected section is read the way CI reads `## Accepted Review Findings`
(`_section_text` in scripts/marketplace_ci/review.py): HTML comments are removed first, then the
first heading matching the pattern is taken, in any letter case and with `\\s` spanning line
breaks, up to the next `#` or `##` heading. `## Known CI Failures (Accepted)` is read the same
way; no CI code parses that section (people read it), so for it this check is a heuristic and
the caller's diff of every changed line is the real guard. CRLF line ends are turned into LF in
both bodies first, so they compare equal (CI's patterns absorb a CR before a line end, and its
waiver reader strips each line); a lone CR is kept, since CI's waiver reader splits lines on it.

Exit 0 when every protected section reads the same in both bodies (absent in both counts as the
same), 1 when one differs (named on stdout), 2 when a file cannot be read as UTF-8 or anything
else goes wrong. Standard library only, so it runs with `python3 -I`.
"""

from __future__ import annotations

import re
import sys

# Copied from scripts/marketplace_ci/review.py (_HTML_COMMENT, _WAIVER_SECTION and the end rule
# in _section_text); tests/marketplace_ci/test_git_pr_body_waiver_check.py fails when they drift.
HTML_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.DOTALL)
SECTION_END = re.compile(r"^#{1,2}\s", re.MULTILINE)
SECTIONS = {
    "Accepted Review Findings": re.compile(
        r"^##\s+Accepted Review Findings\s*$", re.IGNORECASE | re.MULTILINE
    ),
    "Known CI Failures (Accepted)": re.compile(
        r"^##\s+Known CI Failures \(Accepted\)\s*$", re.IGNORECASE | re.MULTILINE
    ),
}


def section_text(body: str, heading: re.Pattern[str]) -> str | None:
    """The section `heading` starts, as CI's `_section_text` reads it; None when absent."""
    stripped = HTML_COMMENT.sub("", body)
    match = heading.search(stripped)
    if match is None:
        return None
    rest = stripped[match.end() :]
    end = SECTION_END.search(rest)
    return rest[: end.start()] if end else rest


def changed_sections(base: str, new: str) -> list[str]:
    base, new = base.replace("\r\n", "\n"), new.replace("\r\n", "\n")
    return [
        name
        for name, heading in SECTIONS.items()
        if section_text(base, heading) != section_text(new, heading)
    ]


def _read(path: str) -> str:
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: git-pr-body-waiver-check.py <base-from-jq> <new-body>", file=sys.stderr)
        return 2
    texts = []
    for path in argv:
        try:
            texts.append(_read(path))
        except (OSError, UnicodeDecodeError) as exc:
            print(f"cannot read {path}: {type(exc).__name__}", file=sys.stderr)
            return 2
    base, new = texts
    if base.endswith("\n"):
        base = base[:-1]
    changed = changed_sections(base, new)
    for name in changed:
        print(f"changed: {name}")
    if not changed:
        print("unchanged: every protected section reads the same")
    return 1 if changed else 0


if __name__ == "__main__":
    try:
        code = main(sys.argv[1:])
    except Exception as exc:  # noqa: BLE001 - any fault is "cannot tell" (2), never "changed" (1)
        print(f"check failed: {type(exc).__name__}", file=sys.stderr)
        code = 2
    sys.exit(code)
