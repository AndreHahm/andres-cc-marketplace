"""Stable command-line interface for scripts.marketplace_ci.

Exit codes: 0 = pass, 1 = policy failure, 2 = invalid invocation/configuration.

Every handler below imports its own dependencies inside its function body,
not at module level (issue #351, direction #3). This is what makes the
review-dispatch-critical subcommands (check-scope-bypass, run-codex-review,
check-bypass, resolve-attested-actor) provably never load sync.py/
validators.py/pr_policy.py (Tier 2) at all: `python -m scripts.marketplace_ci
<subcommand>` only ever executes the one handler function `args.handler`
resolves to, and Python only runs a function's own `import` statements when
that function actually executes. Module-level imports here would defeat
this -- they'd all run unconditionally on every invocation, regardless of
which subcommand was requested. See tests/marketplace_ci/test_import_isolation.py
for the test proving this guarantee actually holds."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

PR_TEMPLATE_RELATIVE_PATH = Path(".github/pull_request_template.md")

REGISTRY_RELATIVE_PATH = Path(".claude/marketplace-sync.json")


def _split_nul_delimited_paths(raw: bytes) -> list[str]:
    """Split `git diff -z --name-only` output on NUL and decode each path.
    Plain newline-splitting a non-`-z` `git diff --name-only` call is unsafe
    for scope decisions: with git's default `core.quotePath=true`, a path
    containing non-ASCII or control bytes is emitted C-quoted (e.g.
    `"plugins/d\303\253mo/skills/x/SKILL.md"`), which then fails every
    `path.startswith("plugins/")`-style prefix check downstream -- silently
    routing a real component change into light/bypass-eligible mode. `-z`
    disables quoting and NUL-delimits instead, which a security review
    flagged as the fix after this repo's own reviewer-scope bypass made
    that mis-parse's consequence "no review runs at all" instead of just
    "this one reviewer misses a path". `errors="surrogateescape"`: git
    emits raw filesystem bytes, which on Linux need not be valid UTF-8 --
    a strict decode would raise and crash the caller on a byte sequence
    that just needs to survive a prefix check, not round-trip perfectly."""
    return [p for p in raw.decode("utf-8", errors="surrogateescape").split("\0") if p]


def _load_registry(repo: Path):
    from scripts.marketplace_ci.registry import Registry

    return Registry.load(repo / REGISTRY_RELATIVE_PATH)


def _load_previous_registry(repo: Path):
    from scripts.marketplace_ci.registry import Registry

    result = subprocess.run(
        ["git", "show", f"HEAD:{REGISTRY_RELATIVE_PATH.as_posix()}"],
        cwd=repo,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return Registry.loads(
        result.stdout.decode("utf-8"), source="HEAD:" + REGISTRY_RELATIVE_PATH.as_posix()
    )


def _report(label: str, actions, repo: Path) -> bool:
    """Print each action using a repo-relative posix path; return True if any
    non-warn action exists."""
    has_problem = False
    for action in actions:
        try:
            shown = action.destination.relative_to(repo).as_posix()
        except ValueError:
            shown = action.destination.as_posix()
        print(f"[{label}] {action.operation}: {shown} - {action.reason}")
        if action.operation != "warn":
            has_problem = True
    return has_problem


def _repo_rules_path(repo: Path) -> Path | None:
    from scripts.marketplace_ci.sync_plan import DEFAULT_REPO_RULES_PATH

    candidate = repo / DEFAULT_REPO_RULES_PATH
    return candidate if candidate.is_dir() else None


def _handle_check_plugin_mirrors(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.registry import RegistryError
    from scripts.marketplace_ci.sync import (
        SyncError,
        plan_external_hook_scripts_mirror,
        plan_hooks_merge,
        plan_settings_hooks_sync,
    )
    from scripts.marketplace_ci.sync_plan import plan_plugin_sync

    repo = Path.cwd()
    try:
        registry = _load_registry(repo)
    except RegistryError as exc:
        print(f"check-plugin-mirrors: {exc}", file=sys.stderr)
        return 2
    plan = plan_plugin_sync(
        repo, registry, previous=None, bootstrap=False, repo_rules_path=_repo_rules_path(repo)
    )
    # Also verify the live .claude/settings.json hooks key and .claude/hooks/_external-scripts/
    # mirror -- without this, a hook-manifest or external-script change could leave the
    # actually-live artifacts stale while this read-only check still reports success, since
    # neither was previously wired into any verification path (found by Codex's cross-model
    # review of this same change, round 5). hooks_plan itself (plan_hooks_merge) is
    # deliberately NOT re-checked here -- that's a pre-existing gap predating this change
    # (.claude/hooks/hooks.json has never had a dedicated check step; only sync-plugin-mirrors/
    # repair-all apply it), out of scope for this fix.
    hooks_plan = plan_hooks_merge(repo, registry)
    try:
        external_scripts_plan = plan_external_hook_scripts_mirror(repo, registry)
        settings_hooks_plan = plan_settings_hooks_sync(repo, hooks_plan)
    except SyncError as exc:
        print(f"check-plugin-mirrors: {exc}", file=sys.stderr)
        return 1
    all_actions = (*plan.actions, *external_scripts_plan.actions, *settings_hooks_plan.actions)
    if not all_actions:
        print("check-plugin-mirrors: OK")
        return 0
    has_problem = _report("mirrors", plan.actions, repo)
    has_problem = (
        _report("external-hook-scripts", external_scripts_plan.actions, repo) or has_problem
    )
    has_problem = _report("settings-hooks", settings_hooks_plan.actions, repo) or has_problem
    if not has_problem:
        print("check-plugin-mirrors: OK (informational warnings only)")
    return 1 if has_problem else 0


def _handle_sync_plugin_mirrors(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.registry import RegistryError
    from scripts.marketplace_ci.sync import (
        SyncError,
        SyncPlan,
        apply_hooks_merge_plan,
        apply_sync_plan,
        plan_external_hook_scripts_mirror,
        plan_hooks_merge,
        plan_settings_hooks_sync,
        stage_generated_destinations,
        stage_hooks_merge_result,
        stage_settings_hooks_result,
    )
    from scripts.marketplace_ci.sync_plan import plan_plugin_sync

    repo = Path.cwd()
    try:
        registry = _load_registry(repo)
    except RegistryError as exc:
        print(f"sync-plugin-mirrors: {exc}", file=sys.stderr)
        return 2
    plan = plan_plugin_sync(
        repo, registry, previous=None, bootstrap=False, repo_rules_path=_repo_rules_path(repo)
    )
    try:
        result = apply_sync_plan(plan)
    except SyncError as exc:
        print(f"sync-plugin-mirrors: {exc}", file=sys.stderr)
        return 1
    hooks_plan = plan_hooks_merge(repo, registry)
    hooks_result = apply_hooks_merge_plan(hooks_plan)
    try:
        external_scripts_plan = plan_external_hook_scripts_mirror(repo, registry)
        external_scripts_result = apply_sync_plan(external_scripts_plan)
        settings_hooks_plan = plan_settings_hooks_sync(repo, hooks_plan)
        settings_hooks_result = apply_sync_plan(SyncPlan(actions=settings_hooks_plan.actions))
    except SyncError as exc:
        print(f"sync-plugin-mirrors: {exc}", file=sys.stderr)
        return 1
    applied_count = (
        len(result.applied)
        + len(hooks_result.applied)
        + len(external_scripts_result.applied)
        + len(settings_hooks_result.applied)
    )
    print(f"sync-plugin-mirrors: applied {applied_count} action(s)")
    if getattr(args, "stage", False):
        try:
            staged = stage_generated_destinations(repo, result.applied)
            staged += stage_hooks_merge_result(repo, hooks_plan)
            staged += stage_generated_destinations(repo, external_scripts_result.applied)
            staged += stage_settings_hooks_result(repo, settings_hooks_plan)
        except SyncError as exc:
            print(f"sync-plugin-mirrors: {exc}", file=sys.stderr)
            return 1
        for path in staged:
            shown = path.resolve().relative_to(repo.resolve()).as_posix()
            print(f"sync-plugin-mirrors: staged {shown}")
    return 0


def _handle_check_token_shapes(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.sync_plan import SyncError
    from scripts.marketplace_ci.token_shapes import plan_token_shapes_sync

    repo = Path.cwd()
    try:
        plan = plan_token_shapes_sync(repo)
    except SyncError as exc:
        print(f"check-token-shapes: {exc}", file=sys.stderr)
        return 2
    if not plan.actions:
        print("check-token-shapes: OK")
        return 0
    _report("token-shapes", plan.actions, repo)
    print("check-token-shapes: consumer copies differ; run sync-token-shapes")
    return 1


def _handle_sync_token_shapes(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.sync import apply_sync_plan
    from scripts.marketplace_ci.sync_plan import SyncError
    from scripts.marketplace_ci.token_shapes import plan_token_shapes_sync

    repo = Path.cwd()
    try:
        result = apply_sync_plan(plan_token_shapes_sync(repo))
    except SyncError as exc:
        print(f"sync-token-shapes: {exc}", file=sys.stderr)
        return 2
    print(f"sync-token-shapes: applied {len(result.applied)} action(s)")
    if result.applied:
        # The .claude/ copies are generated mirrors of the plugin copies; check-plugin-mirrors
        # (part of check-all) fails until they follow.
        print("sync-token-shapes: now run sync-plugin-mirrors so the .claude/ mirrors follow")
    return 0


def _handle_check_codex_exports(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.conversion import find_legacy_command_exports, plan_exports
    from scripts.marketplace_ci.registry import RegistryError

    repo = Path.cwd()
    legacy = find_legacy_command_exports(repo)
    if legacy:
        for path in legacy:
            print(f"check-codex-exports: blocking legacy command export: {path}")
        return 1
    try:
        registry = _load_registry(repo)
    except RegistryError as exc:
        print(f"check-codex-exports: {exc}", file=sys.stderr)
        return 2
    plan = plan_exports(repo, registry, previous=None)
    if not plan.actions:
        print("check-codex-exports: OK")
        return 0
    has_problem = _report("exports", plan.actions, repo)
    if not has_problem:
        print("check-codex-exports: OK (informational warnings only)")
    return 1 if has_problem else 0


def _handle_convert_codex_exports(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.conversion import plan_exports
    from scripts.marketplace_ci.registry import RegistryError
    from scripts.marketplace_ci.sync import SyncError, apply_sync_plan, stage_generated_destinations

    repo = Path.cwd()
    try:
        registry = _load_registry(repo)
    except RegistryError as exc:
        print(f"convert-codex-exports: {exc}", file=sys.stderr)
        return 2
    plan = plan_exports(repo, registry, previous=None)
    try:
        result = apply_sync_plan(plan)
    except SyncError as exc:
        print(f"convert-codex-exports: {exc}", file=sys.stderr)
        return 1
    print(f"convert-codex-exports: applied {len(result.applied)} action(s)")
    if getattr(args, "stage", False):
        try:
            staged = stage_generated_destinations(repo, result.applied)
        except SyncError as exc:
            print(f"convert-codex-exports: {exc}", file=sys.stderr)
            return 1
        for path in staged:
            shown = path.resolve().relative_to(repo.resolve()).as_posix()
            print(f"convert-codex-exports: staged {shown}")
    return 0


def _handle_check_prefixes(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.prefix_check import find_prefix_violations

    repo = Path.cwd()
    violations = find_prefix_violations(repo)
    if not violations:
        print("check-prefixes: OK")
        return 0
    for violation in violations:
        try:
            shown = violation.path.relative_to(repo).as_posix()
        except ValueError:
            shown = violation.path.as_posix()
        print(f"[prefixes] {violation.plugin}: {shown} - {violation.reason}")
    return 1


def _handle_check_prefix_permanence(args: argparse.Namespace) -> int:
    """PR-review-time enforcement that a plugin's registered component-file
    prefix (plugin-rulebook R33) is actually permanent -- compares
    marketplace-inventory.json's plugins[].prefix between --base-sha and
    the current working tree, failing if any record that had a non-null
    prefix at base is now missing, or has a different prefix, at head.
    reconcile.apply_update's own write-once guard only protects the CLI
    tool's own update path; this is the layer that also catches a
    hand-edited inventory file or a delete-and-rebootstrap committed
    directly in a PR (security-reviewer finding, M2). Not part of
    check-all: unlike every other check-all constituent, this one needs a
    base ref to compare against, which check-all's own callers (local dev,
    the `commit` skill) don't have -- kept as its own subcommand, the same
    pattern check-scope-bypass/run-codex-review already use for a
    --base-sha-dependent check."""
    from scripts.marketplace_ci.prefix_check import find_prefix_permanence_violations

    repo = Path.cwd()
    base_sha = args.base_sha

    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", f"{base_sha}^{{commit}}"], cwd=repo, capture_output=True
    )
    if resolved.returncode != 0:
        print(f"check-prefix-permanence: cannot resolve base SHA {base_sha!r}", file=sys.stderr)
        return 2

    # Load the BASE inventory first, before deciding anything about head --
    # a PR that deletes marketplace-inventory.json entirely must still be
    # compared against base, not treated as an early "nothing to check"
    # pass. Found by a live Codex cross-model-review pass (F2): the
    # original version short-circuited to OK on a missing head file before
    # ever loading base, which let a whole-file deletion silently bypass
    # this check -- exactly the "delete and re-bootstrap" bypass this
    # subcommand exists to catch, just via outright deletion instead.
    show = subprocess.run(
        ["git", "show", f"{base_sha}:.claude-plugin/marketplace-inventory.json"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if show.returncode != 0:
        if "does not exist" in show.stderr or "exists on disk, but not in" in show.stderr:
            # Genuinely absent at base (this PR introduces
            # marketplace-inventory.json for the first time) -- nothing to
            # compare against, not a failure.
            print(
                "check-prefix-permanence: OK (no marketplace-inventory.json at base "
                f"{base_sha!r} -- nothing to compare)"
            )
            return 0
        # Any other `git show` failure (corrupt object, unreadable repo,
        # etc) is a real infrastructure problem -- same exit-2 distinction
        # check-scope-bypass/run-codex-review's own git-command failure
        # paths already use, never silently treated as a clean pass.
        print(
            f"check-prefix-permanence: git show {base_sha!r} failed: {show.stderr}", file=sys.stderr
        )
        return 2

    try:
        base_inventory = json.loads(show.stdout)
    except json.JSONDecodeError as exc:
        print(f"check-prefix-permanence: base inventory is not valid JSON: {exc}", file=sys.stderr)
        return 2

    head_path = repo / ".claude-plugin" / "marketplace-inventory.json"
    if not head_path.is_file():
        # Absent at head but present (and just successfully loaded) at
        # base -- treat as an empty inventory rather than short-circuiting
        # to OK. find_prefix_permanence_violations then correctly reports
        # every base-registered prefix as "record no longer exists", the
        # same violation a partial deletion would produce.
        head_inventory: dict = {"plugins": []}
    else:
        try:
            head_inventory = json.loads(head_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(
                f"check-prefix-permanence: head inventory is not valid JSON: {exc}", file=sys.stderr
            )
            return 2

    violations = find_prefix_permanence_violations(base_inventory, head_inventory, repo=repo)
    if not violations:
        print("check-prefix-permanence: OK")
        return 0
    for violation in violations:
        print(
            f"[prefix-permanence] {violation.plugin_id} "
            f"({violation.plugin_name!r}): {violation.reason}"
        )
    return 1


def _handle_check_all(args: argparse.Namespace) -> int:
    repo = Path.cwd()

    if getattr(args, "staged", False):
        from scripts.marketplace_ci.validators import check_staged_parity

        # Fast pre-commit stage: compare the Git index only, never the
        # working tree — see check_staged_parity's own docstring for why.
        result = check_staged_parity(repo)
        for message in result.messages:
            print(f"[staged-parity] {message}")
        if result.exit_code == 0:
            print("check-all --staged: OK")
        if getattr(args, "json_output", None):
            payload = {"staged_parity": result.exit_code, "exit_code": result.exit_code}
            Path(args.json_output).write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
        return result.exit_code

    # Full pre-push stage: by the time a push happens, the working tree is
    # assumed to already match the given committed ref (pre-push runs after
    # the commit(s) it's about to push, not mid-edit) — so this reuses the
    # same filesystem-based checks --committed's caller would otherwise get
    # from a plain `check-all`, without a separate checkout of that ref.
    committed_ref = getattr(args, "committed", None)
    if committed_ref:
        resolved = subprocess.run(
            ["git", "rev-parse", "--verify", committed_ref], cwd=repo, capture_output=True
        )
        if resolved.returncode != 0:
            print(f"check-all --committed: cannot resolve ref {committed_ref!r}", file=sys.stderr)
            return 2

    mirrors_rc = _handle_check_plugin_mirrors(args)
    exports_rc = _handle_check_codex_exports(args)
    prefixes_rc = _handle_check_prefixes(args)
    token_shapes_rc = _handle_check_token_shapes(args)
    rc = (
        2
        if (mirrors_rc == 2 or exports_rc == 2 or prefixes_rc == 2 or token_shapes_rc == 2)
        else (1 if (mirrors_rc or exports_rc or prefixes_rc or token_shapes_rc) else 0)
    )

    if getattr(args, "json_output", None):
        payload = {
            "check_plugin_mirrors": mirrors_rc,
            "check_codex_exports": exports_rc,
            "check_prefixes": prefixes_rc,
            "check_token_shapes": token_shapes_rc,
            "exit_code": rc,
        }
        Path(args.json_output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return rc


def _handle_repair_all(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.conversion import plan_exports
    from scripts.marketplace_ci.registry import RegistryError
    from scripts.marketplace_ci.sync import (
        SyncError,
        SyncPlan,
        apply_hooks_merge_plan,
        apply_sync_plan,
        plan_external_hook_scripts_mirror,
        plan_hooks_merge,
        plan_settings_hooks_sync,
    )
    from scripts.marketplace_ci.sync_plan import plan_plugin_sync

    repo = Path.cwd()
    try:
        registry = _load_registry(repo)
    except RegistryError as exc:
        print(f"repair-all: {exc}", file=sys.stderr)
        return 2

    previous = _load_previous_registry(repo) if args.bootstrap else None
    rules_path = _repo_rules_path(repo)

    mirror_plan = plan_plugin_sync(
        repo, registry, previous=previous, bootstrap=args.bootstrap, repo_rules_path=rules_path
    )
    export_plan = plan_exports(repo, registry, previous=previous, bootstrap=args.bootstrap)
    hooks_plan = plan_hooks_merge(repo, registry)
    try:
        external_scripts_plan = plan_external_hook_scripts_mirror(repo, registry)
        settings_hooks_plan = plan_settings_hooks_sync(repo, hooks_plan)
    except SyncError as exc:
        print(f"repair-all: {exc}", file=sys.stderr)
        return 1

    all_actions = (
        *mirror_plan.actions,
        *export_plan.actions,
        *hooks_plan.actions,
        *external_scripts_plan.actions,
        *settings_hooks_plan.actions,
    )
    if not all_actions:
        print("repair-all: nothing to do")
        return 0

    _report("mirrors", mirror_plan.actions, repo)
    _report("exports", export_plan.actions, repo)
    _report("hooks", hooks_plan.actions, repo)
    _report("external-hook-scripts", external_scripts_plan.actions, repo)
    _report("settings-hooks", settings_hooks_plan.actions, repo)

    if args.bootstrap and not args.apply:
        print("repair-all: bootstrap plan printed above; re-run with --apply to execute")
        return 0

    try:
        mirror_result = apply_sync_plan(mirror_plan)
        export_result = apply_sync_plan(export_plan)
        hooks_result = apply_hooks_merge_plan(hooks_plan)
        external_scripts_result = apply_sync_plan(external_scripts_plan)
        settings_hooks_result = apply_sync_plan(SyncPlan(actions=settings_hooks_plan.actions))
    except SyncError as exc:
        print(f"repair-all: {exc}", file=sys.stderr)
        return 1

    applied_count = (
        len(mirror_result.applied)
        + len(export_result.applied)
        + len(hooks_result.applied)
        + len(external_scripts_result.applied)
        + len(settings_hooks_result.applied)
    )
    print(f"repair-all: applied {applied_count} action(s)")
    return 0


def _handle_check_pr(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.pr_policy import (
        TRUSTED_BOT_LOGINS,
        RealGitHubApi,
        commits_verified_from_trusted_bot,
        evaluate_pr_policy,
    )

    repo = Path.cwd()
    event_path = Path(args.event)
    try:
        event = json.loads(event_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"check-pr: cannot read event file {event_path}: {exc}", file=sys.stderr)
        return 2

    try:
        pr = event["pull_request"]
        title = pr["title"]
        body = pr.get("body") or ""
        user = pr["user"]["login"]
        base_repo = pr["base"]["repo"]
        owner = base_repo["owner"]["login"]
        full_name = base_repo["full_name"]
        base_sha = pr["base"]["sha"]
        head_sha = pr["head"]["sha"]
    except (KeyError, TypeError) as exc:
        print(f"check-pr: event file missing expected field: {exc}", file=sys.stderr)
        return 2

    template_path = repo / PR_TEMPLATE_RELATIVE_PATH
    template = template_path.read_text(encoding="utf-8") if template_path.is_file() else ""

    diff = subprocess.run(
        ["git", "diff", "-z", "--name-only", "--no-renames", f"{base_sha}...{head_sha}"],
        cwd=repo,
        capture_output=True,
    )
    if diff.returncode != 0:
        # A failed diff must never silently substitute an empty path list:
        # check_merge_rights (pr_policy.py) treats "no CODEOWNERS match" as
        # a fall-through to the more permissive collaborator-permission
        # branch -- an empty changed_paths list gets exactly that fallback
        # for free, the same fail-open shape a security review flagged for
        # the C-quoted-path parsing bug this function's own -z fix closes.
        print(f"check-pr: git diff {base_sha!r}...{head_sha!r} failed", file=sys.stderr)
        return 2
    changed_paths = _split_nul_delimited_paths(diff.stdout)

    api = RealGitHubApi(owner=owner, user=user, full_name=full_name, repo=repo)
    bot_commits_verified = user.lower() in TRUSTED_BOT_LOGINS and commits_verified_from_trusted_bot(
        full_name, pr.get("number"), head_sha, pr.get("commits")
    )
    result = evaluate_pr_policy(
        api,
        title=title,
        body=body,
        template=template,
        changed_paths=changed_paths,
        bot_commits_verified=bot_commits_verified,
    )

    for label, check in (("title", result.title), ("template", result.template)):
        status = "PASS" if check.passed else "FAIL"
        suffix = f" - {check.reason}" if check.reason else ""
        print(f"check-pr [{label}]: {status}{suffix}")
    for label, rights in (
        ("pr-privilege", result.pr_privilege),
        ("merge-privilege", result.merge_privilege),
    ):
        status = "PASS" if rights.allowed else "FAIL"
        suffix = f" - {rights.reason}" if rights.reason else ""
        print(f"check-pr [{label}]: {status}{suffix}")

    return 0 if result.passed else 1


def _handle_handle_post_edit(args: argparse.Namespace) -> int:
    """Reads Claude Code's PostToolUse hook JSON from stdin, returns Claude
    hook JSON on stdout. Never raises and never exits non-zero — a sync
    failure is reported via `systemMessage`, matching this hook's own
    `onError: warn` posture (report and fall back to pre-commit, never block
    the turn)."""
    from scripts.marketplace_ci.registry import RegistryError
    from scripts.marketplace_ci.sync import SyncError
    from scripts.marketplace_ci.validators import run_post_edit

    repo = Path.cwd()
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("{}")
        return 0

    file_path = (payload.get("tool_input") or {}).get("file_path")
    if not file_path:
        print("{}")
        return 0

    try:
        rel_path = Path(file_path).resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        print("{}")  # edit outside this repo; not our concern
        return 0

    try:
        result = run_post_edit(repo, rel_path)
    except (RegistryError, SyncError) as exc:
        print(json.dumps({"systemMessage": f"marketplace-ci post-edit sync failed: {exc}"}))
        return 0

    if result.changed:
        print(json.dumps({"systemMessage": f"marketplace-ci: synced {', '.join(result.changed)}"}))
    else:
        print("{}")
    return 0


def _handle_run_delta_structural_checks(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.git_state import ChangedPath
    from scripts.marketplace_ci.review import run_delta_structural_checks

    repo = Path.cwd()
    changed = tuple(ChangedPath(status="M", old_path=p, new_path=p) for p in args.changed)
    findings = run_delta_structural_checks(repo, changed)
    if not findings:
        print("run-delta-structural-checks: OK")
        return 0
    for finding in findings:
        print(f"[structural] {finding.operation}: {finding.path} - {finding.reason}")
    return 1


def _handle_prepare_reviewer_instruction(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.review import prepare_reviewer_instruction

    repo = Path.cwd()
    try:
        prepare_reviewer_instruction(
            args.agent, base_sha=args.base_sha, out=Path(args.out), repo=repo
        )
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    print(f"prepare-reviewer-instruction: wrote {args.out}")
    return 0


def _handle_prepare_review(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.git_state import ChangedPath
    from scripts.marketplace_ci.review import derive_review_scope

    changed = tuple(ChangedPath(status="M", old_path=p, new_path=p) for p in args.changed)
    # No cross-component dependency graph exists yet in this plan; an empty
    # index is an honest default, not a silent omission — see review.py's
    # derive_review_scope docstring and design v4's own scoping notes.
    scope = derive_review_scope(changed, {})
    payload = {
        "mode": scope.mode,
        "structural_check": scope.structural_check,
        "validate": list(scope.validate),
        "audit": list(scope.audit),
        "paths": list(scope.paths),
    }
    output = json.dumps(payload, indent=2)
    if args.json_output:
        Path(args.json_output).write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


def _handle_check_review_output(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.review import ReviewOutputError, validate_review_output

    path = Path(args.file)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"check-review-output: cannot read {path}: {exc}", file=sys.stderr)
        return 2
    try:
        result = validate_review_output(data)
    except ReviewOutputError as exc:
        print(f"check-review-output: {exc}", file=sys.stderr)
        return 1
    print(
        f"check-review-output: OK ({len(result.findings)} finding(s), blocking={result.blocking})"
    )
    return 0


def _handle_check_bypass(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.review import check_bypass, parse_attestation_marker

    event_path = Path(args.event)
    try:
        data = json.loads(event_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"check-bypass: cannot read event file {event_path}: {exc}", file=sys.stderr)
        return 2

    try:
        label_event = {"actor": data["actor"], "sha": data["head_sha"]}
    except KeyError as exc:
        print(f"check-bypass: event file missing expected field: {exc}", file=sys.stderr)
        return 2

    raw_comments = data.get("comments", [])
    permission = data.get("permission")
    parsed_comments = [
        marker for body in raw_comments if (marker := parse_attestation_marker(body)) is not None
    ]
    result = check_bypass(label_event, parsed_comments, permission=permission)
    status = "ALLOWED" if result.allowed else "DENIED"
    suffix = f" - {result.reason}" if result.reason else ""
    print(f"check-bypass: {status}{suffix}")
    return 0 if result.allowed else 1


def _handle_resolve_attested_actor(args: argparse.Namespace) -> int:
    from scripts.marketplace_ci.review import attestation_candidates, resolve_attested_actor

    path = Path(args.comments_with_login)
    try:
        comments = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"resolve-attested-actor: cannot read {path}: {exc}", file=sys.stderr)
        return 2

    if not isinstance(comments, list) or not all(
        isinstance(c, dict) and isinstance(c.get("body", ""), str) for c in comments
    ):
        print(
            f"resolve-attested-actor: {path} must contain a JSON array of {{login, body}} objects",
            file=sys.stderr,
        )
        return 2

    if args.list_candidates:
        # Distinct attesting logins in first-seen order, one per line, so the
        # caller can look up each one's live permission before resolving.
        logins = list(dict.fromkeys(attestation_candidates(comments, args.head_sha)))
        if not logins:
            return 1
        print("\n".join(logins))
        return 0

    permissions = None
    if args.permissions is not None:
        permissions_path = Path(args.permissions)
        try:
            permissions = json.loads(permissions_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            print(f"resolve-attested-actor: cannot read {permissions_path}: {exc}", file=sys.stderr)
            return 2
        if not isinstance(permissions, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in permissions.items()
        ):
            print(
                f"resolve-attested-actor: {permissions_path} must contain a JSON object of "
                "login -> permission strings",
                file=sys.stderr,
            )
            return 2

    actor = resolve_attested_actor(comments, args.head_sha, permissions)
    if actor is None:
        return 1
    print(actor)
    return 0


def _handle_check_scope_bypass(args: argparse.Namespace) -> int:
    """Automatic, scope-derived counterpart to check-bypass's manual
    SHA-bound attestation: computes whether the diff since --base-sha has
    nothing for any Codex reviewer to look at (is_bypass_eligible), then
    requires --before/--after (only present on a `synchronize` event) to
    positively confirm this push didn't absorb new commits from the base
    branch before ever reporting eligible=True. Both missing -- any event
    other than `synchronize` (opened/reopened/edited/labeled), none of
    which reliably prove no rebase happened since the PR's last synchronize
    -- fails closed to eligible=False, the same as a detected rebase. A
    security review found the earlier "only check if both happen to be
    given" version silently skippable: editing the PR title after a rebase
    push re-ran this check with no before/after and reported eligible=True
    again, defeating the rebase carve-out entirely. Exits 0 on a computed
    decision (bypass_eligible in the JSON payload either way), 2 only on an
    infrastructure failure the caller must treat as not-eligible."""
    from scripts.marketplace_ci.review import (
        PrDeltaError,
        compute_pr_delta,
        derive_review_scope,
        is_bypass_eligible,
        rebase_onto_base_absorbed,
    )

    repo = Path.cwd()
    base_sha = args.base_sha

    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", f"{base_sha}^{{commit}}"], cwd=repo, capture_output=True
    )
    if resolved.returncode != 0:
        print(f"check-scope-bypass: cannot resolve base SHA {base_sha!r}", file=sys.stderr)
        return 2

    try:
        changed = compute_pr_delta(repo, base_sha)
    except PrDeltaError as exc:
        print(f"check-scope-bypass: {exc}", file=sys.stderr)
        return 2

    scope = derive_review_scope(changed, {})
    eligible = is_bypass_eligible(scope)
    reason = f"mode={scope.mode}, validate={len(scope.validate)}, audit={len(scope.audit)}"

    if eligible:
        if not (args.before and args.after):
            eligible = False
            reason = (
                "no before/after SHA available to confirm this push is rebase-free "
                "(only present on a synchronize event) -- failing closed"
            )
        elif rebase_onto_base_absorbed(
            base_sha=base_sha, before=args.before, after=args.after, repo=repo
        ):
            eligible = False
            reason = (
                "rebase onto base branch absorbed new commits this push, or before/after "
                "could not be resolved -- full review required either way"
            )

    payload = {"bypass_eligible": eligible, "mode": scope.mode, "reason": reason}
    output_text = json.dumps(payload, indent=2)
    if args.json_output:
        Path(args.json_output).write_text(output_text + "\n", encoding="utf-8")
    print(output_text)
    return 0


def _handle_check_trust_boundary(args: argparse.Namespace) -> int:
    """Local, informational-only preview of the codex-review job's
    hard-refuse trust-boundary gate (marketplace-ci.yml, issue #351) --
    warns if this branch's diff since --target touches a Tier-1
    (review-dispatch-critical) file, so a push doesn't land in CI as a
    surprise. Never fails: this is a developer convenience, not a policy
    gate -- the real gate in CI is still what decides.

    Diffs against `PRE_COMMIT_TO_REF` when set -- the actual object a
    pre-push hook invocation is pushing, per pre-commit's own pre-push
    stage (it parses git's `<local ref> <local oid> <remote ref>
    <remote oid>` pre-push contract and exposes the local oid this way) --
    falling back to `HEAD` otherwise (e.g. a manual `check-trust-boundary`
    run, or `pre-commit run` with no real push event). `HEAD` alone is
    wrong whenever the pushed ref isn't what's currently checked out (e.g.
    `git push origin other-branch` while on a different branch) -- Codex's
    automated PR review caught this, PR #372, 2026-09-22, confirmed via a
    live repro against pre-commit's real pre-push hook."""
    from scripts.marketplace_ci.trust_boundary import find_tier1_touches

    repo = Path.cwd()
    to_ref = os.environ.get("PRE_COMMIT_TO_REF") or "HEAD"
    base_ref = subprocess.run(
        ["git", "merge-base", args.target, to_ref], cwd=repo, capture_output=True, text=True
    )
    if base_ref.returncode != 0:
        print(
            f"check-trust-boundary: could not resolve merge-base with {args.target!r} "
            f"(is it fetched locally?) -- skipping local preview",
            file=sys.stderr,
        )
        return 0

    try:
        touched = find_tier1_touches(base_ref.stdout.strip(), repo, to_ref=to_ref)
    except subprocess.CalledProcessError:
        print(
            "check-trust-boundary: could not compute the Tier-1 diff -- skipping local preview",
            file=sys.stderr,
        )
        return 0

    if touched:
        print(
            "check-trust-boundary: this push touches review-dispatch-critical file(s) "
            f"({', '.join(sorted(touched))}) -- codex-review's trust-boundary gate will "
            "refuse automated dispatch in CI and require a manual bypass attestation, "
            "unless this content is already identical to the target branch (e.g. a stale "
            "local base -- try syncing this branch first). See docs/ci.md.",
            file=sys.stderr,
        )
    return 0


def _finding_to_dict(
    finding, in_diff: bool | None = None, blocking: bool | None = None, decision=None
) -> dict:
    entry = decision.exception if decision is not None else None
    return {
        "reviewer": finding.reviewer,
        "severity": finding.severity,
        "rule": finding.rule,
        "path": finding.path,
        "line": finding.line,
        "evidence": finding.evidence,
        "remediation": finding.remediation,
        "reporters": list(finding.reporters),
        "components": list(finding.components),
        "in_diff": in_diff,
        "blocking": blocking,
        "confidence": finding.confidence,
        "evidence_type": finding.evidence_type,
        "rule_class": finding.rule_class,
        "risk": dict(finding.risk) or None,
        "source": finding.source,
        "gate": decision.outcome if decision is not None else None,
        "suppressed": decision is not None and decision.outcome == "suppressed",
        "exception": (
            {"rule": entry.rule, "path": entry.path, "authority": entry.authority}
            if entry is not None
            else None
        ),
    }


def _diff_scope(
    findings, repo: Path, base_sha: str, changed_paths, precomputed_ranges=None, exceptions=()
):
    """(blocking, in_diff, diff_scoped) for the aggregated findings. A
    Major/Critical on a line this PR changed blocks; every other finding stays
    in the artifact as a non-blocking notice. `in_diff` is None, and every
    Critical/Major blocks, when the changed lines could not be computed.
    `precomputed_ranges` is `(compute_changed_line_ranges(...),)`, passed in so
    the reviewers' briefing and this gate use one computation (the one element
    may itself be None, meaning "could not be computed"); left out, the ranges
    are computed here."""
    from scripts.marketplace_ci.review import (
        compute_changed_line_ranges,
        gate_decision,
        split_findings_by_diff,
    )

    if precomputed_ranges is not None:
        ranges = precomputed_ranges[0]
    else:
        ranges = compute_changed_line_ranges(repo, base_sha)
    # git prints repo-root-relative paths whatever the working directory is, so
    # symlink checks must resolve them against the git root, not against cwd.
    root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.rstrip("\n")
    gated = {
        f
        for f in findings
        if gate_decision(f, in_diff=True, exceptions=exceptions).outcome == "block"
    }
    if ranges is None:
        return gated, None, False
    # One classification pass (one tree lookup); blocking is the gated subset of
    # the findings on a changed line, so the two sets can never disagree.
    in_diff = set(
        split_findings_by_diff(findings, ranges, changed_paths=changed_paths, repo_root=Path(root))[
            0
        ]
    )
    return gated & in_diff, in_diff, True


def _git_out(repo: Path, *argv: str) -> str | None:
    """Trimmed stdout of a git command, or None when it fails or prints nothing. Goes through
    review.py's shared `_run_git` so this module adds no subprocess call site of its own."""
    from scripts.marketplace_ci.review import _run_git

    try:
        out = _run_git(repo, *argv).decode("utf-8", errors="replace").strip()
    except RuntimeError:
        return None
    return out or None


def _run_provenance(repo: Path, base_sha: str | None, reports: Sequence) -> dict:
    """What a review ran on, recorded in every result shape so an artifact can be read
    without the log: the PR head (second parent on the merge ref), the checked-out merge
    ref, the base the delta used, and the model and CLI version the reviewers reported."""
    merge_ref_sha = _git_out(repo, "rev-parse", "HEAD")
    second_parent = _git_out(repo, "rev-parse", "--verify", "-q", "HEAD^2")
    reported: dict[str, str | None] = {"model": None, "cli_version": None}
    for report in reports:
        envelope = report.output.get("provenance") if isinstance(report.output, dict) else None
        if not isinstance(envelope, dict):
            continue
        for key in reported:
            value = envelope.get(key)
            if reported[key] is None and isinstance(value, str):
                reported[key] = value
    return {
        "head_sha": second_parent or merge_ref_sha,
        "merge_ref_sha": merge_ref_sha,
        "base_sha": base_sha,
        **reported,
    }


def _reviewer_results(reports: Sequence, failed: Sequence[str] = ()) -> dict:
    """Per reviewer: `could_not_run` when the dispatch failed, its output is missing or has no
    findings list, or the caller names it in `failed` (its envelope did not validate); else
    `findings` or `clean` by whether its envelope reported any finding."""
    results = {}
    for report in reports:
        findings = report.output.get("findings") if isinstance(report.output, dict) else None
        if report.status == "failed" or report.reviewer in failed or not isinstance(findings, list):
            status = "could_not_run"
        else:
            status = "findings" if findings else "clean"
        results[report.reviewer] = {"status": status, "attempts": report.attempts}
    return results


def _fail_run_codex_review(
    args: argparse.Namespace,
    message: str,
    reports: Sequence = (),
    failed: Sequence[str] = (),
) -> int:
    """Report an infrastructure failure of `run-codex-review` (exit 2): the log
    line, plus a machine-readable copy in `--output` so the uploaded artifact
    always reflects this run (a stale file from the PR checkout is overwritten,
    never published as if it were this run's result). Nothing else reads it."""
    print(f"run-codex-review: {message}", file=sys.stderr)
    if args.output:
        from scripts.marketplace_ci.review import _MAX_ERROR_CHARS

        failure = {
            "status": "could_not_run",
            "blocking": True,
            "error": message[:_MAX_ERROR_CHARS],
            "reviewer_results": _reviewer_results(reports, failed),
            "provenance": _run_provenance(Path.cwd(), getattr(args, "base_sha", None), reports),
        }
        Path(args.output).write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
    return 2


def _instructions_dir_problem(path: Path, repo: Path, output: str | None) -> str | None:
    """Why `--instructions-dir` can't be used, or None. The reviewers write files
    into it, so it must be a new path outside the checkout: an existing directory
    or symlink would be written through, one inside the checkout would leave
    scratch files in a shippable location, and one equal to or below `--output`
    would turn the result file's path into a directory."""
    if path.is_symlink() or path.exists():
        return f"--instructions-dir {str(path)!r} already exists; pass a new path"
    resolved = path.resolve()
    if output and Path(output).resolve() in (resolved, *resolved.parents):
        return "--instructions-dir must not be --output or below it"
    if (path.parent.resolve() / path.name).is_relative_to(repo.resolve()):
        return f"--instructions-dir {str(path)!r} is inside the checkout; use a scratch directory"
    return None


def _verifier_result(outcome) -> dict:
    """One verifier's entry in the result file. A file it could not read is a finding of its own, so
    `clean` always means every candidate file was read and judged."""
    return {
        "name": outcome.name,
        "status": "findings" if outcome.findings else "clean",
        "findings": len(outcome.findings),
        "checked": len(outcome.checked),
    }


def _handle_run_codex_review(args: argparse.Namespace) -> int:
    """The single entry point the Codex GitHub Actions workflow calls: scope
    the diff since `base_sha`, run the deterministic structural check
    in-process, dispatch every Codex reviewer directly (no outer
    Codex-executed skill), validate every returned envelope, and aggregate.
    Exit 2 on any infrastructure failure (unresolvable base SHA, dispatch
    failure, malformed output) — never silently treated as a passing review.
    Exit 1 only for a genuine blocking finding (see _diff_scope: a Major/Critical
    on a changed line).
    """
    from scripts.marketplace_ci import review_contract, review_verifiers
    from scripts.marketplace_ci.review import (
        FULL_ESCALATION_PATHS,
        PrDeltaError,
        ReviewOutputError,
        ReviewResult,
        _changed_path_set,
        aggregate_findings,
        collapse_identical_mirrors,
        compute_changed_line_ranges,
        compute_pr_delta,
        derive_review_scope,
        dispatch_reviewers,
        gate_decision,
        run_delta_structural_checks,
        validate_review_output,
    )

    repo = Path.cwd()
    base_sha = args.base_sha

    # Read before anything is dispatched or claimed: a gate that cannot read its exceptions
    # must stop, not run as if there were none.
    try:
        exceptions = review_contract.load_exceptions(review_contract.EXCEPTIONS_PATH)
    except review_contract.ContractError as exc:
        return _fail_run_codex_review(args, f"exceptions registry unusable: {exc}")

    instructions_dir = Path(args.instructions_dir) if args.instructions_dir else None
    if instructions_dir is not None:
        problem = _instructions_dir_problem(instructions_dir, repo, args.output)
        if problem:
            return _fail_run_codex_review(args, problem)

    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", f"{base_sha}^{{commit}}"], cwd=repo, capture_output=True
    )
    if resolved.returncode != 0:
        return _fail_run_codex_review(args, f"cannot resolve base SHA {base_sha!r}")

    try:
        changed = collapse_identical_mirrors(repo, compute_pr_delta(repo, base_sha), base_sha)
    except PrDeltaError as exc:
        return _fail_run_codex_review(args, str(exc))

    scope = derive_review_scope(changed, {})

    if scope.mode == "full" and not scope.validate and not scope.audit:
        # derive_review_scope populates a real reviewer set for both known
        # full-mode triggers (a shared-governance path edit, or a dependency
        # closure over the size limit) -- always including DELTA_VALIDATE's
        # own baseline, never just the governance-specific set alone, so
        # escalation can never dispatch fewer reviewers than the equivalent
        # non-escalated delta scope would have. This branch is reachable
        # only when a governance path is in FULL_ESCALATION_PATHS but has no
        # matching entry in FULL_MODE_GOVERNANCE_REVIEWERS -- derive_review_scope
        # itself detects that gap and deliberately returns an empty scope
        # here rather than raising or silently dropping the missing
        # reviewer. Dispatching an empty scope.validate/audit would silently
        # report a clean pass with zero actual review coverage, so fail
        # closed instead.
        triggering_paths = [p for p in scope.paths if p in FULL_ESCALATION_PATHS]
        reason = (
            f"shared-governance path(s): {', '.join(triggering_paths)}"
            if triggering_paths
            else f"dependency closure ({len(scope.paths)} affected paths, over the limit)"
        )
        return _fail_run_codex_review(
            args,
            "mode=full escalation has no defined reviewer "
            "dispatch for this trigger -- this requires human review, not an "
            f"automated pass. Trigger: {reason}",
        )

    structural_findings = run_delta_structural_checks(repo, changed)
    try:
        verifier_outcomes = review_verifiers.run_verifiers(repo, changed)
    except Exception as exc:  # fail closed: a verifier that crashed is not a clean pass
        return _fail_run_codex_review(args, f"script verifier failed: {exc!r}")
    changed_ranges = compute_changed_line_ranges(repo, base_sha)
    if instructions_dir is not None:
        # Claim it exclusively and privately: the validation above is only a check, and
        # `mkdir(exist_ok=True)` later would accept a path planted since, symlinks included.
        try:
            instructions_dir.parent.mkdir(parents=True, exist_ok=True)
            instructions_dir.mkdir(mode=0o700)
        except OSError as exc:
            return _fail_run_codex_review(
                args, f"cannot claim --instructions-dir {str(instructions_dir)!r}: {exc}"
            )
    try:
        reports = dispatch_reviewers(
            scope,
            base_sha=base_sha,
            repo=repo,
            instructions_dir=instructions_dir,
            changed_ranges=changed_ranges,
            changed_paths=_changed_path_set(changed),
            exceptions=exceptions,
        )
    except OSError as exc:
        # Raised only before any reviewer starts (e.g. the default instruction
        # directory would land inside the checkout); per-reviewer faults are
        # already reported as failed reports.
        return _fail_run_codex_review(args, f"cannot prepare reviewer dispatch: {exc}")

    failed_reports = [r for r in reports if r.status == "failed"]
    if failed_reports:
        print(
            f"run-codex-review: reviewer dispatch failed for: "
            f"{[r.reviewer for r in failed_reports]}",
            file=sys.stderr,
        )
        for r in failed_reports:
            print(
                f"run-codex-review:   {r.reviewer} (attempts: {r.attempts}): {r.error}",
                file=sys.stderr,
            )
        if args.output:
            # A machine-readable copy of the failure for the uploaded artifact
            # (the log line carries the same text); nothing else reads this file.
            failure_payload = {
                "mode": scope.mode,
                "dispatch_failed": [
                    {"reviewer": r.reviewer, "attempts": r.attempts, "error": r.error}
                    for r in failed_reports
                ],
                "reviewer_attempts": {r.reviewer: r.attempts for r in reports},
                "status": "could_not_run",
                "reviewer_results": _reviewer_results(reports),
                "provenance": _run_provenance(repo, base_sha, reports),
                "blocking": True,
            }
            Path(args.output).write_text(
                json.dumps(failure_payload, indent=2) + "\n", encoding="utf-8"
            )
        return 2

    validated = []
    unusable: list[tuple[str, str]] = []  # (reviewer, why), in dispatch order
    for report in reports:
        if report.output is None:
            unusable.append((report.reviewer, "completed with no output"))
            continue
        try:
            validated.append(validate_review_output(report.output))
        except ReviewOutputError as exc:
            unusable.append((report.reviewer, f"returned invalid output: {exc}"))
    if unusable:
        # Every report is checked before failing, so each unusable one is marked in the artifact
        # and none reads as a completed review just because it came after the first bad one.
        first_reviewer, first_reason = unusable[0]
        message = f"{first_reviewer} {first_reason}"
        if len(unusable) > 1:
            message += f" (also unusable: {', '.join(name for name, _ in unusable[1:])})"
        return _fail_run_codex_review(args, message, reports, [name for name, _ in unusable])

    # Script findings join the model findings before aggregation, so the gate, dedup and the result
    # file treat both alike (`source` stays part of the dedup key and the gate's inputs).
    validated.extend(
        ReviewResult(reviewer=outcome.name, verdict="script", findings=outcome.findings)
        for outcome in verifier_outcomes
    )
    findings = aggregate_findings(validated)
    try:
        blocking_set, in_diff, diff_scoped = _diff_scope(
            findings,
            repo,
            base_sha,
            _changed_path_set(changed),
            (changed_ranges,),
            exceptions,
        )
    except Exception as exc:  # fail closed: exit 2 and overwrite the output file
        return _fail_run_codex_review(args, f"diff-scoped classification failed: {exc!r}", reports)
    blocking = bool(blocking_set)
    structural_blocking = len(structural_findings) > 0

    payload = {
        "mode": scope.mode,
        "reviewed_paths": list(scope.paths),
        "reviewers": [r.reviewer for r in reports],
        "reviewer_attempts": {r.reviewer: r.attempts for r in reports},
        "status": "findings" if (findings or structural_findings) else "clean",
        "reviewer_results": _reviewer_results(reports),
        "provenance": _run_provenance(repo, base_sha, reports),
        "structural_findings": [
            {"path": f.path, "operation": f.operation, "reason": f.reason}
            for f in structural_findings
        ],
        "verifiers": [_verifier_result(outcome) for outcome in verifier_outcomes],
        "diff_scoped": diff_scoped,
        "exceptions_loaded": len(exceptions),
        "findings": [
            _finding_to_dict(
                f,
                None if in_diff is None else f in in_diff,
                f in blocking_set,
                gate_decision(f, in_diff=in_diff is None or f in in_diff, exceptions=exceptions),
            )
            for f in findings
        ],
        "blocking": blocking or structural_blocking,
    }
    output_text = json.dumps(payload, indent=2)
    if args.output:
        Path(args.output).write_text(output_text + "\n", encoding="utf-8")
    print(output_text)

    return 1 if (blocking or structural_blocking) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scripts.marketplace_ci")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "check-plugin-mirrors", help="verify .claude mirrors match the registry"
    ).set_defaults(handler=_handle_check_plugin_mirrors)

    sync_mirrors = subparsers.add_parser("sync-plugin-mirrors", help="apply .claude mirror parity")
    sync_mirrors.add_argument(
        "--stage",
        action="store_true",
        help="also `git add` each applied destination whose own canonical source is already staged",
    )
    sync_mirrors.set_defaults(handler=_handle_sync_plugin_mirrors)

    subparsers.add_parser(
        "check-codex-exports", help="verify .agents/.codex exports match the registry"
    ).set_defaults(handler=_handle_check_codex_exports)

    convert_exports = subparsers.add_parser(
        "convert-codex-exports", help="apply .agents/.codex export parity"
    )
    convert_exports.add_argument(
        "--stage",
        action="store_true",
        help="also `git add` each applied destination whose own canonical source is already staged",
    )
    convert_exports.set_defaults(handler=_handle_convert_codex_exports)

    subparsers.add_parser(
        "check-token-shapes", help="verify each plugin's secret token-shapes copy matches canonical"
    ).set_defaults(handler=_handle_check_token_shapes)

    subparsers.add_parser(
        "sync-token-shapes", help="copy the canonical secret token shapes into each plugin"
    ).set_defaults(handler=_handle_sync_token_shapes)

    subparsers.add_parser(
        "check-prefixes", help="verify plugin-root files carry their registered prefix"
    ).set_defaults(handler=_handle_check_prefixes)

    check_prefix_permanence = subparsers.add_parser(
        "check-prefix-permanence",
        help="verify no plugin's registered prefix was reassigned or dropped since --base-sha",
    )
    check_prefix_permanence.add_argument("--base-sha", required=True, metavar="SHA")
    check_prefix_permanence.set_defaults(handler=_handle_check_prefix_permanence)

    check_all = subparsers.add_parser("check-all", help="run every deterministic check")
    check_all.add_argument("--json-output", metavar="PATH", help="also write a JSON report")
    check_all.add_argument(
        "--staged", action="store_true", help="fast pre-commit check: Git index only"
    )
    check_all.add_argument(
        "--committed", metavar="REF", help="pre-push check: verify the given ref resolves"
    )
    check_all.set_defaults(handler=_handle_check_all)

    repair_all = subparsers.add_parser(
        "repair-all", help="reconcile mirrors/exports/hooks against the registry"
    )
    repair_all.add_argument(
        "--bootstrap", action="store_true", help="also reconcile unregistered destinations"
    )
    repair_all.add_argument(
        "--apply", action="store_true", help="execute a --bootstrap plan (otherwise plan-only)"
    )
    repair_all.set_defaults(handler=_handle_repair_all)

    check_pr = subparsers.add_parser("check-pr", help="validate a PR event against policy")
    check_pr.add_argument("--event", required=True, metavar="PATH", help="PR event JSON path")
    check_pr.set_defaults(handler=_handle_check_pr)

    subparsers.add_parser(
        "handle-post-edit", help="PostToolUse hook: cascade a canonical edit to mirror/export"
    ).set_defaults(handler=_handle_handle_post_edit)

    run_delta = subparsers.add_parser(
        "run-delta-structural-checks", help="scope check-all's structural checks to changed paths"
    )
    run_delta.add_argument("--changed", required=True, nargs="+", metavar="PATH")
    run_delta.set_defaults(handler=_handle_run_delta_structural_checks)

    prepare_instruction = subparsers.add_parser(
        "prepare-reviewer-instruction",
        help="extract a reviewer's developer_instructions from a validated base SHA",
    )
    prepare_instruction.add_argument("--agent", required=True, metavar="NAME")
    prepare_instruction.add_argument("--base-sha", required=True, metavar="SHA")
    prepare_instruction.add_argument("--out", required=True, metavar="PATH")
    prepare_instruction.set_defaults(handler=_handle_prepare_reviewer_instruction)

    prepare_review = subparsers.add_parser(
        "prepare-review", help="compute a ReviewScope for the given changed paths"
    )
    prepare_review.add_argument("--changed", required=True, nargs="+", metavar="PATH")
    prepare_review.add_argument("--json-output", metavar="PATH")
    prepare_review.set_defaults(handler=_handle_prepare_review)

    check_review_output = subparsers.add_parser(
        "check-review-output", help="validate a reviewer's structured output envelope"
    )
    check_review_output.add_argument("--file", required=True, metavar="PATH")
    check_review_output.set_defaults(handler=_handle_check_review_output)

    check_bypass_parser = subparsers.add_parser(
        "check-bypass", help="validate a SHA-bound bypass attestation"
    )
    check_bypass_parser.add_argument("--event", required=True, metavar="PATH")
    check_bypass_parser.set_defaults(handler=_handle_check_bypass)

    resolve_actor_parser = subparsers.add_parser(
        "resolve-attested-actor",
        help="resolve which real GitHub commenter attested a bypass for a given head SHA",
    )
    resolve_actor_parser.add_argument("--comments-with-login", required=True, metavar="PATH")
    resolve_actor_parser.add_argument("--head-sha", required=True, metavar="SHA")
    resolve_mode = resolve_actor_parser.add_mutually_exclusive_group()
    resolve_mode.add_argument(
        "--list-candidates",
        action="store_true",
        help="print the distinct attesting logins (one per line) instead of resolving one",
    )
    resolve_mode.add_argument(
        "--permissions",
        metavar="PATH",
        help="JSON object of login -> permission; only bypass-capable non-bot logins are eligible",
    )
    resolve_actor_parser.set_defaults(handler=_handle_resolve_attested_actor)

    check_scope_bypass = subparsers.add_parser(
        "check-scope-bypass",
        help="compute whether a PR's diff is eligible for the automatic reviewer-scope bypass",
    )
    check_scope_bypass.add_argument("--base-sha", required=True, metavar="SHA")
    check_scope_bypass.add_argument(
        "--before", default="", metavar="SHA", help="pre-push head SHA (synchronize event only)"
    )
    check_scope_bypass.add_argument(
        "--after", default="", metavar="SHA", help="post-push head SHA (synchronize event only)"
    )
    check_scope_bypass.add_argument("--json-output", metavar="PATH")
    check_scope_bypass.set_defaults(handler=_handle_check_scope_bypass)

    run_codex_review = subparsers.add_parser(
        "run-codex-review",
        help="scope, dispatch, validate, and aggregate a full Codex delta review",
    )
    run_codex_review.add_argument("--base-sha", required=True, metavar="SHA")
    run_codex_review.add_argument("--output", metavar="PATH")
    run_codex_review.add_argument(
        "--instructions-dir",
        metavar="PATH",
        help="new directory outside the checkout for the per-reviewer instruction files "
        "(default: a temporary directory, removed afterwards on a best-effort basis)",
    )
    run_codex_review.set_defaults(handler=_handle_run_codex_review)

    check_trust_boundary = subparsers.add_parser(
        "check-trust-boundary",
        help="local, warn-only preview of codex-review's Tier-1 trust-boundary gate",
    )
    check_trust_boundary.add_argument(
        "--target", default="origin/main", metavar="REF", help="branch to diff against"
    )
    check_trust_boundary.set_defaults(handler=_handle_check_trust_boundary)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 2
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
