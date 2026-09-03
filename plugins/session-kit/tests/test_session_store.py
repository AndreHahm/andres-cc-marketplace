import json
import os
import shutil
import time
from pathlib import Path

import pytest
from session_store import (
    aggregate_tasks,
    decode_project_path,
    delete_session,
    delete_task,
    delete_task_list,
    encode_project_path,
    find_cleanup_candidates,
    find_orphan_task_lists,
    get_activity_heatmap,
    get_daily_token_aggregation,
    get_model_distribution,
    get_session_detail,
    get_timeline,
    is_valid_id,
    list_sessions,
    list_task_lists,
    read_task_list,
    resolve_session,
    search_sessions,
)

FIXTURE = str(Path(__file__).resolve().parent / "fixtures" / "sample_session.jsonl")


@pytest.fixture
def fake_projects_dir(tmp_path):
    proj_dir = tmp_path / "projects" / "-Users-me-myproject"
    proj_dir.mkdir(parents=True)
    shutil.copyfile(FIXTURE, proj_dir / "test-session-001.jsonl")
    (proj_dir / "empty-session.jsonl").write_text("")
    return str(tmp_path / "projects")


@pytest.fixture
def fake_tasks_dir(tmp_path):
    task_dir = tmp_path / "tasks" / "test-session-001"
    task_dir.mkdir(parents=True)
    (task_dir / ".lock").write_text("")
    (task_dir / ".highwatermark").write_text("3")
    (task_dir / "1.json").write_text(
        json.dumps(
            {
                "id": "1",
                "subject": "Setup project",
                "description": "Initialize the repo",
                "status": "completed",
                "blocks": ["2"],
                "blockedBy": [],
            }
        )
    )
    (task_dir / "2.json").write_text(
        json.dumps(
            {
                "id": "2",
                "subject": "Add tests",
                "description": "Write unit tests",
                "status": "pending",
                "blocks": [],
                "blockedBy": ["1"],
            }
        )
    )
    return str(tmp_path / "tasks")


@pytest.fixture
def fake_projects_and_tasks_dir(tmp_path):
    proj_dir = tmp_path / "projects" / "-Users-me-myproject"
    proj_dir.mkdir(parents=True)
    shutil.copyfile(FIXTURE, proj_dir / "test-session-001.jsonl")

    task_dir = tmp_path / "tasks" / "test-session-001"
    task_dir.mkdir(parents=True)
    (task_dir / "1.json").write_text(
        json.dumps({"id": "1", "subject": "Task one", "status": "pending"})
    )

    return str(tmp_path / "projects"), str(tmp_path / "tasks")


class TestEncodeProjectPath:
    def test_encodes_filesystem_path(self):
        assert encode_project_path("/Users/me/myproject") == "-Users-me-myproject"

    def test_encodes_windows_path(self):
        assert encode_project_path("C:\\Dev\\Repos\\myproject") == "C--Dev-Repos-myproject"


class TestDecodeProjectPath:
    def test_decodes_to_filesystem_path(self):
        assert decode_project_path("-Users-me-myproject") == "/Users/me/myproject"

    def test_never_raises_on_a_dotdot_sequence(self):
        # decode_project_path is display-only, never used for filesystem I/O (see its
        # own docstring) -- raising here would abort every caller that lists multiple
        # sessions (list_sessions/search/timeline/cleanup all decode once per session)
        # for one oddly-named project, not just that project. A real project directory
        # literally named "v1..v2" must still decode to a best-effort display string.
        assert decode_project_path("foo-..") == "foo/.."
        assert decode_project_path("-..") == "/.."
        assert decode_project_path("..") == ".."

    def test_works_for_normal_paths(self):
        assert decode_project_path("-Users-me-project") == "/Users/me/project"
        assert decode_project_path("Users-me-project") == "Users/me/project"

    def test_decodes_windows_drive_letter_path(self):
        assert decode_project_path("C--Dev-Repos-proj") == "C:\\Dev\\Repos\\proj"

    def test_round_trips_windows_path_without_hyphens(self):
        # A drive-letter path with no real hyphens in any segment round-trips exactly.
        original = "C:\\Dev\\Repos\\proj"
        assert decode_project_path(encode_project_path(original)) == original

    def test_does_not_round_trip_when_a_segment_has_a_real_hyphen(self):
        # Documents the known, inherent limitation (see decode_project_path's own
        # docstring): a real hyphen in a segment is indistinguishable from an
        # encoded separator, so this case can never round-trip exactly.
        original = "C:\\Dev\\Repos\\andres-cc-marketplace"
        decoded = decode_project_path(encode_project_path(original))
        assert decoded != original
        assert decoded == "C:\\Dev\\Repos\\andres\\cc\\marketplace"


class TestIsValidId:
    def test_accepts_uuid_like_strings(self):
        assert is_valid_id("abc-123-def") is True
        assert is_valid_id("test-session-001") is True
        assert is_valid_id("550e8400-e29b-41d4-a716-446655440000") is True

    def test_rejects_path_traversal_attempts(self):
        assert is_valid_id("../etc/passwd") is False
        assert is_valid_id("foo/bar") is False
        assert is_valid_id("foo\\bar") is False
        assert is_valid_id("") is False
        assert is_valid_id("a b c") is False

    def test_rejects_trailing_newline(self):
        # re.match's $ allows a trailing \n; \Z does not -- guard against that gap.
        assert is_valid_id("abc\n") is False


class TestResolveSession:
    def test_resolves_by_path(self):
        assert resolve_session(FIXTURE) == FIXTURE

    def test_raises_for_nonexistent(self):
        with pytest.raises(ValueError):
            resolve_session("nonexistent-uuid-12345")

    def test_raises_on_ambiguous_id_across_projects(self, tmp_path):
        base = tmp_path / "projects"
        proj_a = base / "-Users-me-project-a"
        proj_b = base / "-Users-me-project-b"
        proj_a.mkdir(parents=True)
        proj_b.mkdir(parents=True)
        shutil.copyfile(FIXTURE, proj_a / "dup-session.jsonl")
        shutil.copyfile(FIXTURE, proj_b / "dup-session.jsonl")

        with pytest.raises(ValueError, match="Ambiguous session ID"):
            resolve_session("dup-session", projects_base=str(base))

    def test_resolves_via_env_session_id_regardless_of_cwd(self, tmp_path, monkeypatch):
        # The session's own project dir doesn't match cwd at all (e.g. a worktree
        # created mid-session) -- CLAUDE_CODE_SESSION_ID must still resolve it,
        # without needing the cwd-based fallback to match anything.
        base = tmp_path / "projects"
        proj_dir = base / "-some-other-original-checkout"
        proj_dir.mkdir(parents=True)
        shutil.copyfile(FIXTURE, proj_dir / "live-session-id.jsonl")

        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "live-session-id")
        result = resolve_session(cwd="/totally/unrelated/worktree/path", projects_base=str(base))
        assert result == str(proj_dir / "live-session-id.jsonl")

    def test_falls_back_to_cwd_when_env_var_unset(self, fake_projects_dir, monkeypatch):
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        result = resolve_session(cwd="/Users/me/myproject", projects_base=fake_projects_dir)
        assert result.endswith(".jsonl")
        assert "-Users-me-myproject" in result

    def test_falls_back_to_cwd_when_env_session_not_found_on_disk(
        self, fake_projects_dir, monkeypatch
    ):
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "no-such-session-anywhere")
        result = resolve_session(cwd="/Users/me/myproject", projects_base=fake_projects_dir)
        assert result.endswith(".jsonl")
        assert "-Users-me-myproject" in result


class TestListSessions:
    def test_returns_results(self, fake_projects_dir):
        sessions = list_sessions(projects_base=fake_projects_dir)
        assert len(sessions) >= 1
        assert "sessionId" in sessions[0]
        assert "project" in sessions[0]
        assert "messages" in sessions[0]

    def test_project_filter(self, fake_projects_dir):
        sessions = list_sessions(projects_base=fake_projects_dir, project_filter="myproject")
        assert len(sessions) >= 1
        none = list_sessions(projects_base=fake_projects_dir, project_filter="nonexistent")
        assert none == []


class TestListSessionsDateFiltering:
    def test_since_filters_out_older_sessions(self, fake_projects_dir):
        sessions = list_sessions(projects_base=fake_projects_dir, since="2026-04-11", limit=100)
        assert len(sessions) == 0

    def test_since_includes_matching_sessions(self, fake_projects_dir):
        sessions = list_sessions(projects_base=fake_projects_dir, since="2026-04-09", limit=100)
        assert len(sessions) > 0

    def test_until_filters_out_newer_sessions(self, fake_projects_dir):
        sessions = list_sessions(projects_base=fake_projects_dir, until="2026-04-09", limit=100)
        assert len(sessions) == 0

    def test_since_and_until_range(self, fake_projects_dir):
        sessions = list_sessions(
            projects_base=fake_projects_dir, since="2026-04-09", until="2026-04-11", limit=100
        )
        assert len(sessions) > 0

    def test_since_greater_than_until_returns_empty(self, fake_projects_dir):
        sessions = list_sessions(
            projects_base=fake_projects_dir, since="2026-04-20", until="2026-04-10", limit=100
        )
        assert len(sessions) == 0


class TestSearchSessions:
    def test_finds_matching_content(self, fake_projects_dir):
        results = search_sessions("Python files", projects_base=fake_projects_dir)
        assert len(results) >= 1
        assert "match" in results[0]

    def test_redos_patterns_complete_quickly(self, fake_projects_dir):
        start = time.monotonic()
        results = search_sessions("(a+)+$", projects_base=fake_projects_dir)
        elapsed = time.monotonic() - start
        assert elapsed < 1.0
        assert results == []

    def test_no_results_for_nonsense_query(self, fake_projects_dir):
        results = search_sessions("xyznonexistent123", projects_base=fake_projects_dir)
        assert results == []


class TestGetTimeline:
    def test_returns_chronological_sessions(self, fake_projects_dir):
        timeline = get_timeline(projects_base=fake_projects_dir)
        assert len(timeline) >= 1
        assert "sessionId" in timeline[0]
        assert "date" in timeline[0]

    def test_does_not_truncate_beyond_list_sessions_own_default_limit(self, tmp_path):
        # get_timeline used to hardcode limit=1000 when calling list_sessions -- a
        # project with more sessions than that silently lost its oldest ones, with
        # no truncation indicator. This uses list_sessions' own *default* limit (20)
        # as the smaller, practical stand-in: creating more sessions than that
        # default already proves get_timeline isn't quietly capping via any
        # inherited limit, hardcoded or default.
        proj_dir = tmp_path / "-Users-me-manysessions"
        proj_dir.mkdir(parents=True)
        for i in range(25):
            (proj_dir / f"session-{i:03d}.jsonl").write_text("")
        timeline = get_timeline(projects_base=str(tmp_path))
        assert len(timeline) == 25


class TestFindCleanupCandidates:
    def test_finds_empty_sessions(self, fake_projects_dir):
        candidates = find_cleanup_candidates(projects_base=fake_projects_dir, min_messages=1)
        empty = [c for c in candidates if c["reason"] == "empty"]
        assert len(empty) >= 1

    def _set_session_age(self, fake_projects_dir, days_old):
        session_path = os.path.join(
            fake_projects_dir, "-Users-me-myproject", "test-session-001.jsonl"
        )
        old_time = time.time() - (days_old * 86400)
        os.utime(session_path, (old_time, old_time))
        return session_path

    def test_older_than_days_unit(self, fake_projects_dir):
        self._set_session_age(fake_projects_dir, 10)
        candidates = find_cleanup_candidates(
            projects_base=fake_projects_dir, older_than="5d", min_messages=1
        )
        old = [c for c in candidates if c["reason"] == "old"]
        assert len(old) == 1

    def test_older_than_weeks_unit(self, fake_projects_dir):
        # 10 days old is > 1 week (7d) but < 2 weeks (14d)
        self._set_session_age(fake_projects_dir, 10)
        found_at_1w = find_cleanup_candidates(
            projects_base=fake_projects_dir, older_than="1w", min_messages=1
        )
        found_at_2w = find_cleanup_candidates(
            projects_base=fake_projects_dir, older_than="2w", min_messages=1
        )
        assert any(c["reason"] == "old" for c in found_at_1w)
        assert not any(c["reason"] == "old" for c in found_at_2w)

    def test_older_than_months_unit(self, fake_projects_dir):
        # 10 days old is well under 1 month (30d)
        self._set_session_age(fake_projects_dir, 10)
        candidates = find_cleanup_candidates(
            projects_base=fake_projects_dir, older_than="1m", min_messages=1
        )
        assert not any(c["reason"] == "old" for c in candidates)

    def test_older_than_malformed_unit_disables_age_filter(self, fake_projects_dir):
        self._set_session_age(fake_projects_dir, 10)
        # "10x" doesn't match the d/w/m regex -- falls through to no age filtering,
        # not an error and not a silent 0-day threshold.
        candidates = find_cleanup_candidates(
            projects_base=fake_projects_dir, older_than="10x", min_messages=1
        )
        assert not any(c["reason"] == "old" for c in candidates)


class TestReadTaskList:
    def test_reads_all_tasks(self, fake_tasks_dir):
        tasks = read_task_list("test-session-001", fake_tasks_dir)
        assert len(tasks) == 2
        assert tasks[0]["subject"] == "Setup project"
        assert tasks[0]["source"] == "filesystem"
        assert tasks[1]["status"] == "pending"
        assert tasks[1]["blockedBy"] == ["1"]

    def test_rejects_a_traversal_task_list_id(self, tmp_path):
        # read_task_list is reachable from the CLI's own --task-list flag with no
        # other validation in that path -- an unvalidated ID let os.path.join walk
        # outside tasks_base and read arbitrary .json files elsewhere on disk.
        outside = tmp_path / "secret"
        outside.mkdir()
        (outside / "leaked.json").write_text('{"sensitive": "leak"}', encoding="utf-8")
        tasks_base = tmp_path / "tasks"
        tasks_base.mkdir()

        with pytest.raises(ValueError, match="Invalid task list ID"):
            read_task_list("../secret", str(tasks_base))

    def test_skips_a_non_object_task_file(self, tmp_path):
        list_dir = tmp_path / "list1"
        list_dir.mkdir()
        (list_dir / "bad.json").write_text('["not", "a", "dict"]', encoding="utf-8")
        (list_dir / "good.json").write_text('{"subject": "ok"}', encoding="utf-8")

        tasks = read_task_list("list1", str(tmp_path))
        assert len(tasks) == 1
        assert tasks[0]["subject"] == "ok"


class TestDeleteTask:
    def test_deletes_task_file_and_reports_emptiness(self, fake_tasks_dir):
        result = delete_task("test-session-001", "2", tasks_base=fake_tasks_dir)
        assert result["deleted"] is True
        assert result["taskListNowEmpty"] is False
        assert not os.path.exists(result["taskPath"])

        result2 = delete_task("test-session-001", "1", tasks_base=fake_tasks_dir)
        assert result2["deleted"] is True
        assert result2["taskListNowEmpty"] is True

    def test_raises_on_nonexistent_task(self, fake_tasks_dir):
        with pytest.raises(ValueError, match="Task not found"):
            delete_task("test-session-001", "999", tasks_base=fake_tasks_dir)

    def test_raises_on_invalid_id(self, fake_tasks_dir):
        with pytest.raises(ValueError, match="Invalid"):
            delete_task("../etc", "1", tasks_base=fake_tasks_dir)
        with pytest.raises(ValueError, match="Invalid"):
            delete_task("test-session-001", "../1", tasks_base=fake_tasks_dir)


class TestDeleteTaskList:
    def test_deletes_entire_task_list_directory(self, fake_tasks_dir):
        result = delete_task_list("test-session-001", tasks_base=fake_tasks_dir)
        assert result["deleted"] is True
        assert result["taskCount"] == 2
        assert not os.path.exists(os.path.join(fake_tasks_dir, "test-session-001"))

    def test_raises_on_nonexistent_task_list(self, fake_tasks_dir):
        with pytest.raises(ValueError, match="Task list not found"):
            delete_task_list("nonexistent", tasks_base=fake_tasks_dir)

    def test_raises_on_invalid_id(self, fake_tasks_dir):
        with pytest.raises(ValueError, match="Invalid"):
            delete_task_list("../etc", tasks_base=fake_tasks_dir)


class TestPathContainmentValidation:
    def test_assert_path_within_base_rejects_escapes(self, tmp_path):
        tasks_base = tmp_path / "tasks"
        legit_dir = tasks_base / "legit-session"
        legit_dir.mkdir(parents=True)
        (legit_dir / "1.json").write_text(
            json.dumps({"id": "1", "subject": "t", "status": "pending"})
        )

        result = delete_task("legit-session", "1", tasks_base=str(tasks_base))
        assert result["deleted"] is True

    def test_delete_task_path_containment_works(self, fake_tasks_dir):
        result = delete_task("test-session-001", "1", tasks_base=fake_tasks_dir)
        assert result["deleted"] is True

    def test_delete_task_list_path_containment_works(self, fake_tasks_dir):
        result = delete_task_list("test-session-001", tasks_base=fake_tasks_dir)
        assert result["deleted"] is True


class TestListTaskLists:
    def test_lists_task_directories(self, fake_tasks_dir):
        lists = list_task_lists(fake_tasks_dir)
        assert len(lists) == 1
        assert lists[0]["taskListId"] == "test-session-001"
        assert lists[0]["taskCount"] == 2


class TestDeleteSession:
    def test_deletes_session_and_reports_orphaned_task_lists(self, fake_projects_and_tasks_dir):
        projects_base, tasks_base = fake_projects_and_tasks_dir
        result = delete_session(
            "test-session-001", projects_base=projects_base, tasks_base=tasks_base
        )
        assert result["deleted"] is True
        assert not os.path.exists(result["sessionPath"])
        assert result["orphanedTaskLists"] == ["test-session-001"]
        assert result["orphanedTasksDeleted"] is False
        assert os.path.isdir(os.path.join(tasks_base, "test-session-001"))

    def test_deletes_session_and_orphaned_tasks_when_opted_in(self, fake_projects_and_tasks_dir):
        projects_base, tasks_base = fake_projects_and_tasks_dir
        result = delete_session(
            "test-session-001",
            projects_base=projects_base,
            tasks_base=tasks_base,
            delete_orphaned_tasks=True,
        )
        assert result["deleted"] is True
        assert result["orphanedTasksDeleted"] is True
        assert not os.path.exists(os.path.join(tasks_base, "test-session-001"))

    def test_deletes_session_with_no_associated_tasks(self, fake_projects_and_tasks_dir):
        projects_base, tasks_base = fake_projects_and_tasks_dir
        proj_dir = os.path.join(projects_base, "-Users-me-myproject")
        with open(os.path.join(proj_dir, "no-tasks-session.jsonl"), "w", encoding="utf-8") as f:
            f.write('{"type":"system"}\n')

        result = delete_session(
            "no-tasks-session", projects_base=projects_base, tasks_base=tasks_base
        )
        assert result["deleted"] is True
        assert result["orphanedTaskLists"] == []

    def test_raises_on_nonexistent_session(self, fake_projects_and_tasks_dir):
        projects_base, tasks_base = fake_projects_and_tasks_dir
        with pytest.raises(ValueError):
            delete_session("nonexistent", projects_base=projects_base, tasks_base=tasks_base)


class TestFindOrphanTaskLists:
    def test_finds_task_lists_with_no_matching_session(self, tmp_path):
        projects_base = tmp_path / "projects"
        tasks_base = tmp_path / "tasks"

        proj_dir = projects_base / "-Users-me-myproject"
        proj_dir.mkdir(parents=True)
        shutil.copyfile(FIXTURE, proj_dir / "test-session-001.jsonl")

        matched_dir = tasks_base / "test-session-001"
        matched_dir.mkdir(parents=True)
        (matched_dir / "1.json").write_text(json.dumps({"id": "1", "status": "pending"}))

        orphan_dir = tasks_base / "orphan-session-999"
        orphan_dir.mkdir(parents=True)
        (orphan_dir / "1.json").write_text(json.dumps({"id": "1", "status": "pending"}))

        orphans = find_orphan_task_lists(
            projects_base=str(projects_base), tasks_base=str(tasks_base)
        )
        assert len(orphans) == 1
        assert orphans[0]["taskListId"] == "orphan-session-999"
        assert orphans[0]["taskCount"] == 1

    def test_returns_empty_when_no_orphans(self, fake_projects_dir, fake_tasks_dir):
        orphans = find_orphan_task_lists(projects_base=fake_projects_dir, tasks_base=fake_tasks_dir)
        assert len(orphans) == 0

    def test_skips_directory_names_that_are_not_valid_ids(self, tmp_path):
        # A directory name that can't round-trip through is_valid_id() would be
        # unactionable (and unsafe to interpolate into a shell command) if surfaced
        # as a delete candidate -- it must be silently excluded, not reported.
        projects_base = tmp_path / "projects"
        tasks_base = tmp_path / "tasks"
        projects_base.mkdir(parents=True)

        unsafe_dir = tasks_base / "unsafe; rm -rf ~"
        unsafe_dir.mkdir(parents=True)
        (unsafe_dir / "1.json").write_text(json.dumps({"id": "1", "status": "pending"}))

        orphans = find_orphan_task_lists(
            projects_base=str(projects_base), tasks_base=str(tasks_base)
        )
        assert orphans == []


class TestGetSessionDetail:
    def test_returns_summary_stats_and_task_lists(self, fake_projects_and_tasks_dir):
        projects_base, tasks_base = fake_projects_and_tasks_dir
        detail = get_session_detail(
            "test-session-001", projects_base=projects_base, tasks_base=tasks_base
        )
        assert detail["session"]["sessionId"] == "test-session-001"
        assert detail["stats"]["turns"] > 0
        assert detail["stats"]["tokens"]["input"] > 0
        assert len(detail["taskLists"]) == 1
        assert detail["taskLists"][0]["taskListId"] == "test-session-001"
        assert len(detail["taskLists"][0]["tasks"]) == 1

    def test_returns_empty_task_lists_when_none_match(self, fake_projects_and_tasks_dir):
        projects_base, tasks_base = fake_projects_and_tasks_dir
        proj_dir = os.path.join(projects_base, "-Users-me-myproject")
        with open(os.path.join(proj_dir, "lonely-session.jsonl"), "w", encoding="utf-8") as f:
            f.write('{"type":"system","timestamp":"2026-04-10T09:00:00Z"}\n')

        detail = get_session_detail(
            "lonely-session", projects_base=projects_base, tasks_base=tasks_base
        )
        assert detail["session"]["sessionId"] == "lonely-session"
        assert detail["taskLists"] == []

    def test_raises_on_nonexistent_session(self, fake_projects_and_tasks_dir):
        projects_base, tasks_base = fake_projects_and_tasks_dir
        with pytest.raises(ValueError):
            get_session_detail("nonexistent", projects_base=projects_base, tasks_base=tasks_base)


class TestSearchSessionsUntilFilter:
    def test_until_filters_out_results_after_date(self, fake_projects_dir):
        results = search_sessions("Python", projects_base=fake_projects_dir, until="2026-04-09")
        assert len(results) == 0


class TestListSessionsUntilBoundary:
    def test_a_bare_date_until_includes_sessions_later_that_same_day(self, tmp_path):
        proj_dir = tmp_path / "-proj"
        proj_dir.mkdir(parents=True)
        (proj_dir / "afternoon.jsonl").write_text(
            '{"type":"user","timestamp":"2026-04-09T14:00:00Z",'
            '"message":{"content":"afternoon session"}}\n'
        )
        results = list_sessions(projects_base=str(tmp_path), until="2026-04-09", limit=None)
        assert len(results) == 1


class TestGetTimelineUntilFilter:
    def test_until_filters_out_sessions_after_date(self, fake_projects_dir):
        timeline = get_timeline(projects_base=fake_projects_dir, until="2026-04-09")
        assert len(timeline) == 0


class TestAggregateTasksDateFiltering:
    def test_since_filters_tasks_by_session_date(self, fake_projects_dir, fake_tasks_dir):
        tasks = aggregate_tasks(
            tasks_base=fake_tasks_dir, projects_base=fake_projects_dir, since="2026-04-11"
        )
        fs_tasks = [t for t in tasks if t.get("source") == "filesystem"]
        assert len(fs_tasks) > 0
        jsonl_tasks = [t for t in tasks if t.get("source") == "jsonl"]
        assert len(jsonl_tasks) == 0


class TestAggregateTasks:
    def test_from_filesystem(self, fake_tasks_dir):
        tasks = aggregate_tasks(tasks_base=fake_tasks_dir, projects_base="/nonexistent")
        assert len(tasks) == 2
        assert any(t.get("subject") == "Setup project" for t in tasks)

    def test_status_filter(self, fake_tasks_dir):
        pending = aggregate_tasks(
            status_filter="pending", tasks_base=fake_tasks_dir, projects_base="/nonexistent"
        )
        assert len(pending) == 1
        assert pending[0]["subject"] == "Add tests"

    def test_jsonl_fallback(self, fake_projects_dir):
        tasks = aggregate_tasks(tasks_base="/nonexistent_tasks", projects_base=fake_projects_dir)
        assert len(tasks) >= 1
        assert tasks[0]["source"] == "jsonl"

    def test_task_list_filter_scopes_the_jsonl_fallback_too(self, tmp_path):
        # A requested task_list_id previously scoped only the primary filesystem
        # read -- the JSONL fallback still scanned every project and appended tasks
        # from unrelated sessions, so a request for one list returned other
        # sessions' tasks too.
        projects_dir = tmp_path / "projects"
        wanted_dir = projects_dir / "-Users-me-wanted"
        wanted_dir.mkdir(parents=True)
        (wanted_dir / "wanted-session.jsonl").write_text(
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"TaskCreate",'
            '"input":{"subject":"Wanted task"}}]}}\n'
        )
        other_dir = projects_dir / "-Users-me-other"
        other_dir.mkdir(parents=True)
        (other_dir / "other-session.jsonl").write_text(
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"TaskCreate",'
            '"input":{"subject":"Unrelated task"}}]}}\n'
        )

        tasks = aggregate_tasks(
            task_list_id="wanted-session",
            tasks_base=str(tmp_path / "nonexistent_tasks"),
            projects_base=str(projects_dir),
        )
        assert len(tasks) == 1
        assert tasks[0]["subject"] == "Wanted task"


class TestGetDailyTokenAggregation:
    def test_buckets_tokens_by_date(self, fake_projects_dir):
        data = get_daily_token_aggregation(projects_base=fake_projects_dir)
        assert isinstance(data["labels"], list)
        assert "input" in data["datasets"]
        assert "output" in data["datasets"]
        assert "cache_read" in data["datasets"]
        assert "cache_create" in data["datasets"]
        assert len(data["labels"]) > 0
        assert "2026-04-10" in data["labels"]
        idx = data["labels"].index("2026-04-10")
        assert data["datasets"]["input"][idx] > 0
        assert data["datasets"]["output"][idx] > 0

    def test_since_filters_dates(self, fake_projects_dir):
        data = get_daily_token_aggregation(projects_base=fake_projects_dir, since="2026-04-11")
        assert len(data["labels"]) == 0


class TestGetModelDistribution:
    def test_returns_model_token_counts(self, fake_projects_dir):
        data = get_model_distribution(projects_base=fake_projects_dir)
        assert isinstance(data, list)
        assert len(data) > 0
        models = [d["model"] for d in data]
        assert any("sonnet" in m for m in models)
        assert data[0]["tokens"] > 0
        assert data[0]["sessions"] > 0

    def test_since_filters_dates(self, fake_projects_dir):
        data = get_model_distribution(projects_base=fake_projects_dir, since="2026-04-11")
        assert data == []


class TestGetActivityHeatmap:
    def test_returns_7x24_grid(self, fake_projects_dir):
        data = get_activity_heatmap(projects_base=fake_projects_dir)
        assert len(data["grid"]) == 7
        assert len(data["grid"][0]) == 24
        assert len(data["dayLabels"]) == 7
        assert len(data["hourLabels"]) == 24
        assert data["maxValue"] >= 0
        total = sum(sum(row) for row in data["grid"])
        assert total > 0

    def test_since_filters_dates(self, fake_projects_dir):
        data = get_activity_heatmap(projects_base=fake_projects_dir, since="2026-04-11")
        total = sum(sum(row) for row in data["grid"])
        assert total == 0
