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
    """Records every command; answers `git remote get-url` and `gh api`."""

    def __init__(self, api_stdout="[]", api_rc=0, origin=f"https://github.com/{REPO}.git"):
        self.api_stdout = api_stdout
        self.api_rc = api_rc
        self.origin = origin
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), kwargs))
        if os.path.basename(argv[0]) == "git":
            return subprocess.CompletedProcess(argv, 0, stdout=self.origin + "\n", stderr="")
        return subprocess.CompletedProcess(argv, self.api_rc, stdout=self.api_stdout, stderr="")

    def api_calls(self):
        return [c for c in self.calls if c[0][1:2] == ["api"]]


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
        for pr in ["0", "07", "-1", "12a", "$(id)", "1234567890", "1/../2", ""]:
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
