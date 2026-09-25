"""Plugin mirror synchronization APPLY side: atomic writes, staging, and the
`hooks/hooks.json` structural-merge exception. Plan computation
(`plan_plugin_sync` and its supporting types) lives in sync_plan.py -- see
that module's docstring for why the two are split (issue #351, direction #3).
This module is never imported by the review-dispatch-critical CLI subcommands
(check-scope-bypass, run-codex-review, check-bypass, resolve-attested-actor)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scripts.marketplace_ci.git_state import GitState
from scripts.marketplace_ci.registry import Registry
from scripts.marketplace_ci.sync_plan import SyncAction, SyncError, SyncPlan

DEFAULT_REPO_HOOKS_PATH = Path("scripts/marketplace_ci/hooks/hooks.json")
DEFAULT_REPO_SETTINGS_PATH = Path(".claude/settings.json")
_HOOKS_SOURCE_PATTERN = re.compile(r"^plugins/[^/]+/hooks/hooks\.json$")

# Hook `command` strings that reference a script outside the mirrored COMPONENT_DIRS
# (skills, agents, commands, hooks, rules) -- most commonly a plugin's own root-level
# `scripts/` directory. plan_plugin_sync (sync_plan.py) never mirrors those paths into
# .claude/, so plan_settings_hooks_sync's ${CLAUDE_PLUGIN_ROOT} rewrite has nowhere to
# point without an explicit destination. Hand-maintained rather than mirroring every
# plugin's entire scripts/ directory (deliberately out of scope -- see
# .claude/hooks/README.md). Adding a new hook that references a script outside the five
# component dirs requires a new entry here; plan_settings_hooks_sync raises a SyncError
# if any ${CLAUDE_PLUGIN_ROOT} reference survives rewriting, so a missed addition is a
# build-time failure, not a silently broken hook path (issue #374).
#
# context-kit's 3 scripts are each self-contained (stdlib-only imports, confirmed by
# grep) -- listing the entry point alone is sufficient. codex-kit's 2 hook scripts are
# NOT: they pull in a much larger closure, computed with an automated recursive
# resolver (relative `import`/`new URL(..., import.meta.url)` references, followed
# transitively) seeded from both entry points PLUS two scripts spawned dynamically via
# `path.join(SCRIPT_DIR, "...")` + `spawn()`/`spawnSync()` rather than a static import
# (codex-companion.mjs, app-server-broker.mjs) -- the resolver can't follow a dynamic
# path.join, so each spawn target had to be added as its own seed and re-resolved.
# Mirroring only the two entry-point files initially shipped with this broken
# (ERR_MODULE_NOT_FOUND on load) -- found by Codex's cross-model review of this same
# change; the deeper layers (the two spawn targets, the plugin manifest, the prompt
# template, the JSON schema) were found only by then actually executing the mirrored
# scripts end-to-end and following each new error, not by reading the source once.
# Every remaining `path.join(var, ...)` site was individually checked against the
# real source: the rest resolve to runtime state directories (session/broker
# pid/sock/log files, plugin data dirs) or an optional user-repo file
# (.secretlintignore), never another static plugin file to mirror.
# scripts/lib/app-server-protocol.d.ts is deliberately excluded: every reference to it
# is inside a JSDoc @typedef/@param comment, never a runtime `import`. prompts/
# adversarial-review.md is deliberately excluded: only codex-companion.mjs's
# `adversarial-review` subcommand reads it, and stop-review-gate-hook.mjs only ever
# invokes the `task` subcommand.
# This closure is NOT automatically re-verified -- a future codex-kit change adding a
# new relative import, spawned script, or path.join-constructed static file read to
# any file in this closure could silently reintroduce the same missing-dependency
# failure. Re-run the recursive resolver (or an equivalent live execution of the
# mirrored copies) whenever codex-kit's own hook scripts change.
EXTERNAL_HOOK_SCRIPT_MIRRORS: tuple[tuple[str, str], ...] = (
    ("codex-kit", ".claude-plugin/plugin.json"),
    ("codex-kit", "prompts/stop-review-gate.md"),
    ("codex-kit", "schemas/review-output.schema.json"),
    ("codex-kit", "scripts/session-lifecycle-hook.mjs"),
    ("codex-kit", "scripts/stop-review-gate-hook.mjs"),
    ("codex-kit", "scripts/codex-companion.mjs"),
    ("codex-kit", "scripts/app-server-broker.mjs"),
    ("codex-kit", "scripts/lib/app-server.mjs"),
    ("codex-kit", "scripts/lib/args.mjs"),
    ("codex-kit", "scripts/lib/broker-endpoint.mjs"),
    ("codex-kit", "scripts/lib/broker-lifecycle.mjs"),
    ("codex-kit", "scripts/lib/claude-session-transfer.mjs"),
    ("codex-kit", "scripts/lib/codex-config.mjs"),
    ("codex-kit", "scripts/lib/codex-exec.mjs"),
    ("codex-kit", "scripts/lib/codex.mjs"),
    ("codex-kit", "scripts/lib/fs.mjs"),
    ("codex-kit", "scripts/lib/git.mjs"),
    ("codex-kit", "scripts/lib/job-control.mjs"),
    ("codex-kit", "scripts/lib/process.mjs"),
    ("codex-kit", "scripts/lib/prompts.mjs"),
    ("codex-kit", "scripts/lib/render.mjs"),
    ("codex-kit", "scripts/lib/sandbox-check.mjs"),
    ("codex-kit", "scripts/lib/secret-filenames.mjs"),
    ("codex-kit", "scripts/lib/state.mjs"),
    ("codex-kit", "scripts/lib/tracked-jobs.mjs"),
    ("codex-kit", "scripts/lib/workspace.mjs"),
    ("context-kit", "scripts/context-monitor.py"),
    ("context-kit", "scripts/post-compact-restore.py"),
    ("context-kit", "scripts/pre-compact.py"),
)

EXTERNAL_HOOK_SCRIPTS_MIRROR_ROOT = Path(".claude/hooks/_external-scripts")


@dataclass(frozen=True)
class SyncResult:
    applied: tuple[SyncAction, ...]


@dataclass(frozen=True)
class HooksMergePlan:
    actions: tuple[SyncAction, ...]
    merged_document: dict
    sources: tuple[Path, ...] = ()


def plan_hooks_merge(
    repo: Path,
    registry: Registry,
    repo_hooks_path: Path | None = None,
) -> HooksMergePlan:
    if repo_hooks_path is None:
        repo_hooks_path = repo / DEFAULT_REPO_HOOKS_PATH

    sources: list[tuple[str, Path]] = []
    for plugin_name in sorted(registry.plugin_mirrors):
        candidate = repo / "plugins" / plugin_name / "hooks" / "hooks.json"
        if candidate.is_file():
            sources.append((plugin_name, candidate))
    if repo_hooks_path.is_file():
        sources.append((str(repo_hooks_path), repo_hooks_path))
    sources.sort(key=lambda item: item[0])

    merged: dict[str, list[dict]] = {}
    for _, path in sources:
        document = json.loads(path.read_text(encoding="utf-8"))
        for event_key, entries in document.get("hooks", {}).items():
            merged.setdefault(event_key, []).extend(entries)

    merged_document = {"hooks": merged}
    destination = (repo / ".claude" / "hooks" / "hooks.json").resolve()
    new_bytes = (json.dumps(merged_document, indent=2) + "\n").encode("utf-8")

    actions: list[SyncAction] = []
    if destination.exists():
        if destination.read_bytes() != new_bytes:
            actions.append(
                SyncAction(
                    operation="update",
                    source=None,
                    destination=destination,
                    reason="merged hooks.json content changed",
                )
            )
    else:
        actions.append(
            SyncAction(
                operation="create",
                source=None,
                destination=destination,
                reason="merged hooks.json missing",
            )
        )

    return HooksMergePlan(
        actions=tuple(actions),
        merged_document=merged_document,
        sources=tuple(path for _, path in sources),
    )


def _plugin_name_for_hooks_source(repo: Path, source: Path) -> str | None:
    """Which plugin a plan_hooks_merge source belongs to, or None for the repo-owned
    fragment (DEFAULT_REPO_HOOKS_PATH), which is never plugin-scoped."""
    rel = source.resolve().relative_to(repo.resolve()).as_posix()
    match = _HOOKS_SOURCE_PATTERN.match(rel)
    if match is None:
        return None
    return rel.split("/")[1]


_PLUGIN_ROOT_REFERENCE_PATTERN = re.compile(
    r'\$\{CLAUDE_PLUGIN_ROOT\}("?)((?:/[A-Za-z0-9_.\-/]*)?)'
)
_MIRRORED_COMPONENT_DIR_PREFIXES = tuple(
    f"/{d}/" for d in ("skills", "agents", "commands", "hooks", "rules")
)


def _rewrite_plugin_root_references(
    value,
    *,
    plugin_name: str | None,
    external_mirrors: tuple[tuple[str, str], ...] = EXTERNAL_HOOK_SCRIPT_MIRRORS,
):
    """Recursively rewrite every ${CLAUDE_PLUGIN_ROOT} reference in `value` (a
    plan_hooks_merge source document's already-parsed `hooks` section) to a
    project-relative equivalent resolvable via .claude/settings.json's own `hooks` key
    -- as opposed to only resolving when Claude Code loads the hook from an actually-
    installed plugin's own manifest (issue #374).

    Each occurrence is classified individually (not by a single per-string blanket
    replace, which would silently rewrite an unrecognized reference too): a reference
    into one of the five mirrored component dirs (hooks/, skills/, agents/, commands/,
    rules/) rewrites to ${CLAUDE_PROJECT_DIR}/.claude/..., since plan_plugin_sync
    guarantees that subtree is a byte-identical mirror of the owning plugin's own
    copy; a reference matching `external_mirrors` (production default:
    EXTERNAL_HOOK_SCRIPT_MIRRORS -- overridable so this function's rewrite logic is
    testable without depending on this repo's own real plugin content) rewrites to
    that entry's dedicated mirror under EXTERNAL_HOOK_SCRIPTS_MIRROR_ROOT; a bare
    ${CLAUDE_PLUGIN_ROOT} reference with no path suffix rewrites to the mirrored
    project root alone. Anything else raises SyncError -- an unrecognized reference
    with no known destination must fail loud here, not ship as a silently broken path.
    """
    if isinstance(value, dict):
        return {
            k: _rewrite_plugin_root_references(
                v, plugin_name=plugin_name, external_mirrors=external_mirrors
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [
            _rewrite_plugin_root_references(
                v, plugin_name=plugin_name, external_mirrors=external_mirrors
            )
            for v in value
        ]
    if isinstance(value, str) and "CLAUDE_PLUGIN_ROOT" in value:

        def _replace(match: re.Match) -> str:
            # Two literal quoting forms appear in this repo's real hook manifests:
            # `"${CLAUDE_PLUGIN_ROOT}"/hooks/x` (quote closes right after the
            # variable -- captured as `quote`) and `"${CLAUDE_PLUGIN_ROOT}/hooks/x"`
            # (quote wraps the whole path, entirely outside this match -- `quote`
            # empty). Re-attaching `quote` after the rewritten suffix reproduces a
            # shell-valid result either way: it only ever moves a closing quote to
            # wrap more of the same already-safe path, never changes word-splitting.
            quote, suffix = match.group(1), match.group(2)
            if not suffix:
                return f"${{CLAUDE_PROJECT_DIR}}/.claude{quote}"
            if suffix.startswith(_MIRRORED_COMPONENT_DIR_PREFIXES):
                return f"${{CLAUDE_PROJECT_DIR}}/.claude{suffix}{quote}"
            if plugin_name is not None:
                relative_path = suffix[1:]  # drop the leading '/'
                for entry_plugin, entry_relative_path in external_mirrors:
                    if entry_plugin == plugin_name and entry_relative_path == relative_path:
                        return (
                            "${CLAUDE_PROJECT_DIR}/"
                            + EXTERNAL_HOOK_SCRIPTS_MIRROR_ROOT.as_posix()
                            + f"/{plugin_name}/{relative_path}{quote}"
                        )
            raise SyncError(
                "plan_settings_hooks_sync: unresolvable ${CLAUDE_PLUGIN_ROOT} reference in "
                f"plugin {plugin_name!r} hook command, no mirrored destination for it -- add "
                f"an EXTERNAL_HOOK_SCRIPT_MIRRORS entry: {value!r}"
            )

        rewritten = _PLUGIN_ROOT_REFERENCE_PATTERN.sub(_replace, value)
        if "CLAUDE_PLUGIN_ROOT" in rewritten:
            # _PLUGIN_ROOT_REFERENCE_PATTERN only matches the braced ${CLAUDE_PLUGIN_ROOT}
            # form -- an unbraced $CLAUDE_PLUGIN_ROOT or a parameter-expansion-modified
            # ${CLAUDE_PLUGIN_ROOT:-.} passes through .sub() completely untouched, with
            # _replace (and its SyncError above) never even invoked for it. Without this
            # backstop, that reference would ship into .claude/settings.json exactly as
            # broken as the original ${CLAUDE_PLUGIN_ROOT} problem this whole rewrite
            # exists to prevent -- just in a form the regex doesn't recognize (found by
            # CodeRabbit's automated review of this same change). No real hook manifest in
            # this repo currently uses either form (verified: every real occurrence uses
            # the braced form), so this is a latent gap, not a live bug -- but the whole
            # point of this rewrite is to fail loud on anything it can't handle, not just
            # the forms it happens to recognize.
            raise SyncError(
                "plan_settings_hooks_sync: unrecognized ${CLAUDE_PLUGIN_ROOT} reference form "
                f"in plugin {plugin_name!r} hook command -- only the braced "
                f"${{CLAUDE_PLUGIN_ROOT}} form is supported (an unbraced $CLAUDE_PLUGIN_ROOT "
                f"or a modified ${{CLAUDE_PLUGIN_ROOT:-default}} form is not): {value!r}"
            )
        return rewritten
    return value


@dataclass(frozen=True)
class SettingsHooksSyncPlan:
    actions: tuple[SyncAction, ...]
    rewritten_hooks_document: dict
    sources: tuple[Path, ...] = ()
    destination_safe_to_stage: bool = True


def plan_settings_hooks_sync(
    repo: Path,
    hooks_merge_plan: HooksMergePlan,
    repo_settings_path: Path | None = None,
    external_mirrors: tuple[tuple[str, str], ...] = EXTERNAL_HOOK_SCRIPT_MIRRORS,
) -> SettingsHooksSyncPlan:
    """Derive a project-relative copy of plan_hooks_merge's merged hooks content and
    plan writing it into .claude/settings.json's own `hooks` key, preserving every
    other existing top-level settings.json key untouched. This is what makes the
    merge in .claude/hooks/hooks.json (which stays in its original, plugin-manifest
    ${CLAUDE_PLUGIN_ROOT} form -- see .claude/hooks/README.md) actually live-loadable
    (issue #374). Never mutates plan_hooks_merge/apply_hooks_merge_plan's own output;
    this independently re-reads the same source files. `external_mirrors` defaults to
    EXTERNAL_HOOK_SCRIPT_MIRRORS in production; overridable for testing this
    function's rewrite logic without depending on this repo's own real plugin content.
    """
    if repo_settings_path is None:
        repo_settings_path = repo / DEFAULT_REPO_SETTINGS_PATH

    # Captured here, at plan time -- strictly before apply_sync_plan ever writes the
    # regenerated bytes to disk (this function never itself writes). This timing is
    # load-bearing: checking .claude/settings.json's own staged/unstaged git status
    # AFTER the write (the original version of this check, inside
    # stage_settings_hooks_result) always sees the just-written regenerated content as
    # "unstaged" relative to whatever the index still holds -- since staging that
    # regenerated content is the entire point, that check could never pass for a
    # genuine update, only for a brand-new file (found by Codex's cross-model review,
    # round 5: an ordinary hooks-manifest update left .claude/settings.json permanently
    # unstageable via --stage). Checking here instead correctly captures "did this file
    # already have real, unstaged content before this sync run touched it at all" --
    # the actual risk stage_settings_hooks_result exists to guard against -- and
    # doubles as the create-vs-update distinction for free: a nonexistent path always
    # reports as "nothing pending," so a brand-new file is trivially safe to stage too.
    #
    # This function itself has non-git callers (e.g. check-plugin-mirrors's read-only
    # drift check, and every test that only plans/applies without ever staging) that
    # may run outside a real Git working tree at all -- `_is_fully_staged`'s own `git
    # status` call then fails with a non-zero exit (repo.py isn't a Git repository).
    # Fail closed on that, same as the trust-boundary pattern this repo's `commit`
    # skill already uses ("an unverifiable answer is never treated as a safe one"):
    # a plan produced outside a Git working tree can never actually be staged either
    # way, so treating it as unsafe-to-stage is both correct and harmless.
    try:
        destination_safe_to_stage = _is_fully_staged(repo, repo_settings_path)
    except subprocess.CalledProcessError:
        destination_safe_to_stage = False

    merged: dict[str, list[dict]] = {}
    for source in hooks_merge_plan.sources:
        document = json.loads(source.read_text(encoding="utf-8"))
        plugin_name = _plugin_name_for_hooks_source(repo, source)
        rewritten = _rewrite_plugin_root_references(
            document.get("hooks", {}), plugin_name=plugin_name, external_mirrors=external_mirrors
        )
        for event_key, entries in rewritten.items():
            merged.setdefault(event_key, []).extend(entries)

    current_settings: dict = {}
    if repo_settings_path.is_file():
        current_settings = json.loads(repo_settings_path.read_text(encoding="utf-8"))

    new_settings = dict(current_settings)
    new_settings["hooks"] = merged
    new_bytes = (json.dumps(new_settings, indent=2) + "\n").encode("utf-8")

    actions: list[SyncAction] = []
    destination = repo_settings_path.resolve()
    if destination.exists():
        if destination.read_bytes() != new_bytes:
            actions.append(
                SyncAction(
                    operation="update",
                    source=None,
                    destination=destination,
                    reason="merged, project-relative hooks content changed",
                    content=new_bytes,
                )
            )
    else:
        actions.append(
            SyncAction(
                operation="create",
                source=None,
                destination=destination,
                reason="settings.json missing",
                content=new_bytes,
            )
        )

    return SettingsHooksSyncPlan(
        actions=tuple(actions),
        rewritten_hooks_document={"hooks": merged},
        sources=hooks_merge_plan.sources,
        destination_safe_to_stage=destination_safe_to_stage,
    )


def plan_external_hook_scripts_mirror(
    repo: Path,
    registry: Registry,
    external_mirrors: tuple[tuple[str, str], ...] = EXTERNAL_HOOK_SCRIPT_MIRRORS,
) -> SyncPlan:
    """Mirror exactly the plugin scripts named in `external_mirrors` (production
    default: EXTERNAL_HOOK_SCRIPT_MIRRORS) into
    EXTERNAL_HOOK_SCRIPTS_MIRROR_ROOT/<plugin>/<relative_path> -- a small, explicit
    exception list, not a general plugins/*/scripts/ mirror (see
    .claude/hooks/README.md). An entry whose plugin isn't in `registry.plugin_mirrors`
    is skipped entirely, matching plan_hooks_merge's own registry-scoped source
    discovery -- this keeps the function usable against any registry (e.g. a test
    fixture registering only a synthetic plugin), not hardcoded to this repo's own
    current plugin set. Raises SyncError if a *registered* entry's source file is
    missing -- plan_settings_hooks_sync trusts this list blindly when rewriting
    references, so a stale entry must fail loud here rather than silently produce a
    settings.json hook pointing at a destination this function never created.

    Also plans deletion of any existing file under EXTERNAL_HOOK_SCRIPTS_MIRROR_ROOT
    that no longer corresponds to a current `external_mirrors` entry for a plugin
    still in `registry.plugin_mirrors` -- otherwise, renaming/removing an entry (or
    unregistering its plugin) leaves the old mirrored file behind forever: nothing
    else ever visits this destination tree to catch it (plan_plugin_sync's own
    bootstrap orphan-scan deliberately excludes it, since every *current* entry here
    would otherwise be misreported as orphaned) (found by Codex's automated PR
    review, round 2, PR #375).
    """
    actions: list[SyncAction] = []
    known_destinations: set[Path] = set()
    for plugin_name, relative_path in external_mirrors:
        if plugin_name not in registry.plugin_mirrors:
            continue
        source = repo / "plugins" / plugin_name / relative_path
        destination = (
            repo / EXTERNAL_HOOK_SCRIPTS_MIRROR_ROOT / plugin_name / relative_path
        ).resolve()
        known_destinations.add(destination)
        if not source.is_file():
            raise SyncError(
                "plan_external_hook_scripts_mirror: EXTERNAL_HOOK_SCRIPT_MIRRORS entry "
                f"({plugin_name!r}, {relative_path!r}) has no source file at {source} -- "
                "update or remove this entry"
            )
        source_bytes = source.read_bytes()
        if destination.exists():
            if destination.read_bytes() == source_bytes:
                continue
            actions.append(
                SyncAction(
                    operation="update",
                    source=source,
                    destination=destination,
                    reason="content differs from canonical source",
                )
            )
        else:
            actions.append(
                SyncAction(
                    operation="create",
                    source=source,
                    destination=destination,
                    reason="missing from destination",
                )
            )

    mirror_root = (repo / EXTERNAL_HOOK_SCRIPTS_MIRROR_ROOT).resolve()
    if mirror_root.is_dir():
        for existing_file in sorted(mirror_root.rglob("*")):
            if not existing_file.is_file():
                continue
            resolved = existing_file.resolve()
            if resolved in known_destinations:
                continue
            actions.append(
                SyncAction(
                    operation="delete",
                    source=None,
                    destination=resolved,
                    reason=(
                        "no longer covered by a registered EXTERNAL_HOOK_SCRIPT_MIRRORS "
                        "entry for a plugin currently in plugin_mirrors"
                    ),
                )
            )
    return SyncPlan(actions=tuple(actions))


def _atomic_write(destination: Path, data: bytes, *, source: Path | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = destination.parent / f".{destination.name}.tmp"
    tmp_path.write_bytes(data)
    if source is not None:
        # A mirrored destination is supposed to be a faithful copy of its canonical source --
        # not just byte-identical content, but the same permission bits too. write_bytes() always
        # creates the new file at the process's default mode (no execute bits, regardless of the
        # source's own mode), so an executable hook/bin script loses its executable bit on every
        # create/update unless explicitly restored here. shutil.copymode copies permission bits
        # only (not owner/group), which is exactly the git-tracked distinction (100644 vs 100755).
        shutil.copymode(source, tmp_path)
    os.replace(tmp_path, destination)


def apply_sync_plan(plan: SyncPlan) -> SyncResult:
    blocking = [a for a in plan.actions if a.operation == "collision"]
    if blocking:
        raise SyncError(
            "refusing to apply a plan containing unresolved collisions: "
            + "; ".join(a.reason for a in blocking)
        )

    applied: list[SyncAction] = []
    for action in plan.actions:
        if action.operation in ("create", "update"):
            if action.content is not None:
                data = action.content
                _atomic_write(action.destination, data)
            else:
                assert action.source is not None
                data = action.source.read_bytes()
                _atomic_write(action.destination, data, source=action.source)
            applied.append(action)
        elif action.operation == "delete":
            action.destination.unlink(missing_ok=True)
            applied.append(action)
        # "warn" and "missing_excepted" actions are never executed -- the former is
        # purely informational, the latter is a blocking signal that still must
        # never auto-write incorrect (canonical-source) bytes to the destination.

    return SyncResult(applied=tuple(applied))


def apply_hooks_merge_plan(plan: HooksMergePlan) -> SyncResult:
    applied: list[SyncAction] = []
    for action in plan.actions:
        data = (json.dumps(plan.merged_document, indent=2) + "\n").encode("utf-8")
        _atomic_write(action.destination, data)
        applied.append(action)
    return SyncResult(applied=tuple(applied))


def _staged_path_set(repo: Path) -> set[str]:
    return {
        path
        for change in GitState(repo=repo).staged_paths()
        for path in (change.old_path, change.new_path)
        if path is not None
    }


def _is_fully_staged(repo: Path, path: Path) -> bool:
    """True when `path` has no unstaged worktree changes on top of what's staged -- i.e. the
    index content `git diff --cached` shows for it is the same content actually on disk.

    `plan_plugin_sync`/`plan_exports` read a canonical source's *working-tree* bytes
    (`source.read_bytes()`), not its staged (index) content. If a source is only partially
    staged (some hunks staged, some not), the generated destination gets built from the fuller
    working-tree version and then staged as if it matched -- `check_staged_parity` then rejects
    the commit, since the staged destination no longer byte-matches the staged source. Same
    Y-character check `git-lint-staged-python.sh` already uses for the identical reason.

    `:(top,literal)` anchors the match to the repo root regardless of `cwd` -- but that magic
    word only makes sense applied to a repo-relative pathspec; `path` itself may be absolute
    (every `SyncAction.source`/`HooksMergePlan.sources` entry is), so it's resolved relative to
    `repo` first.

    `--ignored` is required for a path under `.claude/` (as `stage_settings_hooks_result`
    checks): some machines' *global* gitignore excludes `.claude`/`.codex`/`.agents`
    everywhere (the exact reason `_git_add_forced` below already force-adds with `-f`) --
    without `--ignored`, plain `git status --porcelain` silently omits such a path
    entirely, and the "nothing pending" branch below would then wrongly report a
    genuinely untracked, real-content file as "trivially fully staged" (found by Codex's
    cross-model review, round 4, live-reproduced against this repo's own machine-global
    `.claude` exclusion). Harmless for every existing caller's own use (canonical sources
    under `plugins/`, never machine-ignored) -- `--ignored` only ever reveals *additional*
    untracked-and-ignored state; it never hides or changes a result for an already-tracked
    path.
    """
    rel_path = path.resolve().relative_to(repo.resolve()).as_posix()
    result = subprocess.run(
        ["git", "status", "--porcelain", "-z", "--ignored", "--", f":(top,literal){rel_path}"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    entries = result.stdout.split(b"\0")
    if not entries or not entries[0]:
        return True  # nothing pending for this path at all -- trivially fully staged
    status_line = entries[0].decode("utf-8", errors="surrogateescape")
    return status_line[1:2] == " "


def _git_add_forced(repo: Path, destination: Path) -> None:
    # -f: a generated destination under .claude/.codex/.agents is a deliberately tracked file
    # regardless of what a machine-local global gitignore says about those directory names (some
    # machines exclude them everywhere) -- same override the test suite's own
    # GitRepoHelper.stage() already applies for the identical reason.
    #
    # A destination path here is untrusted plugin content on a fetched or contributed branch;
    # it reaches `git` as a single literal argv element via `subprocess.run`'s list form -- never
    # interpolated into a shell command string -- so the shell never re-parses it and no
    # quoting/injection concern applies regardless of what characters the path contains.
    try:
        subprocess.run(["git", "add", "-f", "--", str(destination)], cwd=repo, check=True)
    except subprocess.CalledProcessError as exc:
        raise SyncError(f"git add failed for {destination}: {exc}") from exc


def stage_generated_destinations(repo: Path, actions: tuple[SyncAction, ...]) -> tuple[Path, ...]:
    """Stage each applied create/update action's destination, but only when its own canonical
    `source` is already staged in this commit *and* that source has no unstaged changes on top
    (see `_is_fully_staged`) -- leaving an unrelated repair (drift the sync happened to also fix)
    or a partially-staged source's mismatched destination untouched on disk, unstaged.
    """
    staged = _staged_path_set(repo)
    repo_resolved = repo.resolve()
    staged_destinations: list[Path] = []
    for action in actions:
        if action.operation not in ("create", "update") or action.source is None:
            continue
        rel_source = action.source.resolve().relative_to(repo_resolved).as_posix()
        if rel_source not in staged or not _is_fully_staged(repo, action.source):
            continue
        _git_add_forced(repo, action.destination)
        staged_destinations.append(action.destination)
    return tuple(staged_destinations)


def stage_hooks_merge_result(repo: Path, plan: HooksMergePlan) -> tuple[Path, ...]:
    """Stage the merged `hooks.json` destination(s) when at least one contributing per-plugin
    `hooks/hooks.json` (or the repo-level hooks path) is staged, or a contributing source was
    itself staged as a deletion -- but only when *every remaining* contributing source is fully
    staged (or untouched). `plan.merged_document` was built from *all* contributors' working-tree
    bytes at once (`plan_hooks_merge` reads each with `path.read_text(...)`, not from the index),
    so if even one contributor has unstaged edits, the merge already reflects content that isn't
    actually staged for that contributor -- staging the result regardless of the *other*
    contributors' state would let unstaged hook behavior ride into the commit silently, since
    `check_staged_parity` deliberately excludes top-level hook manifests from its own check.

    The merge has no single 1:1 canonical source the way `plan_plugin_sync`/`plan_exports` do --
    one destination is built from N contributing files -- so `stage_generated_destinations`
    (which requires exactly one `action.source`) never covers it; every `HooksMergePlan` action
    carries `source=None`. Without this, staging a canonical `plugins/<name>/hooks/hooks.json`
    change leaves the regenerated `.claude/hooks/hooks.json` unstaged and unstageable by
    `--stage`, silently narrowing coverage versus the old fully-manual step 8 flow this replaced.
    """
    staged = _staged_path_set(repo)
    repo_resolved = repo.resolve()
    any_staged_source = False
    for source in plan.sources:
        try:
            rel_source = source.resolve().relative_to(repo_resolved).as_posix()
        except ValueError:
            continue  # a source outside the repo (e.g. a caller-supplied external path) can't
            # be "staged" in this repo's index at all
        if not _is_fully_staged(repo, source):
            return ()  # this contributor's unstaged content already leaked into merged_document
        if rel_source in staged:
            any_staged_source = True

    # A contributing plugin's hooks.json can be *deleted* -- `plan.sources` only lists files that
    # still exist on disk, so a staged deletion never appears there, but it still changes what the
    # merge should contain. `GitState.staged_paths()` reports only already-staged changes, so a "D"
    # entry here is guaranteed staged (no separate full-staging check needed for a removed file).
    if not any_staged_source:
        for change in GitState(repo=repo).staged_paths():
            if change.status == "D" and change.old_path is not None:
                if _HOOKS_SOURCE_PATTERN.match(change.old_path) or change.old_path == str(
                    DEFAULT_REPO_HOOKS_PATH.as_posix()
                ):
                    any_staged_source = True
                    break

    if not any_staged_source:
        return ()
    staged_destinations: list[Path] = []
    for action in plan.actions:
        _git_add_forced(repo, action.destination)
        staged_destinations.append(action.destination)
    return tuple(staged_destinations)


def stage_settings_hooks_result(repo: Path, plan: SettingsHooksSyncPlan) -> tuple[Path, ...]:
    """Stage `plan_settings_hooks_sync`'s `.claude/settings.json` destination.

    `plan.destination_safe_to_stage` is computed by `plan_settings_hooks_sync` itself,
    at plan time -- strictly *before* `apply_sync_plan` ever writes the regenerated
    bytes to disk. Checking `.claude/settings.json`'s own staged/unstaged git status
    *after* that write (an earlier version of this function did exactly this) always
    sees the just-written regenerated content as "unstaged" relative to whatever the
    index still holds -- since staging that regenerated content is the whole point,
    that check could never pass for a genuine update, only for a brand-new file (found
    by Codex's cross-model review, round 5: an ordinary hooks-manifest update left
    `.claude/settings.json` permanently unstageable via `--stage`). The plan-time flag
    instead correctly captures "did this file already have real, unstaged or
    never-tracked content before this sync run touched it at all" -- the actual risk
    this function exists to guard against (found across rounds 3 and 4: an unstaged
    edit to an already-tracked settings.json, and a pre-existing-but-untracked one,
    respectively) -- and covers the brand-new-file case for free, since a nonexistent
    path is always "nothing pending."

    Delegates the contributing-hook-manifest-sources-fully-staged gate to
    `stage_hooks_merge_result`, unchanged -- `plan.actions`/`plan.sources` are the exact
    same objects `apply_sync_plan` was given and returns, so no separate "applied"
    variant is needed here.
    """
    if not plan.destination_safe_to_stage:
        return ()
    return stage_hooks_merge_result(
        repo,
        HooksMergePlan(
            actions=plan.actions,
            merged_document=plan.rewritten_hooks_document,
            sources=plan.sources,
        ),
    )
