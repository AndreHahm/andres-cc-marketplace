import json
import subprocess
import sys
from pathlib import Path

import pytest
from memory_scanner import (
    audit_memories,
    delete_memory,
    parse_frontmatter,
    scan_memories,
    search_memories,
)

SCRIPT_PATH = str(Path(__file__).resolve().parent.parent / "scripts" / "memory_scanner.py")
FIXTURES_BASE = str(Path(__file__).resolve().parent / "fixtures" / "memory")


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    def test_parses_valid_frontmatter_with_all_fields(self):
        content = (
            "---\nname: Test memory\ndescription: A test memory file\ntype: user\n---\n\n"
            "This is the body.\n"
        )
        result = parse_frontmatter(content)
        assert result["name"] == "Test memory"
        assert result["description"] == "A test memory file"
        assert result["type"] == "user"
        assert "This is the body." in result["body"]

    def test_returns_none_fields_for_missing_frontmatter(self):
        content = "Just a plain body with no frontmatter."
        result = parse_frontmatter(content)
        assert result["name"] is None
        assert result["description"] is None
        assert result["type"] is None
        assert result["body"] == content

    def test_handles_frontmatter_with_extra_fields(self):
        content = (
            "---\nname: Extra fields test\ndescription: Has extra fields\ntype: feedback\n"
            "author: someone\npriority: high\n---\n\nBody content here.\n"
        )
        result = parse_frontmatter(content)
        assert result["name"] == "Extra fields test"
        assert result["description"] == "Has extra fields"
        assert result["type"] == "feedback"
        assert "Body content here." in result["body"]

    def test_handles_empty_content(self):
        result = parse_frontmatter("")
        assert result["name"] is None
        assert result["description"] is None
        assert result["type"] is None
        assert result["body"] == ""

    def test_handles_frontmatter_with_only_some_fields(self):
        content = "---\nname: Partial frontmatter\ntype: reference\n---\n\nJust a body.\n"
        result = parse_frontmatter(content)
        assert result["name"] == "Partial frontmatter"
        assert result["description"] is None
        assert result["type"] == "reference"
        assert "Just a body." in result["body"]

    def test_strips_quotes_from_frontmatter_values(self):
        content = (
            "---\nname: \"Quoted name\"\ndescription: 'Single quoted'\ntype: user\n---\n\nBody.\n"
        )
        result = parse_frontmatter(content)
        assert result["name"] == "Quoted name"
        assert result["description"] == "Single quoted"


# ---------------------------------------------------------------------------
# scan_memories
# ---------------------------------------------------------------------------


class TestScanMemories:
    def test_discovers_all_memory_files_across_projects(self):
        result = scan_memories(projects_base=FIXTURES_BASE)
        assert result["projectsScanned"] == 4
        assert result["projectsWithMemories"] == 3
        assert result["totalMemories"] == 7

    def test_counts_memories_by_type(self):
        result = scan_memories(projects_base=FIXTURES_BASE)
        assert result["byType"]["user"] == 2
        assert result["byType"]["feedback"] == 1
        assert result["byType"]["project"] == 1
        assert result["byType"]["reference"] == 2
        assert result["byType"]["unknown"] == 1

    def test_filters_by_type(self):
        result = scan_memories(projects_base=FIXTURES_BASE, type_filter="user")
        assert len(result["memories"]) == 2
        for m in result["memories"]:
            assert m["type"] == "user"

    def test_filters_by_project(self):
        result = scan_memories(projects_base=FIXTURES_BASE, project_filter="alpha")
        assert result["projectsScanned"] == 1
        assert len(result["memories"]) == 3
        for m in result["memories"]:
            assert m["project"] == "project-alpha"

    def test_detects_frontmatter_presence(self):
        result = scan_memories(projects_base=FIXTURES_BASE)
        no_fm = next(m for m in result["memories"] if m["file"] == "no_frontmatter.md")
        assert no_fm["hasFrontmatter"] is False

        with_fm = next(
            m
            for m in result["memories"]
            if m["file"] == "user_profile.md" and m["project"] == "project-alpha"
        )
        assert with_fm["hasFrontmatter"] is True

    def test_detects_indexed_status_from_memory_md(self):
        result = scan_memories(projects_base=FIXTURES_BASE)
        indexed = next(
            m
            for m in result["memories"]
            if m["file"] == "user_profile.md" and m["project"] == "project-alpha"
        )
        assert indexed["indexed"] is True

        orphan = next(m for m in result["memories"] if m["file"] == "orphan_file.md")
        assert orphan["indexed"] is False

    def test_returns_empty_result_for_nonexistent_base(self):
        result = scan_memories(projects_base="/nonexistent/path/that/does/not/exist")
        assert result["projectsScanned"] == 0
        assert result["projectsWithMemories"] == 0
        assert result["totalMemories"] == 0
        assert result["memories"] == []

    def test_generates_readable_project_name(self):
        result = scan_memories(projects_base=FIXTURES_BASE, project_filter="alpha")
        assert len(result["memories"]) > 0
        assert result["memories"][0]["projectReadable"] == "project/alpha"

    def test_nested_memory_file_correctly_linked_is_indexed(self, tmp_path):
        """A MEMORY.md link like [Note](decisions/note.md) must match the nested file's
        own relative path, not just its bare basename -- a basename-only comparison
        incorrectly reports a correctly-linked nested file as unindexed."""
        memory_dir = tmp_path / "projects" / "proj" / "memory"
        (memory_dir / "decisions").mkdir(parents=True)
        (memory_dir / "MEMORY.md").write_text(
            "- [Decision on X](decisions/note.md) -- some decision\n", encoding="utf-8"
        )
        (memory_dir / "decisions" / "note.md").write_text("content", encoding="utf-8")

        result = scan_memories(projects_base=str(tmp_path / "projects"))
        mem = next(m for m in result["memories"] if m["file"] == "note.md")
        assert mem["indexed"] is True


# ---------------------------------------------------------------------------
# audit_memories
# ---------------------------------------------------------------------------


class TestAuditMemories:
    def test_detects_expired_date_based_memories_critical(self):
        result = audit_memories(projects_base=FIXTURES_BASE)
        expired = [f for f in result["findings"] if f["category"] == "expired"]
        assert len(expired) > 0
        target = next(f for f in expired if f["file"] == "project_expired_reminder.md")
        assert target["severity"] == "critical"
        assert target["fixType"] == "auto"
        assert target["autoFixable"] is True

    def test_detects_broken_memory_md_links_warning(self):
        result = audit_memories(projects_base=FIXTURES_BASE)
        broken = [f for f in result["findings"] if f["category"] == "broken_link"]
        assert len(broken) > 0
        target = next(f for f in broken if "nonexistent_file.md" in f["message"])
        assert target["severity"] == "warning"
        assert target["autoFixable"] is True

    def test_detects_orphan_files_not_in_memory_md(self):
        result = audit_memories(projects_base=FIXTURES_BASE)
        orphans = [f for f in result["findings"] if f["category"] == "orphan"]
        assert len(orphans) > 0
        assert any(f["file"] == "orphan_file.md" for f in orphans)

    def test_orphan_with_frontmatter_is_auto_fixable(self):
        result = audit_memories(projects_base=FIXTURES_BASE)
        orphan = next(
            f
            for f in result["findings"]
            if f["category"] == "orphan" and f["file"] == "orphan_file.md"
        )
        assert orphan["fixType"] == "auto"
        assert orphan["autoFixable"] is True

    def test_nested_memory_file_correctly_linked_is_not_flagged_orphan(self, tmp_path):
        """Same bug as scan_memories' 'indexed' field, in the orphan-detection check --
        a nested file linked via its relative path must not be reported as unindexed."""
        memory_dir = tmp_path / "projects" / "proj" / "memory"
        (memory_dir / "decisions").mkdir(parents=True)
        (memory_dir / "MEMORY.md").write_text(
            "- [Decision on X](decisions/note.md) -- some decision\n", encoding="utf-8"
        )
        (memory_dir / "decisions" / "note.md").write_text("content", encoding="utf-8")

        result = audit_memories(projects_base=str(tmp_path / "projects"))
        orphans = [f for f in result["findings"] if f["category"] == "orphan"]
        assert orphans == []

    def test_nested_memory_file_orphan_suggestion_uses_relative_path(self, tmp_path):
        """The suggested fix must name the nested file's relative path, not just its bare
        basename -- suggesting a bare basename risks a duplicate/wrong top-level index
        entry for a file that actually lives in a subdirectory."""
        memory_dir = tmp_path / "projects" / "proj" / "memory"
        (memory_dir / "decisions").mkdir(parents=True)
        (memory_dir / "decisions" / "note.md").write_text("content", encoding="utf-8")

        result = audit_memories(projects_base=str(tmp_path / "projects"))
        orphan = next(f for f in result["findings"] if f["category"] == "orphan")
        assert "decisions/note.md" in orphan["suggestion"]

    def test_detects_missing_frontmatter_ai_assisted(self):
        result = audit_memories(projects_base=FIXTURES_BASE)
        missing = [f for f in result["findings"] if f["category"] == "missing_frontmatter"]
        assert len(missing) > 0
        target = next(f for f in missing if f["file"] == "no_frontmatter.md")
        assert target["severity"] == "warning"
        assert target["fixType"] == "ai_assisted"
        assert target["autoFixable"] is False

    def test_detects_stale_file_paths_ai_assisted(self):
        result = audit_memories(projects_base=FIXTURES_BASE)
        stale_paths = [f for f in result["findings"] if f["category"] == "stale_path"]
        assert len(stale_paths) > 0
        target = next(
            f for f in stale_paths if "/tmp/nonexistent-project-path-abc123" in f["message"]
        )
        assert target["fixType"] == "ai_assisted"
        assert target["autoFixable"] is False

    def test_detects_duplicate_memory_names_across_projects(self):
        result = audit_memories(projects_base=FIXTURES_BASE)
        dupes = [f for f in result["findings"] if f["category"] == "duplicate"]
        assert len(dupes) > 0
        projects = {f["project"] for f in dupes}
        assert "project-alpha" in projects
        assert "project-gamma" in projects

    def test_respects_age_threshold_for_staleness(self):
        result = audit_memories(projects_base=FIXTURES_BASE, age_threshold=0)
        stale = [f for f in result["findings"] if f["category"] == "stale"]
        assert len(stale) > 0
        for f in stale:
            assert f["severity"] == "info"
            assert f["fixType"] == "ai_assisted"

    def test_summary_counts_match_findings(self):
        result = audit_memories(projects_base=FIXTURES_BASE)
        total_from_by_severity = sum(result["summary"]["bySeverity"].values())
        assert total_from_by_severity == result["summary"]["issuesFound"]
        assert result["summary"]["issuesFound"] == len(result["findings"])
        assert result["summary"]["totalMemories"] > 0
        assert result["summary"]["healthy"] == result["summary"]["totalMemories"] - len(
            {f["path"] for f in result["findings"]}
        )
        # 3 of the 4 fixture projects have memories (alpha, beta, gamma; empty has none)
        assert result["summary"]["projectsWithMemories"] == 3

    def test_findings_sorted_by_severity_critical_first(self):
        result = audit_memories(projects_base=FIXTURES_BASE)
        severities = [f["severity"] for f in result["findings"]]
        order = {"critical": 0, "warning": 1, "info": 2}
        for i in range(1, len(severities)):
            assert order[severities[i]] >= order[severities[i - 1]]

    def test_returns_clean_result_for_empty_base(self):
        result = audit_memories(projects_base="/nonexistent/path/that/does/not/exist")
        assert result["findings"] == []
        assert result["summary"]["totalMemories"] == 0
        assert result["summary"]["healthy"] == 0
        assert result["summary"]["issuesFound"] == 0


# ---------------------------------------------------------------------------
# search_memories
# ---------------------------------------------------------------------------


class TestSearchMemories:
    def test_finds_matches_across_memory_files(self):
        results = search_memories("engineer", projects_base=FIXTURES_BASE)
        assert len(results) > 0

    def test_returns_line_numbers_for_matches(self):
        results = search_memories("engineer", projects_base=FIXTURES_BASE)
        for r in results:
            assert r["line"] > 0

    def test_includes_context_lines_when_requested(self):
        results = search_memories("engineer", projects_base=FIXTURES_BASE, context=1)
        assert any(r["contextBefore"] or r["contextAfter"] for r in results)

    def test_filters_by_type(self):
        results = search_memories("engineer", projects_base=FIXTURES_BASE, type_filter="user")
        for r in results:
            assert r["type"] == "user"

    def test_filters_by_project(self):
        results = search_memories("engineer", projects_base=FIXTURES_BASE, project_filter="alpha")
        for r in results:
            assert r["project"] == "project-alpha"

    def test_respects_limit(self):
        results = search_memories("e", projects_base=FIXTURES_BASE, limit=3)
        assert len(results) <= 3

    def test_returns_empty_list_for_no_matches(self):
        results = search_memories(
            "xyzzy_this_string_does_not_exist_anywhere", projects_base=FIXTURES_BASE
        )
        assert results == []

    def test_is_case_insensitive(self):
        lower = search_memories("engineer", projects_base=FIXTURES_BASE)
        upper = search_memories("ENGINEER", projects_base=FIXTURES_BASE)
        assert len(lower) == len(upper)

    def test_escapes_regex_special_characters_in_query(self):
        # This should not crash — the query is treated as a literal string
        search_memories("(a+)+$", projects_base=FIXTURES_BASE)


# ---------------------------------------------------------------------------
# delete_memory
# ---------------------------------------------------------------------------


class TestDeleteMemory:
    def test_deletes_a_valid_memory_file(self, tmp_path):
        memory_dir = tmp_path / "projects" / "proj" / "memory"
        memory_dir.mkdir(parents=True)
        target = memory_dir / "note.md"
        target.write_text("content", encoding="utf-8")

        result = delete_memory(str(target), projects_base=str(tmp_path / "projects"))

        assert result["deleted"] is True
        assert not target.exists()

    def test_deletes_a_nested_memory_file(self, tmp_path):
        memory_dir = tmp_path / "projects" / "proj" / "memory" / "sub"
        memory_dir.mkdir(parents=True)
        target = memory_dir / "note.md"
        target.write_text("content", encoding="utf-8")

        result = delete_memory(str(target), projects_base=str(tmp_path / "projects"))

        assert result["deleted"] is True
        assert not target.exists()

    def test_rejects_a_path_outside_projects_base(self, tmp_path):
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        target = outside_dir / "note.md"
        target.write_text("content", encoding="utf-8")

        with pytest.raises(ValueError, match="Path traversal detected"):
            delete_memory(str(target), projects_base=str(tmp_path / "projects"))
        assert target.exists()

    def test_rejects_a_path_inside_base_but_not_under_memory(self, tmp_path):
        other_dir = tmp_path / "projects" / "proj" / "notmemory"
        other_dir.mkdir(parents=True)
        target = other_dir / "note.md"
        target.write_text("content", encoding="utf-8")

        with pytest.raises(ValueError, match="outside a project's memory/ directory"):
            delete_memory(str(target), projects_base=str(tmp_path / "projects"))
        assert target.exists()

    def test_rejects_memory_as_a_top_level_project_name(self, tmp_path):
        """A file directly under <base>/memory/ is not a project's memory/ dir -- it's a
        sibling directory that happens to be *named* "memory". The old containment check
        (checking only whether "memory" appeared anywhere in the resolved path's parts)
        incorrectly accepted this; the fix requires "memory" to be the second path segment
        below the base, i.e. <project>/memory/..., not the base's own direct child."""
        fake_project_dir = tmp_path / "projects" / "memory"
        fake_project_dir.mkdir(parents=True)
        target = fake_project_dir / "unrelated.md"
        target.write_text("content", encoding="utf-8")

        with pytest.raises(ValueError, match="outside a project's memory/ directory"):
            delete_memory(str(target), projects_base=str(tmp_path / "projects"))
        assert target.exists()

    def test_rejects_memory_md_index_itself(self, tmp_path):
        """MEMORY.md is the index -- deleting it (rather than editing it) would leave
        every other memory in the project unindexed. It has the same
        <project>/memory/... shape the containment check otherwise accepts, so it needs
        its own explicit rejection."""
        memory_dir = tmp_path / "projects" / "proj" / "memory"
        memory_dir.mkdir(parents=True)
        index = memory_dir / "MEMORY.md"
        index.write_text("# Index", encoding="utf-8")

        with pytest.raises(ValueError, match="memory index"):
            delete_memory(str(index), projects_base=str(tmp_path / "projects"))
        assert index.exists()

    def test_rejects_a_nonexistent_file(self, tmp_path):
        memory_dir = tmp_path / "projects" / "proj" / "memory"
        memory_dir.mkdir(parents=True)
        target = memory_dir / "missing.md"

        with pytest.raises(ValueError, match="not found"):
            delete_memory(str(target), projects_base=str(tmp_path / "projects"))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, SCRIPT_PATH, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class TestCli:
    def test_scan_outputs_json_with_projects_scanned_4(self):
        proc = _run_cli("scan", "--projects-base", FIXTURES_BASE)
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert data["projects_scanned"] == 4
        assert isinstance(data["memories"], list)

    def test_audit_outputs_json_with_summary_and_findings(self):
        proc = _run_cli("audit", "--projects-base", FIXTURES_BASE)
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert "summary" in data
        assert "findings" in data
        assert isinstance(data["findings"], list)
        assert data["summary"]["total_memories"] > 0

    def test_search_outputs_ndjson(self):
        proc = _run_cli("search", "engineer", "--projects-base", FIXTURES_BASE)
        assert proc.returncode == 0
        lines = [line for line in proc.stdout.strip().split("\n") if line]
        assert len(lines) > 0
        for line in lines:
            obj = json.loads(line)
            assert "project" in obj
            assert "file" in obj
            assert "line" in obj

    def test_search_no_results_outputs_empty_json_array(self):
        proc = _run_cli(
            "search", "xyzzy_this_string_does_not_exist_anywhere", "--projects-base", FIXTURES_BASE
        )
        assert proc.returncode == 0
        assert json.loads(proc.stdout) == []

    def test_missing_search_query_exits_code_2(self):
        proc = _run_cli("search", "--projects-base", FIXTURES_BASE)
        assert proc.returncode == 2

    def test_unknown_command_exits_code_1(self):
        proc = _run_cli("foobar", "--projects-base", FIXTURES_BASE)
        assert proc.returncode == 1
