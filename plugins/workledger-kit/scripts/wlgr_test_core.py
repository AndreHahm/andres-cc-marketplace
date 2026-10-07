#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Persisted tests for workledger-kit's deterministic scripts: open-item core and CLI, GET-only
wrapper,
config trust boundary, path safety, digest writer and the shared smoke check.
Run: python wlgr_test_core.py   (exit 0 = all passed)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import wlgr_config as cfg  # noqa: E402
import wlgr_digest as dig  # noqa: E402
import wlgr_gh_api_readonly as gh  # noqa: E402
import wlgr_open_items as oi  # noqa: E402
import wlgr_paths as paths  # noqa: E402
import wlgr_smoke_checks as smoke  # noqa: E402

PLUGIN_ROOT = HERE.parent
REPO = "AndreHahm/andres-cc-marketplace"


def make_repo(test: unittest.TestCase, ignore: str = ".temp/\n", repos: bool = True) -> Path:
    """A throwaway git repo (nothing is committed; the index is enough for tracked-ness). By
    default it
    has an untracked local override that onboards REPO, because the shipped default has no
    repository."""
    tmp = tempfile.TemporaryDirectory()
    test.addCleanup(tmp.cleanup)
    root = Path(tmp.name).resolve()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    # Hermetic: a developer's global excludes file must not decide what these repos ignore.
    empty = root / ".git" / "empty-excludes"
    empty.write_text("", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "config", "core.excludesFile", str(empty)], check=True)
    (root / ".gitignore").write_text(ignore, encoding="utf-8")
    (root / ".claude").mkdir()
    if repos:
        (root / ".claude" / "workledger-kit.local.json").write_text(
            json.dumps({"repos": [{"slug": REPO, "report_dirs": [".claude/output"]}]}),
            encoding="utf-8",
        )
    return root


def run_cli(script: str, cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HERE / script), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def cand(ref: str, text: str, **kw) -> dict:
    return {
        "source": kw.pop("source", "github-issue"),
        "repo": REPO,
        "source_ref": ref,
        "kind": kw.pop("kind", "open-item"),
        "title": text[:40],
        "text": text,
        "ambiguous": kw.pop("ambiguous", False),
        "extra": kw.pop("extra", {}),
    }


class DedupTests(unittest.TestCase):
    def test_fingerprint_ignores_whitespace_and_case(self):
        self.assertEqual(oi.fingerprint("Fix  the BUG\n now"), oi.fingerprint("fix the bug now"))

    def test_key_roundtrip_and_validation(self):
        key = oi.make_dedup_key(REPO, "#312", "text")
        self.assertEqual(oi.split_key(key)[:2], (REPO, "#312"))
        with self.assertRaises(ValueError):
            oi.make_dedup_key("not-a-repo", "#1", "x")
        with self.assertRaises(ValueError):
            oi.make_dedup_key(REPO, "a|b", "x")

    def test_read_key_only_from_first_line(self):
        key = oi.make_dedup_key(REPO, "#1", "x")
        self.assertEqual(oi.read_dedup_key(f"dedup_key: {key}\n\nbody"), key)
        self.assertIsNone(oi.read_dedup_key(f"intro\ndedup_key: {key}"))
        self.assertIsNone(oi.read_dedup_key("dedup_key: not|enough"))
        self.assertIsNone(oi.read_dedup_key(None))

    def test_fuzzy_lookalike_is_not_a_duplicate(self):
        # '#99' matched '#999' in Linear's fuzzy search; exact comparison must not.
        existing = [
            {"id": "A", "description": f"dedup_key: {oi.make_dedup_key(REPO, '#999', 't')}\n"}
        ]
        self.assertEqual(
            oi.classify_candidate(oi.make_dedup_key(REPO, "#99", "t"), existing)["result"], "new"
        )

    def test_exact_duplicate_and_candidate_match(self):
        key = oi.make_dedup_key(REPO, "#5", "same text")
        changed = oi.make_dedup_key(REPO, "#5", "edited text")
        issues = [{"id": "X", "description": f"dedup_key: {key}\n"}]
        self.assertEqual(oi.classify_candidate(key, issues)["result"], "duplicate")
        self.assertEqual(
            oi.classify_candidate(changed, issues),
            {"result": "candidate-match", "issue": "X", "drift": []},
        )

    def test_masters_skipped_and_missing_key_flagged_as_drift(self):
        key = oi.make_dedup_key(REPO, "#7", "t")
        issues = [
            {"id": "M1", "title": "[MASTER OI]", "description": f"dedup_key: {key}\n"},
            {
                "id": "M2",
                "title": "x",
                "labels": ["meta: master"],
                "description": f"dedup_key: {key}\n",
            },
            {"id": "D", "title": "hand made", "description": "no key here"},
        ]
        result = oi.classify_candidate(key, issues)
        self.assertEqual(result["result"], "new")
        self.assertEqual(result["drift"], ["D"])


class AnnotateAndProposeTests(unittest.TestCase):
    def test_bad_reference_is_skipped_not_fatal(self):
        kept, skipped = oi.annotate_keys(
            [cand("#1", "ok"), cand("a|b.md#1", "pipe in name", source="report")]
        )
        self.assertEqual(([c["source_ref"] for c in kept], len(skipped)), (["#1"], 1))

    def test_annotate_maps_github_labels(self):
        kept, _ = oi.annotate_keys(
            [cand("#2", "t", extra={"github_labels": ["t: enhancement", "p: high"]})]
        )
        self.assertEqual(kept[0]["extra"]["mapped"]["type"], "type: improvement")
        self.assertEqual(kept[0]["extra"]["mapped"]["priority"], "High")

    def test_open_item_proposal_is_triaged_with_first_line_key(self):
        kept, _ = oi.annotate_keys(
            [cand("#3", "Something left open", extra={"origin": "github-issue"})]
        )
        p = oi.propose_issue(kept[0])
        self.assertEqual(p["status"], "Triaged")
        self.assertEqual(oi.read_dedup_key(p["description"]), kept[0]["dedup_key"])
        self.assertIn("kind: open-item", p["labels"])
        self.assertTrue(p["description"].rstrip().endswith("```"))

    def test_pr_record_status_follows_state(self):
        for state, status in (("merged", "Done"), ("closed", "Canceled"), ("open", "In Review")):
            kept, _ = oi.annotate_keys(
                [
                    cand(
                        "PR#9",
                        "t",
                        kind="pr-record",
                        source="pull-request",
                        extra={"state": state, "origin": "pr-backfill"},
                    )
                ]
            )
            self.assertEqual(oi.propose_issue(kept[0])["status"], status)


class FolderFilterTests(unittest.TestCase):
    def test_keeps_non_reports_and_only_chosen_report_folders(self):
        cands = [
            cand(".claude/output/real/a.md#1", "a", source="report"),
            cand(".claude/output/merge-skill-x/b.md#1", "b", source="report"),
            cand(
                ".claude/output/realistic/c.md#1", "c", source="report"
            ),  # prefix must be a whole folder
            cand("#1", "issue"),
        ]
        kept = oi.filter_report_folders(cands, [".claude/output/real", ""])
        self.assertEqual([c["source_ref"] for c in kept], [".claude/output/real/a.md#1", "#1"])

    def test_cli_reads_the_folders_from_a_file(self):
        repo = make_repo(self)
        work = repo / ".temp" / "workledger-digest"
        work.mkdir(parents=True)
        (work / "a.json").write_text(
            json.dumps({"candidates": [cand("x/f.md#1", "t", source="report")], "skipped": []}),
            encoding="utf-8",
        )
        (work / "f.json").write_text(json.dumps(["x"]), encoding="utf-8")
        r = run_cli("wlgr_open_items.py", repo, "filter-folders", "a.json", "f.json", "o.json")
        self.assertEqual(json.loads(r.stdout), {"kept": 1, "removed": 0}, r.stderr)
        (work / "f.json").write_text(json.dumps("not-a-list"), encoding="utf-8")
        self.assertEqual(
            run_cli(
                "wlgr_open_items.py", repo, "filter-folders", "a.json", "f.json", "o.json"
            ).returncode,
            1,
        )


class DescriptionTests(unittest.TestCase):
    def test_first_line_is_key_and_tracking_block_is_last(self):
        key = oi.make_dedup_key(REPO, "#8", "t")
        desc = oi.build_description(
            key, "S", "C", ["done"], {"kind": "open-item", "github_labels": ["t: bug"]}
        )
        self.assertEqual(desc.split("\n", 1)[0], f"dedup_key: {key}")
        self.assertLess(desc.index("## Done when"), desc.index(oi.TRACKING_HEADING))
        self.assertIn('github_labels: ["t: bug"]', desc)


class LabelMappingTests(unittest.TestCase):
    def test_mapping(self):
        m = oi.map_github_labels(
            ["t: enhancement", "p: critical", "i: minor change", "a: ai-setup", "s: triage"]
        )
        self.assertEqual(
            (m["type"], m["priority"], m["impact"]),
            ("type: improvement", "Urgent", "impact: minor"),
        )
        self.assertEqual(len(m["github_labels"]), 5)  # nothing lost

    def test_unlabeled_issue(self):
        self.assertIsNone(oi.map_github_labels([])["type"])


class PlanHashTests(unittest.TestCase):
    def test_order_independent_and_change_sensitive(self):
        a, b = {"k": "1", "t": "x"}, {"k": "2", "t": "y"}
        self.assertEqual(oi.plan_hash([a, b]), oi.plan_hash([b, a]))
        self.assertNotEqual(oi.plan_hash([a, b]), oi.plan_hash([a]))
        self.assertNotEqual(oi.plan_hash([a, b]), oi.plan_hash([a, {**b, "t": "z"}]))


class ChunkTests(unittest.TestCase):
    def test_every_chunk_within_limit_and_lossless(self):
        text = "\n\n".join(["para " * 50] * 30 + ["x" * 5000])
        chunks = oi.chunk_text(text, 2000)
        self.assertTrue(all(0 < len(c) <= 2000 for c in chunks))
        self.assertEqual("".join(chunks).replace("\n", ""), text.replace("\n", ""))

    def test_short_text_is_one_chunk(self):
        self.assertEqual(oi.chunk_text("hello"), ["hello"])

    def test_limit_is_clamped_to_100_2000(self):
        for bad in (1, 99, 2001, 5000, 0, -5):
            with self.assertRaises(ValueError, msg=str(bad)):
                oi.chunk_text("x", bad)

    def test_pathological_inputs_are_linear(self):
        import time

        for text in ("x" * 2_000_000, "\n" * 500_000, ("a" * 150 + "\n") * 10_000):
            start = time.perf_counter()
            chunks = oi.chunk_text(text, 100)
            self.assertLess(time.perf_counter() - start, 2.0)
            self.assertTrue(all(len(c) <= 100 for c in chunks))


class CliFlowTests(unittest.TestCase):
    """The CLI takes only plain file names inside the working folder and prints counts, not text."""

    def setUp(self):
        self.repo = make_repo(self)
        self.work = self.repo / ".temp" / "workledger-digest"
        self.work.mkdir(parents=True)

    def put(self, name, data):
        (self.work / name).write_text(json.dumps(data), encoding="utf-8")

    def get(self, name):
        return json.loads((self.work / name).read_text(encoding="utf-8"))

    def test_annotate_classify_describe_hash_and_digest_state(self):
        self.put("c.json", [cand("#1", "first item"), cand("#2", "second item")])
        r = run_cli("wlgr_open_items.py", self.repo, "annotate", "c.json", "a.json")
        self.assertEqual(
            (r.returncode, json.loads(r.stdout)), (0, {"annotated": 2, "skipped": 0}), r.stderr
        )
        key1 = self.get("a.json")["candidates"][0]["dedup_key"]
        self.put("existing.json", [{"id": "L-1", "description": f"dedup_key: {key1}\n"}])
        r = run_cli(
            "wlgr_open_items.py", self.repo, "classify", "a.json", "existing.json", "k.json"
        )
        self.assertEqual(
            json.loads(r.stdout),
            {"duplicate": 1, "candidate-match": 0, "new": 1, "drift": 0},
            r.stderr,
        )
        self.assertEqual(
            run_cli("wlgr_open_items.py", self.repo, "describe", "a.json", "p.json").returncode, 0
        )
        self.assertEqual(len(self.get("p.json")), 2)
        h = run_cli("wlgr_open_items.py", self.repo, "plan-hash", "p.json")
        self.assertEqual(len(h.stdout.strip()), 64)
        # digest bookkeeping: first run lists everything; after mark-seen nothing is new
        r = run_cli("wlgr_open_items.py", self.repo, "new-since", "a.json", "seen.json", "n.json")
        self.assertEqual(json.loads(r.stdout), {"new": 2, "first_run": True})
        run_cli("wlgr_open_items.py", self.repo, "mark-seen", "a.json", "seen.json")
        r = run_cli("wlgr_open_items.py", self.repo, "new-since", "a.json", "seen.json", "n.json")
        self.assertEqual(json.loads(r.stdout), {"new": 0, "first_run": False})

    def test_first_run_is_per_repository(self):
        self.put("c.json", [cand("#1", "first item")])
        run_cli("wlgr_open_items.py", self.repo, "annotate", "c.json", "a.json")

        def first_run():
            args = ("wlgr_open_items.py", self.repo, "new-since", "a.json", "seen.json", "n.json")
            return json.loads(run_cli(*args).stdout)["first_run"]

        self.assertTrue(first_run())  # no seen-keys file
        self.put("seen.json", [])
        self.assertTrue(first_run())  # an empty file
        self.put("seen.json", ["other/repo|#1|abcd1234"])
        self.assertTrue(first_run())  # only another repository's keys
        self.put("seen.json", [f"{REPO}|#9|abcd1234"])
        self.assertFalse(first_run())  # this repository already has keys

    def test_malformed_seen_keys_file_is_a_clean_error(self):
        self.put("c.json", [cand("#1", "first item")])
        run_cli("wlgr_open_items.py", self.repo, "annotate", "c.json", "a.json")
        for bad in ({"a": 1}, [1, 2], [["x"]], "abc"):
            self.put("seen.json", bad)
            for cmd in ("new-since", "mark-seen"):
                args = ("wlgr_open_items.py", self.repo, cmd, "a.json", "seen.json")
                r = run_cli(*args, *(("n.json",) if cmd == "new-since" else ()))
                self.assertNotEqual(r.returncode, 0, (cmd, bad))
                self.assertNotIn("Traceback", r.stderr, (cmd, bad))

    def test_path_like_names_are_refused(self):
        self.put("c.json", [cand("#1", "x")])
        for bad in (
            "../c.json",
            "sub/c.json",
            "/etc/passwd",
            "..",
            ".hidden",
            "con.json",
            "c.json.",
        ):
            r = run_cli("wlgr_open_items.py", self.repo, "annotate", bad, "out.json")
            self.assertEqual(r.returncode, 1, bad)
        self.assertFalse((self.repo / "out.json").exists())

    def test_output_never_echoes_collected_text(self):
        secret = "SECRET-BODY-TEXT-12345"
        self.put("c.json", [cand("#1", secret)])
        r = run_cli("wlgr_open_items.py", self.repo, "annotate", "c.json", "a.json")
        self.assertNotIn(secret, r.stdout + r.stderr)

    def test_workdir_must_be_gitignored(self):
        repo = make_repo(self, ignore="")  # .temp/ not ignored
        (repo / ".temp" / "workledger-digest").mkdir(parents=True)
        (repo / ".temp" / "workledger-digest" / "c.json").write_text("[]", encoding="utf-8")
        r = run_cli("wlgr_open_items.py", repo, "annotate", "c.json", "a.json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not gitignored", r.stderr)


class DigestTests(unittest.TestCase):
    def test_digest_layout_and_ambiguity_marking(self):
        a = [
            {
                "source": "github-issue",
                "source_ref": "#1",
                "title": "A | b",
                "ambiguous": False,
                "extra": {"url": "http://u"},
            },
            {
                "source": "report",
                "source_ref": "r.md#1",
                "title": "B",
                "ambiguous": True,
                "extra": {},
            },
        ]
        text = dig.build_digest(a, a, "2026-10-07", True, ["issues"])
        self.assertIn("First run", text)
        self.assertIn("| GitHub issues | 1 | 1 | 0 |", text)
        self.assertIn("`r.md#1`: B (needs a person)", text)
        self.assertIn("A / b", text)  # pipe cannot break the layout
        self.assertIn("- issues", text.split("## Sources that failed")[1])

    def test_cli_combines_several_sources_into_one_digest(self):
        repo = make_repo(self)
        work = repo / ".temp" / "workledger-digest"
        work.mkdir(parents=True)
        a1 = {
            "candidates": [
                {
                    "source": "report",
                    "source_ref": "r.md#1",
                    "title": "R",
                    "ambiguous": False,
                    "extra": {},
                }
            ]
        }
        a2 = {
            "candidates": [
                {
                    "source": "github-issue",
                    "source_ref": "#1",
                    "title": "I",
                    "ambiguous": False,
                    "extra": {},
                }
            ]
        }
        for name, data in (
            ("a1.json", a1),
            ("a2.json", a2),
            ("n1.json", a1["candidates"]),
            ("n2.json", []),
        ):
            (work / name).write_text(json.dumps(data), encoding="utf-8")
        out = json.loads(
            run_cli("wlgr_digest.py", repo, "a1.json,a2.json", "n1.json,n2.json").stdout
        )
        self.assertEqual((out["collected"], out["new"]), (2, 1))
        self.assertEqual(len(list(work.glob("digest-*.md"))), 1)
        self.assertEqual(
            run_cli("wlgr_digest.py", repo, "a1.json,../x.json", "n1.json").returncode, 1
        )

    def test_cli_never_overwrites_an_existing_digest(self):
        repo = make_repo(self)
        work = repo / ".temp" / "workledger-digest"
        work.mkdir(parents=True)
        (work / "a.json").write_text(json.dumps({"candidates": []}), encoding="utf-8")
        (work / "n.json").write_text("[]", encoding="utf-8")
        names = [
            json.loads(run_cli("wlgr_digest.py", repo, "a.json", "n.json").stdout)["written"]
            for _ in range(3)
        ]
        self.assertEqual(len(set(names)), 3)
        self.assertTrue(names[1].endswith("-2.md") and names[2].endswith("-3.md"))
        self.assertEqual(
            run_cli("wlgr_digest.py", repo, "a.json", "n.json", "--failed", "bogus").returncode, 2
        )


class ReadOnlyWrapperTests(unittest.TestCase):
    def test_accepts_get_forms_and_forces_method(self):
        cmd, err, _ = gh.build_command(
            ["repos/o/r/pulls?state=all", "--paginate", "--jq", ".[].number"]
        )
        self.assertIsNone(err)
        assert cmd is not None
        self.assertEqual(cmd[:4], ["gh", "api", "--method", "GET"])

    def test_rejects_write_flags_env_leaks_and_non_rest_endpoints(self):
        for argv in (
            ["x", "-f", "a=b"],
            ["x", "-X", "POST"],
            ["x", "--method", "DELETE"],
            ["x", "--input", "f"],
            ["-X"],
            ["x", "--jq", "env"],
            ["x", "--jq", "$ENV.TOKEN"],
            ["x", "--jq"],
            [],
            ["https://evil.example/x"],
            ["graphql"],
            ["GraphQL?query=1"],
            ["graphql/"],
            ["/graphql/"],
            ["GraphQL/?query=1"],
            ["repos/o/r/../../x"],
            ["repos/../user"],
            ["../user"],
            ["repos/./o"],
            ["repos/o/r/.."],
            ["repos/o/r/../issues?state=all"],
            ["repos/%2e%2e/user"],
            ["%2E%2E/graphql"],
            ["%67raphql"],
            ["{owner}/x"],
            ["repos/o/r;id"],
            ["repos/o r"],
            ["repos/$(id)"],
        ):
            cmd, _, code = gh.build_command(argv)
            self.assertIsNone(cmd, argv)
            self.assertIn(code, (1, 2))

    def test_dots_inside_names_and_colons_in_queries_stay_allowed(self):
        for endpoint in (
            "repos/o/r.js/issues",
            "repos/o/r/issues?since=2026-01-01T00:00:00Z",
            "repos/o/r/issues?since=2026-01-01T00%3A00%3A00Z",  # '%' is fine in the query part
        ):
            cmd, err, code = gh.build_command([endpoint])
            self.assertEqual((err, code), (None, 0), endpoint)
            assert cmd is not None
            self.assertEqual(cmd[-1], endpoint)


class PathSafetyTests(unittest.TestCase):
    def test_work_name(self):
        self.assertEqual(paths.work_name("cands-1.json"), "cands-1.json")
        self.assertEqual(paths.work_name("o--r-issues.json"), "o--r-issues.json")
        for bad in ("a/b", "a\\b", "..", ".x", "", "con", "NUL.json", "x.", "x ", "a" * 200, None):
            with self.assertRaises(ValueError, msg=str(bad)):
                paths.work_name(cast(Any, bad))  # the None entry checks the type guard on purpose

    def test_confine(self):
        root = make_repo(self)
        (root / "ok").mkdir()
        self.assertEqual(paths.confine(root / "ok" / "f", root), (root / "ok" / "f").resolve())
        for bad in (root.parent, root / ".." / "x", root / "ok" / "con"):
            with self.assertRaises(ValueError, msg=str(bad)):
                paths.confine(bad, root)

    def test_confine_rejects_symlink_component(self):
        root = make_repo(self)
        target = Path(tempfile.mkdtemp(prefix="wlgr_target_"))
        try:
            os.symlink(target, root / "link", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not permitted on this machine")
        with self.assertRaises(ValueError):
            paths.confine(root / "link" / "x", root)


class ConfigTests(unittest.TestCase):
    def _repo(self, local: dict | None):
        root = make_repo(self, repos=False)
        if local is not None:
            (root / ".claude" / "workledger-kit.local.json").write_text(
                json.dumps(local), encoding="utf-8"
            )
        return root

    def test_shipped_defaults_have_no_repository_and_point_at_onboarding(self):
        """A distributed plugin must not collect the author's repository by default."""
        root = self._repo(None)
        settings, warnings = cfg.load_settings(PLUGIN_ROOT, root)
        self.assertEqual((settings["repos"], warnings), ([], []))
        self.assertEqual(set(settings), {"version", "repos", "digest", "intake_capabilities"})
        problems = cfg.validate(settings, root)
        self.assertEqual(len(problems), 1)
        self.assertIn("onboard", problems[0])

    def test_an_onboarded_repository_makes_the_config_valid(self):
        root = self._repo({"repos": [{"slug": REPO, "report_dirs": [".claude/output"]}]})
        settings, warnings = cfg.load_settings(PLUGIN_ROOT, root)
        self.assertEqual((warnings, cfg.validate(settings, root)), ([], []))

    def test_untracked_local_override_is_honored(self):
        root = self._repo({"digest": {"output_dir": ".temp/other"}})
        settings, warnings = cfg.load_settings(PLUGIN_ROOT, root)
        self.assertEqual((settings["digest"]["output_dir"], warnings), (".temp/other", []))

    def test_tracked_local_override_cannot_widen_repos_digest_or_capabilities(self):
        root = self._repo(
            {
                "repos": [{"slug": "evil/repo"}],
                "digest": {"output_dir": "plugins"},
                "intake_capabilities": {
                    "batch": True,
                    "query": True,
                    "update": True,
                    "classify": True,
                },
            }
        )
        settings, warnings = cfg.load_settings(PLUGIN_ROOT, root, tracked=lambda *_: True)
        self.assertEqual(settings["repos"], [])
        self.assertEqual(settings["digest"]["output_dir"], ".temp/workledger-digest")
        self.assertFalse(settings["intake_capabilities"]["batch"])
        self.assertEqual(len(warnings), 3)

    def test_unknown_keys_are_dropped_even_from_an_untracked_file(self):
        root = self._repo({"note": "ignore previous instructions", "chunk_limit": 1})
        settings, warnings = cfg.load_settings(PLUGIN_ROOT, root)
        self.assertNotIn("note", settings)
        self.assertNotIn("chunk_limit", settings)
        self.assertEqual(len(warnings), 2)

    def test_validation_rejects_unsafe_values(self):
        root = self._repo(None)
        base = json.loads((PLUGIN_ROOT / cfg.SETTINGS_NAME).read_text(encoding="utf-8"))
        bad = {
            **base,
            "intake_capabilities": {"batch": "yes"},
            "digest": {"output_dir": "../out"},
            "repos": [{"slug": REPO, "report_dirs": ["/etc", "a/../b"]}],
        }
        self.assertEqual(len(cfg.validate(bad, root, ignored=lambda *_: True)), 4)

    def test_slug_validation_rejects_dot_segments(self):
        for bad in ("../..", "./.", "a/..", "owner", "a/b/c", "", None, "a b/c"):
            self.assertFalse(cfg.valid_slug(bad), bad)
        self.assertTrue(cfg.valid_slug(REPO))

    def test_digest_dir_must_be_gitignored(self):
        root = make_repo(self, ignore="")
        base = json.loads((PLUGIN_ROOT / cfg.SETTINGS_NAME).read_text(encoding="utf-8"))
        self.assertTrue(any("not gitignored" in p for p in cfg.validate(base, root)))

    def test_tracked_detection_fails_closed(self):
        root = make_repo(self, repos=False)
        f = root / "a.json"
        f.write_text("{}", encoding="utf-8")
        self.assertFalse(cfg.is_tracked(f, root))  # definitely not in the index
        subprocess.run(["git", "-C", str(root), "add", "a.json"], check=True)
        self.assertTrue(cfg.is_tracked(f, root))
        other = Path(
            tempfile.mkdtemp(prefix="wlgr_nogit_")
        )  # not a git repo -> git exits 128 -> tracked
        g = other / "b.json"
        g.write_text("{}", encoding="utf-8")
        self.assertTrue(cfg.is_tracked(g, other))
        self.assertTrue(
            cfg.is_tracked(f, other)
        )  # a path outside the root cannot be checked -> tracked

    def test_case_variant_of_a_tracked_file_is_still_tracked(self):
        """The reviewer's bypass: a file committed as WorkLedger-Kit.local.json opens under the
        lowercase name on Windows/macOS, but a plain pathspec lookup misses it."""
        root = make_repo(self, repos=False)
        variant = root / ".claude" / "WorkLedger-Kit.local.json"
        variant.write_text(json.dumps({"digest": {"output_dir": "plugins"}}), encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(root), "add", "-f", ".claude/WorkLedger-Kit.local.json"], check=True
        )
        lower = root / ".claude" / "workledger-kit.local.json"
        self.assertTrue(cfg.is_tracked(lower, root))
        if (
            lower.is_file()
        ):  # case-insensitive filesystem: the file really opens under the lowercase name
            settings, warnings = cfg.load_settings(PLUGIN_ROOT, root)
            self.assertEqual(settings["digest"]["output_dir"], ".temp/workledger-digest")
            self.assertEqual(len(warnings), 1)

    def test_local_override_is_read_through_the_shared_no_follow_reader(self):
        root = self._repo({"digest": {"output_dir": ".temp/other"}})
        with mock.patch.object(paths, "read_text", wraps=paths.read_text) as reader:
            settings, warnings = cfg.load_settings(PLUGIN_ROOT, root)
        self.assertEqual((settings["digest"]["output_dir"], warnings), (".temp/other", []))
        reader.assert_called_once()
        with mock.patch.object(paths, "read_text", side_effect=OSError("refused")):
            settings, warnings = cfg.load_settings(PLUGIN_ROOT, root)
        self.assertEqual(settings["digest"]["output_dir"], ".temp/workledger-digest")
        self.assertTrue(warnings and "not readable JSON" in warnings[0])

    def test_symlinked_local_file_is_ignored(self):
        root = make_repo(self, repos=False)
        real = Path(tempfile.mkdtemp(prefix="wlgr_real_")) / "x.json"
        real.write_text(json.dumps({"digest": {"output_dir": "plugins"}}), encoding="utf-8")
        try:
            os.symlink(real, root / ".claude" / "workledger-kit.local.json")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not permitted on this machine")
        settings, warnings = cfg.load_settings(PLUGIN_ROOT, root)
        self.assertEqual(settings["digest"]["output_dir"], ".temp/workledger-digest")
        self.assertTrue(warnings and "ignored" in warnings[0])

    def test_local_override_state_reports_existence_and_tracking(self):
        root = self._repo(None)
        self.assertEqual(cfg.local_override_state(root), {"exists": False, "tracked": None})
        (root / ".claude" / "workledger-kit.local.json").write_text("{}", encoding="utf-8")
        self.assertEqual(cfg.local_override_state(root), {"exists": True, "tracked": False})
        subprocess.run(
            ["git", "-C", str(root), "add", "-f", ".claude/workledger-kit.local.json"], check=True
        )
        self.assertEqual(cfg.local_override_state(root), {"exists": True, "tracked": True})

    def test_repo_entry_requires_a_configured_repository(self):
        settings, _ = cfg.load_settings(PLUGIN_ROOT, make_repo(self))  # make_repo onboards REPO
        self.assertEqual(cfg.repo_entry(REPO, settings)["slug"], REPO)
        with self.assertRaises(ValueError):
            cfg.repo_entry("someone/else", settings)


class SelectionAndFolderTests(unittest.TestCase):
    """Duplicates and unconfirmed matches must never reach the proposals file, its hash or a
    submission."""

    def _annotated(self):
        kept, _ = oi.annotate_keys(
            [cand("#1", "dup"), cand("#2", "match v2"), cand("#3", "brand new")]
        )
        return kept

    def test_select_for_plan_drops_duplicates_and_unconfirmed_matches(self):
        ann = self._annotated()
        classified = [
            {"dedup_key": ann[0]["dedup_key"], "result": "duplicate"},
            {"dedup_key": ann[1]["dedup_key"], "result": "candidate-match"},
            {"dedup_key": ann[2]["dedup_key"], "result": "new"},
        ]
        kept, counts = oi.select_for_plan(ann, classified, set())
        self.assertEqual([c["source_ref"] for c in kept], ["#3"])
        self.assertEqual((counts["dropped-duplicate"], counts["dropped-unconfirmed-match"]), (1, 1))
        kept, counts = oi.select_for_plan(ann, classified, {ann[1]["dedup_key"]})
        self.assertEqual([c["source_ref"] for c in kept], ["#2", "#3"])
        self.assertEqual(counts["confirmed-match"], 1)

    def test_unclassified_candidates_are_never_proposed(self):
        ann = self._annotated()
        kept, counts = oi.select_for_plan(ann, [], set())
        self.assertEqual((kept, counts["dropped-unclassified"]), ([], 3))

    def test_folder_counts_are_counts_only_and_ordered(self):
        cands = [cand(f".claude/output/big/f{i}.md#1", "t", source="report") for i in range(3)] + [
            cand(".claude/output/small/a.md#1", "t", source="report"),
            cand("#1", "issue"),
        ]
        self.assertEqual(
            oi.folder_counts(cands), {".claude/output/big": 3, ".claude/output/small": 1}
        )

    def test_cli_flow_classify_then_apply_then_describe_excludes_the_duplicate(self):
        repo = make_repo(self)
        work = repo / ".temp" / "workledger-digest"
        work.mkdir(parents=True)
        (work / "c.json").write_text(
            json.dumps([cand("#1", "already in linear"), cand("#2", "new one")]), encoding="utf-8"
        )
        run_cli("wlgr_open_items.py", repo, "annotate", "c.json", "a.json")
        key1 = json.loads((work / "a.json").read_text(encoding="utf-8"))["candidates"][0][
            "dedup_key"
        ]
        (work / "existing.json").write_text(
            json.dumps([{"id": "L-1", "description": f"dedup_key: {key1}\n"}]), encoding="utf-8"
        )
        run_cli("wlgr_open_items.py", repo, "classify", "a.json", "existing.json", "k.json")
        r = run_cli(
            "wlgr_open_items.py", repo, "apply-classification", "a.json", "k.json", "sel.json"
        )
        counts = json.loads(r.stdout)
        self.assertEqual((counts["new"], counts["dropped-duplicate"]), (1, 1), r.stderr)
        run_cli("wlgr_open_items.py", repo, "describe", "sel.json", "p.json")
        proposals = json.loads((work / "p.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [oi.read_dedup_key(p["description"]) for p in proposals],
            [oi.make_dedup_key(REPO, "#2", "new one")],
        )
        # a confirmed candidate-match is let through, by key, from a file
        (work / "e2.json").write_text(
            json.dumps(
                [
                    {
                        "id": "L-2",
                        "description": "dedup_key: "
                        + oi.make_dedup_key(REPO, "#2", "old text")
                        + "\n",
                    }
                ]
            ),
            encoding="utf-8",
        )
        run_cli("wlgr_open_items.py", repo, "classify", "a.json", "e2.json", "k2.json")
        key2 = oi.make_dedup_key(REPO, "#2", "new one")
        (work / "ok.json").write_text(json.dumps([key2]), encoding="utf-8")
        counts = json.loads(
            run_cli(
                "wlgr_open_items.py",
                repo,
                "apply-classification",
                "a.json",
                "k2.json",
                "ok.json",
                "sel2.json",
            ).stdout
        )
        self.assertEqual(counts["confirmed-match"], 1)

    def test_folder_counts_cli_prints_counts_not_text(self):
        repo = make_repo(self)
        work = repo / ".temp" / "workledger-digest"
        work.mkdir(parents=True)
        secret = "SECRET-ITEM-TEXT"
        (work / "a.json").write_text(
            json.dumps(
                {"candidates": [cand("x/y/z/f.md#1", secret, source="report")], "skipped": []}
            ),
            encoding="utf-8",
        )
        r = run_cli("wlgr_open_items.py", repo, "folder-counts", "a.json")
        self.assertEqual(json.loads(r.stdout)["folders"], {"x/y/z": 1})
        self.assertNotIn(secret, r.stdout)

    def test_classify_scales_with_an_index(self):
        import time

        existing = [
            {"id": i, "description": f"dedup_key: {oi.make_dedup_key(REPO, f'#{i}', 't')}\n"}
            for i in range(5000)
        ]
        index = oi.index_existing(existing)
        start = time.perf_counter()
        results = [
            oi.classify_with_index(oi.make_dedup_key(REPO, f"#{i}", "t"), index)["result"]
            for i in range(5000)
        ]
        self.assertLess(time.perf_counter() - start, 2.0)
        self.assertEqual(set(results), {"duplicate"})


class WorkingFolderSecurityTests(unittest.TestCase):
    """Security review findings: links and tracked content inside the working folder, gitlinks,
    PATH search."""

    def test_a_tracked_entry_inside_the_working_folder_is_a_problem(self):
        repo = make_repo(self)
        work = repo / ".temp" / "workledger-digest"
        work.mkdir(parents=True)
        (work / "planted.json").write_text("{}", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(repo), "add", "-f", ".temp/workledger-digest/planted.json"],
            check=True,
        )
        settings, _ = cfg.load_settings(PLUGIN_ROOT, repo)
        self.assertTrue(any("tracked files" in p for p in cfg.validate(settings, repo)))

    def test_a_symlink_planted_at_a_working_file_is_refused_not_followed(self):
        repo = make_repo(self)
        work = repo / ".temp" / "workledger-digest"
        work.mkdir(parents=True)
        victim = Path(tempfile.mkdtemp(prefix="wlgr_victim_")) / "victim.txt"
        victim.write_text("do not touch", encoding="utf-8")
        try:
            os.symlink(victim, work / "issues.json")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not permitted on this machine")
        with self.assertRaises(ValueError):
            cfg.work_file("issues.json", repo_root=repo)
        with self.assertRaises((ValueError, OSError)):
            cfg.write_work("issues.json", "overwritten", repo_root=repo)
        self.assertEqual(victim.read_text(encoding="utf-8"), "do not touch")

    def test_a_gitlink_covering_the_local_file_counts_as_tracked(self):
        """A submodule at .claude lists only `.claude` in the outer index, never the file inside
        it."""
        repo = make_repo(self, repos=False)
        local = repo / ".claude" / "workledger-kit.local.json"
        local.write_text("{}", encoding="utf-8")
        self.assertFalse(cfg.is_tracked(local, repo))
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "update-index",
                "--add",
                "--cacheinfo",
                "160000,0123456789abcdef0123456789abcdef01234567,.claude",
            ],
            check=True,
        )
        self.assertTrue(cfg.is_tracked(local, repo))

    def test_a_file_in_a_nested_git_work_tree_counts_as_tracked(self):
        repo = make_repo(self, repos=False)
        nested = repo / ".claude" / "nested"
        nested.mkdir()
        subprocess.run(["git", "init", "-q", str(nested)], check=True)
        local = nested / "workledger-kit.local.json"
        local.write_text("{}", encoding="utf-8")
        self.assertTrue(cfg.is_tracked(local, repo))  # a different work tree owns this folder

    def test_find_exe_ignores_the_current_directory_and_excluded_folders(self):
        here = Path(tempfile.mkdtemp(prefix="wlgr_exe_"))
        name = "wlgrfaketool"
        fake = here / (name + (".exe" if sys.platform == "win32" else ""))
        fake.write_text("echo hi", encoding="utf-8")
        fake.chmod(0o755)
        old_path, old_cwd = os.environ.get("PATH", ""), Path.cwd()
        try:
            os.environ["PATH"] = str(here)
            os.chdir(here)
            self.assertIsNone(paths.find_exe(name))  # the current directory is never trusted
            os.chdir(old_cwd)
            exe = paths.find_exe(name)
            assert exe is not None
            self.assertEqual(Path(exe).resolve(), fake.resolve())
            self.assertIsNone(paths.find_exe(name, exclude=[here]))  # nor a folder inside the repo
            os.environ["PATH"] = os.pathsep + str(here)  # an empty entry must not mean "here"
            exe = paths.find_exe(name)
            assert exe is not None
            self.assertEqual(Path(exe).resolve(), fake.resolve())
        finally:
            os.chdir(old_cwd)
            os.environ["PATH"] = old_path

    def test_find_exe_skips_relative_path_entries_and_refuses_cmd_shims(self):
        here = Path(tempfile.mkdtemp(prefix="wlgr_exe2_"))
        name = "wlgrfaketool2"
        shim = here / (name + ".cmd")
        shim.write_text("echo hi", encoding="utf-8")
        shim.chmod(0o755)
        old_path, old_cwd = os.environ.get("PATH", ""), Path.cwd()
        try:
            os.chdir(here.parent)
            os.environ["PATH"] = (
                here.name
            )  # a RELATIVE entry resolves against the current directory
            self.assertIsNone(paths.find_exe(name))
            os.chdir(old_cwd)
            os.environ["PATH"] = str(here)
            if sys.platform == "win32":
                self.assertIsNone(paths.find_exe(name))  # a .cmd shim would get unescaped arguments
        finally:
            os.chdir(old_cwd)
            os.environ["PATH"] = old_path

    def test_repo_root_is_found_from_a_subdirectory_without_running_git(self):
        repo = make_repo(self, repos=False)
        sub_dir = repo / "a" / "b"
        sub_dir.mkdir(parents=True)
        old_cwd, old_path = Path.cwd(), os.environ.get("PATH", "")
        try:
            os.environ["PATH"] = ""  # git is not findable at all
            os.chdir(sub_dir)
            self.assertEqual(cfg.repo_root_from_cwd(), repo.resolve())
            os.chdir(tempfile.mkdtemp(prefix="wlgr_norepo_"))
            with self.assertRaises(ValueError):
                cfg.repo_root_from_cwd()
        finally:
            os.chdir(old_cwd)
            os.environ["PATH"] = old_path

    def test_git_inside_the_repository_is_never_executed(self):
        """find_exe must skip an absolute PATH entry that lies inside the excluded repository."""
        repo = make_repo(self, repos=False)
        bindir = repo / "bin"
        bindir.mkdir()
        name = "wlgrfaketool3"
        fake = bindir / (name + (".exe" if sys.platform == "win32" else ""))
        fake.write_text("x", encoding="utf-8")
        fake.chmod(0o755)
        old_path = os.environ.get("PATH", "")
        try:
            os.environ["PATH"] = str(bindir)
            self.assertIsNone(paths.find_exe(name, exclude=[repo]))
            self.assertIsNotNone(paths.find_exe(name, exclude=[]))
        finally:
            os.environ["PATH"] = old_path

    def test_write_text_is_atomic_strict_and_does_not_follow_a_link_at_the_target(self):
        folder = Path(tempfile.mkdtemp(prefix="wlgr_write_"))
        target = folder / "out.json"
        paths.write_text(target, "first")
        paths.write_text(target, "second")
        self.assertEqual(target.read_text(encoding="utf-8"), "second")
        paths.write_text(
            target, "lone surrogate \ud800 survives as text"
        )  # from hostile JSON; must not raise
        self.assertIn("lone surrogate", target.read_text(encoding="utf-8"))
        self.assertEqual(
            [f.name for f in folder.iterdir()], ["out.json"]
        )  # no temp file left behind
        victim = folder / "victim.txt"
        victim.write_text("untouched", encoding="utf-8")
        link = folder / "linked.json"
        try:
            os.symlink(victim, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not permitted on this machine")
        paths.write_text(link, "replaced the link, not the victim")
        self.assertEqual(victim.read_text(encoding="utf-8"), "untouched")
        self.assertFalse(link.is_symlink())

    def test_a_symlinked_dot_claude_makes_the_local_file_untrusted(self):
        repo = make_repo(self, repos=False)
        real = Path(tempfile.mkdtemp(prefix="wlgr_dotclaude_"))
        (real / "workledger-kit.local.json").write_text("{}", encoding="utf-8")
        shutil_target = repo / ".claude"
        shutil_target.rmdir() if not any(shutil_target.iterdir()) else None
        try:
            os.symlink(real, shutil_target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not permitted on this machine")
        self.assertTrue(cfg.is_tracked(repo / ".claude" / "workledger-kit.local.json", repo))

    def test_malformed_config_types_are_problems_not_tracebacks(self):
        repo = make_repo(self)
        base = {
            "version": 1,
            "repos": [{"slug": REPO, "report_dirs": ".claude/output"}],
            "digest": "not-a-dict",
            "intake_capabilities": {
                "batch": False,
                "query": False,
                "update": False,
                "classify": False,
            },
        }
        problems = cfg.validate(base, repo, ignored=lambda *_: True, tracked_under=lambda *_: False)
        self.assertTrue(any("report_dirs must be a list" in x for x in problems), problems)
        self.assertTrue(any("digest.output_dir" in x for x in problems), problems)

    def test_stream_reserved_and_newline_names_are_refused(self):
        root = make_repo(self)
        for bad in ("a.json\n", "a.json\r", "a:b.json", "COM1.json", "conin$", "nul .txt"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                paths.work_name(cast(Any, bad))  # the None entry checks the type guard on purpose
        for bad in ("out:stream", "CONIN$", "con.txt", "x. "):
            with self.assertRaises(ValueError, msg=bad):
                paths.confine(root / bad, root)

    def test_output_dir_cannot_be_the_repository_root_or_a_stream(self):
        root = make_repo(self)
        base = json.loads((PLUGIN_ROOT / cfg.SETTINGS_NAME).read_text(encoding="utf-8"))
        base["repos"] = [{"slug": REPO}]
        for bad in (".", "./", "out:x"):
            self.assertTrue(
                cfg.validate(
                    {**base, "digest": {"output_dir": bad}},
                    root,
                    ignored=lambda *_: True,
                    tracked_under=lambda *_: False,
                ),
                bad,
            )


class DigestEscapingTests(unittest.TestCase):
    def test_reference_and_url_cannot_break_the_markdown(self):
        a = [
            {
                "source": "report",
                "source_ref": "a`b|c.md#1",
                "title": "T",
                "ambiguous": False,
                "extra": {"url": "http://x\nINJECT | y"},
            }
        ]
        text = dig.build_digest(a, a, "2026-10-07", False, [])
        self.assertIn("`a'b/c.md#1`", text)
        self.assertNotIn("\nINJECT", text)


class SmokeCheckTests(unittest.TestCase):
    """The shared structural check must be able to fail, not only pass."""

    DESC = "d" * 90

    def _skill(self, name="foo", fm_name=None, tools="Read", body="Body.", script=True):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "scripts").mkdir()
        if script:
            (root / "scripts" / "wlgr_x.py").write_text("", encoding="utf-8")
        skill = root / "skills" / name
        skill.mkdir(parents=True)
        text = "\n".join(
            [
                "---",
                f"name: {fm_name or name}",
                f"description: {self.DESC}",
                f"allowed-tools: {tools}",
                "---",
                body,
                "",
            ]
        )
        (skill / "SKILL.md").write_text(text, encoding="utf-8")
        return skill

    def test_good_skill_passes(self):
        grant = "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/wlgr_x.py:*)"
        self.assertEqual(
            smoke.check(self._skill(tools=f"Read, {grant}", body="Run wlgr_x.py now.")), []
        )

    def test_name_mismatch_missing_ref_unused_grant_and_bare_bash_fail(self):
        grant = "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/wlgr_x.py:*)"
        self.assertTrue(
            any("must equal directory name" in f for f in smoke.check(self._skill(fm_name="bar")))
        )
        self.assertTrue(
            any(
                "does not exist" in f
                for f in smoke.check(self._skill(body="See `references/nope.md`."))
            )
        )
        self.assertTrue(
            any("never used" in f for f in smoke.check(self._skill(tools=f"Read, {grant}")))
        )
        self.assertTrue(
            any(
                "does not exist" in f
                for f in smoke.check(
                    self._skill(tools=f"Read, {grant}", script=False, body="wlgr_x.py")
                )
            )
        )
        self.assertTrue(any("bare Bash" in f for f in smoke.check(self._skill(tools="Read, Bash"))))

    def test_broken_relative_path_in_a_workflow_file_is_caught(self):
        """The reviewers' Critical: a workflow file used the SKILL.md-relative prefix."""
        skill = self._skill()
        (skill.parent.parent / "references").mkdir()
        (skill.parent.parent / "references" / "r.md").write_text("x", encoding="utf-8")
        (skill / "workflows").mkdir()
        (skill / "workflows" / "w.md").write_text(
            "See `../../references/r.md` and `../../../references/r.md`.", encoding="utf-8"
        )
        failures = smoke.check(skill)
        self.assertTrue(
            any("../../references/r.md" in f and "workflows" in f for f in failures), failures
        )
        self.assertFalse(any("../../../references/r.md" in f for f in failures))

    def test_plugin_level_docs_resolve_and_quote_only_real_commands(self):
        self.assertEqual(smoke.check_plugin_docs(PLUGIN_ROOT), [])

    def test_a_removed_subcommand_quoted_in_a_doc_is_caught(self):
        """The audit's finding: a reference still said `wlgr_open_items.py labels`, a command a
        refactor removed."""
        root = Path(tempfile.mkdtemp(prefix="wlgr_docs_"))
        (root / "scripts").mkdir()
        (root / "references").mkdir()
        (root / "skills").mkdir()
        (root / "scripts" / "wlgr_tool.py").write_text(
            '"""Usage:\n  wlgr_tool.py annotate <a> <b>\n"""\n', encoding="utf-8"
        )
        (root / "README.md").write_text("x", encoding="utf-8")
        (root / "CONTRIBUTING.md").write_text("x", encoding="utf-8")
        (root / "references" / "r.md").write_text(
            "Run `wlgr_tool.py annotate a b` or `wlgr_tool.py labels x` or see "
            "`references/missing.md`.",
            encoding="utf-8",
        )
        failures = smoke.check_plugin_docs(root)
        self.assertTrue(any("wlgr_tool.py labels" in f for f in failures), failures)
        self.assertTrue(any("references/missing.md" in f for f in failures), failures)
        self.assertFalse(any("annotate" in f for f in failures))

    def test_real_skills_pass(self):
        for skill in sorted((PLUGIN_ROOT / "skills").iterdir()):
            self.assertEqual(smoke.check(skill), [], skill.name)


if __name__ == "__main__":
    unittest.main(verbosity=1)
