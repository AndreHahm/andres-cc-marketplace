from pathlib import Path

from session_transcript import (
    export_transcript,
    extract_user_text,
    get_diff_data,
    get_errors,
    get_irritation_signals,
    get_messages,
    get_messages_paginated,
    get_resume_data,
    get_stats,
    get_tasks,
    is_system_message,
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
