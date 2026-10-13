"""Shared secret token shapes: one canonical JSON, byte-identical per-plugin copies."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.marketplace_ci.__main__ import main
from scripts.marketplace_ci.sync_plan import SyncError
from scripts.marketplace_ci.token_shapes import (
    CANONICAL,
    CONSUMERS,
    load_shapes,
    plan_token_shapes_sync,
)

REAL_REPO = Path(__file__).resolve().parents[2]


def _seed(repo: Path, text: str | None = None) -> str:
    """Write the canonical file (the real one unless `text` is given) into the temp repo."""
    body = text if text is not None else (REAL_REPO / CANONICAL).read_text(encoding="utf-8")
    dest = repo / CANONICAL
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8", newline="\n")
    return body


def _write_consumers(repo: Path, body: str) -> None:
    for rel in CONSUMERS:
        dest = repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8", newline="\n")


def test_real_canonical_file_loads_and_every_pattern_compiles_ascii():
    shapes = load_shapes((REAL_REPO / CANONICAL).read_text(encoding="utf-8"))
    assert [name for name, _ in shapes][:2] == ["aws_access_key", "github_token"]
    for _name, pattern in shapes:
        re.compile(pattern, re.ASCII)


def test_real_repo_consumers_are_in_sync():
    assert plan_token_shapes_sync(REAL_REPO).actions == ()


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        json.dumps({"version": 2, "shapes": []}),
        json.dumps({"version": 1}),
        json.dumps({"version": 1, "shapes": []}),
        json.dumps({"version": 1, "shapes": [{"name": "a"}]}),
        json.dumps({"version": 1, "shapes": [{"name": "a", "pattern": "("}]}),
        json.dumps({"version": 1, "shapes": [{"name": "", "pattern": "x"}]}),
        json.dumps(
            {
                "version": 1,
                "shapes": [{"name": "a", "pattern": "x"}, {"name": "a", "pattern": "y"}],
            }
        ),
        json.dumps({"version": 1, "shapes": [{"name": "a", "pattern": "x", "extra": 1}]}),
    ],
)
def test_load_shapes_rejects_malformed_input(text):
    with pytest.raises(SyncError):
        load_shapes(text)


BS = "\\"
VALID_PREFIX = BS + "bab"  # a word boundary and a two-character literal prefix


def _shape_text(pattern):
    return json.dumps({"version": 1, "shapes": [{"name": "a", "pattern": pattern}]})


@pytest.mark.parametrize(
    "pattern",
    [
        "(?:)",  # matches the empty string everywhere, which would disable all redaction
        "x*",
        "a?",
        BS + "b",  # zero-width on its own
        "(?=z)",  # zero-width only when the next character differs; finite probes miss it
        "[A-Z]{16}",  # no word boundary / literal prefix
        "AKIA[0-9A-Z]{16}",  # literal prefix but no leading word boundary
        BS + "b[A-Z]{3}",  # word boundary but no literal prefix
        BS + "ba*",  # the second prefix character is a quantifier, not a literal
    ],
)
def test_load_shapes_requires_a_boundary_and_literal_prefix(pattern):
    """A shape must start with a word boundary and two literal characters, which guarantees it
    matches at least one character instead of erasing the redaction everywhere."""
    with pytest.raises(SyncError):
        load_shapes(_shape_text(pattern))


@pytest.mark.parametrize(
    "construct",
    [
        "(?P<n>x)",  # Python-only named group
        BS + "Aabc",  # Python-only anchor
        "abc" + BS + "Z",
        "(?i)abc",  # inline flag group, rejected by one of the two engines
        "(?#c)abc",  # inline comment: Python accepts it, JavaScript throws
        "(?>abc)",  # atomic group
        "a++b",  # possessive quantifier
        "a{2}+b",
        "(a)?(?(1)b|c)",  # conditional group: Python accepts it, JavaScript throws
        "(?<n>a)b",  # named group: JavaScript syntax Python rejects
        BS + "a",  # BEL in Python, the letter a in JavaScript
        BS + "x41",  # letter escapes outside the shared set are rejected conservatively
        BS + "N{DIGIT ONE}",
        BS + "0",
        BS + "1",
        "|(?=z)",  # a top-level branch that escapes the required prefix and is zero-width
        "|ab",
        BS + "s",  # JavaScript counts NBSP and BOM as whitespace; Python with re.ASCII does not
        BS + "S",
        ".",  # JavaScript's dot excludes CR, U+2028 and U+2029; Python's excludes only a newline
        "$",  # Python matches before a trailing newline; JavaScript does not
        "[]x]",  # Python reads a leading ] as a literal; JavaScript reads an empty class
        "[^]x]",
    ],
)
def test_load_shapes_rejects_patterns_that_are_not_portable_token_shapes(construct):
    with pytest.raises(SyncError):
        load_shapes(_shape_text(VALID_PREFIX + construct))


def test_plan_refuses_a_symlinked_canonical_or_consumer(repo):
    body = _seed(repo)
    _write_consumers(repo, body)
    target = repo / "elsewhere.json"
    target.write_text(body, encoding="utf-8")
    consumer = repo / CONSUMERS[0]
    consumer.unlink()
    try:
        consumer.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")
    with pytest.raises(SyncError, match="symlink"):
        plan_token_shapes_sync(repo)


def test_plan_refuses_a_symlinked_canonical_file(repo):
    body = _seed(repo)
    real = repo / "real-shapes.json"
    real.write_text(body, encoding="utf-8")
    canonical = repo / CANONICAL
    canonical.unlink()
    try:
        canonical.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")
    with pytest.raises(SyncError, match="symlink"):
        plan_token_shapes_sync(repo)


def test_plan_refuses_a_consumer_under_a_symlinked_directory(repo):
    _seed(repo)
    elsewhere = repo / "elsewhere"
    elsewhere.mkdir()
    plugin_root = repo / CONSUMERS[0].rsplit("/scripts/", 1)[0]
    plugin_root.mkdir(parents=True)
    try:
        (plugin_root / "scripts").symlink_to(elsewhere, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")
    with pytest.raises(SyncError, match="symlink"):
        plan_token_shapes_sync(repo)


def test_plan_creates_missing_consumers(repo):
    _seed(repo)
    plan = plan_token_shapes_sync(repo)
    assert sorted(a.operation for a in plan.actions) == ["create"] * len(CONSUMERS)
    assert {a.destination.relative_to(repo).as_posix() for a in plan.actions} == set(CONSUMERS)


def test_plan_updates_a_drifted_consumer_and_leaves_in_sync_ones(repo):
    body = _seed(repo)
    _write_consumers(repo, body)
    drifted = repo / CONSUMERS[0]
    drifted.write_text(body.replace("AKIA", "AKIB"), encoding="utf-8", newline="\n")
    plan = plan_token_shapes_sync(repo)
    assert [(a.operation, a.destination.relative_to(repo).as_posix()) for a in plan.actions] == [
        ("update", CONSUMERS[0])
    ]


def test_plan_is_empty_when_all_copies_match(repo):
    body = _seed(repo)
    _write_consumers(repo, body)
    assert plan_token_shapes_sync(repo).actions == ()


def test_plan_refuses_an_invalid_canonical(repo):
    _seed(repo, "{}")
    with pytest.raises(SyncError):
        plan_token_shapes_sync(repo)


def test_plan_refuses_a_missing_canonical(repo):
    with pytest.raises(SyncError):
        plan_token_shapes_sync(repo)


def test_consumer_filenames_follow_each_plugins_prefix():
    assert [Path(c).name for c in CONSUMERS] == [
        "anls-token-shapes.json",
        "plib-token-shapes.json",
        "cdx-token-shapes.json",
    ]


def test_check_token_shapes_fails_then_sync_fixes_it(monkeypatch, repo):
    _seed(repo)
    monkeypatch.chdir(repo)
    assert main(["check-token-shapes"]) == 1
    assert main(["sync-token-shapes"]) == 0
    assert main(["check-token-shapes"]) == 0
    for rel in CONSUMERS:
        assert (repo / rel).read_bytes() == (repo / CANONICAL).read_bytes()


def test_check_token_shapes_returns_2_on_an_unusable_canonical(monkeypatch, repo):
    _seed(repo, "{}")
    monkeypatch.chdir(repo)
    assert main(["check-token-shapes"]) == 2
    assert main(["sync-token-shapes"]) == 2


def test_check_all_runs_the_token_shapes_check(monkeypatch, repo, tmp_path):
    _seed(repo)
    registry = repo / ".claude" / "marketplace-sync.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        json.dumps({"version": 1, "plugin_mirrors": [], "codex_exports": {}}), encoding="utf-8"
    )
    report = tmp_path / "report.json"
    monkeypatch.chdir(repo)
    main(["check-all", "--json-output", str(report)])
    assert json.loads(report.read_text(encoding="utf-8"))["check_token_shapes"] == 1
    assert main(["sync-token-shapes"]) == 0
    main(["check-all", "--json-output", str(report)])
    assert json.loads(report.read_text(encoding="utf-8"))["check_token_shapes"] == 0


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_python_ascii_and_node_agree_on_every_shape(tmp_path):
    """The same pattern text must give the same matches in Python (re.ASCII) and Node,
    including next to non-ASCII characters, where Python's default Unicode \\b differs."""
    shapes = load_shapes((REAL_REPO / CANONICAL).read_text(encoding="utf-8"))
    samples = {
        "aws_access_key": "AKIA" + "ABCDEFGHIJKLMNOP",
        "github_token": "gh" + "p_" + "a" * 36,
        "github_pat_token": "github_" + "pat_" + "A1_" * 8,
        "slack_token": "xox" + "b-123-abc-DEF",
        "generic_sk_token": "sk" + "-" + "a1" * 12,
        "google_api_key": "AIza" + "B" * 35,
        "jwt_token": "eyJ" + "abc.def_-.sig-1",
    }
    assert set(samples) == {name for name, _ in shapes}
    neighbours = [
        ("", ""),
        (" ", " "),
        ("é", ""),
        ("", "é"),
        ("中", ""),
        ("_", ""),
        ("", "_x"),
    ]
    texts = [pre + samples[name] + post for name, _ in shapes for pre, post in neighbours]
    texts += ["AKIA" + "A" * 15, "plain text"]
    expected = [
        [[m.group(0) for m in re.finditer(p, t, re.ASCII)] for t in texts] for _, p in shapes
    ]
    script = tmp_path / "run.mjs"
    script.write_text(
        "const [shapes, texts] = JSON.parse(process.argv[2]);\n"
        "console.log(JSON.stringify(shapes.map((p) => texts.map((t) =>"
        " [...t.matchAll(new RegExp(p, 'g'))].map((m) => m[0])))));\n",
        encoding="utf-8",
    )
    out = subprocess.run(
        ["node", str(script), json.dumps([[p for _, p in shapes], texts])],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert json.loads(out) == expected


def test_review_redactor_covers_every_shared_shape_next_to_non_ascii_text():
    from scripts.marketplace_ci.review import _redact_tokens

    samples = {
        "aws_access_key": "AKIA" + "ABCDEFGHIJKLMNOP",
        "github_token": "gh" + "p_" + "a" * 36,
        "github_pat_token": "github_" + "pat_" + "A1_" * 8,
        "slack_token": "xox" + "b-123-abc-DEF",
        "generic_sk_token": "sk" + "-" + "a1" * 12,
        "google_api_key": "AIza" + "B" * 35,
        "jwt_token": "eyJ" + "abc.def_-.sig-1",
    }
    shapes = load_shapes((REAL_REPO / CANONICAL).read_text(encoding="utf-8"))
    assert set(samples) == {name for name, _ in shapes}
    for name, sample in samples.items():
        for before, after in (
            ("", ""),
            ("é", ""),
            ("", "é"),
            ("中", ""),
            ("", "_x"),
        ):
            assert sample not in _redact_tokens(f"x {before}{sample}{after} y"), (name, before)


def test_external_hook_scripts_mirror_carries_the_node_copy():
    """codex-exec.mjs reads its shapes file next to itself; the hook-script mirror copies
    codex-exec.mjs, so it must copy that file too or the mirrored import throws ENOENT."""
    from scripts.marketplace_ci.sync import EXTERNAL_HOOK_SCRIPT_MIRRORS

    node_copy = next(c for c in CONSUMERS if c.startswith("plugins/codex-kit/"))
    assert ("codex-kit", node_copy.removeprefix("plugins/codex-kit/")) in (
        EXTERNAL_HOOK_SCRIPT_MIRRORS
    )


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_mirrored_codex_exec_imports_and_redacts():
    mirrored = REAL_REPO / ".claude/hooks/_external-scripts/codex-kit/scripts/lib/codex-exec.mjs"
    sample = "AKIA" + "ABCDEFGHIJKLMNOP"
    out = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            "import(process.argv[1]).then((m) => console.log(m.redactSecrets(process.argv[2])));",
            mirrored.as_uri(),
            f"x {sample} y",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert out == "x [REDACTED] y"


@pytest.mark.parametrize(
    "document",
    [
        "[]",
        '{"version": 2, "shapes": [{"name": "a", "pattern": "x"}]}',
        '{"version": 1, "shapes": []}',
        '{"version": 1, "shapes": [{"name": "a"}]}',
        '{"version": 1, "shapes": [{"name": "a", "pattern": ""}]}',
        "not json",
    ],
)
def test_review_loader_refuses_an_unusable_shapes_file(tmp_path, document):
    from scripts.marketplace_ci.review import _token_shapes_alternation

    shapes_file = tmp_path / "shapes.json"
    shapes_file.write_text(document, encoding="utf-8")
    with pytest.raises(ValueError):
        _token_shapes_alternation(shapes_file)


@pytest.mark.parametrize(
    "construct",
    [
        "(?:abc)d",
        "(?=x)abc",
        "(?!x)abc",
        "(?<=x)abc",
        "(?<!x)abc",
        "abc" + BS + "(?x",  # a literal escaped parenthesis followed by a quantifier
        "c" + BS + "." + BS + "d+" + BS + "w*[" + BS + "-_]",  # the escapes both engines share
        "c" + BS + "B" + BS + "W" + BS + "D",
        "(?:c|d)e",  # alternation inside a group cannot bypass the mandatory prefix
        "[.$|]x",  # . $ and | are literals inside a character class
        BS + "." + BS + "$" + BS + "|",
        "[" + BS + "]a]b",  # an escaped ] inside a class
        "[^a]b",
    ],
)
def test_load_shapes_accepts_the_syntax_both_engines_share(construct):
    """The whitelists must keep the constructs Python and JavaScript agree on."""
    pattern = VALID_PREFIX + construct
    assert load_shapes(_shape_text(pattern)) == [("a", pattern)]


def test_sync_token_shapes_reminds_to_run_the_mirror_sync(monkeypatch, repo, capsys):
    _seed(repo)
    monkeypatch.chdir(repo)
    assert main(["sync-token-shapes"]) == 0
    assert "sync-plugin-mirrors" in capsys.readouterr().out


def test_load_shapes_accepts_an_escaped_plus_followed_by_a_quantifier():
    """An escaped literal plus then a quantifier is valid in both engines and is not a
    possessive quantifier."""
    pattern = VALID_PREFIX + "c" + BS + "++x"
    assert load_shapes(_shape_text(pattern)) == [("a", pattern)]


def test_sk_shape_covers_underscores_in_project_style_keys():
    """OpenAI project keys (sk-proj-...) can contain underscores; the shape must span them or a
    key is only partly redacted, leaving its tail in the output."""
    pattern = dict(load_shapes((REAL_REPO / CANONICAL).read_text(encoding="utf-8")))[
        "generic_sk_token"
    ]
    key = "sk-" + "proj-" + "abcDEF_123-ghiJKL_456-mnoPQR"
    assert re.sub(pattern, "[REDACTED]", f"leaked {key} here", flags=re.ASCII) == (
        "leaked [REDACTED] here"
    )
