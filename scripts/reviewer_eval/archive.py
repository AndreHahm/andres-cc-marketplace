"""Archive the CI `codex-review-result` artifacts of a PR (Phase 4 of #568, issue #586).

GitHub keeps the artifacts 90 days and the limit cannot be raised, so scoring reads copies
committed under `reviewer-eval/archive/pr-<pr>/<head8>-<run id>-<artifact id>.json`. A PR's
artifacts are the ones whose workflow run was for a commit that is currently in that PR: a head
that was force-pushed away is no longer listed by GitHub and is not archived.

The artifact is untrusted data. It is only unzipped by exact member name, bounded in size and
parsed as JSON; nothing in it is executed or used to build a path. Only artifacts of a run in this
repository (never a fork's, whose workflow file is the fork author's own) on the PR's own head
branch are taken, so a stacked PR's shared commit does not pull in another PR's runs.

Run it from a checkout you trust: on Windows `gh` can resolve from the current directory before
`PATH`, and a symlink already committed under the output directory is a path this script writes
through.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

RESULT_NAME = "codex-review-result.json"
MAX_RESULT_BYTES = 2_000_000
MAX_ARTIFACT_BYTES = 2 * MAX_RESULT_BYTES
_HEAD_SHA = re.compile(r"[0-9a-f]{40}")
_ARTIFACT_FIELDS = (
    "id",
    "expired",
    "head_sha",
    "run_id",
    "head_branch",
    "size_in_bytes",
    "repository_id",
    "head_repository_id",
)


class ArchiveError(Exception):
    """An artifact or listing that cannot be used."""


@dataclass
class Report:
    written: int = 0
    skipped_existing: int = 0
    expired: int = 0
    failed: list[str] = field(default_factory=list)


class Source(Protocol):
    def list_artifacts(self) -> list[dict]: ...
    def pr_heads(self, pr: int) -> list[str]: ...
    def pr_branch(self, pr: int) -> str: ...
    def download(self, artifact_id: int) -> bytes: ...


def select_artifacts(
    listing: list[dict], heads: set[str], branch: str
) -> tuple[list[dict], list[dict]]:
    """The artifacts of `heads` from this repository's runs on `branch`: those still
    downloadable, and those that have expired."""
    of_heads = [
        a
        for a in listing
        if a["head_sha"] in heads
        and a["head_branch"] == branch
        and a["repository_id"] == a["head_repository_id"]
    ]
    return [a for a in of_heads if not a["expired"]], [a for a in of_heads if a["expired"]]


def archive_path(root: Path, pr: int, head_sha: str, run_id: int, artifact_id: int) -> Path:
    """The artifact id is in the name because re-running a job gives one run several artifacts,
    and each is a separate sample of the same head."""
    if isinstance(pr, bool) or not isinstance(pr, int) or pr < 1:
        raise ArchiveError(f"pr is not a positive integer: {pr!r}")
    if not _HEAD_SHA.fullmatch(head_sha):
        raise ArchiveError(f"head sha is not 40 lowercase hex characters: {head_sha!r}")
    for name, value in (("run id", run_id), ("artifact id", artifact_id)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ArchiveError(f"{name} is not a positive integer: {value!r}")
    return root / f"pr-{pr}" / f"{head_sha[:8]}-{run_id}-{artifact_id}.json"


def _reject_constant(name: str) -> None:
    """NaN and Infinity are not JSON, and a file holding them would fail strict parsers."""
    raise ValueError(f"non-finite constant {name}")


def extract_result(payload: bytes) -> dict:
    """The review result inside an artifact zip, which must hold exactly that one JSON object."""
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
            if bundle.namelist() != [RESULT_NAME]:
                raise ArchiveError(f"artifact must contain only {RESULT_NAME}")
            info = bundle.getinfo(RESULT_NAME)
            if info.file_size > MAX_RESULT_BYTES:
                raise ArchiveError(f"{RESULT_NAME} is larger than {MAX_RESULT_BYTES} bytes")
            with bundle.open(info) as member:
                data = member.read(MAX_RESULT_BYTES + 1)
    except ArchiveError:
        raise
    except Exception as exc:  # noqa: BLE001 -- a hostile zip raises many classes (encrypted flag, unknown method, corrupt stream)
        raise ArchiveError(f"artifact cannot be read as a zip file ({type(exc).__name__})") from exc
    if len(data) > MAX_RESULT_BYTES:
        raise ArchiveError(f"{RESULT_NAME} is larger than {MAX_RESULT_BYTES} bytes")
    try:
        result = json.loads(data, parse_constant=_reject_constant)
    except Exception as exc:  # noqa: BLE001 -- also RecursionError from deeply nested input
        raise ArchiveError(f"{RESULT_NAME} is not valid JSON ({type(exc).__name__})") from exc
    if not isinstance(result, dict):
        raise ArchiveError(f"{RESULT_NAME} must be a JSON object")
    return result


def parse_artifact_lines(text: str) -> list[dict]:
    """One JSON object per line, as printed by `gh api --paginate --jq`; each needs the fields
    `select_artifacts` and `archive_path` read."""
    rows = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise ArchiveError(f"artifact listing line {number} is not JSON") from exc
        if not isinstance(row, dict) or any(key not in row for key in _ARTIFACT_FIELDS):
            raise ArchiveError(f"artifact listing line {number} lacks one of {_ARTIFACT_FIELDS}")
        rows.append(row)
    return rows


def archive_pr(pr: int, root: Path, source: Source) -> Report:
    """Copy every downloadable result of `pr` that is not archived yet. An existing file is never
    overwritten, and one bad artifact is reported without stopping the rest."""
    report = Report()
    selected, expired = select_artifacts(
        source.list_artifacts(), set(source.pr_heads(pr)), source.pr_branch(pr)
    )
    report.expired = len(expired)
    for artifact in selected:
        label = f"run {artifact['run_id']} (artifact {artifact['id']})"
        try:
            target = archive_path(
                root, pr, artifact["head_sha"], artifact["run_id"], artifact["id"]
            )
            if os.path.lexists(target):
                report.skipped_existing += 1
                continue
            if artifact["size_in_bytes"] > MAX_ARTIFACT_BYTES:
                raise ArchiveError(f"artifact is larger than {MAX_ARTIFACT_BYTES} bytes")
            result = extract_result(source.download(artifact["id"]))
            provenance = result.get("provenance")
            if isinstance(provenance, dict) and provenance.get("head_sha") != artifact["head_sha"]:
                raise ArchiveError("provenance names a different head than the run's")
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                # "x" fails on any existing path, a dangling symlink included, and cannot race.
                with open(target, "x", encoding="utf-8") as handle:
                    handle.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
            except FileExistsError:
                report.skipped_existing += 1
                continue
            report.written += 1
        except (ArchiveError, OSError, ValueError) as exc:
            report.failed.append(f"{label}: {exc}")
    return report


class GhSource:
    """Reads the current repository through the `gh` CLI, whose `{owner}/{repo}` placeholders
    resolve from the checkout it runs in."""

    def __init__(self) -> None:
        gh = shutil.which("gh")
        if gh is None:
            raise ArchiveError("the gh CLI is not on PATH")
        self._gh = gh

    def _api(self, *argv: str) -> bytes:
        try:
            done = subprocess.run(  # noqa: S603 -- fixed executable, list argv, no shell
                [self._gh, "api", *argv], capture_output=True, check=False, timeout=300
            )
        except subprocess.TimeoutExpired as exc:
            raise ArchiveError("gh api timed out") from exc
        if done.returncode != 0:
            raise ArchiveError(f"gh api failed: {done.stderr.decode('utf-8', 'replace').strip()}")
        return done.stdout

    def list_artifacts(self) -> list[dict]:
        jq = (
            ".artifacts[] | {id, expired, size_in_bytes, head_sha: .workflow_run.head_sha, "
            "run_id: .workflow_run.id, head_branch: .workflow_run.head_branch, "
            "repository_id: .workflow_run.repository_id, "
            "head_repository_id: .workflow_run.head_repository_id}"
        )
        out = self._api(
            "--paginate",
            "repos/{owner}/{repo}/actions/artifacts?name=codex-review-result&per_page=100",
            "--jq",
            jq,
        )
        return parse_artifact_lines(out.decode("utf-8"))

    def pr_heads(self, pr: int) -> list[str]:
        out = self._api(
            "--paginate", f"repos/{{owner}}/{{repo}}/pulls/{int(pr)}/commits", "--jq", ".[].sha"
        )
        return out.decode("utf-8").split()

    def pr_branch(self, pr: int) -> str:
        out = self._api(f"repos/{{owner}}/{{repo}}/pulls/{int(pr)}", "--jq", ".head.ref")
        return out.decode("utf-8").strip()

    def download(self, artifact_id: int) -> bytes:
        return self._api(f"repos/{{owner}}/{{repo}}/actions/artifacts/{int(artifact_id)}/zip")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reviewer_eval.archive", description=__doc__)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--out", default="reviewer-eval/archive")
    args = parser.parse_args(argv)
    try:
        report = archive_pr(args.pr, Path(args.out), GhSource())
    except ArchiveError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(
        f"PR {args.pr}: {report.written} written, {report.skipped_existing} already archived, "
        f"{report.expired} expired, {len(report.failed)} failed"
    )
    for line in report.failed:
        print(f"  failed: {line}", file=sys.stderr)
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
