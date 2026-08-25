#!/usr/bin/env python3
"""Persisted smoke test for marketplace-inventory: frontmatter validity, referenced-file
existence, Bash-scope grant consistency, and the shared CLI script's own subcommands."""

import json
import pathlib
import re
import subprocess
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
SCRIPT = SKILL_DIR / "scripts" / "marketplace-inventory.py"


def check_frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False, "SKILL.md does not start with a frontmatter block"
    end = text.find("\n---\n", 4)
    if end == -1:
        return False, "frontmatter block is never closed"
    fm = text[4:end]
    if "name:" not in fm or "description:" not in fm:
        return False, "missing required frontmatter field ('name' or 'description')"
    return True, "frontmatter present and closed"


def check_referenced_files():
    text = SKILL_MD.read_text(encoding="utf-8")
    missing = []
    for match in re.finditer(
        r"`((?:\.\./)*(?:references/[\w.-]+\.md|scripts/[\w./-]+|assets/[\w.-]+))`", text
    ):
        path = SKILL_DIR / match.group(1)
        if not path.exists():
            missing.append(match.group(1))
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def check_bash_grants():
    # Real invocation instructions in this body live as a literal command line inside a
    # fenced ```bash block -- not as a bare `Bash(...)` mention, which never actually
    # appears verbatim in the body and made the previous version of this check a silent
    # no-op (referenced was always empty regardless of what the body actually invoked).
    text = SKILL_MD.read_text(encoding="utf-8")
    header_end = text.find("\n---\n", 4) + 5
    frontmatter, body = text[:header_end], text[header_end:]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    granted_prefixes = (
        [
            g.rsplit(":", 1)[0].strip()
            for g in re.findall(r"Bash\(([^)]*)\)", fm_line_match.group(1))
        ]
        if fm_line_match
        else []
    )
    invoked = set()
    for block in re.findall(r"```bash\n(.*?)```", body, re.DOTALL):
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            tokens = line.split()
            invoked.add(" ".join(tokens[:2]) if len(tokens) > 1 else tokens[0])
    uncovered = [cmd for cmd in invoked if not any(cmd.startswith(p) for p in granted_prefixes)]
    if uncovered:
        return False, "body invokes command(s) not covered by any granted Bash scope: " + ", ".join(
            sorted(uncovered)
        )
    if not invoked:
        return True, "no shell commands found in fenced bash blocks (nothing to check)"
    return True, f"every invoked command ({len(invoked)}) is covered by a granted Bash scope"


def _find_repo_root():
    """Walk upward from this file to find the repo root (marked by
    .claude-plugin/marketplace.json) -- the number of parent directories
    differs between the canonical plugins/plugin-devkit/... location and
    the .claude/skills/... mirror, so this can't be a fixed parent count."""
    current = SKILL_DIR
    while current != current.parent:
        if (current / ".claude-plugin" / "marketplace.json").is_file():
            return current
        current = current.parent
    raise RuntimeError(
        "could not find repo root (.claude-plugin/marketplace.json) above " + str(SKILL_DIR)
    )


def _build_fixture_repo(tmpdir, plugin_names):
    """Build a small synthetic marketplace repo root: its own
    .claude-plugin/marketplace.json listing `plugin_names`, each with a
    real (empty) source directory -- enough for discover_plugins/build_plan
    to operate on without touching this repo's own real marketplace.json."""
    repo_root = pathlib.Path(tmpdir) / "fixture_repo"
    manifest_dir = repo_root / ".claude-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "fixture-marketplace",
        "plugins": [{"name": name, "source": f"./{name}"} for name in plugin_names],
    }
    (manifest_dir / "marketplace.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name in plugin_names:
        (repo_root / name).mkdir(parents=True, exist_ok=True)
    return repo_root


def _fresh_inventory_path(repo_root):
    """inventory_path must live at exactly <repo_root>/.claude-plugin/
    marketplace-inventory.json -- the script's own write-boundary guard
    (require_inventory_path_under_scope_dir) refuses any other location,
    now that every write-capable subcommand takes repo_root and enforces
    real containment, not just a filename/parent-dir shape match."""
    path = pathlib.Path(repo_root) / ".claude-plugin" / "marketplace-inventory.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *[str(a) for a in args]], capture_output=True, text=True
    )


def check_conflict_missing_active_plugin():
    """Scenario 4 (Conflict, missing active plugin): remove a plugin from
    the fixture marketplace.json while its inventory record stays active;
    confirm plan emits a conflict, never a silent retirement."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = _build_fixture_repo(tmpdir, ["plugin-a", "plugin-b"])
        inventory_path = _fresh_inventory_path(repo_root)
        bootstrap = _run("bootstrap", repo_root, inventory_path)
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"

        manifest_path = repo_root / ".claude-plugin" / "marketplace.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["plugins"] = [p for p in manifest["plugins"] if p["name"] != "plugin-b"]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        plan = _run("plan", repo_root, inventory_path)
        if plan.returncode != 0:
            return False, f"plan failed: {plan.stderr.strip()}"
        operations = json.loads(plan.stdout)["operations"]
        conflicts = [
            op for op in operations if op["operation"] == "conflict" and op["name"] == "plugin-b"
        ]
        if not conflicts:
            return False, f"expected a conflict entry for plugin-b, got: {operations}"
        return True, "missing active plugin correctly surfaced as a conflict, not auto-retired"


def check_plugin_id_mismatch_conflict():
    """Scenario 5 (plugin_id mismatch conflict): a plugin-inventory.json
    whose plugin_id disagrees with the marketplace record's own id must
    surface as a conflict."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = _build_fixture_repo(tmpdir, ["plugin-a"])
        inventory_path = _fresh_inventory_path(repo_root)
        bootstrap = _run("bootstrap", repo_root, inventory_path)
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"

        plugin_inventory_dir = repo_root / "plugin-a" / ".claude-plugin"
        plugin_inventory_dir.mkdir(parents=True, exist_ok=True)
        (plugin_inventory_dir / "plugin-inventory.json").write_text(
            json.dumps({"plugin_id": "totally_different_id", "components": []}),
            encoding="utf-8",
        )

        plan = _run("plan", repo_root, inventory_path)
        if plan.returncode != 0:
            return False, f"plan failed: {plan.stderr.strip()}"
        operations = json.loads(plan.stdout)["operations"]
        conflicts = [
            op
            for op in operations
            if op["operation"] == "conflict"
            and op["name"] == "plugin-a"
            and "plugin_id" in op["reason"]
        ]
        if not conflicts:
            return False, f"expected a plugin_id-mismatch conflict for plugin-a, got: {operations}"
        return True, "plugin_id mismatch correctly surfaced as a conflict"


def check_import_grading_rollup_only():
    """Scenario 6 (Import grading, rollup-only): importing a whole-plugin
    report sets score/security_score from plugin_final_score/
    plugin_security_score exactly, never recomputed from components."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = _build_fixture_repo(tmpdir, ["plugin-a"])
        inventory_path = _fresh_inventory_path(repo_root)
        bootstrap = _run("bootstrap", repo_root, inventory_path)
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        report_path = pathlib.Path(tmpdir) / "report.json"
        report_path.write_text(
            json.dumps(
                {
                    "target": "plugin-a",
                    "target_type": "plugin",
                    "graded_at": "2026-08-25T10:00:00Z",
                    "plugin_final_score": 8.5,
                    "plugin_gates_applied": [],
                    "plugin_security_score": 9.0,
                    "grader_schema_version": "1.1.0",
                }
            ),
            encoding="utf-8",
        )
        result = _run(
            "import-grading", repo_root, inventory_path, report_path, "plugin-a", "plugin"
        )
        if result.returncode != 0:
            return False, f"import-grading failed: {result.stderr.strip()}"
        parsed = json.loads(result.stdout)
        if parsed["current_score"] != 8.5 or parsed["current_security_score"] != 9.0:
            return False, f"expected score 8.5/security 9.0 copied exactly, got: {parsed}"
        return True, "whole-plugin report's scores imported exactly, never recomputed"


def check_import_grading_wrong_target_type_rejected():
    """Scenario 7 (Import grading, wrong target_type rejected): a
    component-level target_type must be rejected before any write."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = _build_fixture_repo(tmpdir, ["plugin-a"])
        inventory_path = _fresh_inventory_path(repo_root)
        bootstrap = _run("bootstrap", repo_root, inventory_path)
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        report_path = pathlib.Path(tmpdir) / "report.json"
        report_path.write_text(
            json.dumps({"target": "plugin-a", "target_type": "skill"}), encoding="utf-8"
        )
        result = _run("import-grading", repo_root, inventory_path, report_path, "plugin-a", "skill")
        if result.returncode == 0:
            return False, "import-grading accepted target_type='skill' -- should have been rejected"
        return True, "non-'plugin' target_type correctly rejected before any write"


def check_stale_hash_rejection():
    """Scenario 8 (Stale hash rejection): apply with a mismatched hash must
    exit non-zero with no write."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = _build_fixture_repo(tmpdir, ["plugin-a"])
        inventory_path = _fresh_inventory_path(repo_root)
        bootstrap = _run("bootstrap", repo_root, inventory_path)
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        plan_path = pathlib.Path(tmpdir) / "empty_plan.json"
        plan_path.write_text("[]", encoding="utf-8")
        apply = _run("apply", repo_root, inventory_path, plan_path, "0" * 64)
        if apply.returncode == 0:
            return False, "apply with a wrong expected_hash succeeded -- should have been rejected"
        if "stale plan" not in apply.stderr:
            return False, f"expected a 'stale plan' rejection message, got: {apply.stderr.strip()}"
        return True, "apply correctly rejected a stale/wrong expected_hash"


def check_status_transition():
    """Scenario 9 (Status transition): resolving a conflict as retired
    closes the previously-open status period and opens a new one."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = _build_fixture_repo(tmpdir, ["plugin-a"])
        inventory_path = _fresh_inventory_path(repo_root)
        bootstrap = _run("bootstrap", repo_root, inventory_path)
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        plugin_id = json.loads(inventory_path.read_text(encoding="utf-8"))["plugins"][0]["id"]
        plan = _run("plan", repo_root, inventory_path)
        if plan.returncode != 0:
            return False, f"plan failed: {plan.stderr.strip()}"
        expected_hash = json.loads(plan.stdout)["expected_hash"]
        plan_path = pathlib.Path(tmpdir) / "transition_plan.json"
        plan_path.write_text(
            json.dumps(
                [
                    {
                        "operation": "status-transition",
                        "id": plugin_id,
                        "new_status": "retired",
                        "reason": "fixture retirement",
                        "evidence": [],
                    }
                ]
            ),
            encoding="utf-8",
        )
        apply = _run("apply", repo_root, inventory_path, plan_path, expected_hash)
        if apply.returncode != 0:
            return False, f"apply failed: {apply.stderr.strip()}"
        plugin = json.loads(inventory_path.read_text(encoding="utf-8"))["plugins"][0]
        if plugin["status"] != "retired":
            return False, f"expected status 'retired', got {plugin['status']!r}"
        open_periods = [p for p in plugin["status_history"] if p["valid_to"] is None]
        if len(open_periods) != 1 or open_periods[0]["status"] != "retired":
            return False, f"expected exactly one open 'retired' period, got: {open_periods}"
        return True, "status-transition correctly closed the old period and opened the new one"


def check_enum_rejection():
    """Scenario 10 (Enum rejection): setting a plugin's functional_role to
    a value outside the controlled vocabulary must be rejected before any
    write."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = _build_fixture_repo(tmpdir, ["plugin-a"])
        inventory_path = _fresh_inventory_path(repo_root)
        bootstrap = _run("bootstrap", repo_root, inventory_path)
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        plugin_id = json.loads(inventory_path.read_text(encoding="utf-8"))["plugins"][0]["id"]
        plan = _run("plan", repo_root, inventory_path)
        if plan.returncode != 0:
            return False, f"plan failed: {plan.stderr.strip()}"
        expected_hash = json.loads(plan.stdout)["expected_hash"]
        plan_path = pathlib.Path(tmpdir) / "bad_plan.json"
        plan_path.write_text(
            json.dumps(
                [
                    {
                        "operation": "update",
                        "id": plugin_id,
                        "field": "functional_role",
                        "new_value": "not_a_real_functional_role",
                    }
                ]
            ),
            encoding="utf-8",
        )
        apply = _run("apply", repo_root, inventory_path, plan_path, expected_hash)
        if apply.returncode == 0:
            return False, (
                "apply accepted an invalid functional_role enum value -- should have been rejected"
            )
        return True, "apply correctly rejected an invalid functional_role enum value"


def check_cli_bootstrap_check_roundtrip():
    """Live functional check: bootstrap a fresh marketplace inventory
    against a real copy of this repo's own marketplace.json, then confirm
    check reports zero drift immediately after -- Testing & Validation
    scenario 2.

    Builds a lightweight real-manifest fixture rather than copying the
    whole repo (93MB, far too large to copy per test run): copies the real
    .claude-plugin/marketplace.json verbatim into a fresh tempdir-rooted
    repo, then creates an empty directory for each plugin it declares --
    discover_plugins only reads the manifest, and read_plugin_inventory only
    checks for a plugin-inventory.json inside each source directory (whose
    absence is correctly reported as missing, not an error), so this
    preserves testing against the real plugin list/names without needing
    each plugin's actual file content. inventory_path must resolve to
    exactly <repo_root>/.claude-plugin/marketplace-inventory.json to satisfy
    require_inventory_path_under_scope_dir, so repo_root itself must be a
    real, writable directory this test controls, not the actual tracked
    repo root."""
    import tempfile

    real_repo_root = _find_repo_root()
    real_manifest = json.loads(
        (real_repo_root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = pathlib.Path(tmpdir) / "repo"
        manifest_dir = repo_root / ".claude-plugin"
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "marketplace.json").write_text(json.dumps(real_manifest), encoding="utf-8")
        for entry in real_manifest.get("plugins", []):
            source = entry.get("source")
            if source:
                (repo_root / source).mkdir(parents=True, exist_ok=True)
        inventory_path = _fresh_inventory_path(repo_root)
        bootstrap = _run("bootstrap", repo_root, inventory_path)
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        check = _run("check", repo_root, inventory_path)
        if check.returncode != 0:
            return False, f"check failed: {check.stderr.strip()}"
        result = json.loads(check.stdout)
        if result["drift_count"] != 0:
            return (
                False,
                f"expected 0 drift immediately after bootstrap, got {result['drift_count']}",
            )
        return True, f"bootstrap+check round-trip clean ({result['drift_count']} drift)"


def check_non_active_reappearance_conflict():
    """Scenario 12 (Conflict, non-active record reappears): a discovered
    candidate matching an existing 'retired' plugin record must be
    surfaced as a conflict, never silently no-op'd -- the fix for a
    cross-model-review finding that build_plan's discovery loop only ever
    compared against 'active' records, silently no-op'ing a planned/
    retired/deprecated/superseded record's reappearance."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = _build_fixture_repo(tmpdir, ["plugin-a"])
        inventory_path = _fresh_inventory_path(repo_root)
        bootstrap = _run("bootstrap", repo_root, inventory_path)
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        inventory["plugins"][0]["status"] = "retired"
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

        plan = _run("plan", repo_root, inventory_path)
        if plan.returncode != 0:
            return False, f"plan failed: {plan.stderr.strip()}"
        operations = json.loads(plan.stdout)["operations"]
        conflicts = [
            op for op in operations if op["operation"] == "conflict" and op["name"] == "plugin-a"
        ]
        if not conflicts:
            return False, f"expected a conflict entry for retired plugin-a, got: {operations}"
        return True, "retired record's reappearance correctly surfaced as a conflict, not no-op"


def check_check_clean_rejection_on_invalid_inventory():
    """Scenario 13 (Check, clean rejection on an invalid inventory): a
    hand-corrupted inventory must make check exit non-zero with a clean
    rejection message, never an uncaught Python traceback -- the fix for a
    cross-model-review finding that cmd_check called validate_inventory
    directly, unwrapped by reconcile.validate_or_exit."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = _build_fixture_repo(tmpdir, ["plugin-a"])
        inventory_path = _fresh_inventory_path(repo_root)
        bootstrap = _run("bootstrap", repo_root, inventory_path)
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        inventory["plugins"][0]["functional_role"] = "not_a_real_functional_role"
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

        check = _run("check", repo_root, inventory_path)
        if check.returncode == 0:
            return False, "check accepted an invalid functional_role -- should have been rejected"
        if "Traceback" in check.stderr:
            return False, f"check crashed with an uncaught traceback: {check.stderr.strip()}"
        return True, "check correctly rejected an invalid inventory with a clean message"


def check_apply_update_rejects_history_field():
    """Scenario 14 (Apply rejects an out-of-allowlist update field): an
    approved plan naming status_history directly in an 'update' operation
    must be rejected before any write -- the fix for a cross-model-review
    finding that apply_update had no field allowlist, letting an 'update'
    operation silently overwrite append-only history."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = _build_fixture_repo(tmpdir, ["plugin-a"])
        inventory_path = _fresh_inventory_path(repo_root)
        bootstrap = _run("bootstrap", repo_root, inventory_path)
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        before = inventory_path.read_text(encoding="utf-8")
        plugin_id = json.loads(before)["plugins"][0]["id"]
        plan = _run("plan", repo_root, inventory_path)
        if plan.returncode != 0:
            return False, f"plan failed: {plan.stderr.strip()}"
        expected_hash = json.loads(plan.stdout)["expected_hash"]
        plan_path = pathlib.Path(tmpdir) / "bad_plan.json"
        plan_path.write_text(
            json.dumps(
                [
                    {
                        "operation": "update",
                        "id": plugin_id,
                        "field": "status_history",
                        "new_value": [],
                    }
                ]
            ),
            encoding="utf-8",
        )
        apply = _run("apply", repo_root, inventory_path, plan_path, expected_hash)
        if apply.returncode == 0:
            return False, "apply accepted an update to status_history -- should have been rejected"
        if "Traceback" in apply.stderr:
            return False, f"apply crashed with an uncaught traceback: {apply.stderr.strip()}"
        after = inventory_path.read_text(encoding="utf-8")
        if before != after:
            return False, "inventory file was modified despite the rejected update"
        return True, "apply correctly rejected an out-of-allowlist update field (status_history)"


def check_import_grading_score_range_rejection():
    """Scenario 15 (Import grading rejects an out-of-range/non-numeric
    score): a report with plugin_final_score outside [0, 10] must be
    rejected before any write -- the fix for a cross-model-review finding
    that imported scores were never type/range-checked."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = _build_fixture_repo(tmpdir, ["plugin-a"])
        inventory_path = _fresh_inventory_path(repo_root)
        bootstrap = _run("bootstrap", repo_root, inventory_path)
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        report_path = pathlib.Path(tmpdir) / "report.json"
        report_path.write_text(
            json.dumps(
                {
                    "target": "plugin-a",
                    "target_type": "plugin",
                    "graded_at": "2026-08-25T10:00:00Z",
                    "plugin_final_score": 999,
                    "plugin_gates_applied": [],
                    "grader_schema_version": "1.1.0",
                }
            ),
            encoding="utf-8",
        )
        result = _run(
            "import-grading", repo_root, inventory_path, report_path, "plugin-a", "plugin"
        )
        if result.returncode == 0:
            return (
                False,
                "import-grading accepted an out-of-range score (999) -- should be rejected",
            )
        if "Traceback" in result.stderr:
            return (
                False,
                f"import-grading crashed with an uncaught traceback: {result.stderr.strip()}",
            )
        plugin = json.loads(inventory_path.read_text(encoding="utf-8"))["plugins"][0]
        if plugin["score"] is not None:
            return False, f"score should be unchanged (None), got {plugin['score']!r}"
        return True, "import-grading correctly rejected an out-of-range score before any write"


def check_schema_conformance():
    """Structural, dependency-free comparison (no jsonschema library needed):
    confirm the schema's declared `plugin` required-key set matches exactly
    what `apply_add()` in the script actually writes into a new record, so
    the two can't silently drift apart with nothing catching it."""
    schema_path = SKILL_DIR / "assets" / "marketplace-inventory.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema_keys = set(schema.get("definitions", {}).get("plugin", {}).get("required", []))
    if not schema_keys:
        return False, "schema has no definitions.plugin.required to compare against"
    script_text = SCRIPT.read_text(encoding="utf-8")
    match = re.search(r"def apply_add\(.*?\n    record = \{(.*?)\n    \}", script_text, re.DOTALL)
    if not match:
        return False, "could not locate apply_add()'s record literal in the script"
    # Only top-level keys (exactly 8-space indented) count -- a nested dict
    # (e.g. status_history's own "status"/"reason" keys) is indented deeper
    # and must not be confused with the record's own top-level fields.
    written_keys = set(re.findall(r'^ {8}"([\w]+)":', match.group(1), re.MULTILINE))
    missing = schema_keys - written_keys
    extra = written_keys - schema_keys
    if missing or extra:
        parts = []
        if missing:
            parts.append(
                "schema requires but apply_add never writes: " + ", ".join(sorted(missing))
            )
        if extra:
            parts.append("apply_add writes but schema doesn't require: " + ", ".join(sorted(extra)))
        return False, "; ".join(parts)
    return (
        True,
        f"schema's {len(schema_keys)} required plugin keys match apply_add()'s record exactly",
    )


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_conflict_missing_active_plugin,
    check_plugin_id_mismatch_conflict,
    check_import_grading_rollup_only,
    check_import_grading_wrong_target_type_rejected,
    check_stale_hash_rejection,
    check_status_transition,
    check_enum_rejection,
    check_cli_bootstrap_check_roundtrip,
    check_schema_conformance,
    check_non_active_reappearance_conflict,
    check_check_clean_rejection_on_invalid_inventory,
    check_apply_update_rejects_history_field,
    check_import_grading_score_range_rejection,
]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
