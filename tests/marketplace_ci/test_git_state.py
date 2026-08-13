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
