from pathlib import PurePosixPath

from scripts.marketplace_ci.git_state import ChangedPath, GitState


def test_staged_paths_reports_added_file(git_repo):
    git_repo.stage("plugins/sample-kit/skills/demo/SKILL.md", "hello")
    state = GitState(repo=git_repo.root)
    assert state.staged_paths() == (
        ChangedPath(status="A", old_path=None, new_path="plugins/sample-kit/skills/demo/SKILL.md"),
    )


def test_staged_paths_reports_modified_file(git_repo):
    git_repo.stage("README.md", "one")
    state = GitState(repo=git_repo.root)
    state.staged_paths()  # sanity call before committing the initial add
    import subprocess

    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=git_repo.root, check=True)
    git_repo.stage("README.md", "two")
    assert state.staged_paths() == (
        ChangedPath(status="M", old_path="README.md", new_path="README.md"),
    )


def test_staged_paths_reports_deleted_file(git_repo):
    import subprocess

    git_repo.stage("obsolete.txt", "gone soon")
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=git_repo.root, check=True)
    (git_repo.root / "obsolete.txt").unlink()
    subprocess.run(["git", "add", "obsolete.txt"], cwd=git_repo.root, check=True)
    state = GitState(repo=git_repo.root)
    assert state.staged_paths() == (
        ChangedPath(status="D", old_path="obsolete.txt", new_path=None),
    )


def test_staged_paths_reports_rename(git_repo):
    import subprocess

    content = "x" * 200  # long enough for git's rename heuristic to match confidently
    git_repo.stage("old-name.txt", content)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=git_repo.root, check=True)
    (git_repo.root / "old-name.txt").rename(git_repo.root / "new-name.txt")
    subprocess.run(
        ["git", "add", "-A", "--", "old-name.txt", "new-name.txt"], cwd=git_repo.root, check=True
    )
    state = GitState(repo=git_repo.root)
    changes = state.staged_paths()
    assert len(changes) == 1
    assert changes[0].status == "R"
    assert changes[0].old_path == "old-name.txt"
    assert changes[0].new_path == "new-name.txt"


def test_read_index_returns_staged_blob(git_repo):
    git_repo.stage("plugins/sample-kit/hooks/hooks.json", '{"hooks": {}}')
    state = GitState(repo=git_repo.root)
    blob = state.read_index(PurePosixPath("plugins/sample-kit/hooks/hooks.json"))
    assert blob == b'{"hooks": {}}'


def test_read_index_returns_none_for_missing_path(git_repo):
    state = GitState(repo=git_repo.root)
    assert state.read_index(PurePosixPath("does/not/exist.txt")) is None


def test_staged_mode_is_executable_true_for_100755(git_repo):
    import subprocess

    path = "plugins/sample-kit/hooks/scripts/guard.sh"
    git_repo.stage(path, "#!/bin/sh\necho hi\n")
    # Force the index mode without relying on a real filesystem chmod -- portable across
    # platforms (issue #413: this is exactly what a Windows checkout can't do via os.chmod).
    subprocess.run(["git", "update-index", "--chmod=+x", "--", path], cwd=git_repo.root, check=True)
    state = GitState(repo=git_repo.root)
    assert state.staged_mode_is_executable(PurePosixPath(path)) is True


def test_staged_mode_is_executable_false_for_100644(git_repo):
    git_repo.stage("README.md", "hello")
    state = GitState(repo=git_repo.root)
    assert state.staged_mode_is_executable(PurePosixPath("README.md")) is False


def test_staged_mode_is_executable_none_for_untracked_path(git_repo):
    state = GitState(repo=git_repo.root)
    assert state.staged_mode_is_executable(PurePosixPath("does/not/exist.sh")) is None


def test_staged_mode_is_executable_raises_on_git_failure(tmp_path):
    # Regression guard (cross-model-review finding on this PR, CodeRabbit): a failed
    # `git ls-files` also produces empty stdout, which is otherwise indistinguishable
    # from a genuinely missing index entry. Without `check=True`, this silently returned
    # None -- exactly the same as "not staged" -- letting a caller (stage_generated_
    # destinations) skip correcting the destination's mode and still stage it as if it
    # succeeded. `repo` here is a real directory but deliberately not a Git repository,
    # so `git ls-files` fails with a non-zero exit and no stdout.
    import subprocess

    state = GitState(repo=tmp_path)
    try:
        state.staged_mode_is_executable(PurePosixPath("anything.sh"))
    except subprocess.CalledProcessError:
        pass
    else:
        raise AssertionError("expected staged_mode_is_executable to raise on git failure")


def test_staged_mode_is_executable_uses_literal_pathspec_for_metacharacter_filename(git_repo):
    # Regression guard (cross-model-review finding on this PR, CodeRabbit): a component
    # filename containing a Git pathspec metacharacter (here, `[1]`) is a legal filename,
    # but without `:(top,literal)`, `git ls-files -s -- <path>` treats it as a glob --
    # `[1]` matches a single literal "1" character, not the two-character substring
    # "[1]" -- so the real file is never matched and the lookup silently falls through to
    # the "no index entry" (None) branch, even though the file genuinely is staged.
    import subprocess

    path = "plugins/sample-kit/hooks/scripts/guard[1].sh"
    git_repo.stage(path, "#!/bin/sh\necho hi\n")
    subprocess.run(["git", "update-index", "--chmod=+x", "--", path], cwd=git_repo.root, check=True)
    state = GitState(repo=git_repo.root)
    assert state.staged_mode_is_executable(PurePosixPath(path)) is True
