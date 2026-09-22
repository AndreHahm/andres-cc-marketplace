"""Local preview of the codex-review job's hard-refuse trust-boundary gate
(marketplace-ci.yml's "Refuse automated Codex dispatch..." step, issue #351).

Not part of the review-dispatch-critical import closure itself (no
review-dispatch handler in __main__.py imports this module) -- this is a
developer-convenience check only, safe to run locally with no bearing on
the real gate's own pass/fail logic. It mirrors CI's own pathspec, but the
base ref it diffs against is a local approximation (merge-base with the
target branch) rather than the PR's actual registered base.sha, so a
result here is informative, not authoritative -- the real gate in CI is
still what decides.

TIER1_FILES is the single source of truth `tests/marketplace_ci/
test_import_isolation.py` cross-checks the workflow's own pathspec
against; keep that test passing if this list ever changes."""

from __future__ import annotations

import subprocess
from pathlib import Path

TIER1_FILES = frozenset(
    {
        "scripts/__init__.py",
        "scripts/marketplace_ci/__init__.py",
        "scripts/marketplace_ci/__main__.py",
        "scripts/marketplace_ci/review.py",
        "scripts/marketplace_ci/git_state.py",
        "scripts/marketplace_ci/registry.py",
        "scripts/marketplace_ci/sync_plan.py",
        "scripts/marketplace_ci/conversion.py",
        "scripts/marketplace_ci/pr_policy.py",
        "pyproject.toml",
        "uv.lock",
    }
)


def find_tier1_touches(base_ref: str, repo: Path, to_ref: str = "HEAD") -> frozenset[str]:
    """Tier-1 paths with a real diff between `base_ref` and `to_ref` (three-dot,
    matching the workflow gate's own `git diff ... "$BASE_SHA"...HEAD`).

    `to_ref` defaults to `HEAD`, but a pre-push hook invocation should pass the
    actually-pushed object instead (see `_handle_check_trust_boundary` in
    `__main__.py`) -- `HEAD` is only what's currently checked out, which can
    differ from what's being pushed (e.g. `git push origin other-branch` while
    on a different branch)."""
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...{to_ref}", "--", *sorted(TIER1_FILES)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return frozenset(line for line in result.stdout.splitlines() if line)
