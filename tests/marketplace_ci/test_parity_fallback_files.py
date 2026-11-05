"""The parity wrapper refuses the unsandboxed fallback when the branch changed any file that
`guarded-dispatch.mjs` runs (issue #644, cross-model review). The refusal list is derived here from
the real import graph, so a new import in the dispatcher cannot silently escape it."""

import importlib.util
import posixpath
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins/git-kit/scripts/git-codex-parity-review.py"
ENTRY = "plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs"
# A static `import ... from "./x.mjs"` / `import "./x.mjs"`, and a run-time data read
# `new URL("./x.json", import.meta.url)`.
_STATIC_IMPORT = re.compile(r"""(?:from|import)\s+["'](\.{1,2}/[^"']+)["']""")
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
