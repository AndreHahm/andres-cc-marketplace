"""Portable validator orchestration: the repository/plugin validator catalog,
subprocess-based black-box execution of plugin validators, plus the staged-
parity pre-commit check and the PostToolUse post-edit hook.

This module is Tier 2 (apply-side) -- never imported by the review-dispatch-
critical CLI subcommands (check-scope-bypass, run-codex-review, check-bypass,
resolve-attested-actor). The delta-scoped structural check
`dispatch_reviewers` needs in-process (`run_delta_structural_checks`) lives in
review.py instead, since that check is itself on the critical path -- see
review.py's own docstring on that function for why (issue #351)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from scripts.marketplace_ci.conversion import convert_agent, plan_exports
from scripts.marketplace_ci.git_state import GitState
from scripts.marketplace_ci.registry import Registry
from scripts.marketplace_ci.sync import apply_sync_plan
from scripts.marketplace_ci.sync_plan import _iter_component_files, plan_plugin_sync

_INTERPRETER_COMMAND = {"python": "python", "bash": "bash"}


@dataclass(frozen=True)
class PluginValidatorEntry:
    id: str
    plugin: str
    path: Path
    interpreter: str  # "python" | "bash"
    platforms: tuple[str, ...]  # platforms this entry can run on directly
    kind: str = "black-box"  # "black-box" | "out-of-scope"
    note: str | None = None


@dataclass(frozen=True)
class RepositoryValidatorEntry:
    id: str
    kind: str  # "reusable" | "adaptable" | "superseded"
    module: str
    description: str


@dataclass(frozen=True)
class ValidatorCatalog:
    repository_validators: tuple[RepositoryValidatorEntry, ...] = ()
    plugin_validators: tuple[PluginValidatorEntry, ...] = ()


@dataclass(frozen=True)
class ValidatorResult:
    id: str
    status: str  # "passed" | "failed" | "skipped"
    reason: str | None = None


def load_catalog(path: Path) -> ValidatorCatalog:
    raw = json.loads(path.read_text(encoding="utf-8"))
    repository_validators = tuple(
        RepositoryValidatorEntry(
            id=entry["id"],
            kind=entry["kind"],
            module=entry["module"],
            description=entry["description"],
        )
        for entry in raw.get("repository_validators", [])
    )
    plugin_validators = tuple(
        PluginValidatorEntry(
            id=entry["id"],
            plugin=entry["plugin"],
            path=Path(entry["path"]),
            interpreter=entry["interpreter"],
            platforms=tuple(entry["platforms"]),
            kind=entry.get("kind", "black-box"),
            note=entry.get("note"),
        )
        for entry in raw.get("plugin_validators", [])
    )
    return ValidatorCatalog(
        repository_validators=repository_validators, plugin_validators=plugin_validators
    )


def run_catalog(catalog: ValidatorCatalog, platform: str) -> tuple[ValidatorResult, ...]:
    """Run every plugin-owned validator as a black-box subprocess.

    Repository-owned validators are never listed here for execution — they're
    invoked directly, in-process, by the CLI commands that already implement
    them (`check-plugin-mirrors`, `check-codex-exports`, ...).
    """
    results: list[ValidatorResult] = []
    for entry in catalog.plugin_validators:
        if entry.kind == "out-of-scope":
            continue
        if platform not in entry.platforms:
            results.append(
                ValidatorResult(
                    id=entry.id,
                    status="skipped",
                    reason=f"{entry.interpreter.capitalize()} prerequisite unavailable on "
                    f"{platform.capitalize()}",
                )
            )
            continue
        argv = [_INTERPRETER_COMMAND[entry.interpreter], entry.path.as_posix()]
        completed = subprocess.run(argv, check=False, capture_output=True)
        if completed.returncode == 0:
            results.append(ValidatorResult(id=entry.id, status="passed"))
        else:
            results.append(
                ValidatorResult(
                    id=entry.id, status="failed", reason=f"exit code {completed.returncode}"
                )
            )
    return tuple(results)


@dataclass(frozen=True)
class HookCheckResult:
    exit_code: int
    messages: tuple[str, ...] = ()


def check_staged_parity(repo: Path) -> HookCheckResult:
    """Compare staged canonical sources against staged mirror/export
    destinations, entirely via the Git index — never the working tree.

    A destination whose *working-tree* content happens to already match its
    canonical source, but was never `git add`-ed, does not satisfy parity:
    the commit that's about to happen would still record a mismatch. This is
    why the mapping is walked directly here rather than reusing
    `plan_plugin_sync`/`plan_exports`'s own output — those only report a
    problem when the *filesystem* disagrees, which is exactly the case an
    unstaged-but-already-correct destination does not trigger.
    """
    git_state = GitState(repo=repo)
    registry_blob = git_state.read_index(PurePosixPath(".claude/marketplace-sync.json"))
    if registry_blob is None:
        return HookCheckResult(exit_code=0)

    # Index-only, matching this function's own contract: an exception added to the
    # working-tree copy of marketplace-sync.json but never staged must never be
    # honored here -- it isn't part of what's actually about to be committed.
    registry = Registry.loads(
        registry_blob.decode("utf-8"), source=".claude/marketplace-sync.json (staged)"
    )
    staged = git_state.staged_paths()
    staged_new_paths = {cp.new_path for cp in staged if cp.new_path is not None}
    if not staged_new_paths:
        return HookCheckResult(exit_code=0)

    claude_root = repo / ".claude"
    plugins_root = repo / "plugins"
    messages: list[str] = []
    divergence_exceptions = {(exc.source, exc.dest) for exc in registry.divergence_exceptions}

    def check_pair(
        rel_source: str,
        rel_dest: str,
        *,
        is_agent: bool = False,
        agent_name: str | None = None,
        honor_exceptions: bool = False,
    ) -> None:
        # Exact match against the staged path set -- not a directory-prefix
        # key -- so that staging one file in a skill (e.g. SKILL.md) never
        # requires an untouched sibling (e.g. references/*.md) to also be
        # staged just because both happen to share a coarse directory key.
        if rel_source not in staged_new_paths:
            return
        staged_source_blob = git_state.read_index(PurePosixPath(rel_source))
        if staged_source_blob is None:
            return  # source itself isn't staged (e.g. a delete); nothing to compare
        if rel_dest not in staged_new_paths:
            messages.append(
                f"{rel_dest}: canonical source is staged but the generated "
                "counterpart was not staged"
            )
            return
        # honor_exceptions is only ever true for the plugin-mirror loop below --
        # divergence_exceptions is a plan_plugin_sync concept with no equivalent in
        # plan_exports, which has zero knowledge of exceptions. Honoring one here for
        # a skill/agent export pair would let check-all --staged pass a stale export
        # that the real, non-staged check-codex-exports (plan_exports) always rejects
        # -- exactly the inconsistency this scoping prevents.
        if honor_exceptions and (rel_source, rel_dest) in divergence_exceptions:
            # Whole-file exception (see DivergenceException docstring) -- both
            # sides being staged is still required above; only the byte-equality
            # check below is skipped.
            return
        staged_dest_blob = git_state.read_index(PurePosixPath(rel_dest))
        if is_agent:
            assert agent_name is not None, "agent_name is required when is_agent=True"
            expected = convert_agent(staged_source_blob.decode("utf-8"), agent_name).encode("utf-8")
        else:
            expected = staged_source_blob
        if staged_dest_blob != expected:
            messages.append(
                f"{rel_dest}: staged content does not match the staged canonical source"
            )

    for plugin_name in registry.plugin_mirrors:
        plugin_root = plugins_root / plugin_name
        if not plugin_root.is_dir():
            continue
        for source_file in _iter_component_files(plugin_root):
            rel_source = source_file.relative_to(repo).as_posix()
            rel_dest = (
                (claude_root / source_file.relative_to(plugin_root)).relative_to(repo).as_posix()
            )
            check_pair(rel_source, rel_dest, honor_exceptions=True)

    for skill_name in registry.skills:
        source_dir = claude_root / "skills" / skill_name
        if not source_dir.is_dir():
            continue
        for file in sorted(source_dir.rglob("*")):
            if not file.is_file():
                continue
            rel_source = file.relative_to(repo).as_posix()
            dest = repo / ".agents" / "skills" / skill_name / file.relative_to(source_dir)
            check_pair(rel_source, dest.relative_to(repo).as_posix())

    for agent_name in registry.agents:
        source_file = claude_root / "agents" / f"{agent_name}.md"
        if not source_file.is_file():
            continue
        rel_source = source_file.relative_to(repo).as_posix()
        check_pair(
            rel_source, f".codex/agents/{agent_name}.toml", is_agent=True, agent_name=agent_name
        )

    return HookCheckResult(exit_code=1 if messages else 0, messages=tuple(messages))


@dataclass(frozen=True)
class PostEditResult:
    changed: tuple[str, ...]


_POST_EDIT_IGNORED_PREFIXES = (".agents/", ".codex/")
_POST_EDIT_WATCHED_PREFIXES = ("plugins/", ".claude/skills/", ".claude/agents/")


def run_post_edit(repo: Path, changed_path: str) -> PostEditResult:
    """Cascade a single canonical edit into both its `.claude` mirror and (if
    applicable) its `.agents`/`.codex` export, in one process — no dependency
    on a second hook observing the mirror write and re-triggering itself.

    Generated destinations (`.agents/`, `.codex/`) are never watched, so the
    adapter's own writes — made via plain Python file I/O in `apply_sync_plan`,
    never through Claude Code's own Write/Edit tool — cannot re-trigger this
    hook even in principle; there is no separate "recursion token" to track
    across invocations, since each hook invocation is a fresh, stateless
    subprocess with nothing to persist between calls.
    """
    if changed_path.startswith(_POST_EDIT_IGNORED_PREFIXES):
        return PostEditResult(changed=())
    if not changed_path.startswith(_POST_EDIT_WATCHED_PREFIXES):
        return PostEditResult(changed=())

    registry_path = repo / ".claude" / "marketplace-sync.json"
    if not registry_path.is_file():
        return PostEditResult(changed=())
    registry = Registry.load(registry_path)

    mirror_plan = plan_plugin_sync(repo, registry, previous=None, bootstrap=False)
    mirror_result = apply_sync_plan(mirror_plan)

    export_plan = plan_exports(repo, registry, previous=None)
    export_result = apply_sync_plan(export_plan)

    changed = tuple(
        action.destination.relative_to(repo).as_posix()
        for action in (*mirror_result.applied, *export_result.applied)
    )
    return PostEditResult(changed=changed)
