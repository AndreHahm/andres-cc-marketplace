"""Proves the actual guarantee issue #351 (direction #3) exists for: that
the review-dispatch-critical CLI subcommands (check-scope-bypass,
run-codex-review, check-bypass, resolve-attested-actor) never import
sync.py/validators.py (Tier 2 -- the mirror/export apply-and-staging side a
same-repo PR could otherwise tamper with to defeat the review it's itself
being reviewed by). Not just that the split compiles: that the isolation
holds, both dynamically (a real subprocess run) and statically (an AST scan
of every import statement, including a function-local one a shallow dynamic
probe wouldn't reach) -- and that the workflow's own hard-refuse gate stays
mechanically tied to the same Tier 1 file set, rather than drifting apart
from a hand-maintained comment alone (security review findings M1/M2 on the
PR implementing this split).

pr_policy.py is intentionally excluded from TIER1_MODULES (the dynamic
allowlist) but included in TIER1_FILES (the workflow gate's own pathspec) --
it's gated for a distinct reason (merge-privilege code with no base-SHA
restore in its own consuming job, `hygiene`), not because it's part of
run-codex-review's own import closure. See review.py's and the workflow's
own comments for the full rationale.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

from scripts.marketplace_ci.trust_boundary import TIER1_FILES

REPO_ROOT = Path(__file__).resolve().parents[2]

# The exact dotted-module set the four review-dispatch-critical subcommands'
# own handler functions are allowed to have pulled into sys.modules -- an
# allowlist, not a denylist, so a *future* Tier 2 module never silently
# escapes this check just because nobody thought to add it to a denylist.
TIER1_MODULES = frozenset(
    {
        "scripts",
        "scripts.marketplace_ci",
        "scripts.marketplace_ci.__main__",
        "scripts.marketplace_ci.review",
        "scripts.marketplace_ci.git_state",
        "scripts.marketplace_ci.registry",
        "scripts.marketplace_ci.sync_plan",
        "scripts.marketplace_ci.conversion",
    }
)

# Files that are wholly Tier 1 -- every import statement anywhere in these
# files (module-level or function-local) must never reference a Tier 2
# module. Deliberately excludes __main__.py, which legitimately imports
# Tier 2 modules inside its OTHER (non-critical) handler functions; see
# CRITICAL_HANDLERS below for the __main__.py-specific, function-scoped check.
TIER1_SOURCE_FILES = (
    "scripts/marketplace_ci/review.py",
    "scripts/marketplace_ci/git_state.py",
    "scripts/marketplace_ci/registry.py",
    "scripts/marketplace_ci/sync_plan.py",
    "scripts/marketplace_ci/conversion.py",
)

# The four __main__.py handler functions backing the review-dispatch-critical
# subcommands. Only these functions' own bodies are checked for Tier 2
# imports -- __main__.py's other handlers (e.g. _handle_sync_plugin_mirrors)
# legitimately import Tier 2 modules, so the whole file can't be scanned.
CRITICAL_HANDLERS = (
    "_handle_check_scope_bypass",
    "_handle_run_codex_review",
    "_handle_check_bypass",
    "_handle_resolve_attested_actor",
)

# The workflow's own hard-refuse gate pathspec -- a superset of TIER1_MODULES'
# files: includes pr_policy.py (see module docstring) and the dependency spec.
# TIER1_FILES itself now lives in trust_boundary.py (imported above), which
# also backs the local `check-trust-boundary` pre-push preview -- this test
# is what keeps that copy, and the workflow's own hand-maintained pathspec,
# from silently drifting apart.

TIER2_MODULES = ("scripts.marketplace_ci.sync", "scripts.marketplace_ci.validators")

_PROBE = """
import sys
from scripts.marketplace_ci.__main__ import main
try:
    main({argv!r})
except BaseException:
    pass
scripts_modules = sorted(m for m in sys.modules if m == "scripts" or m.startswith("scripts."))
print("MODULES:" + ",".join(scripts_modules))
"""


def _scripts_modules_for(argv: list[str]) -> list[str]:
    script = _PROBE.format(argv=argv)
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=REPO_ROOT, capture_output=True, text=True
    )
    marker = next(
        (line for line in result.stdout.splitlines() if line.startswith("MODULES:")), None
    )
    assert marker is not None, (
        f"probe did not run to completion (stdout={result.stdout!r}, stderr={result.stderr!r})"
    )
    payload = marker[len("MODULES:") :]
    return [m for m in payload.split(",") if m]


def _assert_only_tier1_and_actually_ran(argv: list[str]) -> None:
    """Allowlist assertion (a future Tier 2 module added to review.py's own
    dependency closure fails this, with no denylist to forget to update) --
    plus a positive-signal assertion that the handler's own imports actually
    executed, so a probe that exits early via argparse's SystemExit (e.g. a
    future required-argument rename) fails loudly instead of vacuously
    reporting an empty, trivially-"clean" module set."""
    modules = set(_scripts_modules_for(argv))
    assert modules, (
        f"probe for {argv!r} imported no scripts.* modules at all -- the handler's own "
        "imports never ran (did main() exit early, e.g. via argparse?)"
    )
    leaked = modules - TIER1_MODULES
    assert not leaked, f"probe for {argv!r} imported Tier 2/unexpected module(s): {leaked}"


def test_check_scope_bypass_never_imports_tier2_modules():
    _assert_only_tier1_and_actually_ran(["check-scope-bypass", "--base-sha", "0" * 40])


def test_run_codex_review_never_imports_tier2_modules():
    _assert_only_tier1_and_actually_ran(["run-codex-review", "--base-sha", "0" * 40])


def test_check_bypass_never_imports_tier2_modules():
    _assert_only_tier1_and_actually_ran(["check-bypass", "--event", "/nonexistent/event.json"])


def test_resolve_attested_actor_never_imports_tier2_modules():
    _assert_only_tier1_and_actually_ran(
        [
            "resolve-attested-actor",
            "--comments-with-login",
            "/nonexistent/comments.json",
            "--head-sha",
            "x",
        ]
    )


def test_other_subcommands_do_import_tier2_modules_control_case():
    """Control case: a Tier 2, read-only subcommand (`check-all --staged`
    calls validators.check_staged_parity) DOES import validators.py --
    confirming the probe itself can actually detect a Tier 2 import when one
    happens, rather than passing vacuously because the probe never worked.
    Deliberately read-only (never sync-plugin-mirrors/repair-all, which
    write files) since this runs against the real checkout, not a fixture."""
    modules = set(_scripts_modules_for(["check-all", "--staged"]))
    assert "scripts.marketplace_ci.validators" in modules


def _imported_module_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Import):
            for alias in n.names:
                names.add(alias.name)
        elif isinstance(n, ast.ImportFrom) and n.module:
            names.add(n.module)
    return names


def _tier2_references(imported: set[str]) -> set[str]:
    return {m for m in imported if any(m == t or m.startswith(t + ".") for t in TIER2_MODULES)}


def test_tier1_source_files_never_reference_tier2_modules_statically():
    """Static, not just dynamic: scans every import statement -- module-level
    or function-local -- in each wholly-Tier-1 file (via ast.walk, which
    reaches inside every function/class body, not just the top level) and
    asserts none of them reference sync.py/validators.py. Covers a future
    function-local import buried inside a function the dynamic probes above
    (deliberately fed invalid input, so they exit at their first git/file
    error) would never actually execute into -- e.g. a Tier 2 import added
    inside dispatch_reviewers() or validate_review_output(), neither of
    which the shallow dynamic probes reach (security review finding M2)."""
    for rel_path in TIER1_SOURCE_FILES:
        source = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel_path)
        leaked = _tier2_references(_imported_module_names(tree))
        assert not leaked, (
            f"{rel_path} references Tier 2 module(s) somewhere in its source: {leaked}"
        )


def test_critical_handlers_never_reference_tier2_modules_statically():
    """Same static guarantee as above, scoped to just the four
    review-dispatch-critical handler functions in __main__.py -- the rest of
    that file legitimately imports Tier 2 modules in its other handlers, so
    only these four functions' own AST subtrees are checked."""
    tree = ast.parse(
        (REPO_ROOT / "scripts/marketplace_ci/__main__.py").read_text(encoding="utf-8"),
        filename="scripts/marketplace_ci/__main__.py",
    )
    handler_nodes = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name in CRITICAL_HANDLERS
    }
    assert set(handler_nodes) == set(CRITICAL_HANDLERS), (
        f"expected to find all of {CRITICAL_HANDLERS} in __main__.py, found {sorted(handler_nodes)}"
    )
    for name, node in handler_nodes.items():
        leaked = _tier2_references(_imported_module_names(node))
        assert not leaked, f"__main__.py's {name} references Tier 2 module(s): {leaked}"


def test_workflow_hard_refuse_gate_pathspec_matches_tier1_file_set():
    """Cross-checks the codex-review job's own hard-refuse gate pathspec
    list (a shell pathspec, hand-maintained) against TIER1_FILES (this
    test module's own single source of truth) so the two can't silently
    drift apart -- neither can `$ref` the other across the YAML/Python
    boundary, so nothing but a test like this one catches one being
    updated without the other (security review finding M1)."""
    workflow_path = REPO_ROOT / ".github" / "workflows" / "marketplace-ci.yml"
    text = workflow_path.read_text(encoding="utf-8")

    marker = "Refuse automated Codex dispatch when this PR modifies review-dispatch-critical code"
    idx = text.find(marker)
    assert idx != -1, "could not find the hard-refuse gate step by its own name"
    run_block = text[idx : idx + 4000]

    match = re.search(
        r'git diff --quiet "\$BASE_SHA"\.\.\.HEAD -- \\\n(?P<paths>.*?);\s*then',
        run_block,
        re.DOTALL,
    )
    assert match is not None, "could not locate the gate's git diff pathspec block"
    pathspec = {
        line.strip().rstrip("\\").strip()
        for line in match.group("paths").splitlines()
        if line.strip().strip("\\").strip()
    }

    assert pathspec == set(TIER1_FILES)
