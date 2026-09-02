import json
import subprocess

from scripts.marketplace_ci.validators import check_staged_parity


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
    # check_staged_parity reads the registry from the Git index (staged content), never disk --
    # stage it here so every caller's registry is visible the same way a real commit would see it.
    subprocess.run(
        ["git", "add", "-f", ".claude/marketplace-sync.json"],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def test_unstaged_repair_does_not_satisfy_staged_parity(git_repo):
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "new")
    git_repo.write(".claude/skills/demo/SKILL.md", "new")  # written but never `git add`-ed
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 1
    assert any(".claude/skills/demo/SKILL.md" in m for m in result.messages)


def test_staged_mirror_matching_content_satisfies_parity(git_repo):
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "new")
    git_repo.stage(".claude/skills/demo/SKILL.md", "new")
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 0


def test_staged_mirror_with_wrong_content_fails_parity(git_repo):
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "new")
    git_repo.stage(".claude/skills/demo/SKILL.md", "stale content, never updated")
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 1


def test_divergence_exception_skips_content_check_when_both_staged(git_repo):
    _write_registry(
        git_repo.root,
        plugin_mirrors=["sample-kit"],
        divergence_exceptions=[
            {
                "source": "plugins/sample-kit/skills/demo/SKILL.md",
                "dest": ".claude/skills/demo/SKILL.md",
                "reason": "test: intentionally divergent for a documented reason",
            }
        ],
    )
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "canonical content")
    git_repo.stage(".claude/skills/demo/SKILL.md", "genuinely different mirror content")
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 0


def test_divergence_exception_still_requires_dest_staged(git_repo):
    _write_registry(
        git_repo.root,
        plugin_mirrors=["sample-kit"],
        divergence_exceptions=[
            {
                "source": "plugins/sample-kit/skills/demo/SKILL.md",
                "dest": ".claude/skills/demo/SKILL.md",
                "reason": "test: intentionally divergent for a documented reason",
            }
        ],
    )
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "canonical content")
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 1
    assert any("canonical source is staged but" in m for m in result.messages)


def test_divergence_exception_does_not_apply_to_export_pair(git_repo):
    # Codex-found gap: divergence_exceptions is a plan_plugin_sync concept with no
    # equivalent in plan_exports (skill/agent exports to .agents/.codex have zero
    # knowledge of the registry field). An exception declared with an export
    # destination must never be honored here -- it would let check-all --staged pass
    # a stale export the real, non-staged check-codex-exports always rejects.
    _write_registry(
        git_repo.root,
        skills=["export-demo"],
        divergence_exceptions=[
            {
                "source": ".claude/skills/export-demo/SKILL.md",
                "dest": ".agents/skills/export-demo/SKILL.md",
                "reason": "test: an export pair, not a plugin-mirror pair",
            }
        ],
    )
    git_repo.stage(".claude/skills/export-demo/SKILL.md", "canonical content")
    git_repo.stage(".agents/skills/export-demo/SKILL.md", "stale content, never updated")
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 1
    assert any("staged content does not match" in m for m in result.messages)


def test_divergence_exception_does_not_apply_to_a_different_pair(git_repo):
    _write_registry(
        git_repo.root,
        plugin_mirrors=["sample-kit"],
        divergence_exceptions=[
            {
                "source": "plugins/sample-kit/skills/other/SKILL.md",
                "dest": ".claude/skills/other/SKILL.md",
                "reason": "test: exception scoped to a different pair entirely",
            }
        ],
    )
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "canonical content")
    git_repo.stage(".claude/skills/demo/SKILL.md", "stale content, never updated")
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 1


def test_unrelated_staged_change_does_not_trigger_parity_check(git_repo):
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    git_repo.stage("README.md", "unrelated change")
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 0


def test_no_registry_returns_ok(git_repo):
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "new")
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 0


def test_no_staged_changes_returns_ok(git_repo):
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 0


def test_staged_converted_agent_export_matching_content_satisfies_parity(git_repo):
    _write_registry(git_repo.root, agents=["export-demo"])
    agent_markdown = """---
name: export-demo
description: Reviews demo components
tools: ["Read", "Grep"]
---

Review the target carefully.
"""
    from scripts.marketplace_ci.conversion import convert_agent

    git_repo.stage(".claude/agents/export-demo.md", agent_markdown)
    git_repo.stage(".codex/agents/export-demo.toml", convert_agent(agent_markdown, "export-demo"))
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 0


def test_untouched_sibling_reference_file_does_not_block_skillmd_only_change(git_repo):
    """Regression test: a skill's SKILL.md and its references/*.md file share
    the same first-4-path-segment directory prefix (plugins/<plugin>/skills/<name>),
    so staging only SKILL.md must never require an untouched sibling reference
    file to also be staged just because it lives under the same directory."""
    _write_registry(git_repo.root, plugin_mirrors=["sample-kit"])
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "v1")
    git_repo.stage(".claude/skills/demo/SKILL.md", "v1")
    git_repo.stage("plugins/sample-kit/skills/demo/references/foo.md", "ref v1")
    git_repo.stage(".claude/skills/demo/references/foo.md", "ref v1")
    subprocess.run(
        ["git", "commit", "-q", "-m", "baseline"],
        cwd=git_repo.root,
        check=True,
        capture_output=True,
    )

    # Only SKILL.md changes in this commit; the reference file pair is untouched.
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "v2")
    git_repo.stage(".claude/skills/demo/SKILL.md", "v2")
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 0, result.messages


def test_staged_converted_agent_export_stale_content_fails_parity(git_repo):
    _write_registry(git_repo.root, agents=["export-demo"])
    agent_markdown = """---
name: export-demo
description: Reviews demo components
---

Review the target carefully.
"""
    git_repo.stage(".claude/agents/export-demo.md", agent_markdown)
    git_repo.stage(".codex/agents/export-demo.toml", 'name = "export-demo"\nstale = true\n')
    result = check_staged_parity(git_repo.root)
    assert result.exit_code == 1
