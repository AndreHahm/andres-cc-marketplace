"""Chunking of a large reviewed-path set into bounded bridge calls (issue #611).

A reviewer's `--target-paths` is one comma-joined argument; one over the OS limit cannot be
exec'd, which failed every reviewer on a 4,500-path diff. These tests define the chunker and its
coverage invariant: every path lands in exactly one chunk, whatever the budgets.
"""

import json
import subprocess

import pytest

from scripts.marketplace_ci import review
from scripts.marketplace_ci.review import ReviewScope, chunk_paths, dispatch_reviewers

_FAKE_TOML_CONTENT = b'developer_instructions = """\nreview this\n"""\n'


def _paths(count: int, folders: int = 6) -> tuple[str, ...]:
    return tuple(f"pkg{i % folders}/mod{i // folders}/file{i}.py" for i in range(count))


def _joined(chunk: tuple[str, ...]) -> int:
    return len(",".join(chunk).encode())


@pytest.mark.parametrize("count", [0, 1, 7, 250, 4500])
@pytest.mark.parametrize("max_arg_bytes", [400, 5000, 24000])
def test_every_path_is_in_exactly_one_chunk(count, max_arg_bytes):
    paths = _paths(count)
    chunks = chunk_paths(paths, max_arg_bytes=max_arg_bytes)

    flat = [p for chunk in chunks for p in chunk]
    assert sorted(flat) == sorted(paths)
    assert len(flat) == len(set(flat))


def test_a_set_under_the_budget_is_one_chunk_in_the_original_order():
    paths = ("b/two.py", "a/one.py", "c/three.py")

    assert chunk_paths(paths, max_arg_bytes=24000) == (paths,)


def test_no_chunk_exceeds_the_argument_budget():
    chunks = chunk_paths(_paths(4500), max_arg_bytes=24000)

    assert len(chunks) > 1
    assert all(_joined(chunk) <= 24000 for chunk in chunks)


def test_chunking_is_deterministic_and_ignores_input_order():
    paths = _paths(900)

    assert chunk_paths(paths, max_arg_bytes=5000) == chunk_paths(
        tuple(reversed(paths)), max_arg_bytes=5000
    )


def test_a_folder_stays_together_when_it_fits():
    paths = tuple(f"alpha/f{i}.py" for i in range(10)) + tuple(f"beta/f{i}.py" for i in range(10))

    chunks = chunk_paths(paths, max_arg_bytes=_joined(paths[:10]) + 5)

    assert [{p.split("/")[0] for p in chunk} for chunk in chunks] == [{"alpha"}, {"beta"}]


def test_one_path_longer_than_the_budget_still_gets_its_own_chunk():
    long_path = "d/" + "x" * 600 + ".py"

    chunks = chunk_paths(("a.py", long_path, "b.py"), max_arg_bytes=400)

    assert (long_path,) in chunks
    assert sorted(p for chunk in chunks for p in chunk) == sorted(["a.py", long_path, "b.py"])


def test_the_diff_byte_budget_also_splits_chunks():
    paths = _paths(40)
    sizes = {p: 1000 for p in paths}

    chunks = chunk_paths(paths, max_arg_bytes=24000, sizes=sizes, max_bytes=10_000)

    assert len(chunks) >= 4
    assert all(sum(sizes[p] for p in chunk) <= 10_000 for chunk in chunks)
    assert sorted(p for chunk in chunks for p in chunk) == sorted(paths)


def test_dispatch_never_passes_an_oversized_target_paths_argument(repo, completed, monkeypatch):
    paths = _paths(4500)
    scope = ReviewScope(
        mode="delta",
        structural_check="none",
        validate=("dependency-reviewer",),
        audit=(),
        paths=paths,
    )
    seen: list[str] = []

    def fake_bridge(argv, **kw):
        seen.append(argv[argv.index("--target-paths") + 1])
        return completed(0, stdout=b"{}")

    # `git show` for the reviewer's instruction text; the bridge itself is `_run_bridge`.
    monkeypatch.setattr(
        subprocess, "run", lambda argv, **kw: completed(0, stdout=_FAKE_TOML_CONTENT)
    )
    monkeypatch.setattr(review, "_run_bridge", fake_bridge)

    dispatch_reviewers(scope, base_sha="deadbeef", repo=repo)

    assert len(seen) > 1
    assert all(len(arg.encode()) <= 24000 for arg in seen)
    assert sorted(p for arg in seen for p in arg.split(",")) == sorted(paths)


def _chunked_scope() -> ReviewScope:
    return ReviewScope(
        mode="delta",
        structural_check="none",
        validate=("dependency-reviewer",),
        audit=(),
        paths=_paths(4500),
    )


def _bridge_by_chunk(completed, monkeypatch, *, fail_first_path: str | None = None):
    """Fake the bridge so each call's answer depends on its chunk (the first path in its
    --target-paths), never on arrival order: two workers make that order nondeterministic."""

    def fake_bridge(argv, **kw):
        first = argv[argv.index("--target-paths") + 1].split(",")[0]
        if first == fail_first_path:
            return completed(1, stderr=b"bridge exploded")
        envelope = {"verdict": "pass", "findings": [{"axis": f"found:{first}"}]}
        return completed(0, stdout=json.dumps(envelope).encode())

    monkeypatch.setattr(
        subprocess, "run", lambda argv, **kw: completed(0, stdout=_FAKE_TOML_CONTENT)
    )
    monkeypatch.setattr(review, "_run_bridge", fake_bridge)


def test_chunk_findings_merge_into_one_report_per_reviewer(repo, completed, monkeypatch):
    chunks = chunk_paths(_chunked_scope().paths)
    _bridge_by_chunk(completed, monkeypatch)

    reports = dispatch_reviewers(_chunked_scope(), base_sha="deadbeef", repo=repo)

    assert [r.reviewer for r in reports] == ["dependency-reviewer"]
    assert reports[0].status == "completed"
    assert reports[0].attempts == reports[0].chunks == len(chunks) > 1
    assert reports[0].output is not None
    assert sorted(f["axis"] for f in reports[0].output["findings"]) == sorted(
        f"found:{chunk[0]}" for chunk in chunks
    )


def test_a_failed_chunk_fails_the_reviewer_and_is_named(repo, completed, monkeypatch):
    chunks = chunk_paths(_chunked_scope().paths)
    _bridge_by_chunk(completed, monkeypatch, fail_first_path=chunks[1][0])

    (report,) = dispatch_reviewers(_chunked_scope(), base_sha="deadbeef", repo=repo)

    assert report.status == "failed"
    assert report.output is None
    assert report.error is not None
    assert f"chunk 2/{len(chunks)}" in report.error
    assert chunks[1][0] in report.error
    assert "bridge exploded" in report.error
    # The chunks that did finish keep their findings; the failed one contributes none.
    assert report.partial_output is not None
    assert report.chunks == len(chunks) > 2
    kept = sorted(f["axis"] for f in report.partial_output["findings"])
    assert kept == sorted(f"found:{c[0]}" for i, c in enumerate(chunks) if i != 1)
