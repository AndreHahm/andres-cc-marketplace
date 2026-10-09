"""Keeps the hand-copied trusted-restore blocks in marketplace-ci.yml consistent.

Four jobs (hygiene, prefix-permanence, compute-scope, publish) restore trusted
code from the base SHA before running Python next to a token or a trust
decision, and codex-review refuses instead (it cannot restore: its reviewers
must see the PR's real files). Each job carries its own copy of the same shell
block because a workflow cannot share one across jobs without a composite
action that would itself be PR-controlled. Nothing but this test notices one
copy drifting from the others.
"""

from __future__ import annotations

import posixpath
import re
import subprocess
from pathlib import Path

import pytest

from scripts.marketplace_ci.review import BYPASS_INELIGIBLE_PREFIXES
from scripts.marketplace_ci.trust_boundary import TIER1_FILES, find_tier1_touches

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "marketplace-ci.yml"
TEXT = WORKFLOW.read_text(encoding="utf-8")

RESTORE_STEP_FRAGMENTS = (
    "PR-contract check code",
    "prefix-check code",
    "scope-decision code",
    "bypass-validation code",
)
REFUSE_STEP_NAME = (
    "Refuse automated Codex dispatch when this PR adds an importable top-level shadow"
)
NAME_PATTERN = r"^[^/]+\.(py|pyc|pyw|pyd|so)$|^[^/]+/__init__\.[^/]+$|^\.venv(/|$)"


def _run_block(step_name_fragment: str) -> list[str]:
    """The body lines of the `run: |` block of the step whose name contains the fragment."""
    lines = TEXT.split("\n")
    start = next(
        i
        for i, line in enumerate(lines)
        if line.strip().startswith("- name:") and step_name_fragment in line
    )
    run = next(i for i in range(start, start + 8) if lines[i].strip() == "run: |")
    run_indent = len(lines[run]) - len(lines[run].lstrip())
    body: list[str] = []
    for line in lines[run + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= run_indent:
            break
        body.append(line)
    return body


def _detector_section(block: list[str]) -> list[str]:
    """The shadow-refusal section: from its comment header to the end of the block's last `fi`."""
    start = next(i for i, line in enumerate(block) if "Importable-name shadowing" in line)
    section = [re.sub(r"^\s+", "", line) for line in block[start:]]
    # Drop anything after the symlink check's closing `fi` (e.g. a trailing echo in restore jobs).
    last_fi = max(i for i, line in enumerate(section) if line == "fi")
    return [re.sub(r"refusing to .*\"$", 'refusing to X"', line) for line in section[: last_fi + 1]]


def _all_blocks() -> dict[str, list[str]]:
    blocks = {
        f"restore:{fragment}": _run_block(f"Restore the base SHA's copy of the {fragment}")
        for fragment in RESTORE_STEP_FRAGMENTS
    }
    blocks["refuse:codex-review"] = _run_block(REFUSE_STEP_NAME)
    return blocks


def test_restore_jobs_use_no_overlay_restore_never_the_overlay_checkout():
    assert 'git checkout "$BASE_SHA" -- scripts' not in TEXT
    for fragment in RESTORE_STEP_FRAGMENTS:
        block = "\n".join(_run_block(f"Restore the base SHA's copy of the {fragment}"))
        assert "set -euo pipefail" in block, fragment
        assert (
            'git restore --source="$BASE_SHA" --staged --worktree -- scripts pyproject.toml uv.lock'
            in block
        ), fragment
        # The uv/Python-version inputs are restored from base or deleted, never trusted.
        assert re.search(r"for p in uv\.toml \.python-version \.python-versions\b", block), fragment


def test_hygiene_also_restores_codeowners_and_template_inputs():
    block = "\n".join(_run_block("Restore the base SHA's copy of the PR-contract check code"))
    for path in (
        "CODEOWNERS",
        ".github/CODEOWNERS",
        "docs/CODEOWNERS",
        ".github/pull_request_template.md",
    ):
        assert path in block, path


def test_shadow_refusal_section_is_identical_in_all_five_blocks():
    sections = {name: _detector_section(block) for name, block in _all_blocks().items()}
    reference_name, reference = next(iter(sections.items()))
    for name, section in sections.items():
        assert section == reference, f"{name} drifted from {reference_name}"
    joined = "\n".join(reference)
    assert f"grep -zqE '{NAME_PATTERN}'" in joined
    # The top-level symlink comparison is NUL-aware set difference. It must never go back to
    # `grep -f`: that reads patterns one per NEWLINE, so a NUL-terminated record file collapses into
    # garbage and every PR is refused as soon as the base has a top-level symlink.
    assert "comm -z -13" in joined and "sort -z" in joined
    assert "grep -zvxFf" not in TEXT
    assert "--diff-filter=AT" in joined and "--no-renames" in joined


def _job_text(job: str) -> str:
    """The text of one top-level job: from its `  <job>:` header to the next job header."""
    lines = TEXT.split("\n")
    start = next(i for i, line in enumerate(lines) if line == f"  {job}:")
    end = next(
        (i for i in range(start + 1, len(lines)) if re.fullmatch(r"  [a-z][a-z-]*:", lines[i])),
        len(lines),
    )
    return "\n".join(lines[start:end])


TRUSTED_JOBS = ("hygiene", "prefix-permanence", "compute-scope", "codex-review", "publish")
PR_CODE_JOBS = ("python-quality", "marketplace-parity")  # deliberately run the PR's own code


def test_each_trusted_job_syncs_locked_and_config_free_and_the_pr_code_jobs_do_not():
    for job in TRUSTED_JOBS:
        body = _job_text(job)
        assert "uv sync --locked --no-config --group dev" in body, job
        assert "uv sync --group dev" not in body, job
    for job in PR_CODE_JOBS:
        body = _job_text(job)
        assert "uv sync --group dev" in body, job
        assert "--locked" not in body, job


def test_the_restore_or_refusal_runs_before_sync_and_before_any_secret_is_used():
    for job in TRUSTED_JOBS:
        body = _job_text(job)
        sync = body.index("uv sync --locked --no-config --group dev")
        assert body.index("Importable-name shadowing") < sync, job
    codex = _job_text("codex-review")
    refuse = codex.index(REFUSE_STEP_NAME)
    assert refuse < codex.index("uv sync --locked --no-config --group dev")
    assert refuse < codex.index("codex login --with-api-key")
    assert refuse < codex.index("Dispatch reviewers directly")
    # The refusal step must itself fail closed on any error.
    assert "set -euo pipefail" in "\n".join(_run_block(REFUSE_STEP_NAME))


def _scripts_shadow_pattern() -> str:
    block = "\n".join(_run_block(REFUSE_STEP_NAME))
    match = re.search(
        r"grep -zqE '(\^scripts/[^']+)' \"\$RUNNER_TEMP/scripts-added-files\.z\"", block
    )
    assert match is not None, "codex-review's scripts/ shadow refusal is missing"
    return match.group(1)


def test_codex_review_refuses_shadow_forms_below_the_top_level_of_scripts():
    pattern = re.compile(_scripts_shadow_pattern())
    must_refuse = (
        "scripts/marketplace_ci/review/__init__.py",  # package replacing review.py
        "scripts/marketplace_ci/review.so",  # extension replacing review.py
        "scripts/marketplace_ci/__main__.so",
        "scripts/marketplace_ci/pr_policy.pyc",  # sourceless bytecode
        "scripts/marketplace_ci/__pycache__/review.cpython-313.pyc",
        "scripts/__pycache__/__init__.cpython-313.pyc",
        "scripts/newpkg/__init__.py",
        "scripts/marketplace_ci/registry/helper.py",  # directory shadowing registry.py
        # A symlink is one path with no trailing slash, so the directory alternatives
        # must also match the bare name.
        "scripts/marketplace_ci/review",
        "scripts/marketplace_ci/__pycache__",
    )
    must_allow = (
        "scripts/marketplace_ci/new_tier2_module.py",
        "scripts/marketplace_ci/notes/README.md",
        "scripts/helper.sh",
        "docs/ci.md",
    )
    for path in must_refuse:
        assert pattern.search(path), path
    for path in must_allow:
        assert not pattern.search(path), path


def test_codex_review_refuses_any_symlink_added_or_retyped_under_scripts():
    block = "\n".join(_run_block(REFUSE_STEP_NAME))
    assert (
        'git diff -z --raw --no-renames --diff-filter=ATM "$PR_BASE" "$PR_HEAD_SHA" -- scripts'
        in block
    )
    match = re.search(r"grep -zqE '(\^:\[0-7\]\+ 120000 )' \"\$RUNNER_TEMP/scripts-raw\.z\"", block)
    assert match is not None, "codex-review's scripts/ symlink refusal is missing"
    header = re.compile(match.group(1))
    assert header.search(":000000 120000 0000000 1234567 A")  # added symlink
    assert header.search(":100644 120000 1234567 7654321 T")  # file retyped to a symlink
    assert not header.search(":100644 100644 1234567 7654321 M")  # ordinary edit


def test_codex_review_messages_point_at_the_attestation_not_at_editing_the_check():
    block = "\n".join(_run_block(REFUSE_STEP_NAME))
    errors = [line for line in block.split("\n") if "::error::this PR adds" in line]
    assert len(errors) == 4  # name pattern, top-level symlink, scripts/ shadow, scripts/ symlink
    for line in errors:
        assert "attest a bypass" in line, line
        assert "admin-merge" not in line, line
    # The restore jobs' refusals cannot be bypassed, so they keep the other advice.
    restore = "\n".join(_run_block("Restore the base SHA's copy of the PR-contract check code"))
    assert "admin-merge" in restore


def test_the_pr_additions_are_taken_from_the_pr_head_not_from_the_merge_ref():
    """$BASE_SHA can lag the base branch and HEAD may be the merge ref, so diffing them counts
    files the base branch gained meanwhile as the PR's own -- a refusal the Codex bypass cannot
    clear. The range must be merge-base($BASE_SHA, PR head)..PR head in every copy."""
    assert '"$BASE_SHA" HEAD' not in TEXT
    assert (
        TEXT.count('PR_BASE=$(git merge-base "$BASE_SHA" "$PR_HEAD_SHA")') == 6
    )  # 5 + codex scripts/
    assert TEXT.count("PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}") == 5
    for name, block in _all_blocks().items():
        text = "\n".join(block)
        assert 'git ls-tree -z "$PR_BASE"' in text, name
        assert 'git ls-tree -z "$PR_HEAD_SHA"' in text, name
        assert '--diff-filter=AT "$PR_BASE" "$PR_HEAD_SHA"' in text, name


SKEW_GUARD = (
    'if [ "$(git rev-parse HEAD)" != "$PR_HEAD_SHA" ] && '
    '[ "$(git rev-parse --verify -q HEAD^2 || true)" != "$PR_HEAD_SHA" ]; then'
)


def test_every_copy_fails_closed_when_the_checkout_is_not_the_events_pr_head():
    """The event payload's head SHA is frozen when the workflow fires, but the job's checkout is
    fetched when it starts. If a newer push lands in between, the diff below the guard would
    examine the old head while a newer, unexamined tree sits on disk next to the token or key.
    HEAD must be the PR head or, for a merge checkout, its second parent -- else the job stops."""
    assert TEXT.count(SKEW_GUARD) == 6  # 5 shared blocks + the codex scripts/ prelude
    for name, block in _all_blocks().items():
        text = "\n".join(block)
        guard = text.index(SKEW_GUARD)
        assert guard < text.index('PR_BASE=$(git merge-base "$BASE_SHA" "$PR_HEAD_SHA")'), name
        assert "re-run this job" in text, name
    # In codex-review the guard also precedes the scripts/-specific diffs, which run first.
    codex = "\n".join(_run_block(REFUSE_STEP_NAME))
    assert codex.index(SKEW_GUARD) < codex.index("scripts-added-files.z")


def test_the_node_chain_codex_review_runs_stays_inside_the_tier1_set():
    """bridge-invoke.mjs -> codex-exec.mjs -> cdx-process.mjs run with OPENAI_API_KEY; a
    relative import that leaves TIER1_FILES would be code the gate does not guard."""
    node_files = sorted(p for p in TIER1_FILES if p.endswith(".mjs"))
    assert len(node_files) == 3, node_files
    specifier = re.compile(r"""(?:from\s+|import\s*\(\s*|require\(\s*)["'](\.{1,2}/[^"']+)["']""")
    for rel in node_files:
        source = (REPO_ROOT / rel).read_text(encoding="utf-8")
        for target in specifier.findall(source):
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(rel), target))
            assert resolved in TIER1_FILES, f"{rel} imports {resolved}, which is not Tier 1"


def test_every_tier1_file_is_ineligible_for_the_zero_reviewer_bypass():
    for path in TIER1_FILES:
        assert any(path.startswith(prefix) for prefix in BYPASS_INELIGIBLE_PREFIXES), path


@pytest.mark.parametrize("path", sorted(TIER1_FILES))
def test_find_tier1_touches_reports_every_tier1_path(git_repo, path):
    """The local `check-trust-boundary` preview and the workflow gate share TIER1_FILES, so every
    entry (including the uv/Python-version config and the Node bridge chain) must be detected as a
    touch when a commit changes it -- a typo in a new entry would otherwise go unnoticed."""

    def commit(message: str) -> str:
        subprocess.run(["git", "add", "-A"], cwd=git_repo.root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", message], cwd=git_repo.root, check=True)
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo.root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    git_repo.write("README.md", "base")
    base = commit("base")
    git_repo.write(path, "changed")
    commit("touch a tier-1 path")

    assert find_tier1_touches(base, git_repo.root) == frozenset({path})
