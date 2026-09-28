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


def parse_name_status_z(raw: bytes) -> tuple[ChangedPath, ...]:
    """Parse `git diff --name-status -z --find-renames` output, preserving
    both sides of a detected rename as one ChangedPath(status="R", ...).
    Shared beyond GitState.staged_paths below -- __main__.py's scope/review
    diff handlers also need rename-aware parsing so a renamed component
    isn't silently reduced to only its destination path. surrogateescape:
    git emits raw filesystem bytes, which need not be valid UTF-8 -- a
    strict decode would raise and crash the caller on a byte sequence that
    just needs to survive a prefix/basename check, not round-trip
    perfectly (same reasoning as __main__.py's _split_nul_delimited_paths)."""
    fields = raw.decode("utf-8", errors="surrogateescape").split("\0")
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
        return parse_name_status_z(result.stdout)

    def read_index(self, path: PurePosixPath) -> bytes | None:
        result = subprocess.run(
            ["git", "show", f":{path.as_posix()}"],
            cwd=self.repo,
            capture_output=True,
        )
        if result.returncode != 0:
            return None
        return result.stdout

    def staged_mode_is_executable(self, path: PurePosixPath) -> bool | None:
        """The index-recorded mode for `path` -- True for 100755, False for any other
        mode, None if `path` has no index entry at all. Reads Git's own index-recorded
        mode bit, not the working-tree file's OS-reported permissions: on Windows,
        os.chmod()/os.stat() can't represent a real POSIX execute bit at all (only the
        read-only DOS attribute), so a filesystem stat can never answer this question
        there -- the index entry is the only value that's reliably meaningful on every
        platform (issue #413). `check=True` matters here specifically: a failed `git
        ls-files` also produces empty stdout, which is otherwise indistinguishable from
        a genuinely missing index entry -- silently returning None either way would make
        `stage_generated_destinations` skip forcing the destination's mode and still
        stage it as if it succeeded (cross-model-review of this PR, CodeRabbit). `:(top,
        literal)` guards against a component filename containing Git pathspec
        metacharacters matching more than the one intended entry."""
        result = subprocess.run(
            ["git", "ls-files", "-s", "--", f":(top,literal){path.as_posix()}"],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        )
        line = result.stdout.strip()
        if not line:
            return None
        return line.split()[0] == "100755"
