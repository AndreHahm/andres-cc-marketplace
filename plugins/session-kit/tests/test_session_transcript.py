import json
import sys
from pathlib import Path

import pytest
from session_transcript import (
    export_transcript,
    extract_user_text,
    format_tasks_section,
    get_diff_data,
    get_errors,
    get_irritation_signals,
    get_messages,
    get_messages_paginated,
    get_resume_data,
    get_stats,
    get_tasks,
    is_system_message,
    main,
    merge_task_events,
    parse_session,
    read_lines,
)

FIXTURE = str(Path(__file__).resolve().parent / "fixtures" / "sample_session.jsonl")


class TestParseSession:
    def test_returns_all_messages(self):
        result = parse_session(FIXTURE)
        assert result["session_id"] == "test-session-001"
        assert result["message_count"] > 0
        assert "user" in result["messages_by_type"]
        assert "assistant" in result["messages_by_type"]

    def test_handles_empty_file(self, tmp_path):
        f = tmp_path / "empty.jsonl"
        f.write_text("")
        result = parse_session(str(f))
        assert result["message_count"] == 0
        assert result["messages_by_type"] == {}

    def test_handles_corrupted_lines(self, tmp_path):
        f = tmp_path / "corrupt.jsonl"
        f.write_text(
            '{"type":"user","message":{"content":"hello"},"uuid":"u1","timestamp":"2026-04-10T09:00:00Z",'
            '"sessionId":"s1"}\n'
            "this is not json\n"
            '{"type":"user","message":{"content":"world"},"uuid":"u2","timestamp":"2026-04-10T09:01:00Z",'
            '"sessionId":"s1"}\n'
        )
        result = parse_session(str(f))
        assert len(result["messages_by_type"]["user"]) == 2


class TestGetStats:
    def test_token_counts(self):
        stats = get_stats(FIXTURE)
        assert stats["tokens"]["input"] > 0
        assert stats["tokens"]["output"] > 0
        assert stats["turns"] > 0

    def test_model_distribution(self):
        stats = get_stats(FIXTURE)
        assert "claude-sonnet-4-20250514" in stats["models"]
        assert "claude-opus-4-20250514" in stats["models"]

    def test_tool_counts(self):
        stats = get_stats(FIXTURE)
        assert stats["tools"]["Glob"] >= 1
        assert stats["tools"]["Edit"] >= 1
        assert stats["tools"]["Bash"] >= 1

    def test_duration(self):
        stats = get_stats(FIXTURE)
        assert stats["duration_minutes"] > 0


class TestGetErrors:
    def test_resolves_error_to_originating_tool(self, tmp_path):
        f = tmp_path / "errors.jsonl"
        f.write_text(
            '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use",'
            '"id":"toolu_1","name":"Bash","input":{"command":"false"}}]}}\n'
            '{"type":"user","timestamp":"2026-04-10T09:00:00Z","message":{"role":"user",'
            '"content":[{"type":"tool_result","tool_use_id":"toolu_1","is_error":true,'
            '"content":"command failed"}]}}\n'
        )
        result = get_errors(str(f))
        assert result["error_count"] == 1
        assert result["errors"][0]["tool_name"] == "Bash"
        assert result["errors"][0]["error_content"] == "command failed"

    def test_ignores_successful_tool_results(self, tmp_path):
        f = tmp_path / "no_errors.jsonl"
        f.write_text(
            '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use",'
            '"id":"toolu_1","name":"Read","input":{}}]}}\n'
            '{"type":"user","message":{"role":"user","content":[{"type":"tool_result",'
            '"tool_use_id":"toolu_1","is_error":false,"content":"ok"}]}}\n'
        )
        result = get_errors(str(f))
        assert result["error_count"] == 0

    def test_unknown_tool_name_when_tool_use_missing(self, tmp_path):
        f = tmp_path / "orphan_error.jsonl"
        f.write_text(
            '{"type":"user","timestamp":"2026-04-10T09:00:00Z","message":{"role":"user",'
            '"content":[{"type":"tool_result","tool_use_id":"toolu_missing","is_error":true,'
            '"content":"boom"}]}}\n'
        )
        result = get_errors(str(f))
        assert result["errors"][0]["tool_name"] == "unknown"


class TestGetIrritationSignals:
    def test_detects_correction_phrase(self, tmp_path):
        f = tmp_path / "correction.jsonl"
        f.write_text(
            '{"type":"user","timestamp":"2026-04-10T09:00:00Z","message":{"role":"user",'
            '"content":"no, that is wrong, please undo it"}}\n'
        )
        result = get_irritation_signals(str(f))
        assert result["correction_count"] == 1
        assert result["corrections"][0]["phrase"] in {"no,", "wrong", "undo"}

    def test_detects_stuck_loop(self, tmp_path):
        call = (
            '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use",'
            '"name":"Bash","input":{"command":"ls"}}]}}\n'
        )
        f = tmp_path / "loop.jsonl"
        f.write_text(call * 3)
        result = get_irritation_signals(str(f))
        assert result["stuck_loop_count"] == 1
        assert result["stuck_loops"][0] == {"tool_name": "Bash", "count": 3}

    def test_no_loop_below_threshold(self, tmp_path):
        call = (
            '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use",'
            '"name":"Bash","input":{"command":"ls"}}]}}\n'
        )
        f = tmp_path / "short_run.jsonl"
        f.write_text(call * 2)
        result = get_irritation_signals(str(f))
        assert result["stuck_loop_count"] == 0

    def test_different_inputs_do_not_count_as_same_run(self, tmp_path):
        f = tmp_path / "varied.jsonl"
        f.write_text(
            "".join(
                '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use",'
                f'"name":"Bash","input":{{"command":"ls {i}"}}}}]}}}}\n'
                for i in range(3)
            )
        )
        result = get_irritation_signals(str(f))
        assert result["stuck_loop_count"] == 0

    def test_no_false_positive_on_plain_text(self):
        result = get_irritation_signals(FIXTURE)
        assert result["correction_count"] == 0
        assert result["stuck_loop_count"] == 0

    def test_tool_result_gap_does_not_break_a_genuine_run(self, tmp_path):
        """A bare tool-result entry is the normal, expected gap between one retry and the
        next -- it must not reset the run, or a genuine stuck-retry loop would never be
        detected at all (every real tool call is followed by its own result)."""
        call = (
            '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use",'
            '"name":"Bash","input":{"command":"ls"}}]}}\n'
        )
        result_line = (
            '{"type":"user","message":{"role":"user","content":[{"type":"tool_result",'
            '"tool_use_id":"x","content":"ok"}]}}\n'
        )
        f = tmp_path / "loop_with_results.jsonl"
        f.write_text((call + result_line) * 3)
        result = get_irritation_signals(str(f))
        assert result["stuck_loop_count"] == 1
        assert result["stuck_loops"][0] == {"tool_name": "Bash", "count": 3}

    def test_real_user_message_breaks_a_run(self, tmp_path):
        """Three identical tool calls separated by genuine human messages (not just tool
        results) are three deliberate, human-directed re-runs across a real conversation --
        not an unattended stuck loop -- so they must not be flagged."""
        call = (
            '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use",'
            '"name":"Bash","input":{"command":"ls"}}]}}\n'
        )
        human_turn = (
            '{"type":"user","message":{"role":"user","content":"looks good, keep going"}}\n'
        )
        f = tmp_path / "no_loop_across_turns.jsonl"
        f.write_text((call + human_turn) * 3)
        result = get_irritation_signals(str(f))
        assert result["stuck_loop_count"] == 0


class TestGetTasks:
    def test_extracts_task_create(self):
        tasks = get_tasks(FIXTURE)
        assert len(tasks) >= 1
        assert tasks[0]["description"] == "Add input validation to CLI parser"

    def test_reads_task_id_from_either_key_casing(self, tmp_path):
        # Real TaskUpdate tool_use input has been observed with both "taskId" and
        # "task_id" across real sessions -- reading only one silently drops every
        # update using the other casing (merge_task_events() then treats it as an
        # orphan update with no matching create).
        f = tmp_path / "mixed_casing.jsonl"
        f.write_text(
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"TaskUpdate",'
            '"input":{"taskId":"1","status":"completed"}}]}}\n'
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"TaskUpdate",'
            '"input":{"task_id":"2","status":"completed"}}]}}\n'
        )
        tasks = get_tasks(str(f))
        assert [t["task_id"] for t in tasks] == ["1", "2"]


class TestGetMessages:
    def test_filter_by_type(self):
        user_msgs = get_messages(FIXTURE, "user")
        assert all(m["type"] == "user" for m in user_msgs)

        assistant_msgs = get_messages(FIXTURE, "assistant")
        assert all(m["type"] == "assistant" for m in assistant_msgs)

    def test_all_messages(self):
        all_msgs = get_messages(FIXTURE)
        types = {m["type"] for m in all_msgs}
        assert "user" in types
        assert "assistant" in types


class TestGetMessagesPaginated:
    def test_returns_first_page(self):
        result = get_messages_paginated(FIXTURE, offset=0, limit=2)
        assert len(result["messages"]) == 2
        assert result["total"] > 2
        assert result["hasMore"] is True
        assert result["offset"] == 0

    def test_returns_second_page(self):
        result = get_messages_paginated(FIXTURE, offset=2, limit=2)
        assert len(result["messages"]) >= 1
        assert result["offset"] == 2

    def test_returns_all_messages_when_limit_exceeds_total(self):
        result = get_messages_paginated(FIXTURE, offset=0, limit=1000)
        assert result["hasMore"] is False
        assert len(result["messages"]) == result["total"]

    def test_includes_tool_details_when_requested(self):
        with_tools = get_messages_paginated(FIXTURE, offset=0, limit=100, include_tools=True)
        without_tools = get_messages_paginated(FIXTURE, offset=0, limit=100, include_tools=False)

        assistant_with_tools = next((m for m in with_tools["messages"] if m.get("tools")), None)
        assert assistant_with_tools is not None
        assert assistant_with_tools.get("toolDetails")
        assert len(assistant_with_tools["toolDetails"]) > 0

        assistant_without = next((m for m in without_tools["messages"] if m.get("tools")), None)
        assert assistant_without is not None
        assert "toolDetails" not in assistant_without


class TestExportTranscript:
    def test_markdown_format(self):
        transcript = export_transcript(FIXTURE, "md")
        assert "## User" in transcript
        assert "list all Python files" in transcript

    def test_includes_tool_summary(self):
        transcript = export_transcript(FIXTURE, "md")
        assert "Glob" in transcript or "glob" in transcript.lower()


class TestGetResumeData:
    def test_extracts_resume_context(self):
        data = get_resume_data(FIXTURE)
        assert data["session_id"] == "test-session-001"
        assert len(data["files_modified"]) > 0
        assert len(data["last_user_messages"]) > 0
        assert data["tool_calls_summary"] is not None

    def test_tasks_carry_a_default_pending_status(self):
        # The fixture's lone TaskCreate has no matching TaskUpdate -- without
        # merge_task_events() defaulting its status, it would carry no status
        # field at all, silently dropping it from a status-filtered "pending
        # work" view.
        data = get_resume_data(FIXTURE)
        assert len(data["tasks"]) >= 1
        assert all(t.get("status") == "pending" for t in data["tasks"])

    def test_reports_the_last_observed_branch_not_the_alphabetical_max(self, tmp_path):
        f = tmp_path / "branches.jsonl"
        f.write_text(
            '{"type":"user","message":{"content":"start"},"gitBranch":"main"}\n'
            '{"type":"user","message":{"content":"switch"},"gitBranch":"feature/x"}\n'
        )
        data = get_resume_data(str(f))
        assert data["branch"] == "feature/x"

    def test_files_modified_excludes_read_only_tool_calls(self, tmp_path):
        f = tmp_path / "reads.jsonl"
        f.write_text(
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read",'
            '"input":{"file_path":"read_only.py"}}]}}\n'
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Edit",'
            '"input":{"file_path":"actually_modified.py"}}]}}\n'
        )
        data = get_resume_data(str(f))
        assert data["files_modified"] == ["actually_modified.py"]

    def test_does_not_crash_on_a_bare_string_message(self, tmp_path):
        # extract_user_text() already treats a bare-string `message` as a valid
        # shape; get_resume_data()'s assistant-side content extraction must not
        # assume `message` is always a dict.
        f = tmp_path / "string_message.jsonl"
        f.write_text('{"type":"assistant","message":"a plain string, not a dict"}\n')
        data = get_resume_data(str(f))
        assert data["files_modified"] == []


class TestMergeTaskEvents:
    def test_folds_update_into_matching_create(self):
        raw = [
            {"action": "create", "subject": "Task A"},
            {"action": "update", "task_id": "1", "status": "completed"},
        ]
        merged = merge_task_events(raw, "list-1")
        assert len(merged) == 1
        assert merged[0]["status"] == "completed"
        assert merged[0]["taskListId"] == "list-1"
        assert merged[0]["source"] == "jsonl"

    def test_drops_orphan_updates(self):
        raw = [{"action": "update", "task_id": "999", "status": "completed"}]
        assert merge_task_events(raw, "list-1") == []

    def test_default_status_applied_only_when_missing(self):
        raw = [{"action": "create", "subject": "A"}]
        assert merge_task_events(raw, "list-1", default_status="pending")[0]["status"] == "pending"
        assert "status" not in merge_task_events(raw, "list-1")[0]


class TestGetDiffData:
    def test_extracts_diff_context(self):
        data = get_diff_data(FIXTURE)
        assert data["id"] is not None
        assert data["files"] is not None
        assert data["branches"] is not None
        assert data["tools"] is not None
        assert data["first_user_messages"] is not None

    def test_files_excludes_read_only_tool_calls(self, tmp_path):
        # Same MUTATING_FILE_TOOLS filter get_resume_data() already applies -- a file
        # only ever Read (never Write/Edit/NotebookEdit) is not a "change" for diffing
        # two sessions against each other.
        f = tmp_path / "reads.jsonl"
        f.write_text(
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read",'
            '"input":{"file_path":"read_only.py"}}]}}\n'
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Edit",'
            '"input":{"file_path":"actually_modified.py"}}]}}\n'
        )
        data = get_diff_data(str(f))
        assert data["files"] == ["actually_modified.py"]


class TestReadLines:
    def test_parses_valid_jsonl(self):
        lines = read_lines(FIXTURE)
        assert len(lines) > 0
        assert "type" in lines[0]

    def test_skips_malformed_lines(self, tmp_path):
        f = tmp_path / "mixed.jsonl"
        f.write_text('{"type":"user"}\nnot json\n{"type":"assistant"}\n')
        lines = read_lines(str(f))
        assert len(lines) == 2


class TestExtractUserText:
    def test_extracts_from_string_content(self):
        assert extract_user_text({"message": {"content": "hello world"}}) == "hello world"

    def test_extracts_from_string_message(self):
        assert extract_user_text({"message": "hello"}) == "hello"

    def test_extracts_from_array_content(self):
        text = extract_user_text(
            {
                "message": {
                    "content": [
                        {"type": "text", "text": "part1"},
                        {"type": "text", "text": "part2"},
                    ]
                }
            }
        )
        assert text == "part1 part2"

    def test_returns_empty_for_no_content(self):
        assert extract_user_text({}) == ""


class TestIsSystemMessage:
    def test_detects_local_command_messages(self):
        assert is_system_message("<local-command>foo</local-command>") is True

    def test_detects_command_name_messages(self):
        assert is_system_message("<command-name>bar</command-name>") is True

    def test_returns_false_for_normal_text(self):
        assert is_system_message("hello world") is False


class TestExportOutput:
    @staticmethod
    def _export(monkeypatch, *flags: str) -> None:
        monkeypatch.setattr(sys, "argv", ["session_transcript.py", "export", FIXTURE, *flags])
        main()

    def test_writes_a_new_file(self, monkeypatch, tmp_path):
        out = tmp_path / "out.md"
        self._export(monkeypatch, "--output", str(out))
        assert out.read_text(encoding="utf-8") == export_transcript(FIXTURE, "md", True)

    def test_refuses_an_existing_file_and_keeps_it(self, monkeypatch, tmp_path, capsys):
        out = tmp_path / "out.md"
        out.write_text("keep me", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            self._export(monkeypatch, "--output", str(out))
        assert exc.value.code == 2
        captured = capsys.readouterr()
        assert "already exists" in json.loads(captured.err)["error"]
        assert captured.out == ""
        assert out.read_text(encoding="utf-8") == "keep me"

    def test_refuses_a_dangling_symlink(self, monkeypatch, tmp_path):
        target = tmp_path / "target.md"
        out = tmp_path / "out.md"
        out.symlink_to(target)
        with pytest.raises(SystemExit) as exc:
            self._export(monkeypatch, "--output", str(out))
        assert exc.value.code == 2
        assert not target.exists()

    def test_overwrite_replaces_the_file(self, monkeypatch, tmp_path):
        out = tmp_path / "out.md"
        out.write_text("old", encoding="utf-8")
        self._export(monkeypatch, "--output", str(out), "--overwrite")
        assert out.read_text(encoding="utf-8") == export_transcript(FIXTURE, "md", True)

    def test_refuses_a_symlink_to_an_existing_file(self, monkeypatch, tmp_path):
        target = tmp_path / "target.md"
        target.write_text("keep me", encoding="utf-8")
        out = tmp_path / "out.md"
        out.symlink_to(target)
        with pytest.raises(SystemExit) as exc:
            self._export(monkeypatch, "--output", str(out))
        assert exc.value.code == 2
        assert target.read_text(encoding="utf-8") == "keep me"

    @pytest.mark.parametrize("overwrite", [False, True])
    def test_unencodable_text_leaves_no_file_behind(self, monkeypatch, tmp_path, overwrite):
        src = tmp_path / "s.jsonl"
        src.write_text(
            json.dumps({"type": "user", "message": {"content": "bad " + chr(0xD800)}}) + "\n",
            encoding="utf-8",
        )
        out = tmp_path / "out.md"
        if overwrite:
            out.write_text("keep me", encoding="utf-8")
        flags = ["--output", str(out)] + (["--overwrite"] if overwrite else [])
        monkeypatch.setattr(sys, "argv", ["session_transcript.py", "export", str(src), *flags])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 3
        assert out.exists() is overwrite
        if overwrite:
            assert out.read_text(encoding="utf-8") == "keep me"

    @pytest.mark.parametrize("link", [False, True])
    def test_never_overwrites_the_session_itself(self, monkeypatch, tmp_path, link):
        src = tmp_path / "s.jsonl"
        content = Path(FIXTURE).read_bytes()
        src.write_bytes(content)
        out = src
        if link:
            out = tmp_path / "out.md"
            out.symlink_to(src)
        argv = ["session_transcript.py", "export", str(src), "--output", str(out), "--overwrite"]
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 2
        assert src.read_bytes() == content

    @pytest.mark.parametrize("flag", ["--over", "--overwite"])
    def test_abbreviated_or_mistyped_overwrite_is_rejected(self, monkeypatch, tmp_path, flag):
        out = tmp_path / "out.md"
        out.write_text("keep me", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            self._export(monkeypatch, "--output", str(out), flag)
        assert exc.value.code == 2
        assert out.read_text(encoding="utf-8") == "keep me"

    def test_include_tasks_writes_a_tasks_section(self, monkeypatch, tmp_path):
        out = tmp_path / "out.md"
        self._export(monkeypatch, "--output", str(out), "--include-tasks", "pending")
        text = out.read_text(encoding="utf-8")
        assert text.startswith(export_transcript(FIXTURE, "md", True))
        expected = "- [pending] CLI validation: Add input validation to CLI parser"
        assert text.endswith(f"## Tasks\n\n{expected}\n")

    def test_include_tasks_pending_leaves_out_other_tasks(self, monkeypatch):
        tasks = [
            {"status": "completed", "subject": "done"},
            {"status": "pending", "subject": "open\nnext"},
        ]
        monkeypatch.setattr("session_transcript.merge_task_events", lambda *a, **k: tasks)
        assert format_tasks_section(FIXTURE, "pending") == "## Tasks\n\n- [pending] open next\n"
        assert "- [completed] done" in format_tasks_section(FIXTURE, "all")

    def test_tasks_section_without_matches_says_so(self, monkeypatch):
        monkeypatch.setattr("session_transcript.merge_task_events", lambda *a, **k: [])
        assert "No matching tasks." in format_tasks_section(FIXTURE, "all")
