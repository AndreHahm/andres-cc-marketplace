"""Archiving CI review results before their artifacts expire (issue #586)."""

from __future__ import annotations

import io
import json
import subprocess
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


def _artifact(
    id_: int,
    head: str,
    run: int,
    expired: bool = False,
    branch: str = "feat",
    size: int = 1_000,
    repository_id: int = 1,
    head_repository_id: int = 1,
) -> dict:
    return {
        "id": id_,
        "head_sha": head,
        "run_id": run,
        "expired": expired,
        "head_branch": branch,
        "size_in_bytes": size,
        "repository_id": repository_id,
        "head_repository_id": head_repository_id,
    }


def test_select_keeps_unexpired_artifacts_of_the_given_heads():
    listing = [
        _artifact(1, HEAD_A, 10),
        _artifact(2, HEAD_B, 11),
        _artifact(3, HEAD_A, 12, expired=True),
        _artifact(4, "c" * 40, 13),
    ]
    selected, expired = archive.select_artifacts(listing, {HEAD_A, HEAD_B}, "feat")
    assert [a["id"] for a in selected] == [1, 2]
    assert [a["id"] for a in expired] == [3]


def test_select_drops_a_run_of_another_branch_that_shares_a_commit():
    """A stacked PR lists its base PR's tip commit, whose runs belong to the base PR."""
    listing = [_artifact(1, HEAD_A, 10, branch="base-pr"), _artifact(2, HEAD_B, 11)]
    selected, expired = archive.select_artifacts(listing, {HEAD_A, HEAD_B}, "feat")
    assert [a["id"] for a in selected] == [2]
    assert expired == []


def test_select_drops_a_run_from_a_fork():
    """A fork's workflow file is the fork author's own, so its artifact proves nothing."""
    listing = [_artifact(1, HEAD_A, 10, head_repository_id=99), _artifact(2, HEAD_B, 11)]
    selected, _ = archive.select_artifacts(listing, {HEAD_A, HEAD_B}, "feat")
    assert [a["id"] for a in selected] == [2]


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


def _encrypted_zip() -> bytes:
    data = bytearray(_zip({"codex-review-result.json": b"{}"}))
    # Set the "encrypted" bit (0x1) in the general purpose flags of the local and central headers.
    for signature, offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        data[data.index(signature) + offset] |= 0x1
    return bytes(data)


def _unknown_compression_zip() -> bytes:
    data = bytearray(_zip({"codex-review-result.json": b"{}"}))
    for signature, offset in ((b"PK\x03\x04", 8), (b"PK\x01\x02", 10)):
        data[data.index(signature) + offset] = 99
    return bytes(data)


def _corrupt_deflate_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("codex-review-result.json", b'{"a": "' + b"x" * 500 + b'"}')
    data = bytearray(buffer.getvalue())
    start = data.index(b"PK\x03\x04") + 30 + len("codex-review-result.json")
    for index in range(start, start + 8):
        data[index] ^= 0xFF
    return bytes(data)


@pytest.mark.parametrize(
    "payload",
    [
        _encrypted_zip(),
        _unknown_compression_zip(),
        _corrupt_deflate_zip(),
        _zip({"codex-review-result.json": b"[" * 100_000 + b"]" * 100_000}),
        _zip({"codex-review-result.json": b'{"a": NaN}'}),
        _zip({"codex-review-result.json": b'{"a": Infinity}'}),
    ],
    ids=["encrypted", "unknown-compression", "corrupt-stream", "deep-nesting", "nan", "infinity"],
)
def test_extract_result_turns_every_hostile_payload_into_an_archive_error(payload):
    with pytest.raises(archive.ArchiveError):
        archive.extract_result(payload)


@pytest.mark.parametrize(
    ("head", "run", "artifact"),
    [
        ("A" * 40, 1, 1),
        ("g" * 40, 1, 1),
        ("a" * 39, 1, 1),
        (HEAD_A, 0, 1),
        (HEAD_A, 1, -1),
        (HEAD_A, True, 1),
    ],
)
def test_archive_path_rejects_a_value_that_is_not_a_plain_id(tmp_path, head, run, artifact):
    with pytest.raises(archive.ArchiveError):
        archive.archive_path(tmp_path, 579, head, run, artifact)


@pytest.mark.parametrize("pr", [0, -5])
def test_archive_path_rejects_a_non_positive_pr(tmp_path, pr):
    with pytest.raises(archive.ArchiveError):
        archive.archive_path(tmp_path, pr, HEAD_A, 10, 1)


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

    def pr_branch(self, pr):
        return "feat"

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
        {2: _result_zip({"status": "clean"})},
    )
    report = archive.archive_pr(579, tmp_path, fake)
    assert report.written == 1
    assert report.expired == 1


def test_archive_pr_reports_a_bad_artifact_and_keeps_going(tmp_path):
    fake = _Fake(
        [_artifact(1, HEAD_A, 10), _artifact(2, HEAD_B, 11)],
        [HEAD_A, HEAD_B],
        {1: b"broken", 2: _result_zip({"status": "clean"})},
    )
    report = archive.archive_pr(579, tmp_path, fake)
    assert report.written == 1
    assert len(report.failed) == 1
    assert "10" in report.failed[0]
    assert not (tmp_path / "pr-579" / f"{HEAD_A[:8]}-10-1.json").exists()


def test_a_hostile_artifact_does_not_stop_the_rest(tmp_path):
    fake = _Fake(
        [_artifact(1, HEAD_A, 10), _artifact(2, HEAD_B, 11)],
        [HEAD_A, HEAD_B],
        {1: _encrypted_zip(), 2: _result_zip({"status": "clean"})},
    )
    report = archive.archive_pr(579, tmp_path, fake)
    assert report.written == 1
    assert len(report.failed) == 1


def test_an_oversized_artifact_is_reported_without_being_downloaded(tmp_path):
    big = _artifact(1, HEAD_A, 10, size=2 * archive.MAX_RESULT_BYTES + 1)
    zips = {2: _result_zip({"status": "clean"})}
    fake = _Fake([big, _artifact(2, HEAD_B, 11)], [HEAD_A, HEAD_B], zips)
    report = archive.archive_pr(579, tmp_path, fake)
    assert fake.downloaded == [2]
    assert report.written == 1
    assert len(report.failed) == 1
    assert "larger" in report.failed[0]


def test_a_result_whose_provenance_names_another_head_is_rejected(tmp_path):
    forged = _result_zip({"status": "clean", "provenance": {"head_sha": HEAD_B}})
    fake = _Fake([_artifact(1, HEAD_A, 10)], [HEAD_A], {1: forged})
    report = archive.archive_pr(579, tmp_path, fake)
    assert report.written == 0
    assert "provenance" in report.failed[0]


def test_a_result_without_provenance_is_kept(tmp_path):
    """Results before the provenance field existed carry none."""
    fake = _Fake([_artifact(1, HEAD_A, 10)], [HEAD_A], {1: _result_zip({"status": "clean"})})
    assert archive.archive_pr(579, tmp_path, fake).written == 1


def test_a_dangling_symlink_at_the_target_is_not_followed(tmp_path):
    outside = tmp_path / "outside.json"
    target = tmp_path / "out" / "pr-579" / f"{HEAD_A[:8]}-10-1.json"
    target.parent.mkdir(parents=True)
    target.symlink_to(outside)
    fake = _Fake([_artifact(1, HEAD_A, 10)], [HEAD_A], {1: _result_zip()})
    report = archive.archive_pr(579, tmp_path / "out", fake)
    assert not outside.exists()
    assert report.written == 0
    assert report.skipped_existing == 1


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


def test_a_gh_timeout_becomes_an_archive_error(monkeypatch):
    def slow(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="gh", timeout=300)

    monkeypatch.setattr(archive.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(archive.subprocess, "run", slow)
    with pytest.raises(archive.ArchiveError, match="timed out"):
        archive.GhSource().download(1)


def test_parse_artifact_lines_reads_gh_jq_output():
    lines = "".join(
        json.dumps(_artifact(id_, head, run, expired=expired)) + "\n"
        for id_, head, run, expired in ((1, HEAD_A, 10, False), (2, HEAD_B, 11, True))
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
