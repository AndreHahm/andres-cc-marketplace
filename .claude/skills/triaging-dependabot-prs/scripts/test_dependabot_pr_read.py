#!/usr/bin/env python3
"""Fixture tests for dependabot_pr_read.py.

`git` and `gh` are replaced by a recording fake passed to main(), so the tests are hermetic: no
network, no real repository. They pin the exact `gh api` argument list (GET only, pinned host, raw
Accept header for file bodies), the summary shapes, the file-writing refusals, the scrubbed
environment, and that the helper block shared with dependabot_pr_action.py stays identical.
Run: python3 -I scripts/test_dependabot_pr_read.py
"""

import importlib.util
import io
import json
import os
import pathlib
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
READ_PATH = HERE / "dependabot_pr_read.py"
ACTION_PATH = HERE / "dependabot_pr_action.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


read_module = load(READ_PATH, "dependabot_pr_read")

REPO = "OwnerX/repo-y"
GH = "/opt/bin/gh"
GIT = "/opt/bin/git"
SHA = "c" * 40


def fake_which(name):
    return {"gh": GH, "git": GIT}.get(name)


def files_json(n=2):
    return json.dumps(
        [
            {"filename": f"f{i}.txt", "status": "modified", "sha": "x", "patch": "big"}
            for i in range(n)
        ]
    )


def commits_json(n=1):
    return json.dumps(
        [
            {
                "sha": f"{i:040x}",
                "commit": {"verification": {"verified": True}, "message": "m"},
                "author": {"login": "dependabot[bot]"},
                "committer": {"login": "web-flow"},
            }
            for i in range(n)
        ]
    )


class FakeRun:
    """Records every command; answers `git remote get-url`, `gh api` and `gh pr`."""

    def __init__(
        self,
        api_stdout="[]",
        api_rc=0,
        origin=f"https://github.com/{REPO}.git",
        pr_stdout="[]",
        pr_stderr="",
        pr_rc=0,
    ):
        self.api_stdout = api_stdout
        self.api_rc = api_rc
        self.origin = origin
        self.pr_stdout = pr_stdout
        self.pr_stderr = pr_stderr
        self.pr_rc = pr_rc
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), kwargs))
        if os.path.basename(argv[0]) == "git":
            return subprocess.CompletedProcess(argv, 0, stdout=self.origin + "\n", stderr="")
        if argv[1:2] == ["pr"]:
            return subprocess.CompletedProcess(
                argv, self.pr_rc, stdout=self.pr_stdout, stderr=self.pr_stderr
            )
        return subprocess.CompletedProcess(argv, self.api_rc, stdout=self.api_stdout, stderr="")

    def api_calls(self):
        return [c for c in self.calls if c[0][1:2] == ["api"]]

    def pr_calls(self):
        return [c for c in self.calls if c[0][1:2] == ["pr"]]


def run_main(argv, fake, which=fake_which):
    out = io.StringIO()
    with redirect_stdout(out):
        code = read_module.main(argv, run=fake, which=which)
    return code, json.loads(out.getvalue())


class FilesAndCommits(unittest.TestCase):
    def test_files_call_is_a_pinned_get_and_summary_drops_patches(self):
        fake = FakeRun(api_stdout=files_json(2))
        code, out = run_main(["files", "482"], fake)
        self.assertEqual(code, 0, out)
        self.assertEqual(
            fake.api_calls()[0][0],
            [
                GH,
                "api",
                "--hostname",
                "github.com",
                "--method",
                "GET",
                f"repos/{REPO}/pulls/482/files",
                "-f",
                "per_page=100",
            ],
        )
        self.assertEqual(out["count"], 2)
        self.assertFalse(out["truncated"])
        self.assertEqual(
            out["items"][0], {"filename": "f0.txt", "status": "modified", "previous_filename": None}
        )

    def test_commits_summary(self):
        fake = FakeRun(api_stdout=commits_json(1))
        code, out = run_main(["commits", "482"], fake)
        self.assertEqual(code, 0, out)
        self.assertEqual(fake.api_calls()[0][0][6], f"repos/{REPO}/pulls/482/commits")
        self.assertEqual(
            out["items"][0],
            {
                "sha": f"{0:040x}",
                "verified": True,
                "author": "dependabot[bot]",
                "committer": "web-flow",
            },
        )

    def test_commit_without_linked_accounts_has_null_logins(self):
        raw = json.loads(commits_json(1))
        raw[0]["author"] = None
        raw[0]["committer"] = None
        code, out = run_main(["commits", "1"], FakeRun(api_stdout=json.dumps(raw)))
        self.assertEqual(code, 0, out)
        self.assertIsNone(out["items"][0]["author"])
        self.assertIsNone(out["items"][0]["committer"])

    def test_full_page_is_reported_as_truncated(self):
        code, out = run_main(["files", "1"], FakeRun(api_stdout=files_json(100)))
        self.assertEqual(code, 0, out)
        self.assertTrue(out["truncated"])
        code, out = run_main(["files", "1"], FakeRun(api_stdout=files_json(99)))
        self.assertFalse(out["truncated"])

    def test_bad_shapes_and_failures_are_tool_errors(self):
        for stdout in ["not json", "{}", '[{"nope": 1}]', "null"]:
            with self.subTest(stdout=stdout):
                code, out = run_main(["commits", "1"], FakeRun(api_stdout=stdout))
                self.assertEqual(code, 4, out)
                self.assertFalse(out["ok"])
        code, out = run_main(["files", "1"], FakeRun(api_rc=1))
        self.assertEqual(code, 4, out)

    def test_bad_pr_numbers_are_refused_before_any_call(self):
        for pr in [
            "0",
            "07",
            "-1",
            "12a",
            "$(id)",
            "1234567890",
            "1/../2",
            "",
            "482\n",
            " 482",
            "\u0664\u0668\u0662",
            "\uff14\uff18\uff12",
        ]:
            with self.subTest(pr=pr):
                fake = FakeRun()
                code, out = run_main(["files", pr], fake)
                self.assertEqual(code, 2, out)
                self.assertEqual(fake.calls, [])

    def test_no_call_can_write(self):
        forbidden = {"POST", "PUT", "PATCH", "DELETE", "--input", "-F", "--field"}
        for argv in (["files", "5"], ["commits", "5"]):
            fake = FakeRun()
            run_main(argv, fake)
            for call, kwargs in fake.calls:
                self.assertFalse(forbidden & set(call), call)
                self.assertNotIn("shell", kwargs)
                if call[1:2] == ["api"]:
                    self.assertEqual(call[call.index("--method") + 1], "GET")


def checks_stdout(*rows):
    return "".join("\t".join(row) + "\n" for row in rows)


class PrReads(unittest.TestCase):
    """pr-list, pr-view and pr-checks replace the three `gh pr` grants, so the code must pin what
    those grants could not: the repository, a digits-only PR number and a fixed field set."""

    def test_pr_list_is_pinned_to_the_dependabot_app_and_open_state(self):
        items = [{"number": 7, "title": "bump x"}]
        fake = FakeRun(pr_stdout=json.dumps(items))
        code, out = run_main(["pr-list"], fake)
        self.assertEqual(code, 0, out)
        self.assertEqual(
            fake.pr_calls()[0][0],
            [
                GH,
                "pr",
                "list",
                "--author",
                "app/dependabot",
                "--state",
                "open",
                "--limit",
                "100",
                "--json",
                "number,title,url,headRefName,isCrossRepository,mergeStateStatus,createdAt",
                "-R",
                f"github.com/{REPO}",
            ],
        )
        self.assertEqual((out["count"], out["truncated"], out["items"]), (1, False, items))

    def test_pr_list_full_page_is_truncated_and_bad_output_is_a_tool_error(self):
        full = json.dumps([{"number": n} for n in range(100)])
        code, out = run_main(["pr-list"], FakeRun(pr_stdout=full))
        self.assertTrue(out["truncated"], out)
        for fake in (FakeRun(pr_stdout="{}"), FakeRun(pr_stdout="[1]"), FakeRun(pr_stdout="nope")):
            code, out = run_main(["pr-list"], fake)
            self.assertEqual(code, 4, out)
            self.assertFalse(out["ok"])
        code, out = run_main(["pr-list"], FakeRun(pr_rc=1))
        self.assertEqual(code, 4, out)

    def test_pr_view_asks_gh_for_exactly_the_requested_fields(self):
        data = {"state": "OPEN", "headRefOid": SHA}
        fake = FakeRun(pr_stdout=json.dumps(data))
        code, out = run_main(["pr-view", "482", "--fields", "state,headRefOid"], fake)
        self.assertEqual(code, 0, out)
        self.assertEqual(
            fake.pr_calls()[0][0],
            [GH, "pr", "view", "482", "--json", "state,headRefOid", "-R", f"github.com/{REPO}"],
        )
        self.assertEqual(out["data"], data)
        self.assertEqual(out["pr"], "482")

    def test_pr_view_refuses_unlisted_repeated_and_empty_fields_before_any_call(self):
        for fields in ("state,nope", "state,state", "", "state;id", "assignees", "state,"):
            fake = FakeRun()
            code, out = run_main(["pr-view", "482", "--fields", fields], fake)
            self.assertEqual(code, 2, (fields, out))
            self.assertFalse(out["ok"])
            self.assertEqual(fake.calls, [], f"no command may run for fields {fields!r}")

    def test_pr_view_and_pr_checks_refuse_non_digit_numbers_before_any_call(self):
        for kind in ("pr-view", "pr-checks"):
            for bad in (
                "0",
                "01",
                "-1",
                "12a",
                "1 2",
                "$(id)",
                "482/../1",
                "",
                "482\n",
                "\u0664\u0668\u0662",
                "\uff14\uff18\uff12",
            ):
                fake = FakeRun()
                extra = ["--fields", "state"] if kind == "pr-view" else []
                code, out = run_main([kind, bad, *extra], fake)
                self.assertEqual(code, 2, (kind, bad, out))
                self.assertEqual(fake.calls, [], f"no command may run for {bad!r}")

    def test_pr_view_failure_and_bad_shape_are_tool_errors(self):
        for fake in (FakeRun(pr_rc=1), FakeRun(pr_stdout="[]"), FakeRun(pr_stdout="nope")):
            code, out = run_main(["pr-view", "482", "--fields", "state"], fake)
            self.assertEqual(code, 4, out)
            self.assertFalse(out["ok"])

    def test_pr_checks_parses_rows_and_tolerates_failing_and_pending_exit_codes(self):
        stdout = checks_stdout(
            ("Hygiene (PR contract)", "pass", "16s", "https://example.test/1"),
            ("Publish Codex policy result", "fail", "19s", "https://example.test/2"),
            ("CodeRabbit", "pass", "0", "", "Review skipped: author ignored"),
            ("Fork PR", "skipping", "0", "https://example.test/3"),
        )
        for rc in (0, 1, 8):
            fake = FakeRun(pr_stdout=stdout, pr_rc=rc)
            code, out = run_main(["pr-checks", "482"], fake)
            self.assertEqual(code, 0, (rc, out))
            self.assertEqual(
                fake.pr_calls()[0][0],
                [GH, "pr", "checks", "482", "--required", "-R", f"github.com/{REPO}"],
            )
            self.assertEqual(out["count"], 4)
            self.assertEqual(
                out["items"][1],
                {
                    "name": "Publish Codex policy result",
                    "bucket": "fail",
                    "elapsed": "19s",
                    "link": "https://example.test/2",
                },
            )
            self.assertEqual(out["items"][2]["link"], "")

    def test_pr_checks_no_required_checks_is_empty_but_silence_is_not(self):
        quiet = FakeRun(
            pr_stdout="", pr_rc=1, pr_stderr="no required checks reported on the 'x' branch\n"
        )
        code, out = run_main(["pr-checks", "482"], quiet)
        self.assertEqual((code, out["count"], out["items"]), (0, 0, []), out)
        for fake in (
            FakeRun(pr_stdout="", pr_rc=1, pr_stderr="authentication required"),
            FakeRun(pr_stdout="", pr_rc=0),
        ):
            code, out = run_main(["pr-checks", "482"], fake)
            self.assertEqual(code, 4, out)

    def test_pr_checks_unknown_buckets_other_exit_codes_and_short_lines_are_tool_errors(self):
        weird = checks_stdout(("x", "mystery", "1s", ""))
        for fake in (
            FakeRun(pr_stdout=weird, pr_rc=0),
            FakeRun(pr_stdout="only-a-name\n", pr_rc=0),
            FakeRun(pr_stdout=checks_stdout(("x", "pass", "1s", "")), pr_rc=4),
        ):
            code, out = run_main(["pr-checks", "482"], fake)
            self.assertEqual(code, 4, out)
            self.assertFalse(out["ok"])

    def test_every_gh_pr_call_is_a_read_pinned_to_origin(self):
        runs = [
            (["pr-list"], FakeRun()),
            (["pr-view", "5", "--fields", "body,files,commits"], FakeRun(pr_stdout="{}")),
            (
                ["pr-checks", "5"],
                FakeRun(pr_stdout="", pr_rc=1, pr_stderr="no required checks reported"),
            ),
        ]
        for argv, fake in runs:
            run_main(argv, fake)
            for call, _ in fake.pr_calls():
                self.assertIn(call[2], ("list", "view", "checks"), call)
                self.assertEqual(call[-2:], ["-R", f"github.com/{REPO}"], call)
                for word in ("comment", "close", "merge", "edit", "review", "reopen", "ready"):
                    self.assertNotIn(word, call, call)


class UvLock(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = os.path.realpath(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def fetch(self, fake, role="base", ref=SHA, directory=None):
        return run_main(
            [
                "uv-lock",
                "--role",
                role,
                "--ref",
                ref,
                "--dir",
                self.dir if directory is None else directory,
            ],
            fake,
        )

    def test_raw_accept_header_get_and_exact_file_content(self):
        content = 'version = 1\n[[package]]\nname = "ty"\n'
        fake = FakeRun(api_stdout=content)
        code, out = self.fetch(fake)
        self.assertEqual(code, 0, out)
        argv = fake.api_calls()[0][0]
        self.assertEqual(argv[:6], [GH, "api", "--hostname", "github.com", "--method", "GET"])
        self.assertEqual(argv[6], f"repos/{REPO}/contents/uv.lock")
        self.assertIn(f"ref={SHA}", argv)
        i = argv.index("-H")
        self.assertEqual(argv[i + 1], "Accept: application/vnd.github.raw")
        target = pathlib.Path(self.dir) / "base-uv.lock"
        self.assertEqual(out["path"], str(target))
        self.assertEqual(target.read_text(encoding="utf-8"), content)
        self.assertEqual(out["bytes"], len(content.encode()))
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_head_role_writes_its_own_file_only(self):
        code, out = self.fetch(FakeRun(api_stdout="x\n"), role="head")
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(os.listdir(self.dir)), ["head-uv.lock"])

    def test_branch_name_ref_is_accepted(self):
        code, out = self.fetch(FakeRun(api_stdout="x\n"), ref="dependabot/uv/ty-0.0.84")
        self.assertEqual(code, 0, out)

    def test_bad_refs_are_refused_before_any_call(self):
        for ref in ["../x", "a..b", "a b", "a;b", "$(id)", "", "a" * 201]:
            with self.subTest(ref=ref):
                fake = FakeRun()
                code, out = self.fetch(fake, ref=ref)
                self.assertEqual(code, 2, out)
                self.assertEqual(fake.api_calls(), [])
                self.assertEqual(os.listdir(self.dir), [])

    def test_bad_directories_are_refused(self):
        for directory in ["relative/dir", "", os.path.join(self.dir, "missing")]:
            with self.subTest(directory=directory):
                fake = FakeRun()
                code, out = self.fetch(fake, directory=directory)
                self.assertEqual(code, 2, out)
                self.assertEqual(fake.api_calls(), [])

    def test_directory_outside_the_temp_dir_is_refused(self):
        outside = str(HERE)  # the scripts directory itself: a real, absolute, non-temp directory
        fake = FakeRun(api_stdout="x\n")
        code, out = self.fetch(fake, directory=outside)
        self.assertEqual(code, 2, out)
        self.assertIn("system temp directory", out["refused"])
        self.assertEqual(fake.api_calls(), [])
        self.assertFalse((HERE / "base-uv.lock").exists())

    def test_symlink_and_directory_targets_are_refused_and_nothing_is_written_through(self):
        outside = pathlib.Path(self.dir) / "victim.txt"
        outside.write_text("keep", encoding="utf-8")
        link = pathlib.Path(self.dir) / "base-uv.lock"
        os.symlink(outside, link)
        fake = FakeRun(api_stdout="overwritten\n")
        code, out = self.fetch(fake)
        self.assertEqual(code, 2, out)
        self.assertEqual(outside.read_text(encoding="utf-8"), "keep")
        self.assertEqual(fake.api_calls(), [])
        link.unlink()
        link.mkdir()
        code, out = self.fetch(FakeRun(api_stdout="x\n"))
        self.assertEqual(code, 2, out)

    def test_empty_oversize_and_failed_downloads_write_nothing(self):
        big = "a" * (read_module.MAX_LOCK_BYTES + 1)
        for fake in (FakeRun(api_stdout=""), FakeRun(api_stdout=big), FakeRun(api_rc=1)):
            code, out = self.fetch(fake)
            self.assertEqual(code, 4, out)
            self.assertEqual(os.listdir(self.dir), [])

    def test_an_existing_regular_file_is_replaced(self):
        target = pathlib.Path(self.dir) / "base-uv.lock"
        target.write_text("old", encoding="utf-8")
        code, out = self.fetch(FakeRun(api_stdout="new\n"))
        self.assertEqual(code, 0, out)
        self.assertEqual(target.read_text(encoding="utf-8"), "new\n")

    def test_unknown_role_is_an_argparse_error(self):
        with self.assertRaises(SystemExit) as caught:
            with redirect_stdout(io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
                read_module.main(
                    ["uv-lock", "--role", "other", "--ref", SHA, "--dir", self.dir],
                    run=FakeRun(),
                    which=fake_which,
                )
        self.assertEqual(caught.exception.code, 2)


class EnvironmentAndTools(unittest.TestCase):
    def test_overrides_removed_and_auth_kept(self):
        dirty = {
            "GH_HOST": "evil.example",
            "GH_REPO": "Other/repo",
            "GH_ENTERPRISE_TOKEN": "t1",
            "GITHUB_ENTERPRISE_TOKEN": "t2",
            "GH_TOKEN": "keep-me",
            "PATH": os.environ.get("PATH", ""),
        }
        fake = FakeRun(api_stdout=files_json(1))
        with mock.patch.dict(os.environ, dirty, clear=True):
            code, _ = run_main(["files", "1"], fake)
        self.assertEqual(code, 0)
        for _, kwargs in fake.calls:
            env = kwargs["env"]
            for name in read_module.DROPPED_ENV:
                self.assertNotIn(name, env)
            self.assertEqual(env["GH_TOKEN"], "keep-me")
            self.assertEqual(env["GH_PROMPT_DISABLED"], "1")

    def test_tools_run_by_absolute_path(self):
        fake = FakeRun(api_stdout=files_json(1))
        run_main(["files", "1"], fake)
        for call, _ in fake.calls:
            self.assertIn(call[0], (GH, GIT))

    def test_missing_tool_and_bad_origin_are_tool_errors(self):
        for missing in ("gh", "git"):
            fake = FakeRun()
            code, out = run_main(
                ["files", "1"], fake, which=lambda n, m=missing: None if n == m else f"/x/{n}"
            )
            self.assertEqual(code, 4, out)
            self.assertEqual(fake.calls, [])
        for origin in ["", "https://gitlab.com/a/b.git", "not a url"]:
            fake = FakeRun(origin=origin)
            code, out = run_main(["files", "1"], fake)
            self.assertEqual(code, 4, out)
            self.assertEqual(fake.api_calls(), [])

    def test_timeout_and_oserror_are_tool_errors(self):
        def slow(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, 1)

        def boom(argv, **kwargs):
            raise FileNotFoundError(argv[0])

        for fn in (slow, boom):
            code, out = run_main(["files", "1"], fn)
            self.assertEqual(code, 4, out)


class RelativeToolPath(unittest.TestCase):
    def test_relative_which_result_is_refused(self):
        fake = FakeRun()
        code, out = run_main(["files", "1"], fake, which=lambda n: n)
        self.assertEqual(code, 4, out)
        self.assertEqual(fake.calls, [])


class SharedHelpers(unittest.TestCase):
    """The helper block is copied, not imported (each script must run alone under `python3 -I`)."""

    START = "# --- helpers shared, by identical copy"
    END = "# --- end of shared helpers ---"

    @classmethod
    def block(cls, path):
        text = path.read_text(encoding="utf-8")
        start = text.index(cls.START)
        start = text.index("\n", start) + 1
        return text[start : text.index(cls.END)]

    def test_helper_blocks_are_identical(self):
        self.assertEqual(self.block(READ_PATH), self.block(ACTION_PATH))

    def test_shared_constants_are_identical(self):
        action = load(ACTION_PATH, "dependabot_pr_action_for_compare")
        for name in ("ORIGIN_RE", "DROPPED_ENV", "GH_TIMEOUT_SECONDS", "HOST"):
            a, r = getattr(action, name), getattr(read_module, name)
            self.assertEqual(getattr(a, "pattern", a), getattr(r, "pattern", r), name)


class ProcessLevel(unittest.TestCase):
    def test_bad_arguments_exit_2_in_a_real_process(self):
        done = subprocess.run(
            ["python3", "-I", str(READ_PATH), "files", "x"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(done.returncode, 2)
        self.assertFalse(json.loads(done.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
