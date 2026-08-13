"""Git index readers: staged-change enumeration and blob reads."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

_RENAME_STATUSES = ("R", "C")


@dataclass(frozen=True)
class ChangedPath:
    status: str  # "A" | "M" | "D" | "R"
    old_path: str | None
    new_path: str | None


def _parse_name_status_z(raw: bytes) -> tuple[ChangedPath, ...]:
    fields = raw.decode("utf-8").split("\0")
    if fields and fields[-1] == "":
        fields.pop()

    changes: list[ChangedPath] = []
    i = 0
    while i < len(fields):
        status_field = fields[i]
        status_code = status_field[0]
        if status_code in _RENAME_STATUSES:
            old_path, new_path = fields[i + 1], fields[i + 2]
            changes.append(ChangedPath(status="R", old_path=old_path, new_path=new_path))
            i += 3
        elif status_code == "D":
            path = fields[i + 1]
            changes.append(ChangedPath(status="D", old_path=path, new_path=None))
            i += 2
        elif status_code == "A":
            path = fields[i + 1]
            changes.append(ChangedPath(status="A", old_path=None, new_path=path))
            i += 2
        else:
            path = fields[i + 1]
            changes.append(ChangedPath(status="M", old_path=path, new_path=path))
            i += 2
    return tuple(changes)


@dataclass(frozen=True)
class GitState:
    repo: Path

    def staged_paths(self) -> tuple[ChangedPath, ...]:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-status", "-z", "--find-renames"],
            cwd=self.repo,
            check=True,
            capture_output=True,
        )
        return _parse_name_status_z(result.stdout)

    def read_index(self, path: PurePosixPath) -> bytes | None:
        result = subprocess.run(
            ["git", "show", f":{path.as_posix()}"],
            cwd=self.repo,
            capture_output=True,
        )
        if result.returncode != 0:
            return None
        return result.stdout
