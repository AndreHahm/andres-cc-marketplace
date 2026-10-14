"""A canonical file and its byte-identical `.claude/` mirror are one reviewed unit (#572, item 5).

`plugins/<plugin>/skills/x/SKILL.md` and `.claude/skills/x/SKILL.md` are
generated copies of each other, and the parity job already checks that they
stay identical. Reviewing both doubles the work and the findings. A pair that
is identical collapses into the canonical path; a pair that has drifted is not
collapsed, because the drift itself is what the review must see.

The mirror map is read from the trusted base, never from the PR's own copy.
Reference rule: `mirror-identical` in `plugins/git-kit/scripts/git-review-scope.py`,
re-implemented here because a Tier-1 module cannot import a plugin script.
"""

import json
import os
import stat
import subprocess
import sys

import pytest

from scripts.marketplace_ci.git_state import parse_name_status_z
from scripts.marketplace_ci.review import collapse_identical_mirrors

CANONICAL = "plugins/demo-kit/skills/x/SKILL.md"
MIRROR = ".claude/skills/x/SKILL.md"
SYNC = ".claude/marketplace-sync.json"

requires_posix_permission_bits = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows' os.chmod/stat don't support real POSIX executable bits",
)


def _git(root, *args):
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _sync(plugin_mirrors=("demo-kit",), exceptions=()):
    return json.dumps(
        {
            "version": 1,
            "plugin_mirrors": list(plugin_mirrors),
            "scripts_mirrors": [],
            "divergence_exceptions": [{"source": CANONICAL, "dest": d} for d in exceptions],
        }
    )


class Scenario:
    def __init__(self, git_repo):
        self.repo = git_repo
        self.root = git_repo.root

    def base(self, sync_text: str | None = None, **files: str) -> str:
        self.repo.write(CANONICAL, "old\n")
        self.repo.write(MIRROR, "old\n")
        if sync_text is not None:
            self.repo.write(SYNC, sync_text)
        for path, text in files.items():
            self.repo.write(path, text)
        _git(self.root, "add", "-A", "-f")
        _git(self.root, "commit", "-q", "-m", "base")
        return _git(self.root, "rev-parse", "HEAD")

    def change(self, canonical: str, mirror: str, **files: str):
        self.repo.write(CANONICAL, canonical)
        self.repo.write(MIRROR, mirror)
        for path, text in files.items():
            self.repo.write(path, text)
        _git(self.root, "add", "-A", "-f")
        _git(self.root, "commit", "-q", "-m", "change")

    def collapsed(self, base_sha: str) -> set[str]:
        raw = subprocess.run(
            ["git", "diff", "-z", "--name-status", "--find-renames", f"{base_sha}...HEAD"],
            cwd=self.root,
            capture_output=True,
            check=True,
        ).stdout
        changed = parse_name_status_z(raw)
        result = collapse_identical_mirrors(self.root, changed, base_sha)
        return {path for p in result if (path := p.new_path or p.old_path)}


@pytest.fixture
def scenario(git_repo):
    return Scenario(git_repo)


def test_an_identical_pair_is_reviewed_once_under_the_canonical_path(scenario):
    base = scenario.base(_sync())
    scenario.change("new\n", "new\n")
    paths = scenario.collapsed(base)
    assert CANONICAL in paths
    assert MIRROR not in paths


def test_a_drifted_pair_is_not_collapsed(scenario):
    base = scenario.base(_sync())
    scenario.change("new\n", "new but different\n")
    assert {CANONICAL, MIRROR} <= scenario.collapsed(base)


def test_a_mirror_changed_alone_is_not_collapsed(scenario):
    """The mirror differs from its canonical, which did not change: that is drift."""
    base = scenario.base(_sync())
    scenario.change("old\n", "edited only here\n")
    assert MIRROR in scenario.collapsed(base)


@requires_posix_permission_bits
def test_an_executable_bit_difference_is_not_collapsed(scenario):
    base = scenario.base(_sync())
    scenario.change("new\n", "new\n")
    os.chmod(scenario.root / MIRROR, os.stat(scenario.root / MIRROR).st_mode | stat.S_IXUSR)
    _git(scenario.root, "add", "-f", MIRROR)
    _git(scenario.root, "commit", "-q", "-m", "chmod mirror")
    assert {CANONICAL, MIRROR} <= scenario.collapsed(base)


def test_a_declared_divergence_exception_is_not_collapsed(scenario):
    base = scenario.base(_sync(exceptions=(MIRROR,)))
    scenario.change("new\n", "new\n")
    assert {CANONICAL, MIRROR} <= scenario.collapsed(base)


def test_a_plugin_not_in_the_mirror_map_is_not_collapsed(scenario):
    base = scenario.base(_sync(plugin_mirrors=("other-kit",)))
    scenario.change("new\n", "new\n")
    assert {CANONICAL, MIRROR} <= scenario.collapsed(base)


def test_without_a_mirror_map_on_the_base_nothing_is_collapsed(scenario):
    base = scenario.base(None)
    scenario.change("new\n", "new\n")
    assert {CANONICAL, MIRROR} <= scenario.collapsed(base)


def test_the_mirror_map_is_read_from_the_base_not_from_the_pr(scenario):
    """A PR that adds its own plugin to the map must not collapse its own pair."""
    base = scenario.base(_sync(plugin_mirrors=("other-kit",)))
    scenario.change("new\n", "new\n", **{SYNC: _sync(plugin_mirrors=("demo-kit",))})
    paths = scenario.collapsed(base)
    assert CANONICAL in paths and MIRROR in paths


def test_unrelated_paths_pass_through_untouched(scenario):
    base = scenario.base(_sync())
    scenario.change("new\n", "new\n", **{"README.md": "readme\n"})
    assert "README.md" in scenario.collapsed(base)


@pytest.mark.skipif(sys.platform == "win32", reason="needs real symlinks")
def test_identical_symlinks_are_not_collapsed(scenario):
    """A relative link resolves differently from the canonical and the mirror path (they sit
    at different depths), so equal link text is not equal content."""
    base = scenario.base(_sync())
    for rel in (CANONICAL, MIRROR):
        path = scenario.root / rel
        path.unlink()
        path.symlink_to("../../../scripts/x")
    _git(scenario.root, "add", "-A", "-f")
    _git(scenario.root, "commit", "-q", "-m", "symlinks")
    assert {CANONICAL, MIRROR} <= scenario.collapsed(base)
