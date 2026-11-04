"""The cross-model-review run-directory check (issue #637), on the platform running the tests.

The end-to-end test takes the helpers through a real run directory, so on the Windows CI job it is
the only check of the Git Bash path. The other tests drive that branch from any platform by
replacing two shell functions, so they prove its logic and not Git Bash's behaviour.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "git-kit" / "scripts"
LIB = SCRIPTS / "git-review-run-dir.sh"
PROFILE = "C:/Users/runneradmin"

# Maps the short and differently cased spellings a fake cygpath sees to their long Windows form.
FAKE_GIT_BASH = """
set -euo pipefail
fail() { echo "$*" >&2; exit 2; }
source "$1"
run_dir_is_git_bash() { return 0; }
cygpath() {
  [ "$1" = -lm ] || exit 9
  case $2 in
    /tmp/*) echo "C:/Users/RunnerAdmin/AppData/Local/Temp/${2#/tmp/}" ;;
    /shared/*) echo "D:/shared/${2#/shared/}" ;;
    'C:\\Users\\RUNNER~1') echo "C:/Users/runneradmin" ;;
    missing) return 1 ;;
    *) echo "$2" ;;
  esac
}
check_run_dir_private "$2"
"""

FAKE_OUTSIDE_REPO = FAKE_GIT_BASH.replace(
    'check_run_dir_private "$2"',
    'check_run_dir_outside_repo "$2" "$3"',
).replace(
    "    missing) return 1 ;;",
    '    /c/*) echo "C:/${2#/c/}" ;;\n    missing) return 1 ;;',
)


def _fake(run_dir, profile):
    env = {k: v for k, v in os.environ.items() if k != "USERPROFILE"}
    if profile is not None:
        env["USERPROFILE"] = profile
    return subprocess.run(
        ["bash", "-c", FAKE_GIT_BASH, "_", LIB.as_posix(), run_dir],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


@pytest.mark.parametrize(
    "profile",
    [PROFILE, PROFILE + "/", "c:/users/RUNNERADMIN", r"C:\Users\RUNNER~1"],
)
def test_git_bash_accepts_a_directory_inside_the_profile(profile):
    result = _fake("/tmp/tmp.abcdefgh", profile)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("run_dir", "profile", "message"),
    [
        ("/shared/tmp.abcdefgh", PROFILE, "inside the user profile"),
        ("/tmp/tmp.abcdefgh", PROFILE + "2", "inside the user profile"),
        ("/tmp/tmp.abcdefgh", None, "USERPROFILE is not set"),
        ("/tmp/tmp.abcdefgh", "", "USERPROFILE is not set"),
        ("/tmp/tmp.abcdefgh", "C:/", "local drive"),
        ("/tmp/tmp.abcdefgh", "//server/share/me", "local drive"),
        ("/tmp/tmp.abcdefgh", "missing", "cannot resolve the user profile"),
        ("missing", PROFILE, "cannot resolve the run directory"),
    ],
)
def test_git_bash_refuses_anything_else(run_dir, profile, message):
    result = _fake(run_dir, profile)
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert message in result.stderr


@pytest.mark.parametrize(
    ("root", "refused"),
    [
        ("/c/Users/runneradmin", True),  # the temp directory is inside this work tree
        ("/c/users/RUNNERADMIN/AppData", True),
        ("/c/Users/runneradmin/repo", False),
        ("/c/Users/runneradmin2", False),
    ],
)
def test_git_bash_compares_the_repository_in_windows_form(root, refused):
    result = subprocess.run(
        ["bash", "-c", FAKE_OUTSIDE_REPO, "_", LIB.as_posix(), "/tmp/tmp.abcdefgh", root],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == (2 if refused else 0), result.stderr
    assert ("outside the repository" in result.stderr) is refused


def test_git_bash_detection_ignores_the_environment(tmp_path):
    """Neither OSTYPE nor a uname earlier on PATH may select the weaker branch."""
    shim = tmp_path / "uname"
    shim.write_text("#!/bin/sh\necho MINGW64_NT\n", encoding="utf-8")
    shim.chmod(0o755)
    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; run_dir_is_git_bash && echo weak || echo strict',
            "_",
            LIB.as_posix(),
        ],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "OSTYPE": "msys", "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}"},
    )
    native = subprocess.run(
        ["bash", "-c", "/usr/bin/uname -s"], capture_output=True, text=True, check=True
    )
    expected = "weak" if native.stdout.startswith(("MINGW", "MSYS")) else "strict"
    assert result.stdout.strip() == expected


def test_windows_runs_really_take_the_git_bash_branch():
    """Keeps the Windows job honest: WSL's bash would pass the rest of this file on Linux paths."""
    if sys.platform != "win32":
        pytest.skip("only meaningful on Windows")
    result = subprocess.run(
        ["bash", "-c", 'source "$1"; run_dir_is_git_bash', "_", LIB.as_posix()],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


def test_the_helpers_run_end_to_end_in_a_real_run_directory(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "a.txt").write_text("one\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-qm", "init")
    (repo / "a.txt").write_text("two\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("new\n", encoding="utf-8")
    script = """
set -euo pipefail
umask 077
scripts=$1
merge_base=$2
RUN=$(mktemp -d)
trap 'rm -rf -- "$RUN"' EXIT
export GIT_INDEX_FILE=$RUN/index
bash "$scripts/git-review-copy-index.sh" "$RUN"
bash "$scripts/git-review-intent-add.sh" "$RUN"
bash "$scripts/git-review-scope-run.sh" "$RUN" 1 "$merge_base" main
printf 'first' | bash "$scripts/git-review-write-run-file.sh" "$RUN" part.md -
printf ' second' | bash "$scripts/git-review-write-run-file.sh" "$RUN" part.md --append -
bash "$scripts/git-review-write-run-file.sh" "$RUN" whole.md @part.md
cat "$RUN/whole.md"
echo
git diff --no-renames --name-only "$merge_base"
test -s "$RUN/manifest-1.json"
"""
    result = subprocess.run(
        ["bash", "-c", script, "_", SCRIPTS.as_posix(), _git(repo, "rev-parse", "HEAD")],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert "first second" in lines
    assert {"a.txt", "untracked.txt"} <= set(lines)


@pytest.mark.parametrize(
    ("helper", "args"),
    [
        ("git-review-copy-index.sh", ()),
        ("git-review-intent-add.sh", ()),
        ("git-review-scope-run.sh", ("1", "0" * 40, "main")),
        ("git-review-write-run-file.sh", ("out.md", "-")),
    ],
)
def test_every_helper_refuses_a_run_directory_inside_the_repository(tmp_path, helper, args):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "temp").mkdir()
    script = """
script=$1
shift
RUN=$(mktemp -d)
bash "$script" "$RUN" "$@"
"""
    result = subprocess.run(
        ["bash", "-c", script, "_", (SCRIPTS / helper).as_posix(), *args],
        cwd=repo,
        input="x",
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "TMPDIR": (repo / "temp").as_posix()},
    )
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "outside the repository" in result.stderr
