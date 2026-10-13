"""git-kit's git-review-scope.py narrows a review diff and always says what it left out (#541).

Pure `plan_scope` cases use in-memory fakes; the end-to-end cases run the script against a real
temporary git repository.
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/git-kit/scripts/git-review-scope.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("git_review_scope", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["git_review_scope"] = module
    spec.loader.exec_module(module)
    return module


M = _load_module()

SYNC = {
    "plugin_mirrors": ["git-kit"],
    "scripts_mirrors": ["git-kit"],
    "exceptions": set(),
}


def _config(**overrides):
    config = M.load_config(None, None, False)
    config.update(overrides)
    return config


def _plan(files, *, tree=None, config=None, sizes=None, **kwargs):
    tree = {f: b"x" for f in files} if tree is None else tree
    sizes = sizes or {}
    return M.plan_scope(
        files,
        config or _config(),
        kwargs.pop("sync", SYNC),
        read=lambda p: tree.get(p),
        diff_size=lambda p: sizes.get(p, 100),
        base="mb",
        **kwargs,
    )


def _reasons(manifest):
    return {e["path"]: e["reason"] for e in manifest["excluded"]}


# --- mirror collapsing -------------------------------------------------------------------------


def test_identical_claude_mirror_collapses_to_canonical():
    tree = {
        "plugins/git-kit/skills/a/SKILL.md": b"same",
        ".claude/skills/a/SKILL.md": b"same",
    }
    manifest = _plan(list(tree), tree=tree)
    assert _reasons(manifest) == {".claude/skills/a/SKILL.md": "mirror-identical"}
    assert [f["path"] for f in manifest["files"]] == ["plugins/git-kit/skills/a/SKILL.md"]


def test_differing_mirror_is_kept_because_drift_is_a_finding():
    tree = {
        "plugins/git-kit/skills/a/SKILL.md": b"canonical",
        ".claude/skills/a/SKILL.md": b"drifted",
    }
    manifest = _plan(list(tree), tree=tree)
    assert manifest["excluded"] == []
    assert len(manifest["files"]) == 2


def test_mirror_without_canonical_is_kept():
    tree = {".claude/skills/orphan/SKILL.md": b"x"}
    assert _plan(list(tree), tree=tree)["excluded"] == []


def test_divergence_exception_is_never_collapsed():
    tree = {"plugins/git-kit/skills/a/SKILL.md": b"s", ".claude/skills/a/SKILL.md": b"s"}
    sync = dict(SYNC, exceptions={".claude/skills/a/SKILL.md"})
    assert _plan(list(tree), tree=tree, sync=sync)["excluded"] == []


def test_scripts_mirror_uses_scripts_mirrors_list():
    tree = {"plugins/git-kit/scripts/x.py": b"s", ".claude/scripts/x.py": b"s"}
    assert _reasons(_plan(list(tree), tree=tree)) == {".claude/scripts/x.py": "mirror-identical"}
    other = dict(SYNC, scripts_mirrors=[])
    assert _plan(list(tree), tree=tree, sync=other)["excluded"] == []


def test_agents_skill_export_collapses_through_the_claude_copy():
    tree = {
        "plugins/git-kit/skills/a/SKILL.md": b"s",
        ".claude/skills/a/SKILL.md": b"s",
        ".agents/skills/a/SKILL.md": b"s",
    }
    reasons = _reasons(_plan(list(tree), tree=tree))
    assert reasons[".agents/skills/a/SKILL.md"] == "mirror-identical"


def test_codex_agent_export_is_never_collapsed_even_with_its_source_in_the_diff():
    tree = {".claude/agents/r.md": b"a", ".codex/agents/r.toml": b"forged"}
    manifest = _plan(list(tree), tree=tree)
    assert manifest["excluded"] == []
    assert ".codex/agents/r.toml" in [f["path"] for f in manifest["files"]]


def test_manifest_reports_the_slice_size_the_skill_batches_by():
    manifest = _plan(["a.py"], tree={"a.py": b"1"})
    assert manifest["max_slice_bytes"] == M.DEFAULT_MAX_SLICE_BYTES


def test_symlink_or_deleted_mirror_is_never_collapsed():
    tree = {"plugins/git-kit/skills/a/SKILL.md": b"s"}  # mirror absent from tree: reader gives None
    assert _plan([".claude/skills/a/SKILL.md"], tree=tree)["excluded"] == []


# --- configured exclusions ---------------------------------------------------------------------


def test_config_dir_extension_glob_and_lockfile_exclusions():
    config = _config(dirs=["issues/"], extensions=[".svg"], globs=["docs/**/*.snap"])
    files = [
        "issues/1.md",
        "img/a.svg",
        "docs/x/y.snap",
        "uv.lock",
        "pyproject.toml",
        "src/keep.py",
    ]
    manifest = _plan(files, config=config)
    assert _reasons(manifest) == {
        "issues/1.md": "config-dir",
        "img/a.svg": "config-extension",
        "docs/x/y.snap": "config-glob",
        "uv.lock": "lockfile",
    }
    assert sorted(f["path"] for f in manifest["files"]) == ["pyproject.toml", "src/keep.py"]


def test_dir_exclusion_is_repo_root_anchored():
    manifest = _plan(["issues/a.md", "plugins/x/issues/a.md"], config=_config(dirs=["issues/"]))
    assert _reasons(manifest) == {"issues/a.md": "config-dir"}


def test_run_pick_excludes_a_folder_for_this_run():
    manifest = _plan([".claude/rules/r.md", "src/a.py"], picks=[".claude/"])
    assert _reasons(manifest) == {".claude/rules/r.md": "run-pick"}


@pytest.mark.parametrize(
    "path",
    [
        "plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs",
        "plugins/codex-kit/scripts/lib/codex-exec.mjs",
        "plugins/git-kit/git-kit.settings.json",
        ".claude/git-kit.local.json",
        "plugins/git-kit/skills/cross-model-review/prompts/review.md",
        "plugins/git-kit/scripts/git-review-scope.py",
        ".claude/marketplace-sync.json",
    ],
)
def test_protected_paths_cannot_be_excluded_by_config_pick_or_extension(path):
    config = _config(dirs=["plugins/"], extensions=[".json", ".mjs", ".md", ".py"])
    manifest = _plan([path], config=config, picks=["plugins/", ".claude/"])
    assert manifest["excluded"] == []
    assert [f["path"] for f in manifest["files"]] == [path]
    assert any("exclusion refused" in line for line in manifest["inspection_limits"])


def test_every_exclusion_is_disclosed_in_inspection_limits():
    manifest = _plan(["issues/1.md", "uv.lock", "pyproject.toml"], config=_config(dirs=["issues/"]))
    text = "\n".join(manifest["inspection_limits"])
    assert "config-dir" in text and "issues/1.md" in text
    assert "lockfile" in text and "uv.lock" in text


# --- config loading ----------------------------------------------------------------------------


def test_local_config_only_adds_to_tracked_lists():
    tracked = json.dumps({"cross_model_review_exclude_dirs": ["a/"]})
    local = json.dumps(
        {"cross_model_review_exclude_dirs": ["b"], "cross_model_review_budget_bytes": 1}
    )
    config = M.load_config(tracked, local, False)
    assert config["dirs"] == ["a/", "b/"]
    assert config["budget_bytes"] == M.DEFAULT_BUDGET_BYTES  # numeric keys come from tracked only


def test_tracked_local_config_is_ignored_and_disclosed():
    local = json.dumps({"cross_model_review_exclude_dirs": ["plugins/"]})
    config = M.load_config(None, local, True)
    assert config["dirs"] == M.DEFAULT_EXCLUDE_DIRS
    assert any("tracked by git" in n for n in config["notes"])


def test_invalid_entries_are_dropped_with_a_note():
    tracked = json.dumps(
        {
            "cross_model_review_exclude_dirs": ["/abs/", "../up/", "ok/", 5, ""],
            "cross_model_review_exclude_extensions": ["svg", ".PNG"],
            "cross_model_review_exclude_globs": "not-a-list",
            "cross_model_review_budget_bytes": True,
        }
    )
    config = M.load_config(tracked, None, False)
    assert config["dirs"] == ["ok/"]
    assert config["extensions"] == [".png"]
    assert config["globs"] == []
    assert config["budget_bytes"] == M.DEFAULT_BUDGET_BYTES
    assert len([n for n in config["notes"] if "ignored" in n]) >= 5


def test_unreadable_tracked_settings_fall_back_to_defaults():
    config = M.load_config("{not json", None, False)
    assert config["dirs"] == M.DEFAULT_EXCLUDE_DIRS
    assert config["budget_bytes"] == M.DEFAULT_BUDGET_BYTES
    assert any("unreadable" in n for n in config["notes"])


def test_built_in_dirs_apply_only_while_the_tracked_key_is_absent():
    assert M.load_config(None, None, False)["dirs"] == ["issues/"]
    assert M.load_config("{}", None, False)["dirs"] == ["issues/"]
    explicit = json.dumps({"cross_model_review_exclude_dirs": []})
    assert M.load_config(explicit, None, False)["dirs"] == []
    local = json.dumps({"cross_model_review_exclude_dirs": ["x/"]})
    assert M.load_config(explicit, local, False)["dirs"] == ["x/"]


# --- slicing and budget ------------------------------------------------------------------------


def test_files_are_grouped_by_risk_class():
    files = ["a.py", "settings.json", "tests/t.py", "README.md", "data.yaml"]
    classes = {f["path"]: f["class"] for f in _plan(files)["files"]}
    assert classes == {
        "a.py": "scripts",
        "settings.json": "grants",
        "tests/t.py": "tests",
        "README.md": "prose",
        "data.yaml": "other",
    }


def test_slices_split_at_the_max_slice_size():
    files = ["a.py", "b.py", "c.py"]
    manifest = _plan(files, config=_config(max_slice_bytes=250), sizes={f: 100 for f in files})
    assert [s["files"] for s in manifest["slices"]] == [["a.py", "b.py"], ["c.py"]]
    assert [s["name"] for s in manifest["slices"]] == ["scripts", "scripts-2"]


def test_over_budget_slices_are_dropped_by_priority_and_disclosed():
    files = ["a.py", "README.md"]
    manifest = _plan(files, config=_config(budget_bytes=150), sizes={"a.py": 100, "README.md": 100})
    assert [f["path"] for f in manifest["files"]] == ["a.py"]
    assert [s["name"] for s in manifest["dropped_slices"]] == ["prose"]
    assert any("reduced scope" in n and "README.md" in n for n in manifest["inspection_limits"])


def test_first_slice_is_kept_even_when_it_alone_exceeds_the_budget():
    manifest = _plan(["big.py"], config=_config(budget_bytes=10), sizes={"big.py": 500})
    assert [f["path"] for f in manifest["files"]] == ["big.py"]
    assert manifest["dropped_slices"] == []


def test_the_oversized_first_slice_exception_applies_only_when_nothing_else_is_chosen():
    # Deliberate: with a protected slice chosen, an oversized slice must fit the budget (a padding
    # file cannot be kept free of it), it is dropped, and the drop is disclosed.
    files = ["plugins/codex-kit/scripts/a.mjs", "big.py", "later.py"]
    sizes = {"plugins/codex-kit/scripts/a.mjs": 1, "big.py": 500, "later.py": 5}
    manifest = _plan(files, config=_config(budget_bytes=10, max_slice_bytes=500), sizes=sizes)
    kept = sorted(f["path"] for f in manifest["files"])
    assert kept == ["later.py", "plugins/codex-kit/scripts/a.mjs"]
    assert [s["name"] for s in manifest["dropped_slices"]] == ["scripts"]
    assert any("reduced scope" in n and "big.py" in n for n in manifest["inspection_limits"])


def test_candidate_dirs_report_remaining_bytes_largest_first():
    manifest = _plan(
        ["a/x.py", "b/y.py", "root.py"], sizes={"a/x.py": 10, "b/y.py": 99, "root.py": 5}
    )
    assert manifest["candidate_dirs"] == [
        {"dir": "b/", "files": 1, "bytes": 99},
        {"dir": "a/", "files": 1, "bytes": 10},
    ]


# --- round two ---------------------------------------------------------------------------------


def _loaded(manifest, completed=None):
    """The manifest as the next round sees it, with the given (default: all) slices finished."""
    names = [s["name"] for s in manifest["slices"]] if completed is None else completed
    prior, why = M.load_prior(json.dumps(manifest), "mb", names)
    assert why is None, why
    return prior


def _round_one(tree):
    return _loaded(_plan(list(tree), tree=tree))


def test_round_two_reviews_only_files_changed_since_round_one():
    before = {"a.py": b"1", "b.py": b"1"}
    prior = _round_one(before)
    after = {"a.py": b"1", "b.py": b"2", "c.py": b"new"}
    manifest = _plan(list(after), tree=after, prior=prior)
    assert manifest["round"] == 2
    assert sorted(f["path"] for f in manifest["files"]) == ["b.py", "c.py"]
    assert _reasons(manifest) == {"a.py": "unchanged-since-prior-round"}


def test_recheck_forces_an_unchanged_file_back_in():
    tree = {"a.py": b"1", "b.py": b"1"}
    manifest = _plan(list(tree), tree=tree, prior=_round_one(tree), recheck=["a.py"])
    assert [f["path"] for f in manifest["files"]] == ["a.py"]


def test_round_two_does_not_lift_a_config_exclusion():
    tree = {"issues/1.md": b"1"}
    config = _config(dirs=["issues/"])
    manifest = _plan(list(tree), tree=tree, config=config, prior=_round_one(tree))
    assert _reasons(manifest) == {"issues/1.md": "config-dir"}


def _prior_json(**overrides):
    data = {
        "version": M.MANIFEST_VERSION,
        "round": 1,
        "base": "mb",
        "slices": [],
        "planned_hashes": {},
        "carried_hashes": {},
    }
    data.update(overrides)
    return json.dumps(data)


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("{nope", "not valid JSON"),
        (json.dumps([]), "unsupported"),
        (_prior_json(version=1), "unsupported"),
        (_prior_json(round=0), "round"),
        (_prior_json(planned_hashes={"a": 1}), "reviewed hashes"),
        (_prior_json(carried_hashes=[]), "reviewed hashes"),
        (_prior_json(slices="x"), "reviewed hashes"),
        (_prior_json(slices=[5]), "slices"),
        (_prior_json(base="other"), "merge-base"),
    ],
)
def test_bad_prior_manifest_falls_back_to_full_scope(text, reason):
    prior, fallback = M.load_prior(text, "mb")
    assert prior is None and reason in fallback
    tree = {"a.py": b"1"}
    manifest = _plan(list(tree), tree=tree, prior=prior, fallback=fallback)
    assert manifest["round"] == 1
    assert [f["path"] for f in manifest["files"]] == ["a.py"]
    assert any("full scope reviewed" in n for n in manifest["inspection_limits"])


def test_valid_prior_manifest_loads():
    prior, fallback = M.load_prior(_prior_json(round=3, carried_hashes={"a": "h"}), "mb")
    assert fallback is None and prior["round"] == 3 and prior["reviewed_hashes"] == {"a": "h"}


# --- end to end against a real repository ------------------------------------------------------


def _git(repo, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path, monkeypatch):
    # The developer's global git config (ignore rules, hooks) must not leak into the fixture repo.
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    root = tmp_path / "repo"
    (root / "plugins/git-kit").mkdir(parents=True)
    (root / ".claude").mkdir()
    settings = {"cross_model_review_exclude_dirs": ["issues/"]}
    (root / SETTINGS_REL).write_text(json.dumps(settings))
    (root / ".claude/marketplace-sync.json").write_text(
        json.dumps({"plugin_mirrors": ["git-kit"], "scripts_mirrors": ["git-kit"]})
    )
    _git(root.parent, "init", "-q", "-b", "main", str(root))
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    return root


SETTINGS_REL = "plugins/git-kit/git-kit.settings.json"


def _run(repo, out, *extra):
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            str(repo),
            "--merge-base",
            base,
            "--output",
            str(out),
            *extra,
        ],
        capture_output=True,
        text=True,
    )


def test_end_to_end_excludes_configured_dir_and_collapses_mirror(repo, tmp_path):
    (repo / "issues").mkdir()
    (repo / "issues/1.md").write_text("noise")
    (repo / "plugins/git-kit/scripts").mkdir()
    (repo / "plugins/git-kit/scripts/x.py").write_text("print(1)\n")
    (repo / ".claude/scripts").mkdir()
    (repo / ".claude/scripts/x.py").write_text("print(1)\n")
    _git(repo, "add", "-N", "-A")
    out = tmp_path / "m1.json"
    result = _run(repo, out)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(out.read_text())
    assert [f["path"] for f in manifest["files"]] == ["plugins/git-kit/scripts/x.py"]
    assert _reasons(manifest) == {
        "issues/1.md": "config-dir",
        ".claude/scripts/x.py": "mirror-identical",
    }
    assert out.stat().st_mode & 0o777 == 0o600


def test_end_to_end_settings_come_from_base_not_the_working_tree(repo, tmp_path):
    (repo / SETTINGS_REL).write_text(json.dumps({"cross_model_review_exclude_dirs": ["src/"]}))
    (repo / "src").mkdir()
    (repo / "src/a.py").write_text("x")
    _git(repo, "add", "-N", "-A")
    out = tmp_path / "m.json"
    assert _run(repo, out).returncode == 0
    manifest = json.loads(out.read_text())
    assert "src/a.py" in [f["path"] for f in manifest["files"]]  # the diff's own exclusion is inert


def test_end_to_end_tracked_local_config_is_ignored(repo, tmp_path):
    (repo / ".claude/git-kit.local.json").write_text(
        json.dumps({"cross_model_review_exclude_dirs": ["src/"]})
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "tracked local")
    (repo / "src").mkdir()
    (repo / "src/a.py").write_text("x")
    _git(repo, "add", "-N", "-A")
    out = tmp_path / "m.json"
    assert _run(repo, out).returncode == 0
    manifest = json.loads(out.read_text())
    assert [f["path"] for f in manifest["files"]] == ["src/a.py"]
    assert any("tracked by git" in n for n in manifest["inspection_limits"])


def test_end_to_end_untracked_local_config_adds_exclusions(repo, tmp_path):
    (repo / ".claude/git-kit.local.json").write_text(
        json.dumps({"cross_model_review_exclude_dirs": ["src/"]})
    )
    (repo / "src").mkdir()
    (repo / "src/a.py").write_text("x")
    _git(repo, "add", "-N", "src")
    out = tmp_path / "m.json"
    assert _run(repo, out).returncode == 0
    assert _reasons(json.loads(out.read_text())) == {"src/a.py": "config-dir"}


def test_end_to_end_round_two_and_missing_prior_fallback(repo, tmp_path):
    (repo / "a.py").write_text("1")
    (repo / "b.py").write_text("1")
    _git(repo, "add", "-N", "-A")
    first = tmp_path / "r1.json"
    assert _run(repo, first).returncode == 0
    (repo / "b.py").write_text("2")
    second = tmp_path / "r2.json"
    assert (
        _run(
            repo, second, "--prior-manifest", str(first), "--completed-slice", "scripts"
        ).returncode
        == 0
    )
    manifest = json.loads(second.read_text())
    assert manifest["round"] == 2
    assert [f["path"] for f in manifest["files"]] == ["b.py"]
    third = tmp_path / "r3.json"
    assert _run(repo, third, "--prior-manifest", str(tmp_path / "missing.json")).returncode == 0
    fallback = json.loads(third.read_text())
    assert fallback["round"] == 1 and "not a regular file" in fallback["fallback"]


def test_existing_output_is_never_overwritten(repo, tmp_path):
    out = tmp_path / "taken.json"
    out.write_text("keep me")
    result = _run(repo, out)
    assert result.returncode == 2 and "already exists" in result.stderr
    assert out.read_text() == "keep me"


def test_symlink_output_is_refused(repo, tmp_path):
    target = tmp_path / "target.json"
    target.write_text("keep me")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    assert _run(repo, link).returncode == 2
    assert target.read_text() == "keep me"


def test_invalid_run_pick_is_refused(repo, tmp_path):
    result = _run(repo, tmp_path / "m.json", "--exclude-dir", "../outside")
    assert result.returncode == 2 and "invalid entry" in result.stderr


def test_unknown_merge_base_is_a_could_not_run_not_an_empty_scope(repo, tmp_path):
    result = _run_with_base(repo, "0" * 40, tmp_path / "m.json")
    assert result.returncode == 2 and "git diff failed" in result.stderr


def _run_with_base(repo, base, out, *extra):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            str(repo),
            "--merge-base",
            base,
            "--output",
            str(out),
            *extra,
        ],
        capture_output=True,
        text=True,
    )


# --- findings from the security review (C1, M1-M7, minor) --------------------------------------


def test_mirror_is_not_collapsed_when_canonical_is_neither_in_the_diff_nor_on_the_base():
    tree = {"plugins/git-kit/skills/a/SKILL.md": b"s", ".claude/skills/a/SKILL.md": b"s"}
    only_mirror = [".claude/skills/a/SKILL.md"]
    assert _plan(only_mirror, tree=tree)["excluded"] == []  # canonical unreviewed: keep the mirror
    manifest = _plan(only_mirror, tree=tree, base_read=lambda p: tree.get(p))
    assert _reasons(manifest) == {".claude/skills/a/SKILL.md": "mirror-identical"}


def test_reader_never_reads_through_a_symlinked_parent_directory(tmp_path):
    (tmp_path / "real").mkdir()
    (tmp_path / "real/f.txt").write_text("secret")
    (tmp_path / "link").symlink_to("real")
    (tmp_path / "plain.txt").write_text("ok")
    read = M._make_reader(tmp_path)
    assert read("plain.txt") == b"ok"
    assert read("link/f.txt") is None
    assert read("real/f.txt") == b"secret"
    assert read("../outside") is None


def test_end_to_end_directory_symlink_cannot_launder_a_malicious_mirror(repo, tmp_path):
    (repo / "plugins/git-kit/skills").mkdir()
    (repo / ".claude/skills/new").mkdir(parents=True)
    (repo / ".claude/skills/new/SKILL.md").write_text("EVIL\n")
    (repo / "plugins/git-kit/skills/new").symlink_to("../../../.claude/skills/new")
    _git(repo, "add", "-A")
    out = tmp_path / "m.json"
    assert _run(repo, out).returncode == 0
    manifest = json.loads(out.read_text())
    assert ".claude/skills/new/SKILL.md" in [f["path"] for f in manifest["files"]]
    assert manifest["excluded"] == []


def test_end_to_end_rename_lists_the_removed_path_too(repo, tmp_path):
    (repo / "src").mkdir()
    (repo / "src/auth.py").write_text("def check():\n    return verify()\n" * 20)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "add auth")
    (repo / "moved").mkdir()
    _git(repo, "mv", "src/auth.py", "moved/auth.py")
    out = tmp_path / "m.json"
    assert _run(repo, out).returncode == 0
    paths = [f["path"] for f in json.loads(out.read_text())["files"]]
    assert "src/auth.py" in paths and "moved/auth.py" in paths


def test_end_to_end_gitattributes_cannot_hide_content_and_is_flagged(repo, tmp_path):
    (repo / "p.py").write_text("print(1)\n" * 50)
    (repo / ".gitattributes").write_text("*.py -diff\n")
    _git(repo, "add", "-N", "-A")
    out = tmp_path / "m.json"
    assert _run(repo, out).returncode == 0
    manifest = json.loads(out.read_text())
    sizes = {f["path"]: f["bytes"] for f in manifest["files"]}
    assert sizes["p.py"] > 400  # measured as text, not "Binary files differ"
    assert any(".gitattributes changed" in n for n in manifest["inspection_limits"])
    assert M.classify(".gitattributes") == "protected"


def test_protected_files_are_kept_ahead_of_the_budget():
    files = ["aaa/hooks/pad.json", "plugins/codex-kit/scripts/lib/codex-exec.mjs", "z.md"]
    sizes = {"aaa/hooks/pad.json": 500, files[1]: 400, "z.md": 10}
    manifest = _plan(files, config=_config(budget_bytes=450), sizes=sizes)
    kept = [f["path"] for f in manifest["files"]]
    assert files[1] in kept
    assert "aaa/hooks/pad.json" not in kept
    assert any("reduced scope" in n for n in manifest["inspection_limits"])


def test_classification_resists_padding_and_covers_executed_test_files():
    assert M.classify("aaa/hooks/pad.txt") == "prose"  # not a grant, lowest priority
    assert M.classify("x/hooks/run.sh") == "grants"
    assert M.classify("tests/conftest.py") == "scripts"
    assert M.classify("tests/test_a.py") == "tests"


def test_protected_match_is_case_insensitive():
    manifest = _plan(
        [".claude/Git-Kit.Local.json"], config=_config(dirs=[".claude/"]), picks=[".claude/"]
    )
    assert manifest["excluded"] == []


def test_lockfile_alone_is_kept_and_disclosed_but_excluded_with_its_manifest():
    alone = _plan(["uv.lock", "a/package-lock.json"])
    assert alone["excluded"] == []
    assert any("lockfile(s) kept for review" in n for n in alone["inspection_limits"])
    paired = _plan(["a/package-lock.json", "a/package.json", "uv.lock", "pyproject.toml"])
    assert _reasons(paired) == {"a/package-lock.json": "lockfile", "uv.lock": "lockfile"}
    sibling_elsewhere = _plan(["a/package-lock.json", "b/package.json"])
    assert _reasons(sibling_elsewhere) == {}


def test_round_two_reviews_files_dropped_by_the_budget_in_round_one():
    tree = {"a.py": b"1", "README.md": b"1"}
    sizes = {"a.py": 100, "README.md": 100}
    one = _plan(list(tree), tree=tree, config=_config(budget_bytes=150), sizes=sizes)
    assert list(one["planned_hashes"]) == ["a.py"]
    two = _plan(list(tree), tree=tree, prior=_loaded(one))
    assert sorted(f["path"] for f in two["files"]) == ["README.md"]
    assert _reasons(two) == {"a.py": "unchanged-since-prior-round"}


def test_round_two_reviews_files_a_run_pick_hid_in_round_one():
    tree = {"notes/1.md": b"1", "a.py": b"1"}
    one = _plan(list(tree), tree=tree, picks=["notes/"])
    two = _plan(list(tree), tree=tree, prior=_loaded(one))
    assert sorted(f["path"] for f in two["files"]) == ["notes/1.md"]


def test_reviewed_hashes_carry_forward_so_round_three_skips_round_one_files_too():
    tree = {"a.py": b"1", "b.py": b"1"}
    one = _plan(list(tree), tree=tree)
    tree["b.py"] = b"2"
    two = _plan(list(tree), tree=tree, prior=_loaded(one))
    three = _plan(list(tree), tree=tree, prior=_loaded(two))
    assert three["files"] == []
    assert set(three["carried_hashes"]) == {"a.py", "b.py"}


def test_unreadable_fingerprint_is_never_skipped():
    prior = {"round": 1, "reviewed_hashes": {"a.py": "unreadable"}}
    manifest = _plan(["a.py"], prior=prior, fingerprint=lambda _p: "unreadable")
    assert [f["path"] for f in manifest["files"]] == ["a.py"]


def test_fingerprint_sees_symlink_target_mode_and_deletion(tmp_path):
    fp = M._make_fingerprint(tmp_path)
    (tmp_path / "f").write_text("x")
    plain = fp("f")
    (tmp_path / "f").chmod(0o755)
    assert fp("f") != plain  # mode-only change
    (tmp_path / "l").symlink_to("one")
    first = fp("l")
    (tmp_path / "l").unlink()
    (tmp_path / "l").symlink_to("two")
    assert fp("l") != first  # retargeted symlink
    assert fp("l") != fp("missing") == "deleted"


@pytest.fixture
def plain_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    root = tmp_path / "pr"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    (root / ".claude").mkdir()
    (root / ".claude/keep").write_text("k")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "b")
    return root


def _head(repo):
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def test_local_config_untracked_real_file_is_trusted(plain_repo):
    (plain_repo / ".claude/git-kit.local.json").write_text("{}")
    assert M._local_config(plain_repo, _head(plain_repo), []) == ("{}", False)


def test_local_config_absent_is_neither_text_nor_untrusted(plain_repo):
    assert M._local_config(plain_repo, _head(plain_repo), []) == (None, False)


def test_local_config_tracked_in_the_index_or_in_the_diff_is_untrusted(plain_repo):
    (plain_repo / ".claude/git-kit.local.json").write_text("{}")
    assert M._local_config(plain_repo, _head(plain_repo), [".claude/git-kit.local.json"])[1]
    _git(plain_repo, "add", "-f", ".claude/git-kit.local.json")
    assert M._local_config(plain_repo, _head(plain_repo), [])[1]


def test_local_config_case_variant_tracked_by_git_is_untrusted(plain_repo):
    (plain_repo / ".claude/Git-Kit.local.json").write_text("{}")
    _git(plain_repo, "add", "-f", ".claude/Git-Kit.local.json")
    _git(plain_repo, "commit", "-q", "-m", "variant")
    (plain_repo / ".claude/git-kit.local.json").write_text("{}")
    assert M._local_config(plain_repo, _head(plain_repo), [])[1]


def test_local_config_behind_a_symlink_is_untrusted(plain_repo, tmp_path):
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "elsewhere/git-kit.local.json").write_text("{}")
    (plain_repo / ".claude/git-kit.local.json").symlink_to(
        tmp_path / "elsewhere/git-kit.local.json"
    )
    assert M._local_config(plain_repo, _head(plain_repo), []) == ("", True)


def test_local_config_is_untrusted_when_git_cannot_answer(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude/git-kit.local.json").write_text("{}")
    assert M._local_config(tmp_path, "0" * 40, [])[1]  # not a git repository: fail closed


def test_git_timeout_is_a_failed_command_not_a_crash(monkeypatch, tmp_path):
    def boom(*_a, **_k):
        raise subprocess.TimeoutExpired("git", 1)

    monkeypatch.setattr(M.subprocess, "run", boom)
    assert M._git(tmp_path, "status").returncode == 124


def test_deeply_nested_json_is_rejected_not_a_crash():
    deep = "[" * 100_000
    assert M.load_prior(deep, "mb")[0] is None
    assert "unreadable" in "".join(M.load_config(deep, None, False)["notes"])


@pytest.mark.parametrize("base", ["main", "ABCDEF" * 7, "abc123"])
def test_merge_base_must_be_a_full_lowercase_sha(repo, tmp_path, base):
    result = _run_with_base(repo, base, tmp_path / "m.json")
    assert result.returncode == 2 and "invalid --merge-base" in result.stderr


def test_pathspec_magic_in_scope_is_refused_and_a_plain_scope_is_disclosed(repo, tmp_path):
    refused = _run(repo, tmp_path / "a.json", "--scope", ":(exclude)plugins/codex-kit")
    assert refused.returncode == 2 and "pathspec magic" in refused.stderr
    (repo / "src").mkdir()
    (repo / "src/a.py").write_text("x")
    _git(repo, "add", "-N", "-A")
    out = tmp_path / "b.json"
    assert _run(repo, out, "--scope", "src").returncode == 0
    assert any("scope limited" in n for n in json.loads(out.read_text())["inspection_limits"])


def test_unresolvable_base_ref_falls_back_to_defaults_and_says_so(repo, tmp_path):
    out = tmp_path / "m.json"
    assert _run(repo, out, "--base-ref", "no-such-ref").returncode == 0
    limits = "\n".join(json.loads(out.read_text())["inspection_limits"])
    assert "built-in defaults" in limits and "mirror collapsing disabled" in limits


def test_glob_does_not_match_a_path_with_a_trailing_newline():
    config = _config(globs=["docs/*.snap"])
    manifest = _plan(["docs/a.snap\n"], config=config)
    assert manifest["excluded"] == []


def test_slices_beyond_nine_keep_numeric_order_when_the_budget_drops():
    files = [f"f{i:02d}.py" for i in range(12)]
    manifest = _plan(
        files, config=_config(max_slice_bytes=100, budget_bytes=300), sizes={f: 100 for f in files}
    )
    assert [s["index"] for s in manifest["slices"]] == [1, 2, 3]
    assert len(manifest["dropped_slices"]) == 9


def test_malformed_mirror_map_is_disclosed_and_never_crashes():
    sync = M.parse_sync(json.dumps({"divergence_exceptions": 5, "plugin_mirrors": ["../x", "ok"]}))
    assert sync["plugin_mirrors"] == ["ok"]
    assert any("divergence_exceptions" in n for n in sync["notes"])
    assert any("disabled" in n for n in M.parse_sync(None)["notes"])


def test_every_protected_slice_survives_the_budget_not_only_the_first():
    files = [
        "plugins/codex-kit/scripts/a.mjs",
        "plugins/codex-kit/scripts/b.mjs",
        "plugins/codex-kit/scripts/c.mjs",
    ]
    manifest = _plan(
        files,
        config=_config(max_slice_bytes=100, budget_bytes=150),
        sizes={f: 100 for f in files},
    )
    assert sorted(f["path"] for f in manifest["files"]) == files
    assert manifest["dropped_slices"] == []


# --- findings from the second security review --------------------------------------------------


def test_mirror_is_put_back_when_its_canonical_is_picked_out_by_the_user():
    tree = {"plugins/git-kit/scripts/x.py": b"s", ".claude/scripts/x.py": b"s"}
    manifest = _plan(list(tree), tree=tree, picks=["plugins/"])
    assert _reasons(manifest) == {"plugins/git-kit/scripts/x.py": "run-pick"}
    assert [f["path"] for f in manifest["files"]] == [".claude/scripts/x.py"]


def test_mirror_is_put_back_when_the_budget_drops_its_canonical():
    tree = {
        "plugins/git-kit/scripts/x.py": b"s",
        ".claude/scripts/x.py": b"s",
        "settings.json": b"{}",
    }
    sizes = {"settings.json": 100, "plugins/git-kit/scripts/x.py": 100, ".claude/scripts/x.py": 100}
    manifest = _plan(list(tree), tree=tree, config=_config(budget_bytes=150), sizes=sizes)
    assert "mirror-identical" not in _reasons(manifest).values()
    dropped = [p for s in manifest["dropped_slices"] for p in s["files"]]
    assert ".claude/scripts/x.py" in dropped and "plugins/git-kit/scripts/x.py" in dropped


def test_mirror_stays_collapsed_when_the_base_already_holds_the_same_bytes():
    tree = {"plugins/git-kit/scripts/x.py": b"s", ".claude/scripts/x.py": b"s"}
    manifest = _plan(
        [".claude/scripts/x.py"], tree=tree, base_read=lambda p: tree.get(p), picks=["plugins/"]
    )
    assert _reasons(manifest) == {".claude/scripts/x.py": "mirror-identical"}


def test_agents_export_collapses_through_either_reviewed_canonical():
    tree = {
        "plugins/git-kit/skills/a/SKILL.md": b"s",
        ".claude/skills/a/SKILL.md": b"s",
        ".agents/skills/a/SKILL.md": b"s",
    }
    manifest = _plan(list(tree), tree=tree)
    assert sorted(_reasons(manifest)) == [".agents/skills/a/SKILL.md", ".claude/skills/a/SKILL.md"]
    assert [f["path"] for f in manifest["files"]] == ["plugins/git-kit/skills/a/SKILL.md"]


def test_lockfile_is_kept_when_its_manifest_is_not_reviewed_this_round():
    files = ["pyproject.toml", "uv.lock"]
    excluded_manifest = _plan(files, config=_config(extensions=[".toml"]))
    assert _reasons(excluded_manifest) == {"pyproject.toml": "config-extension"}
    assert [f["path"] for f in excluded_manifest["files"]] == ["uv.lock"]
    tree = {f: b"1" for f in files}
    round_one = _loaded(_plan(files, tree=tree))
    tree["uv.lock"] = b"swapped"
    round_two = _plan(files, tree=tree, prior=round_one)
    assert _reasons(round_two) == {"pyproject.toml": "unchanged-since-prior-round"}
    assert [f["path"] for f in round_two["files"]] == ["uv.lock"]  # an old manifest excuses nothing


def test_lockfile_is_put_back_when_the_budget_drops_its_manifest():
    files = ["settings.json", "pyproject.toml", "uv.lock"]
    manifest = _plan(files, config=_config(budget_bytes=150), sizes={f: 100 for f in files})
    assert "lockfile" not in _reasons(manifest).values()


def test_unfinished_slices_are_reviewed_again_and_finished_ones_are_not():
    tree = {"a.py": b"1", "README.md": b"1"}
    one = _plan(list(tree), tree=tree)
    none_done = _plan(list(tree), tree=tree, prior=_loaded(one, completed=[]))
    assert sorted(f["path"] for f in none_done["files"]) == ["README.md", "a.py"]
    scripts_done = _plan(list(tree), tree=tree, prior=_loaded(one, completed=["scripts"]))
    assert [f["path"] for f in scripts_done["files"]] == ["README.md"]
    unknown = _plan(list(tree), tree=tree, prior=_loaded(one, completed=["no-such-slice"]))
    assert len(unknown["files"]) == 2


def test_other_and_unreadable_fingerprints_are_never_skipped():
    prior = {"round": 1, "reviewed_hashes": {"sub": "other"}}
    manifest = _plan(["sub"], prior=prior, fingerprint=lambda _p: "other")
    assert [f["path"] for f in manifest["files"]] == ["sub"]


def test_fingerprint_of_a_directory_is_other(tmp_path):
    (tmp_path / "sub").mkdir()
    assert M._make_fingerprint(tmp_path)("sub") == "other"


def test_fingerprint_behind_a_symlinked_parent_is_unreadable(tmp_path):
    (tmp_path / "real").mkdir()
    (tmp_path / "real/f.py").write_text("x")
    (tmp_path / "a").symlink_to("real")
    assert M._make_fingerprint(tmp_path)("a/f.py") == "unreadable"


def test_gitmodules_is_protected_and_flagged():
    assert M.classify(".gitmodules") == "protected"
    manifest = _plan([".gitmodules"], config=_config(dirs=[".git"], extensions=[".gitmodules"]))
    assert ".gitmodules changed" in "\n".join(manifest["inspection_limits"])


def test_end_to_end_submodule_pointer_bump_is_not_hidden_by_ignore_all(repo, tmp_path):
    (repo / ".gitmodules").write_text(
        '[submodule "sub"]\n\tpath = sub\n\turl = x\n\tignore = all\n'
    )
    _git(repo, "add", ".gitmodules")
    _git(repo, "update-index", "--add", "--cacheinfo", f"160000,{'a' * 40},sub")
    _git(repo, "commit", "-q", "-m", "submodule")
    _git(repo, "update-index", "--cacheinfo", f"160000,{'b' * 40},sub")
    out = tmp_path / "m.json"
    assert _run(repo, out).returncode == 0
    assert "sub" in [f["path"] for f in json.loads(out.read_text())["files"]]


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("plugins/x/skills/s/SKILL.md", "grants"),
        ("plugins/x/agents/a.md", "grants"),
        ("plugins/x/commands/c.md", "grants"),
        (".claude/rules/r.md", "grants"),
        ("CLAUDE.md", "grants"),
        ("sub/AGENTS.md", "grants"),
        (".mcp.json", "grants"),
        (".pre-commit-config.yaml", "grants"),
        (".github/actions/a/action.yml", "grants"),
        ("docs/guide.md", "prose"),
    ],
)
def test_permission_carrying_files_are_grants(path, expected):
    assert M.classify(path) == expected


def test_executable_extensionless_file_is_a_script_but_a_plain_one_is_not():
    assert M.classify("hooks/guard", executable=True) == "scripts"
    assert M.classify("data/blob") == "other"


def test_bridge_mirror_under_claude_is_protected_from_a_folder_pick():
    path = ".claude/skills/codex-review-bridge/scripts/bridge-invoke.mjs"
    manifest = _plan([path], picks=[".claude/"])
    assert manifest["excluded"] == [] and M.classify(path) == "protected"


def test_protected_bytes_do_not_count_against_the_budget():
    files = ["plugins/codex-kit/scripts/a.mjs", "b.py"]
    manifest = _plan(
        files,
        config=_config(budget_bytes=150),
        sizes={"plugins/codex-kit/scripts/a.mjs": 900, "b.py": 100},
    )
    assert sorted(f["path"] for f in manifest["files"]) == sorted(files)
    assert manifest["dropped_slices"] == []


def test_plugin_names_dot_and_dotdot_are_rejected_in_the_mirror_map():
    sync = M.parse_sync(json.dumps({"plugin_mirrors": [".", "..", "ok"]}))
    assert sync["plugin_mirrors"] == ["ok"]


def test_unknown_diff_size_is_disclosed_and_counts_as_zero():
    manifest = _plan(["a.py"], sizes={"a.py": -1})
    assert [f["bytes"] for f in manifest["files"]] == [0]
    assert any("diff size unknown" in n for n in manifest["inspection_limits"])


def test_local_exclusions_are_labelled_and_announced():
    local = json.dumps({"cross_model_review_exclude_dirs": ["scratch/"]})
    tracked = json.dumps({"cross_model_review_exclude_dirs": ["issues/"]})
    config = M.load_config(tracked, local, False)
    manifest = _plan(["scratch/a.md", "issues/b.md"], config=config)
    assert {e["path"]: e["detail"] for e in manifest["excluded"]} == {
        "scratch/a.md": "scratch/ (local)",
        "issues/b.md": "issues/",
    }
    assert any("local config applied" in n for n in config["notes"])


def test_local_config_case_variant_in_head_is_untrusted_even_with_a_narrow_scope(plain_repo):
    (plain_repo / ".CLAUDE").mkdir()
    (plain_repo / ".CLAUDE/Git-Kit.Local.json").write_text("{}")
    _git(plain_repo, "add", "-f", ".CLAUDE")
    _git(plain_repo, "commit", "-q", "-m", "variant")
    (plain_repo / ".claude/git-kit.local.json").write_text("{}")
    assert M._local_config(plain_repo, _head(plain_repo), [])[1]


def test_prior_manifest_inside_the_repository_is_refused(repo, tmp_path):
    (repo / "a.py").write_text("1")
    _git(repo, "add", "-N", "-A")
    first = tmp_path / "r1.json"
    assert _run(repo, first).returncode == 0
    inside = repo / "r1.json"
    inside.write_text(first.read_text())
    out = tmp_path / "r2.json"
    assert (
        _run(repo, out, "--prior-manifest", str(inside), "--completed-slice", "scripts").returncode
        == 0
    )
    manifest = json.loads(out.read_text())
    assert manifest["round"] == 1 and "inside the repository" in manifest["fallback"]


def test_diff_dir_gets_a_diff_per_slice_and_a_codex_variant_without_ineligible_files(
    repo, tmp_path
):
    (repo / "ok.py").write_text("print(1)\n")
    (repo / "odd name.py").write_text("print(2)\n")
    (repo / "link.py").symlink_to("ok.py")
    _git(repo, "add", "-N", "-A")
    out, diffs = tmp_path / "m.json", tmp_path / "diffs"
    assert _run(repo, out, "--diff-dir", str(diffs)).returncode == 0
    manifest = json.loads(out.read_text())
    eligible = {f["path"]: f["codex_eligible"] for f in manifest["files"]}
    assert eligible == {"ok.py": True, "odd name.py": False, "link.py": False}
    name = next(s["name"] for s in manifest["slices"] if "ok.py" in s["files"])
    full = (diffs / f"{name}.diff").read_bytes()
    codex = (diffs / f"{name}.codex.diff").read_bytes()
    assert b"odd name.py" in full and b"link.py" in full and b"ok.py" in full
    assert b"ok.py" in codex and b"odd name.py" not in codex and b"link.py" not in codex
    assert oct((diffs / f"{name}.diff").stat().st_mode & 0o777) == "0o600"


def test_a_file_named_like_pathspec_magic_still_gets_its_own_diff(repo, tmp_path):
    (repo / "plain.py").write_text("print(1)\n")
    (repo / ":(glob)payload.sh").write_text("echo hidden-payload\n")
    (repo / "star").mkdir()
    (repo / "star" / "*").write_text("echo star-payload\n")
    _git(repo, "add", "-N", "-A")
    out, diffs = tmp_path / "m.json", tmp_path / "diffs"
    assert _run(repo, out, "--diff-dir", str(diffs)).returncode == 0
    manifest = json.loads(out.read_text())
    sizes = {f["path"]: f["bytes"] for f in manifest["files"]}
    assert sizes[":(glob)payload.sh"] > 0 and sizes["star/*"] > 0
    full = [p for p in diffs.glob("*.diff") if not p.name.endswith(".codex.diff")]
    text = b"".join(p.read_bytes() for p in full)
    assert b"hidden-payload" in text and b"star-payload" in text
    assert text.count(b"print(1)") == 1  # a glob-named file must not pull in other files' diffs


def test_output_inside_the_repository_is_refused(repo, tmp_path):
    (repo / "a.py").write_text("1")
    _git(repo, "add", "-N", "-A")
    assert _run(repo, repo / "manifest.json").returncode == 2
    assert not (repo / "manifest.json").exists()


def test_diff_dir_must_be_fresh_and_outside_the_repository(repo, tmp_path):
    (repo / "a.py").write_text("1")
    _git(repo, "add", "-N", "-A")
    existing = tmp_path / "exists"
    existing.mkdir()
    assert _run(repo, tmp_path / "m1.json", "--diff-dir", str(existing)).returncode == 2
    assert _run(repo, tmp_path / "m2.json", "--diff-dir", str(repo / "diffs")).returncode == 2
    assert not (repo / "diffs").exists()


def test_prior_manifest_symlink_is_refused(repo, tmp_path):
    (repo / "a.py").write_text("1")
    _git(repo, "add", "-N", "-A")
    first = tmp_path / "r1.json"
    assert _run(repo, first).returncode == 0
    link = tmp_path / "link.json"
    link.symlink_to(first)
    out = tmp_path / "r2.json"
    assert (
        _run(repo, out, "--prior-manifest", str(link), "--completed-slice", "scripts").returncode
        == 0
    )
    assert "not a regular file" in json.loads(out.read_text())["fallback"]


def test_round_two_without_completed_slices_reviews_everything_and_says_so(repo, tmp_path):
    (repo / "a.py").write_text("1")
    _git(repo, "add", "-N", "-A")
    first = tmp_path / "r1.json"
    assert _run(repo, first).returncode == 0
    out = tmp_path / "r2.json"
    assert _run(repo, out, "--prior-manifest", str(first)).returncode == 0
    manifest = json.loads(out.read_text())
    assert [f["path"] for f in manifest["files"]] == ["a.py"]
    assert any("no --completed-slice" in n for n in manifest["inspection_limits"])


def test_local_config_variant_committed_after_the_merge_base_is_caught_with_an_empty_index(
    plain_repo, tmp_path, monkeypatch
):
    merge_base = _head(plain_repo)
    (plain_repo / ".Claude").mkdir()
    (plain_repo / ".Claude/Git-Kit.Local.json").write_text("{}")
    _git(plain_repo, "add", "-f", ".Claude")
    _git(plain_repo, "commit", "-q", "-m", "variant on the branch")
    (plain_repo / ".claude/git-kit.local.json").write_text("{}")
    # A failed index copy leaves the throwaway index without the branch's own entries.
    monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "empty-index"))
    assert M._local_config(plain_repo, merge_base, [])[1]
