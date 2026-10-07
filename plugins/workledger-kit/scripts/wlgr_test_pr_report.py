#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Persisted tests for wlgr_pr_report.py. Run: python wlgr_test_pr_report.py"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import wlgr_open_items as oi  # noqa: E402
import wlgr_pr_report as rep  # noqa: E402

REPO = "AndreHahm/andres-cc-marketplace"


def pr(n, title, body="", state="closed", merged="2026-09-01T00:00:00Z", closed=None):
    return {
        "number": n,
        "title": title,
        "body": body,
        "state": state,
        "merged_at": merged,
        "closed_at": closed or merged,
        "html_url": f"https://github.com/{REPO}/pull/{n}",
    }


class RefTests(unittest.TestCase):
    def test_groups_are_exclusive_and_self_reference_ignored(self):
        r = rep.parse_refs(5, "Fixes #1. Follow-up to #2. See #3 and #1 and #5 and #2")
        self.assertEqual(r, {"closes": [1], "cue": [2], "mention": [3]})

    def test_urls_and_words_are_not_mentions(self):
        self.assertEqual(rep.parse_refs(1, "see org/repo#9 and word#7")["mention"], [])

    def test_scopes(self):
        self.assertEqual(
            rep.plugin_scopes("feat(git-kit, plugin-devkit): x"), ["git-kit", "plugin-devkit"]
        )
        self.assertEqual(rep.plugin_scopes("no scope here"), ["(no scope)"])


class AdversarialInputTests(unittest.TestCase):
    """Before the fix, 40,000 spaces cost 1.6-6 seconds per body (measured); matching is now
    linear."""

    def test_hostile_bodies_are_fast(self):
        for body in (
            "fixes" + " " * 200000 + "x",
            "- [ ] a" + " " * 200000 + "b",
            "\n" * 200000,
            "closes" + " \t" * 100000 + "#1",
        ):
            start = time.perf_counter()
            rep.parse_refs(1, body)
            rep.real_boxes([pr(1, "t", body)])
            self.assertLess(time.perf_counter() - start, 1.0)

    def test_scope_cannot_break_the_table(self):
        self.assertEqual(rep.plugin_scopes("feat(a|b): x"), ["a/b"])


class CliTests(unittest.TestCase):
    def test_facts_file_in_workfolder_becomes_a_report_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True)
            empty = Path(tmp) / ".git" / "empty-excludes"
            empty.write_text("", encoding="utf-8")
            subprocess.run(
                ["git", "-C", tmp, "config", "core.excludesFile", str(empty)], check=True
            )
            (Path(tmp) / ".gitignore").write_text(".temp/\n", encoding="utf-8")
            (Path(tmp) / ".claude").mkdir()
            (Path(tmp) / ".claude" / "workledger-kit.local.json").write_text(
                json.dumps({"repos": [{"slug": REPO}]}), encoding="utf-8"
            )
            work = Path(tmp) / ".temp" / "workledger-digest"
            work.mkdir(parents=True)
            (work / "f.json").write_text(json.dumps([pr(1, "feat(git-kit): a")]), encoding="utf-8")

            def run(*a):
                return subprocess.run(
                    [sys.executable, str(HERE / "wlgr_pr_report.py"), *a],
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )

            ok = run("f.json", "r.md")
            self.assertEqual((ok.returncode, json.loads(ok.stdout)["prs"]), (0, 1), ok.stderr)
            self.assertIn("| git-kit | 1 | 0 |", (work / "r.md").read_text(encoding="utf-8"))
            self.assertEqual(run("../f.json", "r.md").returncode, 1)  # path-like name refused
            self.assertEqual(run("f.json", "r.md", "--since", "yesterday").returncode, 2)
            # a repository with no PRs: unnamed unless --repo says which one it is
            (work / "e.json").write_text("[]", encoding="utf-8")
            self.assertEqual(run("e.json", "empty.md").returncode, 0)
            self.assertIn("unknown", (work / "empty.md").read_text(encoding="utf-8"))
            named = run("e.json", "named.md", "--repo", "someone/else")
            self.assertEqual(named.returncode, 0, named.stderr)
            self.assertIn("someone/else", (work / "named.md").read_text(encoding="utf-8"))
            self.assertEqual(run("e.json", "bad.md", "--repo", "not a slug").returncode, 2)
            self.assertEqual(run("e.json", "bad.md", "--repo").returncode, 2)  # value missing


class ReportTests(unittest.TestCase):
    PRS = [
        pr(10, "feat(git-kit): a", "Closes #3\n- [ ] add docs"),
        pr(11, "fix(codex-kit): b", "Follow-up to #10", merged="2026-10-02T00:00:00Z"),
        pr(12, "chore: c", "", state="open", merged=None, closed=None),
        pr(13, "fix(git-kit): d", "", state="closed", merged=None, closed="2026-09-15T00:00:00Z"),
    ]

    def test_baseline_has_every_pr_and_all_views(self):
        out = rep.build_report(self.PRS, REPO, "2026-10-06")
        for n in (10, 11, 12, 13):
            self.assertIn(f"#{n}", out)
        self.assertIn("- #3: closed by #10", out)
        self.assertIn("#11: follow-up/continues #10", out)
        self.assertIn("#10: 1 unchecked task(s)", out)
        self.assertIn("| git-kit | 2 | 1 |", out)
        self.assertIn("Inferred links are not shown", out)

    def test_template_boxes_are_not_follow_ups_but_unique_boxes_are(self):
        prs = [pr(n, "feat(a): x", "- [ ] Tests added") for n in (1, 2, 3)] + [
            pr(4, "feat(a): y", "- [ ] one real task")
        ]
        out = rep.build_report(prs, REPO, "2026-10-06")
        follow = out.split("## Follow-up PRs and tasks")[1].split("## Per plugin")[0]
        self.assertIn("#4: 1 unchecked task(s)", follow)
        self.assertNotIn("#1:", follow)

    def test_delta_keeps_open_and_recent_only(self):
        out = rep.build_report(self.PRS, REPO, "2026-10-06", since="2026-10-01")
        timeline = out.split("## Timeline")[1].split("## PR to")[0]
        self.assertIn("#11", timeline)
        self.assertIn("#12", timeline)  # open PRs always included
        self.assertNotIn("#10", timeline)
        self.assertNotIn("#13", timeline)

    def test_closed_unmerged_does_not_close_issues(self):
        prs = [pr(20, "fix: x", "Closes #9", merged=None, closed="2026-09-01T00:00:00Z")]
        self.assertIn(
            "- none",
            rep.build_report(prs, REPO, "2026-10-06").split("## Issues closed by merged PRs")[1],
        )

    def test_chunking_report_fits_notion_limit(self):
        many = [
            pr(n, f"feat(plugin-{n % 7}): item {n}", "Follow-up to #1\n- [ ] x")
            for n in range(100, 400)
        ]
        chunks = oi.chunk_text(rep.build_report(many, REPO, "2026-10-06"))
        self.assertTrue(len(chunks) > 1 and all(len(c) <= 2000 for c in chunks))


if __name__ == "__main__":
    unittest.main(verbosity=1)
