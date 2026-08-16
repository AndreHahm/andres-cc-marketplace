#!/usr/bin/env python3
"""Validate a drafted PR title against this repository's actual CI hygiene check.

`create-pr`'s generic "conventional commit format" guidance is looser than what
scripts/marketplace_ci/pr_policy.py's check_pr_title() actually enforces in CI
(a stricter regex, and an allowed-type list that excludes `style` and `ci`, both
of which are otherwise valid commit types per git-kit's own commit skill). This
script calls that real function directly so the two can never drift apart.

This repository's own convention only - exits 0 (nothing to check) if
scripts/marketplace_ci/pr_policy.py doesn't exist here.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check-pr-title.py '<title>'", file=sys.stderr)
        return 2
    title = sys.argv[1]

    repo_root = Path.cwd()
    if not (repo_root / "scripts" / "marketplace_ci" / "pr_policy.py").is_file():
        print("No scripts/marketplace_ci/pr_policy.py here; nothing to check.")
        return 0

    sys.path.insert(0, str(repo_root))
    from scripts.marketplace_ci.pr_policy import check_pr_title

    result = check_pr_title(title)
    if result.passed:
        print(f"PASS: {title!r} satisfies this repo's PR title policy.")
        return 0
    print(f"FAIL: {title!r} - {result.reason}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
