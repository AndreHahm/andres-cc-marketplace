import json
from datetime import UTC, datetime, timedelta

from formatters import (
    format_duration,
    format_size,
    parse_date_boundary,
    parse_timestamp,
    render_table,
    to_json,
    to_ndjson,
    truncate,
)


class TestToJson:
    def test_compact_serialization(self):
        result = to_json({"a": 1, "b": "hello"})
        assert json.loads(result) == {"a": 1, "b": "hello"}
        assert "\n" not in result

    def test_handles_null_values(self):
        assert json.loads(to_json({"a": None})) == {"a": None}

    def test_handles_datetime_objects(self):
        d = datetime(2026, 4, 10, 9, 0, 0, tzinfo=UTC)
        parsed = json.loads(to_json({"ts": d}))
        assert "2026" in parsed["ts"]

    def test_handles_set_objects(self):
        parsed = json.loads(to_json({"items": {"b", "a", "c"}}))
        assert parsed["items"] == ["a", "b", "c"]


class TestToNdjson:
    def test_produces_newline_delimited_json(self):
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = to_ndjson(items)
        lines = result.strip().split("\n")
        assert len(lines) == 3
        assert json.loads(lines[0]) == {"id": 1}
        assert json.loads(lines[2]) == {"id": 3}

    def test_returns_empty_string_for_empty_list(self):
        assert to_ndjson([]) == ""


class TestTruncate:
    def test_short_string_unchanged(self):
        assert truncate("hello", 100) == "hello"

    def test_long_string_truncated_with_ellipsis(self):
        result = truncate("a" * 200, 50)
        assert len(result) == 53
        assert result.endswith("...")

    def test_exact_length_unchanged(self):
        assert truncate("hello", 5) == "hello"


class TestFormatDuration:
    def test_seconds_only(self):
        assert format_duration(45) == "45s"

    def test_minutes_and_seconds(self):
        assert format_duration(125) == "2m 5s"

    def test_hours_and_minutes(self):
        assert format_duration(3661) == "1h 1m"

    def test_zero(self):
        assert format_duration(0) == "0s"


class TestFormatSize:
    def test_bytes(self):
        assert format_size(500) == "500 B"

    def test_kilobytes(self):
        assert format_size(2048) == "2.0 KB"

    def test_megabytes(self):
        assert format_size(5_242_880) == "5.0 MB"

    def test_zero_bytes(self):
        assert format_size(0) == "0 B"


class TestParseTimestamp:
    def test_epoch_milliseconds(self):
        d = parse_timestamp(1712739600000)
        assert isinstance(d, datetime)
        assert d.year >= 2024

    def test_epoch_seconds(self):
        d = parse_timestamp(1712739600)
        assert isinstance(d, datetime)

    def test_iso_string(self):
        d = parse_timestamp("2026-04-10T09:00:00Z")
        assert isinstance(d, datetime)
        assert d.year == 2026

    def test_none_returns_none(self):
        assert parse_timestamp(None) is None


class TestParseDateBoundary:
    def test_iso_date_string_returns_midnight_utc(self):
        d = parse_date_boundary("2026-04-01")
        assert isinstance(d, datetime)
        assert d.astimezone(UTC).isoformat() == "2026-04-01T00:00:00+00:00"

    def test_iso_datetime_string_returns_exact_time(self):
        d = parse_date_boundary("2026-04-01T14:30:00Z")
        assert isinstance(d, datetime)
        assert d.astimezone(UTC).isoformat() == "2026-04-01T14:30:00+00:00"

    def test_relative_days_7d(self):
        d = parse_date_boundary("7d")
        assert isinstance(d, datetime)
        now = datetime.now(UTC)
        diff = now - d
        assert abs(diff - timedelta(days=7)) < timedelta(seconds=1)

    def test_relative_weeks_2w(self):
        d = parse_date_boundary("2w")
        assert isinstance(d, datetime)
        now = datetime.now(UTC)
        diff = now - d
        assert abs(diff - timedelta(days=14)) < timedelta(seconds=1)

    def test_relative_months_3m(self):
        d = parse_date_boundary("3m")
        assert isinstance(d, datetime)
        now = datetime.now(UTC)
        # 3 calendar months back, roughly 89-92 days
        diff_days = (now - d).days
        assert 85 <= diff_days <= 95

    def test_invalid_string_returns_none(self):
        assert parse_date_boundary("garbage") is None
        assert parse_date_boundary("") is None
        assert parse_date_boundary("abc123") is None


class TestRenderTable:
    def test_renders_header_separator_and_rows(self):
        rows = [
            {"id": "abc123", "name": "Test", "count": 42},
            {"id": "def456", "name": "Other", "count": 7},
        ]
        columns = [
            {"key": "id", "label": "ID"},
            {"key": "name", "label": "NAME"},
            {"key": "count", "label": "COUNT", "align": "right"},
        ]
        result = render_table(rows, columns)
        lines = [line for line in result.split("\n") if line]
        assert len(lines) == 5
        assert "ID" in lines[0]
        assert "NAME" in lines[0]
        assert "COUNT" in lines[0]
        assert set(lines[1].replace(" ", "")) <= {"-", "─"}
        assert "abc123" in lines[2]
        assert lines[4] == "2 rows"

    def test_empty_rows_returns_header_separator_footer(self):
        columns = [{"key": "id", "label": "ID"}]
        result = render_table([], columns)
        lines = [line for line in result.split("\n") if line]
        assert len(lines) == 3
        assert lines[2] == "0 rows"

    def test_truncates_long_values_with_width_option(self):
        rows = [{"text": "a" * 100}]
        columns = [{"key": "text", "label": "TEXT", "width": 20}]
        result = render_table(rows, columns)
        assert f"{'a' * 17}..." in result

    def test_right_aligns_numeric_columns(self):
        rows = [{"n": 42}, {"n": 1234}]
        columns = [{"key": "n", "label": "NUM", "align": "right"}]
        result = render_table(rows, columns)
        lines = [line for line in result.split("\n") if line]
        line42 = lines[2]
        line1234 = lines[3]
        assert len(line42.rstrip()) <= len(line1234.rstrip())

    def test_custom_format_function(self):
        rows = [{"bytes": 2048}]
        columns = [{"key": "bytes", "label": "SIZE", "format": lambda v: format_size(v)}]
        result = render_table(rows, columns)
        assert "2.0 KB" in result
