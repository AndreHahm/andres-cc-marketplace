"""The parity wrapper refuses the unsandboxed fallback when the branch changed any file that
`guarded-dispatch.mjs` runs (issue #644, cross-model review). The refusal list is derived here from
the real import graph, so a new import in the dispatcher cannot silently escape it. Followed:
static and dynamic relative imports and `new URL("./x", import.meta.url)` reads. Not followed: a
file located with `path.join(...)` and read with `fs`; the one such read today, the guardrails
`assets/settings.json`, is listed by hand. The wrapper also refuses changes that are only staged
or unstaged, since the fallback runs the working tree."""

import importlib.util
import posixpath
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins/git-kit/scripts/git-codex-parity-review.py"
ENTRY = "plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs"
# A static `import ... from "./x.mjs"` / `import "./x.mjs"`, a dynamic `import("./x.mjs")`, and a
# run-time data read `new URL("./x.json", import.meta.url)`.
_STATIC_IMPORT = re.compile(r"""(?:from|import)\s*\(?\s*["'](\.{1,2}/[^"']+)["']""")
_URL_READ = re.compile(r"""new URL\(\s*["'](\.{1,2}/[^"']+)["']\s*,\s*import\.meta\.url""")


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
    return seen


def test_every_file_the_dispatcher_runs_is_in_the_fallback_refusal_list():
    wrapper = _load_wrapper()
    missing = sorted(_closure(ENTRY) - set(wrapper.FALLBACK_FILES))
    assert not missing, f"guarded-dispatch.mjs runs files the fallback refusal ignores: {missing}"


def test_every_fallback_file_exists():
    wrapper = _load_wrapper()
    assert [p for p in wrapper.FALLBACK_FILES if not (REPO / p).is_file()] == []


def test_the_closure_finds_the_known_transitive_imports():
    """Guards the guard: if the regexes stop matching, the closure would shrink to the entry
    point and the first test would pass for the wrong reason."""
    closure = _closure(ENTRY)
    assert "plugins/codex-kit/scripts/lib/codex-exec.mjs" in closure
    assert "plugins/codex-kit/scripts/lib/cdx-process.mjs" in closure  # via codex-exec.mjs
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
    for name in wrapper.FALLBACK_FILES:
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("original\n", encoding="utf-8")
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
    target = wrapper.FALLBACK_FILES[2]
    (repo / target).write_text("changed\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "edit")
    assert wrapper.fallback_touches("main") == [target]


def test_fallback_touches_sees_a_staged_edit_that_is_not_committed(branch_repo):
    wrapper, repo = branch_repo
    target = wrapper.FALLBACK_FILES[3]
    (repo / target).write_text("changed\n", encoding="utf-8")
    _git(repo, "add", target)
    assert wrapper.fallback_touches("main") == [target]


def test_fallback_touches_sees_an_unstaged_edit(branch_repo):
    wrapper, repo = branch_repo
    target = wrapper.FALLBACK_FILES[0]
    (repo / target).write_text("changed\n", encoding="utf-8")
    assert wrapper.fallback_touches("main") == [target]


def test_fallback_touches_ignores_a_change_made_only_on_the_base_after_branching(branch_repo):
    """Compared with the merge-base, so a protected file that `main` changed since the branch
    was cut is not blamed on the branch."""
    wrapper, repo = branch_repo
    target = wrapper.FALLBACK_FILES[1]
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
