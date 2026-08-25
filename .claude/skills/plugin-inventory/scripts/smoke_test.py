#!/usr/bin/env python3
"""Persisted smoke test for plugin-inventory: frontmatter validity, referenced-file
existence, Bash-scope grant consistency, and the shared CLI script's own subcommands."""

import json
import pathlib
import re
import subprocess
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
SCRIPT = SKILL_DIR / "scripts" / "plugin-inventory.py"


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


def _write_skill(skills_dir, name):
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: fixture skill for smoke_test.py\n---\n\nBody.\n",
        encoding="utf-8",
    )


def _fresh_inventory_path(plugin_dir):
    """inventory_path must live at exactly <plugin_dir>/.claude-plugin/
    plugin-inventory.json -- the script's own write-boundary guard
    (require_inventory_path_under_scope_dir) refuses any other location,
    now that every write-capable subcommand takes plugin_dir and enforces
    real containment, not just a filename/parent-dir shape match."""
    path = pathlib.Path(plugin_dir) / ".claude-plugin" / "plugin-inventory.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *[str(a) for a in args]], capture_output=True, text=True
    )


def check_discovery_accuracy():
    """Scenario 1 (Discovery, live): discover against a small synthetic
    fixture plugin (not the large real plugin-devkit, so the assertion can
    be exact) and confirm every fixture skill appears exactly once, sorted,
    with no duplicates."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = pathlib.Path(tmpdir) / "skills"
        _write_skill(skills_dir, "skill-b")
        _write_skill(skills_dir, "skill-a")
        result = _run("discover", tmpdir)
        if result.returncode != 0:
            return False, f"discover failed: {result.stderr.strip()}"
        candidates = json.loads(result.stdout)
        names = [c["name"] for c in candidates]
        if names != ["skill-a", "skill-b"]:
            return False, f"expected sorted ['skill-a', 'skill-b'], got {names}"
        if any(c["type"] != "skill" for c in candidates):
            return False, f"expected type 'skill' for both candidates, got {candidates}"
        return True, "both fixture skills discovered exactly once, sorted"


def check_plan_apply_add_operation():
    """Scenario 3 (Plan/Apply, add operation): bootstrap with one skill,
    add a second skill directory, confirm plan proposes an 'add' operation
    for it, apply it, and confirm the new component is active afterward."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        skills_dir = plugin_dir / "skills"
        _write_skill(skills_dir, "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"

        _write_skill(skills_dir, "skill-b")
        plan = _run("plan", plugin_dir, inventory_path)
        if plan.returncode != 0:
            return False, f"plan failed: {plan.stderr.strip()}"
        plan_data = json.loads(plan.stdout)
        add_ops = [op for op in plan_data["operations"] if op["operation"] == "add"]
        if len(add_ops) != 1 or add_ops[0]["name"] != "skill-b":
            return False, f"expected exactly one 'add' op for skill-b, got {add_ops}"
        if not add_ops[0].get("requires_approval"):
            return False, "add operation for skill-b did not set requires_approval: true"

        plan_path = pathlib.Path(tmpdir) / "approved_plan.json"
        plan_path.write_text(json.dumps(add_ops), encoding="utf-8")
        apply = _run("apply", plugin_dir, inventory_path, plan_path, plan_data["expected_hash"])
        if apply.returncode != 0:
            return False, f"apply failed: {apply.stderr.strip()}"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        active_names = {c["name"] for c in inventory["components"] if c["status"] == "active"}
        if "skill-b" not in active_names:
            return False, f"skill-b not active after apply: {active_names}"
        return True, "add operation proposed by plan and correctly applied"


def check_stale_hash_rejection():
    """Scenario 4 (Stale hash rejection): apply with a deliberately wrong
    expected_hash must be rejected outright, never applied."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        plan_path = pathlib.Path(tmpdir) / "empty_plan.json"
        plan_path.write_text("[]", encoding="utf-8")
        apply = _run(
            "apply",
            plugin_dir,
            inventory_path,
            plan_path,
            "0000000000000000000000000000000000000000000000000000000000000000",
        )
        if apply.returncode == 0:
            return False, "apply with a wrong expected_hash succeeded -- should have been rejected"
        if "stale plan" not in apply.stderr:
            return False, f"expected a 'stale plan' rejection message, got: {apply.stderr.strip()}"
        return True, "apply correctly rejected a stale/wrong expected_hash"


def check_import_grading_dedup():
    """Scenario 5 (Import grading, dedup): importing the identical report
    twice appends a scoring event only the first time -- the second import
    is a no-op duplicate (same report hash already imported)."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        report_path = pathlib.Path(tmpdir) / "report.json"
        report_path.write_text(
            json.dumps(
                {
                    "target": "skill-a",
                    "target_type": "skill",
                    "graded_at": "2026-08-25T10:00:00Z",
                    "final_score": 9.0,
                    "gates_applied": [],
                    "dimensions": {"safety_risk_handling": {"score": 8.0, "is_na": False}},
                    "grader_schema_version": "1.1.0",
                }
            ),
            encoding="utf-8",
        )
        first = _run("import-grading", plugin_dir, inventory_path, report_path, "skill-a", "skill")
        if first.returncode != 0:
            return False, f"first import-grading failed: {first.stderr.strip()}"
        if not json.loads(first.stdout)["quality_score_appended"]:
            return False, "first import-grading should have appended a new scoring event"
        second = _run("import-grading", plugin_dir, inventory_path, report_path, "skill-a", "skill")
        if second.returncode != 0:
            return False, f"second import-grading failed: {second.stderr.strip()}"
        if json.loads(second.stdout)["quality_score_appended"]:
            return False, "re-importing the identical report should have been a no-op duplicate"
        return True, "re-importing an identical report correctly deduplicated (no new event)"


def check_conflict_missing_active_component():
    """Scenario 6 (Conflict, missing active component): once a component is
    active and its filesystem path then disappears, check must surface a
    'conflict' operation, not silently drop or auto-retire the record."""
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        skills_dir = plugin_dir / "skills"
        _write_skill(skills_dir, "skill-a")
        _write_skill(skills_dir, "skill-b")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        shutil.rmtree(skills_dir / "skill-b")
        check = _run("check", inventory_path, plugin_dir)
        if check.returncode != 0:
            return False, f"check failed: {check.stderr.strip()}"
        drift = json.loads(check.stdout)["drift"]
        conflicts = [
            op for op in drift if op["operation"] == "conflict" and op["name"] == "skill-b"
        ]
        if not conflicts:
            return False, f"expected a conflict entry for skill-b, got drift: {drift}"
        return True, "missing active component correctly surfaced as a conflict, not auto-retired"


def check_repair_history_structural_rejection():
    """Scenario 9 (Repair history, structurally invalid replacement
    rejected): a replacement history with two open periods must be rejected
    before any write happens."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        component_id = json.loads(inventory_path.read_text(encoding="utf-8"))["components"][0]["id"]
        replacement_path = pathlib.Path(tmpdir) / "replacement.json"
        replacement_path.write_text(
            json.dumps(
                [
                    {
                        "status": "active",
                        "valid_from": "2020-01-01",
                        "valid_to": None,
                        "reason": "bad fixture 1",
                        "evidence": [],
                    },
                    {
                        "status": "retired",
                        "valid_from": "2021-01-01",
                        "valid_to": None,
                        "reason": "bad fixture 2 -- also open, invalid",
                        "evidence": [],
                    },
                ]
            ),
            encoding="utf-8",
        )
        repair = _run(
            "repair-history",
            plugin_dir,
            inventory_path,
            component_id,
            "status_history",
            replacement_path,
            "--confirm",
            component_id,
        )
        if repair.returncode == 0:
            return False, "repair-history accepted a replacement with two open periods"
        return True, "repair-history correctly rejected a structurally invalid replacement history"


def check_enum_rejection():
    """Scenario 10 (Enum rejection): setting a component's functional_role to
    a value outside the controlled vocabulary must be rejected by
    validate_inventory before any write happens."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        component_id = inventory["components"][0]["id"]
        current_hash_result = _run("plan", plugin_dir, inventory_path)
        expected_hash = json.loads(current_hash_result.stdout)["expected_hash"]
        plan_path = pathlib.Path(tmpdir) / "bad_plan.json"
        plan_path.write_text(
            json.dumps(
                [
                    {
                        "operation": "update",
                        "id": component_id,
                        "field": "functional_role",
                        "new_value": "not_a_real_functional_role",
                    }
                ]
            ),
            encoding="utf-8",
        )
        apply = _run("apply", plugin_dir, inventory_path, plan_path, expected_hash)
        if apply.returncode == 0:
            return False, (
                "apply accepted an invalid functional_role enum value -- should have been rejected"
            )
        return True, "apply correctly rejected an invalid functional_role enum value"


def check_history_invariants():
    """Scenario 7 (History invariants): every bootstrapped component's
    status_history/naming_history has exactly one open period (valid_to:
    null) whose value matches the record's current status/name."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        component = json.loads(inventory_path.read_text(encoding="utf-8"))["components"][0]
        for field, current_key in (("status_history", "status"), ("naming_history", "name")):
            periods = component[field]
            open_periods = [p for p in periods if p["valid_to"] is None]
            if len(open_periods) != 1:
                return False, f"{field} has {len(open_periods)} open periods, expected exactly 1"
            value_key = "status" if field == "status_history" else "name"
            if open_periods[0][value_key] != component[current_key]:
                return False, (
                    f"{field}'s open period {value_key} {open_periods[0][value_key]!r} does not "
                    f"match the record's current {current_key} {component[current_key]!r}"
                )
        return True, "status_history and naming_history each have exactly one matching open period"


def check_cli_bootstrap_check_roundtrip():
    """A live functional check, not just structural: bootstrap a fresh
    inventory from a real copy of this repo's own plugin-devkit plugin, run
    check immediately after, and confirm zero drift -- the same round-trip
    Testing & Validation scenario 2 describes.

    Copies the real plugin_dir into the tempdir first (rather than
    discovering from the real path while writing to an unrelated scratch
    location) so inventory_path can satisfy the script's own
    require_inventory_path_under_scope_dir guard -- every write-capable
    subcommand now requires inventory_path to resolve to exactly
    <plugin_dir>/.claude-plugin/plugin-inventory.json, which means
    plugin_dir itself must be a real, writable directory this test controls,
    not the actual tracked repo. The copy preserves testing against real
    component data; only the write target moves."""
    import shutil
    import tempfile

    real_plugin_dir = _find_repo_root() / "plugins" / "plugin-devkit"
    if not real_plugin_dir.is_dir():
        return False, f"resolved plugin_dir does not exist: {real_plugin_dir}"
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "plugin-devkit"
        shutil.copytree(
            real_plugin_dir, plugin_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run(
            "bootstrap", plugin_dir, inventory_path, "plugin_deadbeef", "plugin-devkit"
        )
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        check = subprocess.run(
            [sys.executable, str(SCRIPT), "check", str(inventory_path), str(plugin_dir)],
            capture_output=True,
            text=True,
        )
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
    candidate matching an existing 'retired' record must be surfaced as a
    conflict, never silently no-op'd -- the fix for a cross-model-review
    finding that build_plan's discovery loop only ever compared against
    'active' records, silently no-op'ing a planned/retired/deprecated/
    superseded record's reappearance."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        inventory["components"][0]["status"] = "retired"
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

        plan = _run("plan", plugin_dir, inventory_path)
        if plan.returncode != 0:
            return False, f"plan failed: {plan.stderr.strip()}"
        operations = json.loads(plan.stdout)["operations"]
        conflicts = [
            op for op in operations if op["operation"] == "conflict" and op["name"] == "skill-a"
        ]
        if not conflicts:
            return False, f"expected a conflict entry for retired skill-a, got: {operations}"
        return True, "retired record's reappearance correctly surfaced as a conflict, not no-op"


def check_check_clean_rejection_on_invalid_inventory():
    """Scenario 13 (Check, clean rejection on an invalid inventory): a
    hand-corrupted inventory must make check exit non-zero with a clean
    rejection message, never an uncaught Python traceback -- the fix for a
    cross-model-review finding that cmd_check called validate_inventory
    directly, unwrapped by reconcile.validate_or_exit."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        inventory["components"][0]["functional_role"] = "not_a_real_functional_role"
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

        check = _run("check", inventory_path, plugin_dir)
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
    operation silently overwrite append-only history and bypass
    repair-history's own --confirm gate."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        before = inventory_path.read_text(encoding="utf-8")
        component_id = json.loads(before)["components"][0]["id"]
        plan = _run("plan", plugin_dir, inventory_path)
        expected_hash = json.loads(plan.stdout)["expected_hash"]
        plan_path = pathlib.Path(tmpdir) / "bad_plan.json"
        plan_path.write_text(
            json.dumps(
                [
                    {
                        "operation": "update",
                        "id": component_id,
                        "field": "status_history",
                        "new_value": [],
                    }
                ]
            ),
            encoding="utf-8",
        )
        apply = _run("apply", plugin_dir, inventory_path, plan_path, expected_hash)
        if apply.returncode == 0:
            return False, "apply accepted an update to status_history -- should have been rejected"
        after = inventory_path.read_text(encoding="utf-8")
        if before != after:
            return False, "inventory file was modified despite the rejected update"
        return True, "apply correctly rejected an out-of-allowlist update field (status_history)"


def check_import_grading_score_range_rejection():
    """Scenario 15 (Import grading rejects an out-of-range/non-numeric
    score): a report with final_score outside [0, 10] must be rejected
    before any write -- the fix for a cross-model-review finding that
    imported scores were never type/range-checked."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        report_path = pathlib.Path(tmpdir) / "report.json"
        report_path.write_text(
            json.dumps(
                {
                    "target": "skill-a",
                    "target_type": "skill",
                    "graded_at": "2026-08-25T10:00:00Z",
                    "final_score": 999,
                    "gates_applied": [],
                    "grader_schema_version": "1.1.0",
                }
            ),
            encoding="utf-8",
        )
        result = _run("import-grading", plugin_dir, inventory_path, report_path, "skill-a", "skill")
        if result.returncode == 0:
            return (
                False,
                "import-grading accepted an out-of-range score (999) -- should be rejected",
            )
        component = json.loads(inventory_path.read_text(encoding="utf-8"))["components"][0]
        if component["score"] is not None:
            return False, f"score should be unchanged (None), got {component['score']!r}"
        return True, "import-grading correctly rejected an out-of-range score before any write"


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_discovery_accuracy,
    check_plan_apply_add_operation,
    check_stale_hash_rejection,
    check_import_grading_dedup,
    check_conflict_missing_active_component,
    check_history_invariants,
    check_repair_history_structural_rejection,
    check_enum_rejection,
    check_cli_bootstrap_check_roundtrip,
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
