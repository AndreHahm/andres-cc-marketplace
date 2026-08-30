import json
import subprocess

import pytest

from scripts.marketplace_ci.__main__ import main


def _write_registry(repo, **kwargs):
    payload = {
        "version": 1,
        "plugin_mirrors": kwargs.get("plugin_mirrors", []),
        "codex_exports": {
            "skills": kwargs.get("skills", []),
            "agents": kwargs.get("agents", []),
        },
    }
    if "divergence_exceptions" in kwargs:
        payload["divergence_exceptions"] = kwargs["divergence_exceptions"]
    registry_path = repo / ".claude" / "marketplace-sync.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    # check_staged_parity reads the registry from the Git index, never disk -- stage it
    # here so callers using a real git_repo see it the same way a commit would. A no-op,
    # tolerated failure for the plain `repo` fixture (no `.git` at all).
    subprocess.run(
        ["git", "add", "-f", ".claude/marketplace-sync.json"], cwd=repo, capture_output=True
    )
    return registry_path


def test_main_with_no_command_returns_2(monkeypatch, repo):
    monkeypatch.chdir(repo)
    assert main([]) == 2


def test_check_plugin_mirrors_fails_when_out_of_sync(monkeypatch, repo):
    _write_registry(repo, plugin_mirrors=["sample-kit"])
    monkeypatch.chdir(repo)
    assert main(["check-plugin-mirrors"]) == 1


def test_sync_then_check_plugin_mirrors_passes(monkeypatch, repo):
    _write_registry(repo, plugin_mirrors=["sample-kit"])
    monkeypatch.chdir(repo)
    assert main(["sync-plugin-mirrors"]) == 0
    assert main(["check-plugin-mirrors"]) == 0
    assert (repo / ".claude" / "skills" / "demo" / "SKILL.md").exists()


def test_check_plugin_mirrors_passes_with_only_warn_actions(monkeypatch, repo):
    # Regression guard: a "warn"-only plan (a divergence-excepted destination that's
    # missing, or intentionally differs from its canonical source) must exit 0 -- a
    # real production case (this repo's own marketplace-development/SKILL.md exception)
    # was regressing every CI run before this fix, since _handle_check_plugin_mirrors
    # returned 1 for ANY non-empty plan.actions, discarding _report's has_problem signal.
    _write_registry(
        repo,
        plugin_mirrors=["sample-kit"],
        divergence_exceptions=[
            {
                "source": "plugins/sample-kit/skills/demo/SKILL.md",
                "dest": ".claude/skills/demo/SKILL.md",
                "reason": "test: excepted destination not created yet",
            }
        ],
    )
    monkeypatch.chdir(repo)
    assert main(["check-plugin-mirrors"]) == 0


def test_check_codex_exports_blocks_legacy_command_export(monkeypatch, repo):
    _write_registry(repo)
    (repo / ".agents" / "skills" / "source-command-old").mkdir(parents=True)
    monkeypatch.chdir(repo)
    assert main(["check-codex-exports"]) == 1


def test_convert_then_check_codex_exports_passes(monkeypatch, repo):
    _write_registry(repo, skills=["export-demo"], agents=["export-demo"])
    monkeypatch.chdir(repo)
    assert main(["convert-codex-exports"]) == 0
    assert main(["check-codex-exports"]) == 0
    assert (repo / ".agents" / "skills" / "export-demo" / "SKILL.md").exists()
    assert (repo / ".codex" / "agents" / "export-demo.toml").exists()


def test_check_all_ok_after_full_sync(monkeypatch, repo):
    _write_registry(
        repo, plugin_mirrors=["sample-kit"], skills=["export-demo"], agents=["export-demo"]
    )
    monkeypatch.chdir(repo)
    assert main(["sync-plugin-mirrors"]) == 0
    assert main(["convert-codex-exports"]) == 0
    assert main(["check-all"]) == 0


def test_check_all_writes_json_output(monkeypatch, repo, tmp_path):
    _write_registry(repo, plugin_mirrors=["sample-kit"])
    monkeypatch.chdir(repo)
    out = tmp_path / "report.json"
    rc = main(["check-all", "--json-output", str(out)])
    assert rc == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["exit_code"] == 1


def test_repair_all_bootstrap_without_apply_does_not_write(monkeypatch, repo):
    _write_registry(repo, plugin_mirrors=["sample-kit"])
    monkeypatch.chdir(repo)
    rc = main(["repair-all", "--bootstrap"])
    assert rc == 0
    assert not (repo / ".claude" / "skills" / "demo" / "SKILL.md").exists()


def test_repair_all_bootstrap_with_apply_writes(monkeypatch, repo):
    _write_registry(repo, plugin_mirrors=["sample-kit"])
    monkeypatch.chdir(repo)
    rc = main(["repair-all", "--bootstrap", "--apply"])
    assert rc == 0
    assert (repo / ".claude" / "skills" / "demo" / "SKILL.md").exists()


def test_repair_all_applied_count_excludes_warn_actions(monkeypatch, repo, capsys):
    from scripts.marketplace_ci.conversion import plan_exports
    from scripts.marketplace_ci.registry import Registry
    from scripts.marketplace_ci.sync import plan_hooks_merge, plan_plugin_sync

    orphan = repo / ".claude" / "skills" / "ghost" / "SKILL.md"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("no canonical source", encoding="utf-8")

    _write_registry(repo, plugin_mirrors=["sample-kit"])
    registry = Registry.load(repo / ".claude" / "marketplace-sync.json")
    mirror_plan = plan_plugin_sync(repo, registry, previous=None, bootstrap=True)
    export_plan = plan_exports(repo, registry, previous=None, bootstrap=True)
    hooks_plan = plan_hooks_merge(repo, registry)
    all_actions = (*mirror_plan.actions, *export_plan.actions, *hooks_plan.actions)
    expected_applied = sum(1 for a in all_actions if a.operation != "warn")
    assert any(a.operation == "warn" for a in all_actions)  # the orphan is really in the plan

    monkeypatch.chdir(repo)
    rc = main(["repair-all", "--bootstrap", "--apply"])
    assert rc == 0

    out = capsys.readouterr().out
    summary_line = next(line for line in out.splitlines() if line.startswith("repair-all: applied"))
    applied_count = int(summary_line.split()[2])
    assert applied_count == expected_applied  # never inflated by the never-applied warn
    assert orphan.exists()  # untouched; warn actions are never executed


def test_registry_missing_returns_2(monkeypatch, repo):
    monkeypatch.chdir(repo)
    assert main(["check-plugin-mirrors"]) == 2


def test_help_text_lists_commands(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    for command in (
        "check-plugin-mirrors",
        "sync-plugin-mirrors",
        "check-codex-exports",
        "convert-codex-exports",
        "check-all",
        "repair-all",
    ):
        assert command in out


def test_check_all_staged_fails_on_unstaged_mirror_repair(monkeypatch, git_repo):
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "new")
    git_repo.write(".claude/skills/demo/SKILL.md", "new")  # never staged
    monkeypatch.chdir(git_repo.root)
    assert main(["check-all", "--staged"]) == 1


def test_check_all_staged_passes_when_index_is_consistent(monkeypatch, git_repo):
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "new")
    git_repo.stage(".claude/skills/demo/SKILL.md", "new")
    monkeypatch.chdir(git_repo.root)
    assert main(["check-all", "--staged"]) == 0


def test_check_all_committed_rejects_unresolvable_ref(monkeypatch, git_repo):
    _write_registry(git_repo.root)
    monkeypatch.chdir(git_repo.root)
    assert main(["check-all", "--committed", "not-a-real-ref"]) == 2


def _commit_and_sha(git_repo, path, content, message):
    import subprocess

    git_repo.stage(path, content)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=git_repo.root, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()


def test_check_pr_owner_short_circuit_passes(monkeypatch, git_repo, tmp_path):
    base_sha = _commit_and_sha(git_repo, "README.md", "hello", "init")
    head_sha = _commit_and_sha(git_repo, "README.md", "hello world", "update")

    template = git_repo.root / ".github" / "pull_request_template.md"
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_text("## Summary\n\n## Checklist\n", encoding="utf-8")

    event = {
        "pull_request": {
            "title": "feat: add readme update",
            "body": "## Summary\n\nUpdates readme.\n",
            "user": {"login": "andre"},
            "base": {
                "repo": {"owner": {"login": "andre"}, "full_name": "andre/repo"},
                "sha": base_sha,
            },
            "head": {"sha": head_sha},
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    monkeypatch.chdir(git_repo.root)
    assert main(["check-pr", "--event", str(event_path)]) == 0


def test_check_pr_handles_non_ascii_changed_path(monkeypatch, git_repo, tmp_path):
    """Security-review regression (M-N3): check-pr's own diff call fed
    changed_paths into CODEOWNERS/merge-privilege matching using plain
    `--name-only` splitlines, which C-quotes a non-ASCII path and could
    fail-open a CODEOWNERS match into the more permissive collaborator
    branch. Same -z fix as check-scope-bypass/run-codex-review; this test
    just confirms the diff step no longer chokes on such a path."""
    base_sha = _commit_and_sha(git_repo, "README.md", "hello", "init")
    import subprocess

    git_repo.write("plugins/demo-kit/skills/x/café.py", "content")
    subprocess.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "non-ascii change"], cwd=git_repo.root, check=True)
    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    template = git_repo.root / ".github" / "pull_request_template.md"
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_text("## Summary\n\n## Checklist\n", encoding="utf-8")

    event = {
        "pull_request": {
            "title": "feat: add non-ascii file",
            "body": "## Summary\n\nAdds a file.\n",
            "user": {"login": "andre"},
            "base": {
                "repo": {"owner": {"login": "andre"}, "full_name": "andre/repo"},
                "sha": base_sha,
            },
            "head": {"sha": head_sha},
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    monkeypatch.chdir(git_repo.root)
    assert main(["check-pr", "--event", str(event_path)]) == 0


def test_check_pr_unresolvable_diff_returns_2(monkeypatch, git_repo, tmp_path):
    """Security-review regression (m2): a failed diff must never silently
    substitute an empty changed_paths list -- that fails open on
    check_merge_rights' CODEOWNERS matching (no match falls through to the
    more permissive collaborator-permission branch)."""
    head_sha = _commit_and_sha(git_repo, "README.md", "hello", "init")

    event = {
        "pull_request": {
            "title": "feat: add readme update",
            "body": "## Summary\n\nUpdates readme.\n",
            "user": {"login": "andre"},
            "base": {
                "repo": {"owner": {"login": "andre"}, "full_name": "andre/repo"},
                "sha": "0" * 40,
            },
            "head": {"sha": head_sha},
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    monkeypatch.chdir(git_repo.root)
    assert main(["check-pr", "--event", str(event_path)]) == 2


def test_check_pr_bad_title_fails(monkeypatch, git_repo, tmp_path):
    base_sha = _commit_and_sha(git_repo, "README.md", "hello", "init")
    head_sha = _commit_and_sha(git_repo, "README.md", "hello world", "update")

    event = {
        "pull_request": {
            "title": "not a conventional title",
            "body": "",
            "user": {"login": "andre"},
            "base": {
                "repo": {"owner": {"login": "andre"}, "full_name": "andre/repo"},
                "sha": base_sha,
            },
            "head": {"sha": head_sha},
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    monkeypatch.chdir(git_repo.root)
    assert main(["check-pr", "--event", str(event_path)]) == 1


def test_check_pr_missing_event_file_returns_2(monkeypatch, git_repo, tmp_path):
    monkeypatch.chdir(git_repo.root)
    assert main(["check-pr", "--event", str(tmp_path / "does-not-exist.json")]) == 2


def test_check_pr_missing_field_returns_2(monkeypatch, git_repo, tmp_path):
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"pull_request": {"title": "feat: x"}}), encoding="utf-8")
    monkeypatch.chdir(git_repo.root)
    assert main(["check-pr", "--event", str(event_path)]) == 2


def test_handle_post_edit_cascades_and_reports_via_stdout(monkeypatch, repo, capsys):
    import io

    _write_registry(repo, plugin_mirrors=["sample-kit"], skills=["demo"])
    monkeypatch.chdir(repo)
    event = {
        "tool_input": {
            "file_path": str(repo / "plugins" / "sample-kit" / "skills" / "demo" / "SKILL.md")
        }
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    assert main(["handle-post-edit"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert "systemMessage" in out
    assert ".claude/skills/demo/SKILL.md" in out["systemMessage"]


def test_handle_post_edit_no_file_path_returns_empty_json(monkeypatch, repo, capsys):
    import io

    monkeypatch.chdir(repo)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"tool_input": {}})))
    assert main(["handle-post-edit"]) == 0
    assert json.loads(capsys.readouterr().out) == {}


def test_handle_post_edit_malformed_stdin_returns_empty_json(monkeypatch, repo, capsys):
    import io

    monkeypatch.chdir(repo)
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert main(["handle-post-edit"]) == 0
    assert json.loads(capsys.readouterr().out) == {}


def test_run_delta_structural_checks_ok_without_registry(monkeypatch, repo):
    monkeypatch.chdir(repo)
    assert (
        main(
            ["run-delta-structural-checks", "--changed", "plugins/sample-kit/skills/demo/SKILL.md"]
        )
        == 0
    )


def test_prepare_reviewer_instruction_writes_file(monkeypatch, git_repo):
    git_repo.stage(
        ".codex/agents/security-reviewer.toml",
        'name = "security-reviewer"\ndeveloper_instructions = """\nbe careful\n"""\n',
    )
    import subprocess

    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=git_repo.root, check=True)
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    monkeypatch.chdir(git_repo.root)
    out = git_repo.root / "out.txt"
    rc = main(
        [
            "prepare-reviewer-instruction",
            "--agent",
            "security-reviewer",
            "--base-sha",
            base_sha,
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    assert "be careful" in out.read_text(encoding="utf-8")


def test_prepare_reviewer_instruction_unresolvable_sha_returns_2(monkeypatch, git_repo, tmp_path):
    monkeypatch.chdir(git_repo.root)
    rc = main(
        [
            "prepare-reviewer-instruction",
            "--agent",
            "security-reviewer",
            "--base-sha",
            "0" * 40,
            "--out",
            str(tmp_path / "x"),
        ]
    )
    assert rc == 2


def test_prepare_review_prints_scope_json(monkeypatch, repo, capsys):
    monkeypatch.chdir(repo)
    rc = main(["prepare-review", "--changed", "plugins/demo-kit/skills/x/SKILL.md"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "delta"
    assert payload["audit"] == ["skill-reviewer"]


def test_check_review_output_accepts_valid_envelope(monkeypatch, repo, tmp_path):
    valid = {
        "contract_version": "1",
        "dispatch": {
            "id": "test-dispatch",
            "reviewer": "security-reviewer",
            "backend": "codex",
            "target_paths": ["x"],
        },
        "provenance": {
            "provider": "openai",
            "model": "test-model",
            "cli_version": "0.0.0",
            "execution_profile": "read-only",
        },
        "findings": [],
        "verdict": "pass",
        "inspection_limits": [],
    }
    path = tmp_path / "output.json"
    path.write_text(json.dumps(valid), encoding="utf-8")
    monkeypatch.chdir(repo)
    assert main(["check-review-output", "--file", str(path)]) == 0


def test_check_review_output_rejects_malformed_envelope(monkeypatch, repo, tmp_path):
    path = tmp_path / "output.json"
    path.write_text(json.dumps({"contract_version": "1"}), encoding="utf-8")
    monkeypatch.chdir(repo)
    assert main(["check-review-output", "--file", str(path)]) == 1


def test_check_bypass_allows_valid_attestation(monkeypatch, repo, tmp_path):
    event = {
        "actor": "andre",
        "head_sha": "abc123",
        "permission": "write",
        "comments": [
            "<!-- marketplace-ci-bypass-attestation "
            '{"schema_version": 1, "actor": "andre", "head_sha": "abc123", '
            '"reason": "incident", "created_at": "2026-08-13T00:00:00Z"} -->'
        ],
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    monkeypatch.chdir(repo)
    assert main(["check-bypass", "--event", str(event_path)]) == 0


def test_check_bypass_denies_missing_attestation(monkeypatch, repo, tmp_path):
    event = {"actor": "andre", "head_sha": "abc123", "comments": []}
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    monkeypatch.chdir(repo)
    assert main(["check-bypass", "--event", str(event_path)]) == 1


def test_check_bypass_missing_field_returns_2(monkeypatch, repo, tmp_path):
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"actor": "andre"}), encoding="utf-8")
    monkeypatch.chdir(repo)
    assert main(["check-bypass", "--event", str(event_path)]) == 2


def test_check_scope_bypass_unresolvable_base_sha_returns_2(monkeypatch, git_repo):
    monkeypatch.chdir(git_repo.root)
    assert main(["check-scope-bypass", "--base-sha", "0" * 40]) == 2


def test_check_scope_bypass_eligible_for_out_of_scope_only_diff(monkeypatch, git_repo, tmp_path):
    import subprocess as subprocess_module

    git_repo.write("README.md", "base")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "base"], cwd=git_repo.root, check=True)
    base_sha = subprocess_module.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    git_repo.write("evals/demo-kit/evals.json", "{}")
    git_repo.write("plugins/demo-kit/LICENSE", "notes")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "docs only"], cwd=git_repo.root, check=True)

    out = tmp_path / "scope-bypass.json"
    monkeypatch.chdir(git_repo.root)
    # --before/--after both == base_sha: a degenerate but valid "definitely
    # no rebase happened" proof (base_sha is trivially its own ancestor),
    # required since check-scope-bypass now fails closed without them (C2).
    rc = main(
        [
            "check-scope-bypass",
            "--base-sha",
            base_sha,
            "--before",
            base_sha,
            "--after",
            base_sha,
            "--json-output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["bypass_eligible"] is True
    assert payload["mode"] == "delta"


def test_check_scope_bypass_not_eligible_without_before_after(monkeypatch, git_repo, tmp_path):
    """Security-review regression (C2): an otherwise-bypass-eligible diff
    must fail closed to ineligible when --before/--after aren't supplied --
    e.g. an `edited`/`reopened`/`labeled` event, which carries no reliable
    proof that a rebase didn't happen on a prior push."""
    import subprocess as subprocess_module

    git_repo.write("README.md", "base")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "base"], cwd=git_repo.root, check=True)
    base_sha = subprocess_module.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    git_repo.write("plugins/demo-kit/LICENSE", "notes")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "docs only"], cwd=git_repo.root, check=True)

    out = tmp_path / "scope-bypass.json"
    monkeypatch.chdir(git_repo.root)
    rc = main(["check-scope-bypass", "--base-sha", base_sha, "--json-output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["bypass_eligible"] is False
    assert "before/after" in payload["reason"]


def test_check_scope_bypass_not_eligible_for_component_diff(monkeypatch, git_repo, tmp_path):
    import subprocess as subprocess_module

    git_repo.write("README.md", "base")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "base"], cwd=git_repo.root, check=True)
    base_sha = subprocess_module.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    git_repo.write("plugins/demo-kit/skills/x/SKILL.md", "modified")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(
        ["git", "commit", "-q", "-m", "skill change"], cwd=git_repo.root, check=True
    )

    out = tmp_path / "scope-bypass.json"
    monkeypatch.chdir(git_repo.root)
    rc = main(["check-scope-bypass", "--base-sha", base_sha, "--json-output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["bypass_eligible"] is False


def test_check_scope_bypass_not_eligible_for_rename_to_excluded_basename(
    monkeypatch, git_repo, tmp_path
):
    """External-reviewer regression (PR #50, live on this feature's own
    first PR): git mv-ing a real skill component onto a plugin-root
    LICENSE/etc basename must not be bypass-eligible -- git's default
    rename detection reports only the destination under --name-only, which
    used to make the whole diff look reviewer-empty even though it deletes
    a loadable component."""
    import subprocess as subprocess_module

    git_repo.write(
        "plugins/demo-kit/skills/x/SKILL.md",
        "some skill content long enough for git's default rename similarity "
        "threshold to still detect this as a rename rather than a delete+add pair",
    )
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "base"], cwd=git_repo.root, check=True)
    base_sha = subprocess_module.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    subprocess_module.run(
        ["git", "mv", "plugins/demo-kit/skills/x/SKILL.md", "plugins/demo-kit/LICENSE"],
        cwd=git_repo.root,
        check=True,
    )
    subprocess_module.run(
        ["git", "commit", "-q", "-m", "rename skill to license"], cwd=git_repo.root, check=True
    )

    out = tmp_path / "scope-bypass.json"
    monkeypatch.chdir(git_repo.root)
    rc = main(
        [
            "check-scope-bypass",
            "--base-sha",
            base_sha,
            "--before",
            base_sha,
            "--after",
            base_sha,
            "--json-output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["bypass_eligible"] is False
    assert payload["mode"] == "delta"


def test_check_scope_bypass_rebase_override_forces_ineligible(monkeypatch, git_repo, tmp_path):
    """Even a diff that would otherwise qualify for the bypass (out-of-scope
    files only) must not bypass when --before/--after show this push
    rebased onto a newer base."""
    import subprocess as subprocess_module

    git_repo.write("README.md", "root")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "root"], cwd=git_repo.root, check=True)
    default_branch = subprocess_module.run(
        ["git", "branch", "--show-current"],
        cwd=git_repo.root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    # Fork the feature branch before any later base-branch progress exists.
    subprocess_module.run(["git", "checkout", "-q", "-b", "feature"], cwd=git_repo.root, check=True)
    git_repo.write("plugins/demo-kit/LICENSE", "notes")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "docs only"], cwd=git_repo.root, check=True)
    before = subprocess_module.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    # Advance the default branch -- this later commit becomes the PR's base
    # SHA, which `before` (forked earlier) does not yet contain.
    subprocess_module.run(["git", "checkout", "-q", default_branch], cwd=git_repo.root, check=True)
    git_repo.write("main-progress.txt", "new main commit")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(
        ["git", "commit", "-q", "-m", "main progress"], cwd=git_repo.root, check=True
    )
    base_sha = subprocess_module.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    subprocess_module.run(["git", "checkout", "-q", "feature"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "rebase", "-q", default_branch], cwd=git_repo.root, check=True)
    after = subprocess_module.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    out = tmp_path / "scope-bypass.json"
    monkeypatch.chdir(git_repo.root)
    rc = main(
        [
            "check-scope-bypass",
            "--base-sha",
            base_sha,
            "--before",
            before,
            "--after",
            after,
            "--json-output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["bypass_eligible"] is False
    assert "rebase" in payload["reason"]


def test_check_scope_bypass_never_eligible_for_gate_own_code(monkeypatch, git_repo, tmp_path):
    """Security-review regression (C4): a diff touching the gate's own
    decision logic must never be bypass-eligible, even mixed with an
    otherwise bypass-eligible file and even with valid before/after proving
    no rebase happened."""
    import subprocess as subprocess_module

    git_repo.write("README.md", "base")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "base"], cwd=git_repo.root, check=True)
    base_sha = subprocess_module.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    git_repo.write("plugins/demo-kit/LICENSE", "notes")
    git_repo.write("scripts/marketplace_ci/review.py", "# sneaky change")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(
        ["git", "commit", "-q", "-m", "self-modifying"], cwd=git_repo.root, check=True
    )

    out = tmp_path / "scope-bypass.json"
    monkeypatch.chdir(git_repo.root)
    rc = main(
        [
            "check-scope-bypass",
            "--base-sha",
            base_sha,
            "--before",
            base_sha,
            "--after",
            base_sha,
            "--json-output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["bypass_eligible"] is False


def test_check_scope_bypass_handles_non_ascii_path_correctly(monkeypatch, git_repo, tmp_path):
    """Security-review regression (N2): git's default core.quotePath=true
    C-quotes a non-ASCII path in plain `git diff --name-only` output (e.g.
    `"plugins/demo-kit/skills/x/caf\\303\\251.py"`), which then fails every
    `startswith("plugins/")`-style check and silently misroutes a real
    component change into light/bypass-eligible mode. `-z` NUL-delimited
    output must avoid this."""
    import subprocess as subprocess_module

    git_repo.write("README.md", "base")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "base"], cwd=git_repo.root, check=True)
    base_sha = subprocess_module.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    git_repo.write("plugins/demo-kit/skills/x/café.py", "modified")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(
        ["git", "commit", "-q", "-m", "non-ascii component change"], cwd=git_repo.root, check=True
    )

    out = tmp_path / "scope-bypass.json"
    monkeypatch.chdir(git_repo.root)
    rc = main(
        [
            "check-scope-bypass",
            "--base-sha",
            base_sha,
            "--before",
            base_sha,
            "--after",
            base_sha,
            "--json-output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["mode"] == "delta"
    assert payload["bypass_eligible"] is False


def test_run_codex_review_unresolvable_base_sha_returns_2(monkeypatch, git_repo):
    monkeypatch.chdir(git_repo.root)
    assert main(["run-codex-review", "--base-sha", "0" * 40]) == 2


def test_run_codex_review_end_to_end_clean_pass(monkeypatch, git_repo):
    import subprocess as subprocess_module

    for name in (
        "plugin-rulebook-checker",
        "dependency-reviewer",
        "security-reviewer",
        "skill-reviewer",
    ):
        git_repo.write(
            f".codex/agents/{name}.toml",
            f'name = "{name}"\ndeveloper_instructions = """\ncheck\n"""\n',
        )
    git_repo.write("plugins/demo-kit/skills/x/SKILL.md", "original")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "base"], cwd=git_repo.root, check=True)
    base_sha = subprocess_module.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    git_repo.write("plugins/demo-kit/skills/x/SKILL.md", "modified")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "change"], cwd=git_repo.root, check=True)

    real_run = subprocess_module.run
    valid_envelope = json.dumps(
        {
            "contract_version": "1",
            "dispatch": {
                "id": "test-dispatch",
                "reviewer": "plugin-rulebook-checker",
                "backend": "codex",
                "target_paths": ["plugins/demo-kit/skills/x/SKILL.md"],
            },
            "provenance": {
                "provider": "openai",
                "model": "test-model",
                "cli_version": "0.0.0",
                "execution_profile": "read-only",
            },
            "findings": [],
            "verdict": "pass",
            "inspection_limits": [],
        }
    ).encode()

    def fake_run(argv, **kw):
        if argv[0] == "node":
            return subprocess_module.CompletedProcess(
                argv, returncode=0, stdout=valid_envelope, stderr=b""
            )
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess_module, "run", fake_run)
    monkeypatch.chdir(git_repo.root)
    rc = main(["run-codex-review", "--base-sha", base_sha])
    assert rc == 0


def test_run_codex_review_narrows_rulebook_checker_target_paths(monkeypatch, git_repo):
    import subprocess as subprocess_module

    for name in (
        "plugin-rulebook-checker",
        "dependency-reviewer",
        "security-reviewer",
        "skill-reviewer",
    ):
        git_repo.write(
            f".codex/agents/{name}.toml",
            f'name = "{name}"\ndeveloper_instructions = """\ncheck\n"""\n',
        )
    git_repo.write("plugins/demo-kit/skills/x/SKILL.md", "original")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "base"], cwd=git_repo.root, check=True)
    base_sha = subprocess_module.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    # A real component change, plus two files plugin-rulebook-checker's own
    # R1-R27 scope never covers -- an evals/ fixture and a plugin-root
    # README. security-reviewer should still see all three; only
    # plugin-rulebook-checker's own dispatch should be narrowed.
    git_repo.write("plugins/demo-kit/skills/x/SKILL.md", "modified")
    git_repo.write("evals/demo-kit/evals.json", "{}")
    git_repo.write("plugins/demo-kit/README.md", "docs")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "change"], cwd=git_repo.root, check=True)

    real_run = subprocess_module.run
    captured_target_paths: dict[str, str] = {}

    def make_envelope(reviewer):
        return json.dumps(
            {
                "contract_version": "1",
                "dispatch": {
                    "id": "test-dispatch",
                    "reviewer": reviewer,
                    "backend": "codex",
                    "target_paths": ["plugins/demo-kit/skills/x/SKILL.md"],
                },
                "provenance": {
                    "provider": "openai",
                    "model": "test-model",
                    "cli_version": "0.0.0",
                    "execution_profile": "read-only",
                },
                "findings": [],
                "verdict": "pass",
                "inspection_limits": [],
            }
        ).encode()

    def fake_run(argv, **kw):
        if argv[0] == "node":
            reviewer = argv[argv.index("--reviewer-type") + 1]
            captured_target_paths[reviewer] = argv[argv.index("--target-paths") + 1]
            return subprocess_module.CompletedProcess(
                argv, returncode=0, stdout=make_envelope(reviewer), stderr=b""
            )
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess_module, "run", fake_run)
    monkeypatch.chdir(git_repo.root)
    rc = main(["run-codex-review", "--base-sha", base_sha])
    assert rc == 0

    rulebook_paths = captured_target_paths["plugin-rulebook-checker"].split(",")
    assert "plugins/demo-kit/skills/x/SKILL.md" in rulebook_paths
    assert "evals/demo-kit/evals.json" not in rulebook_paths
    assert "plugins/demo-kit/README.md" not in rulebook_paths

    security_paths = captured_target_paths["security-reviewer"].split(",")
    assert "evals/demo-kit/evals.json" in security_paths
    assert "plugins/demo-kit/README.md" in security_paths


def test_run_codex_review_blocking_finding_returns_1(monkeypatch, git_repo):
    import subprocess as subprocess_module

    git_repo.write(
        ".codex/agents/plugin-rulebook-checker.toml",
        'name = "plugin-rulebook-checker"\ndeveloper_instructions = """\ncheck\n"""\n',
    )
    git_repo.write(
        ".codex/agents/dependency-reviewer.toml", 'developer_instructions = """\ncheck\n"""\n'
    )
    git_repo.write(
        ".codex/agents/security-reviewer.toml", 'developer_instructions = """\ncheck\n"""\n'
    )
    git_repo.write("README.md", "original")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "base"], cwd=git_repo.root, check=True)
    base_sha = subprocess_module.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    git_repo.write("plugins/demo-kit/hooks/hooks.json", "{}")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "change"], cwd=git_repo.root, check=True)

    real_run = subprocess_module.run
    blocking_envelope = json.dumps(
        {
            "contract_version": "1",
            "dispatch": {
                "id": "test-dispatch",
                "reviewer": "security-reviewer",
                "backend": "codex",
                "target_paths": ["plugins/demo-kit/hooks/hooks.json"],
            },
            "provenance": {
                "provider": "openai",
                "model": "test-model",
                "cli_version": "0.0.0",
                "execution_profile": "read-only",
            },
            "findings": [
                {
                    "id": "C1",
                    "severity": "critical",
                    "axis": "R6",
                    "location": "plugins/demo-kit/hooks/hooks.json",
                    "evidence": "e",
                    "finding": "f",
                    "fix": "m",
                    "confidence": "high",
                }
            ],
            "verdict": "reject",
            "inspection_limits": [],
        }
    ).encode()

    def fake_run(argv, **kw):
        if argv[0] == "node":
            return subprocess_module.CompletedProcess(
                argv, returncode=0, stdout=blocking_envelope, stderr=b""
            )
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess_module, "run", fake_run)
    monkeypatch.chdir(git_repo.root)
    rc = main(["run-codex-review", "--base-sha", base_sha])
    assert rc == 1


def test_run_codex_review_full_mode_governance_trigger_actually_dispatches(monkeypatch, git_repo):
    """Full mode is no longer an unconditional fail-closed dead end: a
    governance-path trigger now dispatches DELTA_VALIDATE's own baseline
    (plugin-rulebook-checker, dependency-reviewer, security-reviewer) union'd
    with plugin-validator, the reviewer targeted at .claude/marketplace-sync.json
    specifically -- escalation is additive, never a replacement, so this
    trigger always dispatches at least as many reviewers as an ordinary
    delta scope would have."""
    import subprocess as subprocess_module

    for name in (
        "plugin-validator",
        "plugin-rulebook-checker",
        "dependency-reviewer",
        "security-reviewer",
    ):
        git_repo.write(f".codex/agents/{name}.toml", 'developer_instructions = """\ncheck\n"""\n')
    git_repo.stage(".claude/marketplace-sync.json", '{"version": 1}')
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "base"], cwd=git_repo.root, check=True)
    base_sha = subprocess_module.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()

    # This is exactly the governance-path escalation trigger.
    git_repo.stage(
        ".claude/marketplace-sync.json", '{"version": 1, "plugin_mirrors": ["sample-kit"]}'
    )
    subprocess_module.run(
        ["git", "commit", "-q", "-m", "change registry"], cwd=git_repo.root, check=True
    )

    calls = []
    real_run = subprocess_module.run
    clean_envelope = json.dumps(
        {
            "contract_version": "1",
            "dispatch": {
                "id": "test-dispatch",
                "reviewer": "plugin-validator",
                "backend": "codex",
                "target_paths": [".claude/marketplace-sync.json"],
            },
            "provenance": {
                "provider": "openai",
                "model": "test-model",
                "cli_version": "0.0.0",
                "execution_profile": "read-only",
            },
            "findings": [],
            "verdict": "pass",
            "inspection_limits": [],
        }
    ).encode()

    def fake_run(argv, **kw):
        if argv[0] == "node":
            calls.append(argv)
            return subprocess_module.CompletedProcess(
                argv, returncode=0, stdout=clean_envelope, stderr=b""
            )
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess_module, "run", fake_run)
    monkeypatch.chdir(git_repo.root)
    rc = main(["run-codex-review", "--base-sha", base_sha])
    assert rc == 0
    dispatched = {
        argv[argv.index("--reviewer-type") + 1] for argv in calls if "--reviewer-type" in argv
    }
    assert dispatched == {
        "plugin-validator",
        "plugin-rulebook-checker",
        "dependency-reviewer",
        "security-reviewer",
    }


def test_run_codex_review_full_mode_still_fails_closed_if_a_trigger_defines_no_reviewers(
    monkeypatch, git_repo
):
    """Defensive-guard regression test: if a future full-mode trigger is
    ever added without a corresponding reviewer set (the exact gap this
    guard exists to catch), run-codex-review must still refuse rather than
    silently pass with zero coverage. Simulated directly via a monkeypatched
    derive_review_scope, since both real triggers are now fully defined."""
    import subprocess as subprocess_module

    from scripts.marketplace_ci.review import ReviewScope

    git_repo.write("README.md", "x")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "base"], cwd=git_repo.root, check=True)
    base_sha = subprocess_module.run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo.root, capture_output=True, text=True, check=True
    ).stdout.strip()
    git_repo.write("README.md", "y")
    subprocess_module.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
    subprocess_module.run(["git", "commit", "-q", "-m", "change"], cwd=git_repo.root, check=True)

    undefined_full_scope = ReviewScope(
        mode="full",
        structural_check="scripts.marketplace_ci.validators:run_delta_structural_checks",
        validate=(),
        audit=(),
        paths=("README.md",),
    )
    monkeypatch.setattr(
        "scripts.marketplace_ci.__main__.derive_review_scope", lambda *a, **kw: undefined_full_scope
    )

    calls = []
    real_run = subprocess_module.run

    def fake_run(argv, **kw):
        if argv[0] == "node":
            calls.append(argv)
            return subprocess_module.CompletedProcess(argv, returncode=0, stdout=b"{}", stderr=b"")
        return real_run(argv, **kw)

    monkeypatch.setattr(subprocess_module, "run", fake_run)
    monkeypatch.chdir(git_repo.root)
    rc = main(["run-codex-review", "--base-sha", base_sha])
    assert rc == 2  # fails closed -- never a silent pass with zero coverage
    assert calls == []  # no reviewer was dispatched at all for an undefined trigger
