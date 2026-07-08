#!/usr/bin/env python3
"""Tests for copy_files.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "copy_files.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Single-file mode
# ---------------------------------------------------------------------------


class TestSingleFile:
    def test_copy_file(self, tmp_path: Path) -> None:
        src = tmp_path / "a.txt"
        dst = tmp_path / "b.txt"
        src.write_text("hello")

        r = run(str(src), str(dst))
        assert r.returncode == 0
        assert dst.read_text() == "hello"
        assert "COPIED" in r.stdout

    def test_skip_existing_destination(self, tmp_path: Path) -> None:
        src = tmp_path / "a.txt"
        dst = tmp_path / "b.txt"
        src.write_text("new")
        dst.write_text("old")

        r = run(str(src), str(dst))
        assert r.returncode == 1
        assert dst.read_text() == "old"
        assert "SKIP" in r.stdout

    def test_overwrite_existing_destination(self, tmp_path: Path) -> None:
        src = tmp_path / "a.txt"
        dst = tmp_path / "b.txt"
        src.write_text("new")
        dst.write_text("old")

        r = run(str(src), str(dst), "--overwrite")
        assert r.returncode == 0
        assert dst.read_text() == "new"

    def test_missing_source(self, tmp_path: Path) -> None:
        r = run(str(tmp_path / "missing.txt"), str(tmp_path / "dst.txt"))
        assert r.returncode == 2
        assert "ERROR" in r.stderr

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        src = tmp_path / "a.txt"
        dst = tmp_path / "deep" / "nested" / "b.txt"
        src.write_text("hi")

        r = run(str(src), str(dst))
        assert r.returncode == 0
        assert dst.read_text() == "hi"

    def test_move_removes_source(self, tmp_path: Path) -> None:
        src = tmp_path / "a.txt"
        dst = tmp_path / "b.txt"
        src.write_text("data")

        r = run(str(src), str(dst), "--move")
        assert r.returncode == 0
        assert not src.exists()
        assert dst.read_text() == "data"
        assert "MOVED" in r.stdout

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        src = tmp_path / "a.txt"
        dst = tmp_path / "b.txt"
        src.write_text("x")

        r = run(str(src), str(dst), "--dry-run")
        assert r.returncode == 0
        assert not dst.exists()
        assert "[dry-run]" in r.stdout

    def test_copy_directory(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "file.txt").write_text("content")
        dst_dir = tmp_path / "dst"

        r = run(str(src_dir), str(dst_dir))
        assert r.returncode == 0
        assert (dst_dir / "file.txt").read_text() == "content"

    def test_missing_src_and_dst_without_manifest(self) -> None:
        r = run()
        assert r.returncode != 0


# ---------------------------------------------------------------------------
# Manifest mode
# ---------------------------------------------------------------------------


class TestManifest:
    def _write_manifest(self, tmp_path: Path, lines: list[str]) -> Path:
        manifest = tmp_path / "manifest.txt"
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return manifest

    def test_single_pair_arrow_syntax(self, tmp_path: Path) -> None:
        src = tmp_path / "a.txt"
        dst = tmp_path / "b.txt"
        src.write_text("hello")
        m = self._write_manifest(tmp_path, [f"{src} -> {dst}"])

        r = run("--manifest", str(m))
        assert r.returncode == 0
        assert dst.read_text() == "hello"

    def test_single_pair_tab_syntax(self, tmp_path: Path) -> None:
        src = tmp_path / "a.txt"
        dst = tmp_path / "b.txt"
        src.write_text("hello")
        m = self._write_manifest(tmp_path, [f"{src}\t{dst}"])

        r = run("--manifest", str(m))
        assert r.returncode == 0
        assert dst.read_text() == "hello"

    def test_multiple_pairs(self, tmp_path: Path) -> None:
        files = [(tmp_path / f"s{i}.txt", tmp_path / f"d{i}.txt") for i in range(3)]
        lines = []
        for src, _ in files:
            src.write_text(src.name)
        for src, dst in files:
            lines.append(f"{src} -> {dst}")
        m = self._write_manifest(tmp_path, lines)

        r = run("--manifest", str(m))
        assert r.returncode == 0
        for src, dst in files:
            assert dst.read_text() == src.name

    def test_blank_lines_and_comments_ignored(self, tmp_path: Path) -> None:
        src = tmp_path / "a.txt"
        dst = tmp_path / "b.txt"
        src.write_text("x")
        m = self._write_manifest(tmp_path, [
            "# this is a comment",
            "",
            f"{src} -> {dst}",
            "",
        ])

        r = run("--manifest", str(m))
        assert r.returncode == 0
        assert dst.exists()

    def test_returns_worst_exit_code_on_skip(self, tmp_path: Path) -> None:
        src1 = tmp_path / "s1.txt"
        dst1 = tmp_path / "d1.txt"
        src2 = tmp_path / "s2.txt"
        dst2 = tmp_path / "d2.txt"
        src1.write_text("a")
        src2.write_text("b")
        dst2.write_text("existing")  # will be skipped → exit 1

        m = self._write_manifest(tmp_path, [
            f"{src1} -> {dst1}",
            f"{src2} -> {dst2}",
        ])

        r = run("--manifest", str(m))
        assert r.returncode == 1  # worst of [0, 1]
        assert dst1.read_text() == "a"   # first pair succeeded
        assert dst2.read_text() == "existing"  # second pair skipped

    def test_returns_exit_2_on_missing_source(self, tmp_path: Path) -> None:
        m = self._write_manifest(tmp_path, [
            f"{tmp_path / 'missing.txt'} -> {tmp_path / 'dst.txt'}",
        ])
        r = run("--manifest", str(m))
        assert r.returncode == 2

    def test_manifest_not_found(self, tmp_path: Path) -> None:
        r = run("--manifest", str(tmp_path / "no-such-manifest.txt"))
        assert r.returncode == 2

    def test_invalid_manifest_line(self, tmp_path: Path) -> None:
        m = self._write_manifest(tmp_path, ["this line has no separator"])
        r = run("--manifest", str(m))
        assert r.returncode == 2
        assert "ERROR" in r.stderr

    def test_overwrite_flag_applies_to_manifest(self, tmp_path: Path) -> None:
        src = tmp_path / "a.txt"
        dst = tmp_path / "b.txt"
        src.write_text("new")
        dst.write_text("old")
        m = self._write_manifest(tmp_path, [f"{src} -> {dst}"])

        r = run("--manifest", str(m), "--overwrite")
        assert r.returncode == 0
        assert dst.read_text() == "new"

    def test_dry_run_with_manifest(self, tmp_path: Path) -> None:
        src = tmp_path / "a.txt"
        dst = tmp_path / "b.txt"
        src.write_text("x")
        m = self._write_manifest(tmp_path, [f"{src} -> {dst}"])

        r = run("--manifest", str(m), "--dry-run")
        assert r.returncode == 0
        assert not dst.exists()
        assert "[dry-run]" in r.stdout
