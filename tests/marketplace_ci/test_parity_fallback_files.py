"""The parity wrapper skips the unsandboxed fallback when the branch changed any file that
`guarded-dispatch.mjs` runs (issue #644, cross-model review). The list is derived here from the real
import graph, so a new import in the dispatcher cannot silently escape it. Followed: static and
dynamic relative imports, `new URL("./x", import.meta.url)` reads and `path.join(SKILL_DIR, ...)`
reads (the guardrails assets). The wrapper also sees changes that are only staged or unstaged,
since the fallback runs the working tree."""

import ast
import importlib.util
import posixpath
import re
import subprocess
from pathlib import Path

import pytest

# The real resolver, captured at import: conftest's autouse fixture replaces it per test.
from scripts.marketplace_ci.review import _executable_outside_checkout as _real_resolver

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins/git-kit/scripts/git-codex-parity-review.py"
ENTRY = "plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs"
# A static `import ... from "./x.mjs"` / `import "./x.mjs"`, a dynamic `import("./x.mjs")`, and a
# run-time data read `new URL("./x.json", import.meta.url)`.
_STATIC_IMPORT = re.compile(r"""(?:from|import)\s*\(?\s*["'](\.{1,2}/[^"']+)["']""")
_URL_READ = re.compile(r"""new URL\(\s*["'](\.{1,2}/[^"']+)["']\s*,\s*import\.meta\.url""")
# `path.join(SKILL_DIR, "assets", "x.txt")`: SKILL_DIR is the skill folder, one level above the
# `scripts/` folder the dispatcher lives in (`path.resolve(SCRIPT_DIR, "..")`).
_SKILL_DIR_JOIN = re.compile(r"""path\.join\(\s*SKILL_DIR\s*((?:,\s*"[^"]+"\s*)+)\)""")


def _load_wrapper():
    spec = importlib.util.spec_from_file_location("git_codex_parity_review", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _closure(entry: str) -> set[str]:
    """Repo-relative paths of `entry` and every relative file it imports or reads, transitively."""
    seen: set[str] = set()
    pending = [entry]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        if not current.endswith(".mjs"):
            continue  # a data file has no imports of its own
        text = (REPO / current).read_text(encoding="utf-8")
        for pattern in (_STATIC_IMPORT, _URL_READ):
            for target in pattern.findall(text):
                pending.append(
                    posixpath.normpath(posixpath.join(posixpath.dirname(current), target))
                )
        skill_dir = posixpath.dirname(posixpath.dirname(current))
        for joined in _SKILL_DIR_JOIN.findall(text):
            parts = re.findall(r'"([^"]+)"', joined)
            pending.append(posixpath.normpath(posixpath.join(skill_dir, *parts)))
    return seen


def test_every_fallback_file_exists():
    from scripts.marketplace_ci import review

    assert [p for p in review.FALLBACK_FILES if not (REPO / p).is_file()] == []


def test_the_closure_finds_the_known_transitive_imports():
    """Guards the guard: if the regexes stop matching, the closure would shrink to the entry
    point and the first test would pass for the wrong reason."""
    closure = _closure(ENTRY)
    assert "plugins/codex-kit/scripts/lib/codex-exec.mjs" in closure
    assert "plugins/codex-kit/scripts/lib/cdx-process.mjs" in closure  # via codex-exec.mjs
    guardrails = "plugins/codex-kit/skills/codex-windows-guardrails/assets/"
    assert guardrails + "settings.json" in closure  # path.join(SKILL_DIR, ...) reads
    assert guardrails + "dangerous-command-instructions.txt" in closure
    assert "plugins/codex-kit/scripts/lib/cdx-token-shapes.json" in closure  # run-time data read


@pytest.mark.parametrize(
    "source",
    [
        'import { a } from "./x.mjs";',
        'import "./x.mjs";',
        'const m = await import("./x.mjs");',
        "const m = await import( './x.mjs' );",
    ],
)
def test_the_import_pattern_follows_static_and_dynamic_imports(source):
    assert _STATIC_IMPORT.findall(source) == ["./x.mjs"]


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def branch_repo(tmp_path, monkeypatch):
    """A real repository: `main` holds every protected file, `feature` is branched from it."""
    wrapper = _load_wrapper()
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    # `fallback_files_changed` hashes raw bytes, so the fixture pins LF bytes and no end-of-line
    # conversion: this repository's own `.gitattributes` (`eol=lf`) gives real checkouts the same.
    _git(repo, "config", "core.autocrlf", "false")
    from scripts.marketplace_ci import review

    for name in review.FALLBACK_FILES:
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"original\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "checkout", "-q", "-b", "feature")
    monkeypatch.chdir(repo)
    return wrapper, repo


def test_fallback_touches_is_empty_for_an_untouched_branch(branch_repo):
    wrapper, _ = branch_repo
    assert wrapper.fallback_touches("main") == []


def test_fallback_touches_sees_a_committed_edit(branch_repo):
    wrapper, repo = branch_repo
    target = wrapper.CHECKOUT_READ_FILES[0]
    (repo / target).write_text("changed\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "edit")
    assert wrapper.fallback_touches("main") == [target]


def test_fallback_touches_sees_a_staged_edit_that_is_not_committed(branch_repo):
    wrapper, repo = branch_repo
    target = wrapper.CHECKOUT_READ_FILES[0]
    (repo / target).write_text("changed\n", encoding="utf-8")
    _git(repo, "add", target)
    assert wrapper.fallback_touches("main") == [target]


def test_fallback_touches_sees_an_unstaged_edit(branch_repo):
    wrapper, repo = branch_repo
    target = wrapper.CHECKOUT_READ_FILES[0]
    (repo / target).write_text("changed\n", encoding="utf-8")
    assert wrapper.fallback_touches("main") == [target]


def test_fallback_touches_does_not_look_at_what_the_snapshot_covers(branch_repo):
    """Issue #676: an edited dispatcher is not a reason to lose the fallback any more."""
    from scripts.marketplace_ci import review

    wrapper, repo = branch_repo
    for name in review.SNAPSHOT_FILES:
        (repo / name).write_text("changed\n", encoding="utf-8")
    assert wrapper.fallback_touches("main") == []


def test_fallback_touches_ignores_a_change_made_only_on_the_base_after_branching(branch_repo):
    """Compared with the merge-base, so a protected file that `main` changed since the branch
    was cut is not blamed on the branch."""
    wrapper, repo = branch_repo
    target = wrapper.CHECKOUT_READ_FILES[0]
    _git(repo, "checkout", "-q", "main")
    (repo / target).write_text("changed on main\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "main moves on")
    _git(repo, "checkout", "-q", "feature")
    assert wrapper.fallback_touches("main") == []


def test_fallback_touches_fails_closed_when_git_cannot_answer(monkeypatch):
    wrapper = _load_wrapper()
    monkeypatch.setattr(wrapper, "_run", lambda argv, **kw: None)
    assert wrapper.fallback_touches("abc") is None
    failing = subprocess.CompletedProcess([], 128, "", "")
    monkeypatch.setattr(wrapper, "_run", lambda argv, **kw: failing)
    assert wrapper.fallback_touches("abc") is None


def test_the_wrappers_checkout_read_list_matches_the_one_run_codex_review_enforces():
    from scripts.marketplace_ci import review

    assert _load_wrapper().CHECKOUT_READ_FILES == review.CHECKOUT_READ_FILES


def test_every_file_the_dispatcher_runs_is_in_the_enforced_refusal_list():
    from scripts.marketplace_ci import review

    assert _closure(ENTRY) - set(review.FALLBACK_FILES) == set()


def test_fallback_files_changed_is_empty_for_an_untouched_branch(branch_repo):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    assert review.fallback_files_changed(repo, "main") == []


@pytest.mark.parametrize("how", ["committed", "staged", "unstaged"])
def test_fallback_files_changed_sees_every_kind_of_edit(branch_repo, how):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    target = review.FALLBACK_FILES[4]
    (repo / target).write_text("changed\n", encoding="utf-8")
    if how == "committed":
        _git(repo, "commit", "-q", "-am", "edit")
    elif how == "staged":
        _git(repo, "add", target)
    assert review.fallback_files_changed(repo, "main") == [target]


def test_fallback_files_changed_ignores_a_change_made_only_on_the_base(branch_repo):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    _git(repo, "checkout", "-q", "main")
    (repo / review.FALLBACK_FILES[1]).write_text("changed on main\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "main moves on")
    _git(repo, "checkout", "-q", "feature")
    assert review.fallback_files_changed(repo, "main") == []


@pytest.mark.parametrize("flag", ["--skip-worktree", "--assume-unchanged"])
def test_fallback_files_changed_sees_an_edit_hidden_by_an_index_flag(branch_repo, flag):
    """Issue #652: `git diff` trusts the index's stat data, so a file flagged skip-worktree or
    assume-unchanged hides an edit from it; the content hash does not."""
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    target = review.FALLBACK_FILES[0]
    _git(repo, "update-index", flag, target)
    (repo / target).write_text("edited behind the index\n", encoding="utf-8")
    assert _git(repo, "diff", "--name-only", "main", "--", target) == ""  # the old check is blind
    assert review.fallback_files_changed(repo, "main") == [target]


def test_fallback_files_changed_sees_an_edit_hidden_by_a_branch_supplied_encoding(branch_repo):
    """Cross-model review of the #652 change: with filters on, `git hash-object` converts the
    working file through attributes the branch itself can add. A file spelled in UTF-7 (the
    newline as `+AAo-`) decodes to the base text, so it would hash to the base blob while the
    dispatcher, which runs the raw bytes, reads a different file."""
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    target = review.FALLBACK_FILES[0]
    attributes = f"{target} working-tree-encoding=UTF-7\n"
    (repo / ".gitattributes").write_text(attributes, encoding="utf-8")
    (repo / target).write_bytes(b"original+AAo-")
    filtered = subprocess.run(
        ["git", "hash-object", "--stdin-paths"],
        cwd=repo,
        input=f"{target}\n",
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if filtered != _git(repo, "rev-parse", f"main:{target}"):
        pytest.skip("this git does not convert working-tree-encoding=UTF-7; no bypass to test")
    assert review.fallback_files_changed(repo, "main") == [target]


def _symlink_or_skip(link: Path, target: Path, *, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError):
        pytest.skip("this platform or account cannot create symlinks")


def test_fallback_files_changed_sees_a_file_swapped_for_a_symlink(branch_repo):
    """Cross-model review, round 2: `git hash-object` follows a symlink, so a link to a copy with
    the same bytes would hash like the file it replaced, where the earlier `git diff` check
    reported the type change."""
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    target = review.FALLBACK_FILES[0]
    copy = repo / "same-bytes-copy.mjs"
    copy.write_bytes(b"original\n")
    (repo / target).unlink()
    _symlink_or_skip(repo / target, copy)
    assert review.fallback_files_changed(repo, "main") == [target]


def test_fallback_files_changed_sees_a_directory_swapped_for_a_symlink(branch_repo):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    lib_prefix = "plugins/codex-kit/scripts/lib/"
    lib_files = [p for p in review.FALLBACK_FILES if p.startswith(lib_prefix)]
    assert lib_files  # guards the guard: the folder holds fallback files
    moved = repo / "lib-copy"
    (repo / lib_prefix.rstrip("/")).rename(moved)
    _symlink_or_skip(repo / lib_prefix.rstrip("/"), moved, directory=True)
    assert review.fallback_files_changed(repo, "main") == lib_files


def test_the_production_dispatch_call_passes_the_per_call_fallback_gate():
    """`dispatch_reviewers` leaves `unsandboxed_allowed` off by default, so a caller that forgets
    it gets no per-call fallback-file check; the production caller must pass it."""
    source = (REPO / "scripts/marketplace_ci/__main__.py").read_text(encoding="utf-8")
    calls = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "dispatch_reviewers"
    ]
    assert calls, "no dispatch_reviewers call found in __main__.py"
    for call in calls:
        assert any(kw.arg == "unsandboxed_allowed" for kw in call.keywords)


def test_fallback_files_changed_runs_an_absolute_git_from_outside_the_checkout(
    branch_repo, monkeypatch
):
    """Security review: a bare "git" is looked up in the parent's cwd first on Windows, so a
    git.exe the branch committed at the repo root could answer the gate's questions. Pins the
    argv and the PATH the gate uses; a planted-executable run depends on the machine's
    NoDefaultCurrentDirectoryInExePath setting, so it is not asserted here."""
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    monkeypatch.setattr(review, "_executable_outside_checkout", _real_resolver)
    seen = []
    real_run = subprocess.run

    def spy(argv, **kwargs):
        seen.append((argv[0], kwargs.get("env")))
        return real_run(argv, **kwargs)

    monkeypatch.setattr(review.subprocess, "run", spy)
    assert review.fallback_files_changed(repo, "main") == []
    assert len(seen) == 3  # merge-base, ls-tree, hash-object
    for program, env in seen:
        assert Path(program).is_absolute() and Path(program).stem.lower() == "git"
        assert env is not None and env["PATH"] == review._path_outside_checkout()


def test_fallback_files_changed_is_none_when_git_is_only_found_inside_the_checkout(
    branch_repo, monkeypatch
):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    monkeypatch.setattr(review, "_executable_outside_checkout", lambda name: None)
    assert review.fallback_files_changed(repo, "main") is None


def test_fallback_files_changed_sees_a_deleted_file(branch_repo):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    target = review.FALLBACK_FILES[2]
    (repo / target).unlink()
    assert review.fallback_files_changed(repo, "main") == [target]


def test_fallback_files_changed_sees_a_file_the_base_does_not_have(branch_repo):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    target = review.FALLBACK_FILES[2]
    _git(repo, "checkout", "-q", "main")
    _git(repo, "rm", "-q", target)
    _git(repo, "commit", "-q", "-m", "main drops the file")
    _git(repo, "checkout", "-q", "-B", "feature")
    assert review.fallback_files_changed(repo, "main") == []  # absent on both sides
    (repo / target).parent.mkdir(parents=True, exist_ok=True)
    (repo / target).write_text("new on the branch\n", encoding="utf-8")
    assert review.fallback_files_changed(repo, "main") == [target]


def test_fallback_files_changed_is_none_when_git_cannot_answer(branch_repo):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    assert review.fallback_files_changed(repo, "no-such-ref") is None


# --- the fallback is automatic, like cross-model-review's: decided by the wrapper, no question ---


def test_fallback_decision_is_on_for_an_untouched_branch_on_windows(branch_repo):
    wrapper, _ = branch_repo
    use, note = wrapper.fallback_decision("main", platform="win32")
    assert use is True
    assert "codex-windows-guardrails" in note and "danger-full-access" in note


def test_fallback_decision_is_silent_and_off_where_the_sandbox_works(branch_repo):
    wrapper, _ = branch_repo
    assert wrapper.fallback_decision("main", platform="linux") == (False, "")


def test_fallback_decision_skips_the_fallback_when_the_branch_changed_what_codex_reads(branch_repo):
    wrapper, repo = branch_repo
    target = wrapper.CHECKOUT_READ_FILES[0]
    (repo / target).write_text("changed\n", encoding="utf-8")
    use, note = wrapper.fallback_decision("main", platform="win32")
    assert use is False
    assert target in note and "sandboxed only" in note


def test_fallback_decision_keeps_the_fallback_for_a_branch_that_edits_the_dispatcher(branch_repo):
    """Issue #676: the dispatcher runs from a snapshot of the base tip."""
    from scripts.marketplace_ci import review

    wrapper, repo = branch_repo
    for name in review.SNAPSHOT_FILES:
        (repo / name).write_text("changed\n", encoding="utf-8")
    use, _ = wrapper.fallback_decision("main", platform="win32")
    assert use is True


def test_fallback_decision_skips_the_fallback_when_git_cannot_answer(monkeypatch):
    wrapper = _load_wrapper()
    monkeypatch.setattr(wrapper, "_run", lambda argv, **kw: None)
    use, note = wrapper.fallback_decision("abc", platform="win32")
    assert use is False and "sandboxed only" in note


def test_the_asset_the_dispatcher_puts_in_its_prompt_is_protected():
    from scripts.marketplace_ci import review

    assert any(p.endswith("dangerous-command-instructions.txt") for p in review.SNAPSHOT_FILES)


# --- run-codex-review wiring ---


def _cli():
    from scripts.marketplace_ci import __main__ as cli

    return cli


def test_sandbox_known_down_replaces_the_probe_with_a_failing_one():
    import argparse

    cli = _cli()
    args = argparse.Namespace(sandbox_known_down=True)
    probe = cli._sandbox_probe_for(args, lambda: None)
    assert probe is not None and "reported down by the caller" in (probe() or "")


def test_without_the_hint_the_real_probe_runs_on_windows_only(monkeypatch):
    import argparse

    cli = _cli()
    args = argparse.Namespace(sandbox_known_down=False)
    real = lambda: None  # noqa: E731
    monkeypatch.setattr(cli.sys, "platform", "win32")
    assert cli._sandbox_probe_for(args, real) is real
    monkeypatch.setattr(cli.sys, "platform", "linux")
    assert cli._sandbox_probe_for(args, real) is None


def test_the_parser_knows_both_fallback_flags_and_defaults_them_off():
    cli = _cli()
    parsed = cli.build_parser().parse_args(["run-codex-review", "--base-sha", "abc"])
    assert parsed.allow_unsandboxed_fallback is False
    assert parsed.sandbox_known_down is False
    flagged = cli.build_parser().parse_args(
        [
            "run-codex-review",
            "--base-sha",
            "abc",
            "--allow-unsandboxed-fallback",
            "--sandbox-known-down",
        ]
    )
    assert flagged.allow_unsandboxed_fallback and flagged.sandbox_known_down


def test_provenance_names_the_reviewers_that_ran_unsandboxed():
    cli = _cli()
    from scripts.marketplace_ci.review import ReviewerReport

    reports = [
        ReviewerReport(reviewer="a-reviewer", status="completed", output={}, unsandboxed=True),
        ReviewerReport(reviewer="b-reviewer", status="completed", output={}),
    ]
    provenance = cli._run_provenance(REPO, "deadbeef", reports)
    assert provenance["unsandboxed_reviewers"] == ["a-reviewer"]
    clean = cli._run_provenance(REPO, "deadbeef", [reports[1]])
    assert "unsandboxed_reviewers" not in clean


# --- Issue #676: the fallback runs from a snapshot of the base tip, not the working tree ---


def test_the_checkout_read_and_snapshot_files_together_are_the_refusal_list():
    from scripts.marketplace_ci import review

    assert review.CHECKOUT_READ_FILES == (".codex/config.toml",)
    assert (*review.SNAPSHOT_FILES, *review.CHECKOUT_READ_FILES) == review.FALLBACK_FILES


def test_every_file_the_dispatcher_runs_is_in_the_snapshot():
    from scripts.marketplace_ci import review

    assert _closure(ENTRY) - set(review.SNAPSHOT_FILES) == set()


def test_snapshot_holds_the_base_bytes_of_every_snapshot_file(branch_repo, tmp_path):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    dest = tmp_path / "snap"
    dest.mkdir()
    assert review.snapshot_fallback_files(repo, "main", dest) is None
    for name in review.SNAPSHOT_FILES:
        assert (dest / name).read_bytes() == b"original\n"
    assert not (dest / ".codex/config.toml").exists()


@pytest.mark.parametrize("how", ["committed", "unstaged"])
def test_snapshot_ignores_a_branch_edit_to_what_the_fallback_runs(branch_repo, tmp_path, how):
    """The branch edits the dispatcher; the snapshot still holds the base tip's copy."""
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    edited = review.SNAPSHOT_FILES[0]
    (repo / edited).write_bytes(b"edited by the branch\n")
    if how == "committed":
        _git(repo, "commit", "-q", "-am", "edit")
    dest = tmp_path / "snap"
    dest.mkdir()
    assert review.snapshot_fallback_files(repo, "main", dest) is None
    assert (dest / edited).read_bytes() == b"original\n"


def test_snapshot_comes_from_the_base_tip_not_the_branchs_fork_point(branch_repo, tmp_path):
    """A branch picks its own fork point, so an older merge-base copy (without later guardrail
    fixes) must not be what runs with full access."""
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    target = review.SNAPSHOT_FILES[0]
    _git(repo, "checkout", "-q", "main")
    (repo / target).write_bytes(b"fixed on main later\n")
    _git(repo, "commit", "-q", "-am", "main moves on")
    _git(repo, "checkout", "-q", "feature")
    dest = tmp_path / "snap"
    dest.mkdir()
    assert review.snapshot_fallback_files(repo, "main", dest) is None
    assert (dest / target).read_bytes() == b"fixed on main later\n"


@pytest.mark.parametrize("base", ["no-such-ref", "--output=x"])
def test_snapshot_fails_with_a_reason_for_an_unresolvable_base(branch_repo, tmp_path, base):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    assert review.snapshot_fallback_files(repo, base, tmp_path) is not None


def _snapshot(review, repo, tmp_path):
    dest = tmp_path / "snap"
    dest.mkdir()
    manifest: dict[str, str] = {}
    assert review.snapshot_fallback_files(repo, "main", dest, manifest) is None
    return dest, manifest


def test_snapshot_intact_is_true_for_a_fresh_snapshot(branch_repo, tmp_path):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    dest, manifest = _snapshot(review, repo, tmp_path)
    assert set(manifest) == set(review.SNAPSHOT_FILES)
    assert review.snapshot_intact(repo, dest, manifest) is True


def test_snapshot_intact_sees_a_file_overwritten_after_the_snapshot(branch_repo, tmp_path):
    """An earlier unsandboxed reviewer runs as this account and could rewrite the snapshot."""
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    dest, manifest = _snapshot(review, repo, tmp_path)
    (dest / review.SNAPSHOT_FILES[0]).write_bytes(b"tampered\n")
    assert review.snapshot_intact(repo, dest, manifest) is False


def test_snapshot_intact_sees_a_file_removed_after_the_snapshot(branch_repo, tmp_path):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    dest, manifest = _snapshot(review, repo, tmp_path)
    (dest / review.SNAPSHOT_FILES[0]).unlink()
    assert review.snapshot_intact(repo, dest, manifest) is False


def test_snapshot_intact_is_false_without_a_manifest(branch_repo, tmp_path):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    assert review.snapshot_intact(repo, tmp_path, {}) is False


def test_snapshot_fails_with_a_reason_when_the_base_lacks_a_file(branch_repo, tmp_path):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    _git(repo, "checkout", "-q", "main")
    _git(repo, "rm", "-q", review.SNAPSHOT_FILES[1])
    _git(repo, "commit", "-q", "-m", "drop")
    dest = tmp_path / "snap"
    dest.mkdir()
    reason = review.snapshot_fallback_files(repo, "main", dest)
    assert reason is not None and review.SNAPSHOT_FILES[1] in reason


def test_snapshot_fails_with_a_reason_when_git_is_not_found_outside_the_checkout(
    branch_repo, tmp_path, monkeypatch
):
    from scripts.marketplace_ci import review

    _, repo = branch_repo
    monkeypatch.setattr(review, "_executable_outside_checkout", lambda name: None)
    assert review.snapshot_fallback_files(repo, "main", tmp_path) == (
        "git was not found on PATH outside the checkout"
    )


def test_dispatch_launches_the_guardrails_script_from_the_snapshot_root(monkeypatch, tmp_path):
    from scripts.marketplace_ci import review

    seen = {}

    def fake_dispatch_one(name, scope, **kwargs):
        seen[name] = kwargs["guardrails_script"]
        return review.ReviewerReport(reviewer=name, status="failed", error="stop", attempts=0)

    monkeypatch.setattr(review, "_dispatch_one", fake_dispatch_one)
    scope = review.ReviewScope(
        mode="delta",
        structural_check="delta",
        validate=("skill-reviewer",),
        audit=(),
        paths=("a.md",),
    )
    repo, root = tmp_path / "repo", tmp_path / "snap"
    for with_root in (root, None):
        seen.clear()
        review.dispatch_reviewers(
            scope,
            base_sha="0" * 40,
            repo=repo,
            instructions_dir=tmp_path / "ins",
            allow_guardrails_fallback=True,
            fallback_root=with_root,
        )
        assert seen["skill-reviewer"] == (
            (with_root or repo) / review.GUARDRAILS_DISPATCH_RELATIVE_PATH
        )
