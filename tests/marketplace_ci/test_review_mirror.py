"""The mirror verifier (issue #576, #568 Phase 2): `r19-mirror-drift`.

`run_delta_structural_checks` already finds a `.claude/` mirror (or Codex export) that has drifted
from its canonical `plugins/` source for every component a PR touches. This verifier turns each
result into a rule-keyed script finding, so it goes through `aggregate_findings` and
`gate_decision` like every other verifier, and the exceptions registry can suppress it. The finding
sits on the canonical file and cites the changed paths of its component, so a PR that touches the
component owns the drift even when the drifted file itself is untouched. `run-codex-review` keeps
listing `structural_findings` in its result file (the parity wrapper expects the key) but no longer
blocks on that list by itself.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.marketplace_ci import review_contract
from scripts.marketplace_ci import review_verifiers as rv
from scripts.marketplace_ci.__main__ import main
from scripts.marketplace_ci.git_state import ChangedPath

RULE = "r19-mirror-drift"
ROSTER = tuple(r.name for r in review_contract.ROSTER)
CANON = "plugins/demo-kit/skills/demo/SKILL.md"
MIRROR = ".claude/skills/demo/SKILL.md"
REF = "plugins/demo-kit/skills/demo/references/notes.md"
REF_MIRROR = ".claude/skills/demo/references/notes.md"
OTHER = "plugins/demo-kit/skills/other/SKILL.md"
OTHER_MIRROR = ".claude/skills/other/SKILL.md"


def _commit(root: Path, message: str) -> str:
    subprocess.run(["git", "add", "-A", "-f"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def _registry(git_repo):
    git_repo.write(
        ".claude/marketplace-sync.json",
        json.dumps({"version": 1, "plugin_mirrors": ["demo-kit"], "codex_exports": {}}),
    )


def _base(git_repo):
    """A registered plugin whose mirrors are all in sync."""
    _registry(git_repo)
    for canon, mirror in ((CANON, MIRROR), (REF, REF_MIRROR), (OTHER, OTHER_MIRROR)):
        git_repo.write(canon, f"content of {canon}\n")
        git_repo.write(mirror, f"content of {canon}\n")
    return _commit(git_repo.root, "base")


def _outcome(git_repo, changed, base, **kwargs):
    outcomes = rv.run_verifiers(git_repo.root, changed, base, **kwargs)
    return next(o for o in outcomes if o.name == "path-and-mirror")


def _modify(path):
    return ChangedPath("M", path, path)


def _drift(findings):
    return [f for f in findings if f.rule == RULE]


def test_drift_in_a_touched_component_is_a_rule_keyed_blocking_finding(git_repo):
    base = _base(git_repo)
    git_repo.write(CANON, "edited, mirror not updated\n")
    _commit(git_repo.root, "edit")
    (finding,) = _drift(_outcome(git_repo, (_modify(CANON),), base).findings)
    assert finding.severity == "Critical" and finding.source == "script"
    assert finding.rule_class == "graph" and finding.path == CANON and finding.line is None
    assert finding.components == (f"{CANON}:*",)
    assert "update" in finding.evidence


def test_an_in_sync_mirror_is_clean(git_repo):
    base = _base(git_repo)
    git_repo.write(CANON, "edited\n")
    git_repo.write(MIRROR, "edited\n")
    _commit(git_repo.root, "edit both")
    assert _drift(_outcome(git_repo, (_modify(CANON),), base).findings) == []


def test_drift_in_a_component_the_pr_did_not_touch_is_not_reported(git_repo):
    base = _base(git_repo)
    git_repo.write(OTHER_MIRROR, "drifted in a component nobody edited\n")
    git_repo.write(CANON, "edited\n")
    git_repo.write(MIRROR, "edited\n")
    _commit(git_repo.root, "edit demo only")
    assert _drift(_outcome(git_repo, (_modify(CANON),), base).findings) == []


def test_a_new_component_with_no_mirror_is_reported(git_repo):
    base = _base(git_repo)
    new = "plugins/demo-kit/skills/fresh/SKILL.md"
    git_repo.write(new, "new skill\n")
    _commit(git_repo.root, "add")
    (finding,) = _drift(_outcome(git_repo, (ChangedPath("A", None, new),), base).findings)
    assert finding.path == new and "create" in finding.evidence


def test_a_drifted_file_the_pr_left_alone_is_owned_through_the_changed_component(git_repo):
    base = _base(git_repo)
    git_repo.write(REF_MIRROR, "someone edited only the mirror\n")  # drift in an untouched file
    git_repo.write(CANON, "edited\n")
    git_repo.write(MIRROR, "edited\n")
    _commit(git_repo.root, "touch SKILL.md only")
    (finding,) = _drift(_outcome(git_repo, (_modify(CANON),), base).findings)
    assert finding.path == REF and finding.components == (f"{CANON}:*",)


def test_a_rename_away_from_a_component_still_checks_that_component(git_repo):
    base = _base(git_repo)
    git_repo.write(REF_MIRROR, "drift elsewhere in the same component\n")
    (git_repo.root / CANON).rename(git_repo.root / "plugins/demo-kit/LICENSE")
    _commit(git_repo.root, "rename away")
    change = (ChangedPath("R", CANON, "plugins/demo-kit/LICENSE"),)
    assert _drift(_outcome(git_repo, change, base).findings) != []


def test_without_a_registry_nothing_is_checked(git_repo):
    git_repo.write(CANON, "x\n")
    base = _commit(git_repo.root, "base")
    git_repo.write(CANON, "y\n")
    _commit(git_repo.root, "edit")
    assert _drift(_outcome(git_repo, (_modify(CANON),), base).findings) == []


def test_a_precomputed_plan_is_used_instead_of_planning_again(git_repo):
    base = _base(git_repo)
    git_repo.write(CANON, "edited, mirror not updated\n")
    _commit(git_repo.root, "edit")
    assert _drift(_outcome(git_repo, (_modify(CANON),), base, structural=()).findings) == []


def test_more_changed_paths_than_can_be_cited_fails_the_run_closed(monkeypatch, git_repo):
    base = _base(git_repo)
    git_repo.write(CANON, "edited, mirror not updated\n")
    _commit(git_repo.root, "edit")
    monkeypatch.setattr(rv, "MAX_CITED_PATHS", 0)
    with pytest.raises(RuntimeError, match="cite"):
        rv.run_verifiers(git_repo.root, (_modify(CANON),), base)


def test_the_same_head_gives_the_same_findings(git_repo):
    base = _base(git_repo)
    git_repo.write(CANON, "edited, mirror not updated\n")
    _commit(git_repo.root, "edit")
    change = (_modify(CANON),)
    assert rv.run_verifiers(git_repo.root, change, base) == rv.run_verifiers(
        git_repo.root, change, base
    )


# --- run-codex-review wiring ------------------------------------------------------------------

CLEAN = json.dumps(
    {
        "contract_version": "1",
        "dispatch": {
            "id": "d",
            "reviewer": "security-reviewer",
            "backend": "codex",
            "target_paths": [CANON],
        },
        "provenance": {
            "provider": "openai",
            "model": "m",
            "cli_version": "9.9.9",
            "execution_profile": "read-only",
        },
        "findings": [],
        "verdict": "pass",
        "inspection_limits": [],
    }
).encode()


def _drifted_review_repo(git_repo):
    for name in ROSTER:
        git_repo.write(f".codex/agents/{name}.toml", 'developer_instructions = """\ncheck\n"""\n')
    base = _base(git_repo)
    git_repo.write(CANON, "edited, mirror not updated\n")
    _commit(git_repo.root, "edit")
    return git_repo.root, base


def _run(monkeypatch, root, base, tmp_path):
    real_run = subprocess.run

    def fake_run(argv, **kw):
        if argv[0] == "node":
            return subprocess.CompletedProcess(argv, returncode=0, stdout=CLEAN, stderr=b"")
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.chdir(root)
    out = tmp_path / "result.json"
    rc = main(["run-codex-review", "--base-sha", base, "--output", str(out)])
    return rc, json.loads(out.read_text(encoding="utf-8"))


def test_mirror_drift_blocks_the_run_through_the_gate(monkeypatch, git_repo, tmp_path):
    root, base = _drifted_review_repo(git_repo)
    rc, payload = _run(monkeypatch, root, base, tmp_path)
    assert rc == 1 and payload["blocking"] is True
    (finding,) = [f for f in payload["findings"] if f["rule"] == RULE]
    assert finding["gate"] == "block" and finding["in_diff"] is True
    assert finding["source"] == "script" and finding["rule_class"] == "graph"
    assert len(payload["structural_findings"]) == 1  # still listed, for the parity wrapper


def test_mirror_drift_in_an_untouched_component_does_not_block(monkeypatch, git_repo, tmp_path):
    for name in ROSTER:
        git_repo.write(f".codex/agents/{name}.toml", 'developer_instructions = """\ncheck\n"""\n')
    base = _base(git_repo)
    git_repo.write("README.md", "docs only")
    _commit(git_repo.root, "docs")
    rc, payload = _run(monkeypatch, git_repo.root, base, tmp_path)
    assert rc == 0 and payload["blocking"] is False and payload["structural_findings"] == []


def test_a_registry_entry_can_now_suppress_mirror_drift(monkeypatch, git_repo, tmp_path):
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        "exceptions:\n"
        f"  - rule: {RULE}\n"
        '    path: "plugins/**"\n'
        "    reason: test reason\n"
        "    authority: docs/ci.md\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(review_contract, "EXCEPTIONS_PATH", registry)
    root, base = _drifted_review_repo(git_repo)
    rc, payload = _run(monkeypatch, root, base, tmp_path)
    assert rc == 0 and payload["blocking"] is False
    (finding,) = [f for f in payload["findings"] if f["rule"] == RULE]
    assert finding["gate"] == "suppressed" and finding["suppressed"] is True
    assert len(payload["structural_findings"]) == 1  # the list is informational, not a gate


# --- the gate counts a `path:*` component as changed however little of it changed ---------------


def _drift_finding(components, source="script"):
    from dataclasses import replace

    base = rv._unreadable_finding("plugins/x/b.md", "reason", RULE)
    return replace(base, components=components, source=source)


def _in_diff(finding):
    from scripts.marketplace_ci.review import split_findings_by_diff

    in_diff, _ = split_findings_by_diff(
        [finding], {"plugins/x/a.md": ((5, 5),)}, changed_paths=["plugins/x/a.md"]
    )
    return bool(in_diff)


def test_a_script_component_with_a_star_counts_any_change_to_the_file():
    assert _in_diff(_drift_finding(("plugins/x/a.md:*",))) is True


def test_a_bare_component_still_needs_the_file_changed_in_full():
    assert _in_diff(_drift_finding(("plugins/x/a.md",))) is False


def test_a_line_component_still_needs_that_line_changed():
    assert _in_diff(_drift_finding(("plugins/x/a.md:9",))) is False
    assert _in_diff(_drift_finding(("plugins/x/a.md:5",))) is True


def test_a_model_finding_cannot_widen_its_own_scope_with_a_star():
    assert _in_diff(_drift_finding(("plugins/x/a.md:*",), source="model")) is False


def test_a_star_on_an_unchanged_file_does_not_count():
    assert _in_diff(_drift_finding(("plugins/x/other.md:*",))) is False


def test_drift_in_an_untouched_file_of_a_touched_component_blocks_the_run(
    monkeypatch, git_repo, tmp_path
):
    """The reviewer's M1: the PR edits SKILL.md (an ordinary hunk), syncs its mirror, and hand-edits
    the mirror of a file it did not touch. The old channel exited 1 on any drift."""
    for name in ROSTER:
        git_repo.write(f".codex/agents/{name}.toml", 'developer_instructions = """\ncheck\n"""\n')
    base = _base(git_repo)
    git_repo.write(CANON, f"content of {CANON}\nan ordinary edit\n")
    git_repo.write(MIRROR, f"content of {CANON}\nan ordinary edit\n")
    git_repo.write(REF_MIRROR, "hand-edited mirror of a file the PR did not touch\n")
    _commit(git_repo.root, "edit and sync one file, drift another")
    rc, payload = _run(monkeypatch, git_repo.root, base, tmp_path)
    assert rc == 1 and payload["blocking"] is True
    (finding,) = [f for f in payload["findings"] if f["rule"] == RULE]
    assert finding["path"] == REF and finding["gate"] == "block"


def test_a_starred_component_is_not_run_through_the_line_number_parser():
    """A changed file named `a:1` is cited as `a:1:*`; stripping the star must give the whole path
    back, not path `a` with line 1."""
    from dataclasses import replace

    from scripts.marketplace_ci.review import split_findings_by_diff

    finding = replace(
        rv._unreadable_finding("plugins/x/skills/y/references/b.md", "reason", RULE),
        components=("plugins/x/skills/y/a:1:*",),
    )
    in_diff, _ = split_findings_by_diff(
        [finding],
        {"plugins/x/skills/y/a:1": ((1, 1),)},
        changed_paths=["plugins/x/skills/y/a:1"],
    )
    assert in_diff == (finding,)


def test_a_malformed_registry_is_a_could_not_run_failure_not_a_traceback(
    monkeypatch, git_repo, tmp_path
):
    for name in ROSTER:
        git_repo.write(f".codex/agents/{name}.toml", 'developer_instructions = """\ncheck\n"""\n')
    base = _base(git_repo)
    git_repo.write(".claude/marketplace-sync.json", "{not json")
    git_repo.write(CANON, "edited\n")
    _commit(git_repo.root, "break the registry")
    rc, payload = _run(monkeypatch, git_repo.root, base, tmp_path)
    assert rc == 2 and payload["status"] == "could_not_run" and payload["blocking"] is True
