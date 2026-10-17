"""Archiving CI review results before their artifacts expire (issue #586)."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from scripts.reviewer_eval import archive

HEAD_A = "a" * 40
HEAD_B = "b" * 40
RESULT = {"status": "findings", "findings": [], "provenance": {"head_sha": HEAD_A}}


def _zip(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        for name, data in members.items():
            bundle.writestr(name, data)
    return buffer.getvalue()


def _result_zip(result: object = RESULT) -> bytes:
    return _zip({"codex-review-result.json": json.dumps(result).encode()})


def _artifact(id_: int, head: str, run: int, expired: bool = False) -> dict:
    return {"id": id_, "head_sha": head, "run_id": run, "expired": expired}


def test_select_keeps_unexpired_artifacts_of_the_given_heads():
    listing = [
        _artifact(1, HEAD_A, 10),
        _artifact(2, HEAD_B, 11),
        _artifact(3, HEAD_A, 12, expired=True),
        _artifact(4, "c" * 40, 13),
    ]
    selected, expired = archive.select_artifacts(listing, {HEAD_A, HEAD_B})
    assert [a["id"] for a in selected] == [1, 2]
    assert [a["id"] for a in expired] == [3]


def test_archive_path_names_the_pr_head_and_run(tmp_path):
    path = archive.archive_path(tmp_path, 579, HEAD_A, 10, 7)
    assert path == tmp_path / "pr-579" / f"{HEAD_A[:8]}-10-7.json"


def test_extract_result_returns_the_parsed_result():
    assert archive.extract_result(_result_zip()) == RESULT


@pytest.mark.parametrize(
    "payload",
    [
        b"not a zip",
        _zip({}),
        _zip({"other.json": b"{}"}),
        _zip({"codex-review-result.json": b"{"}),
        _zip({"codex-review-result.json": b"[]"}),
        _zip({"codex-review-result.json": b"{}", "extra.txt": b"x"}),
    ],
)
def test_extract_result_rejects_anything_but_one_json_object(payload):
    with pytest.raises(archive.ArchiveError):
        archive.extract_result(payload)


def test_extract_result_rejects_an_oversized_member():
    big = json.dumps({"x": "y" * (archive.MAX_RESULT_BYTES + 1)}).encode()
    with pytest.raises(archive.ArchiveError, match="larger"):
        archive.extract_result(_zip({"codex-review-result.json": big}))


class _Fake:
    def __init__(self, listing, commits, zips):
        self.listing = listing
        self.commits = commits
        self.zips = zips
        self.downloaded: list[int] = []

    def list_artifacts(self):
        return self.listing

    def pr_heads(self, pr):
        return self.commits

    def download(self, artifact_id):
        self.downloaded.append(artifact_id)
        return self.zips[artifact_id]


def test_archive_pr_writes_each_result_once(tmp_path):
    fake = _Fake(
        [_artifact(1, HEAD_A, 10), _artifact(2, HEAD_B, 11)],
        [HEAD_A, HEAD_B],
        {1: _result_zip(), 2: _result_zip({"status": "clean"})},
    )
    report = archive.archive_pr(579, tmp_path, fake)
    assert report.written == 2
    assert report.skipped_existing == 0
    stored = json.loads((tmp_path / "pr-579" / f"{HEAD_B[:8]}-11-2.json").read_text())
    assert stored == {"status": "clean"}


def test_archive_pr_is_idempotent_and_never_overwrites(tmp_path):
    fake = _Fake([_artifact(1, HEAD_A, 10)], [HEAD_A], {1: _result_zip()})
    archive.archive_pr(579, tmp_path, fake)
    target = tmp_path / "pr-579" / f"{HEAD_A[:8]}-10-1.json"
    target.write_text('{"edited": true}\n', encoding="utf-8")
    fake.downloaded.clear()
    report = archive.archive_pr(579, tmp_path, fake)
    assert report.written == 0
    assert report.skipped_existing == 1
    assert fake.downloaded == []
    assert json.loads(target.read_text()) == {"edited": True}


def test_archive_pr_reports_expired_artifacts_and_keeps_going(tmp_path):
    fake = _Fake(
        [_artifact(1, HEAD_A, 10, expired=True), _artifact(2, HEAD_B, 11)],
        [HEAD_A, HEAD_B],
        {2: _result_zip()},
    )
    report = archive.archive_pr(579, tmp_path, fake)
    assert report.written == 1
    assert report.expired == 1


def test_archive_pr_reports_a_bad_artifact_and_keeps_going(tmp_path):
    fake = _Fake(
        [_artifact(1, HEAD_A, 10), _artifact(2, HEAD_B, 11)],
        [HEAD_A, HEAD_B],
        {1: b"broken", 2: _result_zip()},
    )
    report = archive.archive_pr(579, tmp_path, fake)
    assert report.written == 1
    assert len(report.failed) == 1
    assert "10" in report.failed[0]
    assert not (tmp_path / "pr-579" / f"{HEAD_A[:8]}-10-1.json").exists()


def test_a_rerun_of_the_same_run_is_archived_as_its_own_file(tmp_path):
    fake = _Fake(
        [_artifact(1, HEAD_A, 10), _artifact(2, HEAD_A, 10)],
        [HEAD_A],
        {1: _result_zip({"status": "findings"}), 2: _result_zip({"status": "clean"})},
    )
    report = archive.archive_pr(579, tmp_path, fake)
    assert report.written == 2
    assert report.skipped_existing == 0
    names = sorted(p.name for p in (tmp_path / "pr-579").iterdir())
    assert names == [f"{HEAD_A[:8]}-10-1.json", f"{HEAD_A[:8]}-10-2.json"]


def test_archive_pr_ignores_artifacts_of_other_heads(tmp_path):
    fake = _Fake([_artifact(1, "c" * 40, 10)], [HEAD_A], {})
    report = archive.archive_pr(579, tmp_path, fake)
    assert report.written == 0
    assert fake.downloaded == []


def test_a_written_file_is_valid_json_ending_in_a_newline(tmp_path):
    fake = _Fake([_artifact(1, HEAD_A, 10)], [HEAD_A], {1: _result_zip()})
    archive.archive_pr(579, tmp_path, fake)
    text = Path(tmp_path / "pr-579" / f"{HEAD_A[:8]}-10-1.json").read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert json.loads(text) == RESULT


def test_parse_artifact_lines_reads_gh_jq_output():
    lines = (
        f'{{"id":1,"expired":false,"head_sha":"{HEAD_A}","run_id":10}}\n'
        f'{{"id":2,"expired":true,"head_sha":"{HEAD_B}","run_id":11}}\n'
    )
    parsed = archive.parse_artifact_lines(lines)
    assert [a["id"] for a in parsed] == [1, 2]
    assert parsed[1]["expired"] is True


def test_parse_artifact_lines_rejects_a_malformed_line():
    with pytest.raises(archive.ArchiveError):
        archive.parse_artifact_lines('{"id":1}\nnot json\n')


def test_parse_artifact_lines_rejects_a_row_missing_a_field():
    with pytest.raises(archive.ArchiveError):
        archive.parse_artifact_lines('{"id":1,"expired":false}\n')
