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

sys.path.insert(0, str(SKILL_DIR.parent.parent / "scripts"))
from inventory_common import json_store  # noqa: E402  # ty: ignore[unresolved-import]


def _current_hash(inventory_path):
    """The same json_store.compute_hash the CLI itself uses for repair-history's
    --expected-hash/--expected-replacement-hash and apply's expected_hash -- lets a
    test build a valid hash for the "correct" case, and a deliberately wrong one
    for the "stale" case."""
    return json_store.compute_hash(json.loads(inventory_path.read_text(encoding="utf-8")))


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
            "--expected-hash",
            _current_hash(inventory_path),
            "--expected-replacement-hash",
            _current_hash(replacement_path),
        )
        if repair.returncode == 0:
            return False, "repair-history accepted a replacement with two open periods"
        return True, "repair-history correctly rejected a structurally invalid replacement history"


def check_repair_history_stale_hash_rejected():
    """A --expected-hash that doesn't match the live inventory must be
    rejected before any write -- repair-history's own optimistic-concurrency
    gate, added after a live PR review found the original --confirm gate had
    no defense against a repair approved from a snapshot that changed before
    this command actually ran."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        before_text = inventory_path.read_text(encoding="utf-8")
        component_id = json.loads(before_text)["components"][0]["id"]
        replacement_path = pathlib.Path(tmpdir) / "replacement.json"
        replacement_path.write_text(
            json.dumps(
                [
                    {
                        "status": "planned",
                        "valid_from": "2020-01-01",
                        "valid_to": "2020-06-01",
                        "reason": "real prior status, backfilled from git history",
                        "evidence": ["commit abc1234"],
                    },
                    {
                        "status": "active",
                        "valid_from": "2020-06-01",
                        "valid_to": None,
                        "reason": "became active",
                        "evidence": ["commit def5678"],
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
            "--expected-hash",
            "0" * 64,
            "--expected-replacement-hash",
            _current_hash(replacement_path),
        )
        if repair.returncode == 0:
            return False, "repair-history accepted a wrong/stale --expected-hash"
        if "stale repair" not in repair.stderr:
            return (
                False,
                f"expected a 'stale repair' rejection message, got: {repair.stderr.strip()}",
            )
        after_text = inventory_path.read_text(encoding="utf-8")
        if after_text != before_text:
            return False, "inventory file was modified despite a stale --expected-hash"
        return True, "repair-history correctly rejected a stale/wrong --expected-hash"


def check_repair_history_invalid_status_rejected():
    """A replacement status_history period with a status value outside
    STATUS_VALUES must be rejected before any write -- validate_history_periods
    alone only checks date shapes/ordering, not the status enum itself."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        before_text = inventory_path.read_text(encoding="utf-8")
        component_id = json.loads(before_text)["components"][0]["id"]
        replacement_path = pathlib.Path(tmpdir) / "replacement.json"
        replacement_path.write_text(
            json.dumps(
                [
                    {
                        "status": "totally-invalid",
                        "valid_from": "2020-01-01",
                        "valid_to": None,
                        "reason": "a status value outside STATUS_VALUES",
                        "evidence": [],
                    }
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
            "--expected-hash",
            _current_hash(inventory_path),
            "--expected-replacement-hash",
            _current_hash(replacement_path),
        )
        if repair.returncode == 0:
            return False, "repair-history accepted a status value outside STATUS_VALUES"
        after_text = inventory_path.read_text(encoding="utf-8")
        if after_text != before_text:
            return False, "inventory file was modified despite an invalid status value"
        return True, "repair-history correctly rejected an invalid status enum value"


def check_repair_history_missing_reason_rejected():
    """A replacement period missing 'reason' (or with a non-list 'evidence')
    must be rejected before any write -- validate_history_periods alone
    never checks these fields at all."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        before_text = inventory_path.read_text(encoding="utf-8")
        component_id = json.loads(before_text)["components"][0]["id"]
        replacement_path = pathlib.Path(tmpdir) / "replacement.json"
        replacement_path.write_text(
            json.dumps(
                [
                    {
                        "status": "active",
                        "valid_from": "2020-01-01",
                        "valid_to": None,
                        "evidence": [],
                    }
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
            "--expected-hash",
            _current_hash(inventory_path),
            "--expected-replacement-hash",
            _current_hash(replacement_path),
        )
        if repair.returncode == 0:
            return False, "repair-history accepted a period with no 'reason' field"
        after_text = inventory_path.read_text(encoding="utf-8")
        if after_text != before_text:
            return False, "inventory file was modified despite a missing 'reason' field"
        return True, "repair-history correctly rejected a period missing 'reason'"


def check_repair_history_stale_replacement_hash_rejected():
    """A --expected-replacement-hash that doesn't match the actual
    replacement_history_path file's content must be rejected before any
    write -- a real gap found by a live security-reviewer pass on PR #238:
    --expected-hash alone only binds the *inventory's* pre-repair state, not
    the replacement content itself, so a caller could get approval for one
    replacement file and then swap in a different one at invocation time."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        before_text = inventory_path.read_text(encoding="utf-8")
        component_id = json.loads(before_text)["components"][0]["id"]
        replacement_path = pathlib.Path(tmpdir) / "replacement.json"
        replacement_path.write_text(
            json.dumps(
                [
                    {
                        "status": "planned",
                        "valid_from": "2020-01-01",
                        "valid_to": "2020-06-01",
                        "reason": "real prior status, backfilled from git history",
                        "evidence": ["commit abc1234"],
                    },
                    {
                        "status": "active",
                        "valid_from": "2020-06-01",
                        "valid_to": None,
                        "reason": "became active",
                        "evidence": ["commit def5678"],
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
            "--expected-hash",
            _current_hash(inventory_path),
            "--expected-replacement-hash",
            "0" * 64,
        )
        if repair.returncode == 0:
            return False, "repair-history accepted a wrong/stale --expected-replacement-hash"
        if "stale repair" not in repair.stderr:
            return (
                False,
                f"expected a 'stale repair' rejection message, got: {repair.stderr.strip()}",
            )
        after_text = inventory_path.read_text(encoding="utf-8")
        if after_text != before_text:
            return False, "inventory file was modified despite a stale --expected-replacement-hash"
        return True, "repair-history correctly rejected a stale/wrong --expected-replacement-hash"


def check_repair_history_evidence_item_type_rejected():
    """A replacement period whose 'evidence' list contains a non-string item
    must be rejected before any write -- the schema declares evidence as an
    array of strings; validating only the container (not its items) would
    let arbitrary nested JSON into the append-only audit history, found by a
    live security-reviewer pass on PR #238."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        before_text = inventory_path.read_text(encoding="utf-8")
        component_id = json.loads(before_text)["components"][0]["id"]
        replacement_path = pathlib.Path(tmpdir) / "replacement.json"
        replacement_path.write_text(
            json.dumps(
                [
                    {
                        "status": "active",
                        "valid_from": "2020-01-01",
                        "valid_to": None,
                        "reason": "evidence contains a non-string item",
                        "evidence": [{"nested": "object"}],
                    }
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
            "--expected-hash",
            _current_hash(inventory_path),
            "--expected-replacement-hash",
            _current_hash(replacement_path),
        )
        if repair.returncode == 0:
            return False, "repair-history accepted an 'evidence' list with a non-string item"
        after_text = inventory_path.read_text(encoding="utf-8")
        if after_text != before_text:
            return False, "inventory file was modified despite a non-string 'evidence' item"
        return True, "repair-history correctly rejected an 'evidence' list with a non-string item"


def check_repair_history_succeeds_on_malformed_current_inventory():
    """repair-history must be usable on the exact malformed history it's
    documented to fix -- e.g. two open status_history periods hand-corrupted
    into the current on-disk file. A live security-reviewer pass on PR #238
    found the original implementation pre-validated the *current* inventory
    with validate_inventory before doing anything else, which would reject
    the malformed file outright and lock the operator out of the one
    command meant to repair it. This confirms that pre-validation was
    removed and repair-history can now actually run in that scenario --
    atomic_write_json's own post-write validator (not a pre-read one) is
    what guarantees the *result* is valid."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        component = inventory["components"][0]
        component_id = component["id"]
        # Hand-corrupt status_history to have two open periods -- bypasses the
        # CLI entirely, simulating a bug in an earlier run or a hand edit.
        component["status_history"] = [
            {
                "status": "active",
                "valid_from": "2020-01-01",
                "valid_to": None,
                "reason": "original bootstrap period",
                "evidence": [],
            },
            {
                "status": "deprecated",
                "valid_from": "2021-01-01",
                "valid_to": None,
                "reason": "bug in an earlier run left this open too",
                "evidence": [],
            },
        ]
        component["status"] = "active"
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
        replacement_path = pathlib.Path(tmpdir) / "replacement.json"
        replacement_path.write_text(
            json.dumps(
                [
                    {
                        "status": "active",
                        "valid_from": "2020-01-01",
                        "valid_to": None,
                        "reason": "corrected: only one open period",
                        "evidence": ["manual correction"],
                    }
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
            "--expected-hash",
            _current_hash(inventory_path),
            "--expected-replacement-hash",
            _current_hash(replacement_path),
        )
        if repair.returncode != 0:
            return (
                False,
                "repair-history refused to run against its own documented malformed-history "
                f"scenario: {repair.stderr.strip()}",
            )
        check = _run("check", inventory_path, plugin_dir)
        if check.returncode != 0 or json.loads(check.stdout)["drift_count"] != 0:
            return (
                False,
                f"check reported drift after repairing a malformed inventory: {check.stdout}",
            )
        return (
            True,
            "repair-history correctly repaired a current inventory validate_inventory would reject",
        )


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
        if current_hash_result.returncode != 0:
            return False, f"plan failed: {current_hash_result.stderr.strip()}"
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
        # plugin-devkit's own real plugin-inventory.json may already exist (it does,
        # independently of this test) -- this scenario bootstraps a *fresh* copy
        # regardless, so strip any inventory the copytree above carried along.
        if inventory_path.exists():
            inventory_path.unlink()
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
        if plan.returncode != 0:
            return False, f"plan failed: {plan.stderr.strip()}"
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
        if "Traceback" in apply.stderr:
            return False, f"apply crashed with an uncaught traceback: {apply.stderr.strip()}"
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
        if "Traceback" in result.stderr:
            return (
                False,
                f"import-grading crashed with an uncaught traceback: {result.stderr.strip()}",
            )
        component = json.loads(inventory_path.read_text(encoding="utf-8"))["components"][0]
        if component["score"] is not None:
            return False, f"score should be unchanged (None), got {component['score']!r}"
        return True, "import-grading correctly rejected an out-of-range score before any write"


def check_status_transition_rename():
    """Scenario 16 (Status transition with rename): a status-transition
    operation carrying new_name must atomically update both name and
    naming_history -- the fix for a cross-model-review finding that no
    operation could actually rename a record (history.
    close_and_append_naming_period existed but was never called)."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        component_id = json.loads(inventory_path.read_text(encoding="utf-8"))["components"][0]["id"]
        plan = _run("plan", plugin_dir, inventory_path)
        if plan.returncode != 0:
            return False, f"plan failed: {plan.stderr.strip()}"
        expected_hash = json.loads(plan.stdout)["expected_hash"]
        plan_path = pathlib.Path(tmpdir) / "rename_plan.json"
        plan_path.write_text(
            json.dumps(
                [
                    {
                        "operation": "status-transition",
                        "id": component_id,
                        "new_status": "active",
                        "new_name": "skill-a-renamed",
                        "reason": "component was renamed on disk",
                        "evidence": [],
                    }
                ]
            ),
            encoding="utf-8",
        )
        apply = _run("apply", plugin_dir, inventory_path, plan_path, expected_hash)
        if apply.returncode != 0:
            return False, f"apply failed: {apply.stderr.strip()}"
        component = json.loads(inventory_path.read_text(encoding="utf-8"))["components"][0]
        if component["name"] != "skill-a-renamed":
            return False, f"expected name 'skill-a-renamed', got {component['name']!r}"
        open_periods = [p for p in component["naming_history"] if p["valid_to"] is None]
        if len(open_periods) != 1 or open_periods[0]["name"] != "skill-a-renamed":
            return (
                False,
                f"expected exactly one open 'skill-a-renamed' naming period, got: {open_periods}",
            )
        return (
            True,
            "status-transition with new_name correctly renamed both name and naming_history",
        )


def check_import_grading_ambiguous_target_rejected():
    """Scenario 17 (Import grading, ambiguous target rejected): a retired
    and an active component sharing the same (name, type) must make
    import-grading refuse to guess, rather than silently updating whichever
    one a bare next(...) happens to find first -- the fix for a
    cross-model-review finding that this could silently import a report
    against the wrong (retired) record."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        original = dict(inventory["components"][0])
        inventory["components"][0]["status"] = "retired"
        inventory["components"][0]["status_history"][0]["valid_to"] = "2026-08-20"
        inventory["components"][0]["status_history"].append(
            {
                "status": "retired",
                "valid_from": "2026-08-20",
                "valid_to": None,
                "reason": "fixture retirement",
                "evidence": [],
            }
        )
        new_record = dict(original)
        new_record["id"] = "component_newactive"
        new_record["status"] = "active"
        new_record["status_history"] = [
            {
                "status": "active",
                "valid_from": "2026-08-25",
                "valid_to": None,
                "reason": "fixture: re-materialized as a new active record",
                "evidence": [],
            }
        ]
        new_record["naming_history"] = [dict(new_record["naming_history"][0])]
        new_record["naming_history"][0]["valid_to"] = None
        new_record["score"] = None
        inventory["components"].append(new_record)
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

        report_path = pathlib.Path(tmpdir) / "report.json"
        report_path.write_text(
            json.dumps(
                {
                    "target": "skill-a",
                    "target_type": "skill",
                    "graded_at": "2026-08-25T10:00:00Z",
                    "final_score": 9.9,
                    "gates_applied": [],
                    "grader_schema_version": "1.1.0",
                }
            ),
            encoding="utf-8",
        )
        result = _run("import-grading", plugin_dir, inventory_path, report_path, "skill-a", "skill")
        if result.returncode == 0:
            return False, "import-grading accepted an ambiguous target -- should have been rejected"
        if "Traceback" in result.stderr:
            return (
                False,
                f"import-grading crashed with an uncaught traceback: {result.stderr.strip()}",
            )
        after = json.loads(inventory_path.read_text(encoding="utf-8"))
        for c in after["components"]:
            if c["score"] is not None:
                return False, f"a record's score was modified despite the ambiguity rejection: {c}"
        return (
            True,
            "import-grading correctly rejected an ambiguous name-based target before any write",
        )


def check_import_grading_rejects_non_string_graded_at():
    """Scenario 18 (Import grading rejects a non-string graded_at): a
    report with graded_at as an integer must be rejected on the first
    import -- the fix for a cross-model-review finding that a presence-only
    check let a malformed graded_at through, crashing a *later* import with
    an uncaught TypeError when history sorted/maxed over mixed types."""
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
                    "graded_at": 12345,
                    "final_score": 8.0,
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
                "import-grading accepted a non-string graded_at -- should have been rejected",
            )
        if "Traceback" in result.stderr:
            return (
                False,
                f"import-grading crashed with an uncaught traceback: {result.stderr.strip()}",
            )
        return True, "import-grading correctly rejected a non-string graded_at before any write"


def check_import_grading_rejects_offset_graded_at():
    """Scenario 19 (Import grading rejects a non-UTC-offset graded_at): a
    report with a syntactically valid but non-'Z' ISO timestamp must be
    rejected on the first import -- the fix for a round-3 finding that a
    bare non-empty-string check let two differently-offset (but both
    individually valid) timestamps through, which then sort in the wrong
    chronological order under history.py's raw lexicographic sort/max."""
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
                    "graded_at": "2026-08-21T01:00:00+10:00",
                    "final_score": 8.0,
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
                "import-grading accepted a non-'Z' graded_at offset -- should have been rejected",
            )
        if "Traceback" in result.stderr:
            return (
                False,
                f"import-grading crashed with an uncaught traceback: {result.stderr.strip()}",
            )
        return True, "import-grading correctly rejected a non-UTC-offset graded_at"


def check_reconciliation_prefers_active_on_duplicate_key():
    """Scenario 20 (Reconciliation prefers the active record on a duplicate
    key): when a retired record shares (name, type) with the active record
    that superseded it, and the retired one comes later in array order, a
    discovered candidate matching the active record's path must resolve to
    a clean no-op -- not a spurious conflict against the shadowed-by-array-
    order retired record. Fix for a round-3 finding that existing_by_key's
    dict comprehension kept whichever record came last on a duplicate key."""
    import copy
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        active = inventory["components"][0]
        retired = copy.deepcopy(active)
        retired["id"] = active["id"] + "-old"
        retired["status"] = "retired"
        retired["status_history"] = [
            {
                "status": "retired",
                "valid_from": active["status_history"][0]["valid_from"],
                "valid_to": None,
                "reason": "fixture retired duplicate",
                "evidence": [],
            }
        ]
        retired["naming_history"] = copy.deepcopy(active["naming_history"])
        # Appended after the active record -- array order is what exposes the bug.
        inventory["components"].append(retired)
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

        check = _run("check", inventory_path, plugin_dir)
        if check.returncode != 0:
            return False, f"check failed unexpectedly: {check.stderr.strip()}"
        result = json.loads(check.stdout)
        if result["drift_count"] != 0:
            return (
                False,
                f"expected 0 drift (clean no-op against the active record), "
                f"got drift_count={result['drift_count']}: {result['drift']}",
            )
        return (
            True,
            "reconciliation correctly resolved against the active record, not the retired one",
        )


def check_check_rejects_malformed_compatibility():
    """Scenario 21 (Check rejects a malformed compatibility shape): a
    component whose compatibility field is a list instead of a dict must
    make check exit non-zero with a clean rejection message, never an
    uncaught Python traceback -- the fix for a round-3 finding that
    validate_records' compatibility.values() call raised an AttributeError
    that validate_or_exit's (ValueError, KeyError, OSError) tuple didn't
    catch."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        bootstrap = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        inventory["components"][0]["compatibility"] = ["not", "a", "dict"]
        inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

        check = _run("check", inventory_path, plugin_dir)
        if check.returncode == 0:
            return False, "check accepted a list-shaped compatibility field -- should be rejected"
        if "Traceback" in check.stderr:
            return False, f"check crashed with an uncaught traceback: {check.stderr.strip()}"
        return True, "check correctly rejected a malformed compatibility shape with a clean message"


def check_bootstrap_refuses_existing_inventory():
    """Scenario 22 (Bootstrap refuses an already-existing inventory):
    calling bootstrap twice against the same path must make the second call
    fail closed with 'refusing to bootstrap: ... already exists' and leave
    the first call's file untouched -- this is exactly the guard
    check_cli_bootstrap_check_roundtrip's real-plugin-devkit-directory copy
    now has to work around by unlinking a pre-existing plugin-inventory.json
    before bootstrapping; nothing previously asserted the guard itself still
    fires."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = pathlib.Path(tmpdir) / "fixture_plugin"
        _write_skill(plugin_dir / "skills", "skill-a")
        inventory_path = _fresh_inventory_path(plugin_dir)
        first = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if first.returncode != 0:
            return False, f"first bootstrap failed: {first.stderr.strip()}"
        before_text = inventory_path.read_text(encoding="utf-8")

        second = _run("bootstrap", plugin_dir, inventory_path, "plugin_test", "fixture-plugin")
        if second.returncode == 0:
            return False, "second bootstrap against an existing inventory should have failed"
        if "already exists" not in second.stderr:
            return False, f"unexpected rejection message: {second.stderr.strip()}"
        after_text = inventory_path.read_text(encoding="utf-8")
        if after_text != before_text:
            return False, "inventory file was modified despite the second bootstrap being refused"
        return True, "bootstrap correctly refused to overwrite an existing inventory"


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
    check_repair_history_stale_hash_rejected,
    check_repair_history_invalid_status_rejected,
    check_repair_history_missing_reason_rejected,
    check_repair_history_stale_replacement_hash_rejected,
    check_repair_history_evidence_item_type_rejected,
    check_repair_history_succeeds_on_malformed_current_inventory,
    check_enum_rejection,
    check_cli_bootstrap_check_roundtrip,
    check_non_active_reappearance_conflict,
    check_check_clean_rejection_on_invalid_inventory,
    check_apply_update_rejects_history_field,
    check_import_grading_score_range_rejection,
    check_status_transition_rename,
    check_import_grading_ambiguous_target_rejected,
    check_import_grading_rejects_non_string_graded_at,
    check_import_grading_rejects_offset_graded_at,
    check_reconciliation_prefers_active_on_duplicate_key,
    check_check_rejects_malformed_compatibility,
    check_bootstrap_refuses_existing_inventory,
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
