#!/usr/bin/env python3
"""Fixture tests for dependabot_pr_action.py.

`git` and `gh` are replaced by a recording fake passed to main(), so the tests are hermetic: no
network, no real repository. They check the exact comment body built for every action, every
refusal, and the exact argument list handed to `gh` (absolute binary path, never a shell, always
-R github.com/<origin repository>, never --body-file / --comment / --delete-branch), plus the
environment the tools run with.
Run: python3 -I scripts/test_dependabot_pr_action.py
"""

import importlib.util
import io
import json
import os
import pathlib
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest import mock

SCRIPT = pathlib.Path(__file__).resolve().parent / "dependabot_pr_action.py"
SPEC = importlib.util.spec_from_file_location("dependabot_pr_action", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"cannot load {SCRIPT}")
action_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(action_module)

REPO = "OwnerX/repo-y"
TARGET = f"github.com/{REPO}"
SHA = "a" * 40
OTHER_SHA = "b" * 40
GH = "/opt/bin/gh"
GIT = "/opt/bin/git"


def fake_which(name):
    return {"gh": GH, "git": GIT}.get(name)


def pr_json(**overrides):
    data = {
        "state": "OPEN",
        "author": {"is_bot": True, "login": "app/dependabot"},
        "headRefName": "dependabot/uv/ty-0.0.84",
        "isCrossRepository": False,
        "headRefOid": SHA,
        "url": f"https://github.com/{REPO}/pull/482",
    }
    data.update(overrides)
    return json.dumps(data)


class FakeRun:
    """Records every command; answers git, gh pr view, and the final gh action."""

    def __init__(self, view=None, origin=f"https://github.com/{REPO}.git", action_rc=0, view_rc=0):
        self.view = pr_json() if view is None else view
        self.origin = origin
        self.action_rc = action_rc
        self.view_rc = view_rc
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), kwargs))
        tool = os.path.basename(argv[0])
        if tool == "git":
            return subprocess.CompletedProcess(argv, 0, stdout=self.origin + "\n", stderr="")
        if argv[1:3] == ["pr", "view"]:
            return subprocess.CompletedProcess(argv, self.view_rc, stdout=self.view, stderr="")
        return subprocess.CompletedProcess(argv, self.action_rc, stdout="done\n", stderr="")

    def action_calls(self):
        return [c for c in self.calls if c[0][1:3] in (["pr", "comment"], ["pr", "close"])]


def run_main(argv, fake, which=fake_which):
    out = io.StringIO()
    with redirect_stdout(out):
        code = action_module.main(argv, run=fake, which=which)
    return code, json.loads(out.getvalue())


def args(action, *extra, pr="482", sha=SHA):
    return [action, pr, "--head-sha", sha, *extra]


class BodyTable(unittest.TestCase):
    CASES = [
        (["rebase"], "@dependabot rebase"),
        (["recreate"], "@dependabot recreate"),
        (["ignore-this", "--scope", "dependency"], "@dependabot ignore this dependency"),
        (["ignore-this", "--scope", "major"], "@dependabot ignore this major version"),
        (["ignore-this", "--scope", "minor"], "@dependabot ignore this minor version"),
        (["ignore-this", "--scope", "patch"], "@dependabot ignore this patch version"),
        (["ignore-dep", "--dep", "ty"], "@dependabot ignore ty"),
        (["ignore-dep", "--dep", "ty", "--scope", "major"], "@dependabot ignore ty major version"),
        (["ignore-dep", "--dep", "ty", "--scope", "minor"], "@dependabot ignore ty minor version"),
        (
            ["ignore-dep", "--dep", "actions/labeler", "--scope", "patch"],
            "@dependabot ignore actions/labeler patch version",
        ),
        (["unignore-all"], "@dependabot unignore *"),
        (["unignore-dep", "--dep", "ty"], "@dependabot unignore ty"),
        (
            ["unignore-dep", "--dep", "ty", "--condition", "[< 1.9, > 1.8.0]"],
            "@dependabot unignore ty [< 1.9, > 1.8.0]",
        ),
        (["show-ignore-conditions", "--dep", "ty"], "@dependabot show ty ignore conditions"),
    ]

    def test_every_action_builds_its_exact_body_and_posts_it_once(self):
        for words, expected in self.CASES:
            with self.subTest(words=words):
                fake = FakeRun()
                code, out = run_main(args(words[0], *words[1:]), fake)
                self.assertEqual(code, 0, out)
                self.assertEqual(out["body"], expected)
                self.assertEqual(
                    fake.action_calls()[0][0],
                    [GH, "pr", "comment", "482", "-R", TARGET, "--body", expected],
                )
                self.assertEqual(len(fake.action_calls()), 1)

    def test_close_runs_plain_gh_pr_close_only(self):
        fake = FakeRun()
        code, out = run_main(args("close"), fake)
        self.assertEqual(code, 0, out)
        self.assertIsNone(out["body"])
        self.assertEqual(fake.action_calls()[0][0], [GH, "pr", "close", "482", "-R", TARGET])

    def test_dry_run_flag_may_come_first_or_last(self):
        for argv in (["--dry-run", *args("rebase")], [*args("rebase"), "--dry-run"]):
            fake = FakeRun()
            code, out = run_main(argv, fake)
            self.assertEqual(code, 0, out)
            self.assertTrue(out["dry_run"])
            self.assertEqual(fake.action_calls(), [])

    def test_no_forbidden_flags_no_shell_absolute_tools_and_pinned_host(self):
        forbidden = {"--body-file", "-F", "--comment", "-c", "--delete-branch", "-d"}
        for words, _ in [*self.CASES, (["close"], None)]:
            fake = FakeRun()
            run_main(args(words[0], *words[1:]), fake)
            for argv, kwargs in fake.calls:
                self.assertFalse(forbidden & set(argv), argv)
                self.assertNotIn("shell", kwargs)
                self.assertIn(argv[0], (GH, GIT), "tools are run by absolute path")
                if argv[0] == GH:
                    self.assertEqual(argv[argv.index("-R") + 1], TARGET)


class Environment(unittest.TestCase):
    def test_host_and_repository_overrides_are_removed_but_auth_is_kept(self):
        dirty = {
            "GH_HOST": "evil.example",
            "GH_REPO": "Other/repo",
            "GH_ENTERPRISE_TOKEN": "t1",
            "GITHUB_ENTERPRISE_TOKEN": "t2",
            "GH_TOKEN": "keep-me",
            "PATH": os.environ.get("PATH", ""),
        }
        fake = FakeRun()
        with mock.patch.dict(os.environ, dirty, clear=True):
            code, out = run_main(args("rebase"), fake)
        self.assertEqual(code, 0, out)
        for _, kwargs in fake.calls:
            env = kwargs["env"]
            for name in ("GH_HOST", "GH_REPO", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
                self.assertNotIn(name, env)
            self.assertEqual(env["GH_TOKEN"], "keep-me")
            self.assertEqual(env["GH_PROMPT_DISABLED"], "1")

    def test_output_is_decoded_leniently(self):
        fake = FakeRun()
        run_main(args("rebase"), fake)
        for _, kwargs in fake.calls:
            self.assertEqual(kwargs["encoding"], "utf-8")
            self.assertEqual(kwargs["errors"], "replace")


class ArgumentRefusals(unittest.TestCase):
    def refused(self, argv, code=2):
        fake = FakeRun()
        got, out = run_main(argv, fake)
        self.assertEqual(got, code, out)
        self.assertFalse(out["ok"])
        self.assertEqual(fake.action_calls(), [], "nothing may be posted or closed on a refusal")
        return fake, out

    def test_bad_pr_numbers(self):
        for pr in ["0", "07", "-1", "12a", "1 2", "$(id)", "1234567890", "", " 5"]:
            with self.subTest(pr=pr):
                fake, _ = self.refused(args("rebase", pr=pr))
                self.assertEqual(fake.calls, [], "arguments are checked before any git/gh call")

    def test_bad_head_sha(self):
        for sha in ["abc", "A" * 40, "g" * 40, "a" * 39, "a" * 41, ""]:
            with self.subTest(sha=sha):
                self.refused(args("rebase", sha=sha))

    def test_dependency_names(self):
        bad = ["@types/node", "-x", "a b", 'a"b', "a$b", "a`b`", "a;b", "", "a" * 101, "../x y"]
        for dep in bad:
            with self.subTest(dep=dep):
                self.refused(args("ignore-dep", f"--dep={dep}"))
        for dep in ["ty", "pymdown-extensions", "actions/labeler", "a" * 100, "Foo.Bar_baz-1"]:
            with self.subTest(dep=dep):
                code, _ = run_main(args("ignore-dep", f"--dep={dep}"), FakeRun())
                self.assertEqual(code, 0)

    def test_conditions(self):
        bad = ["< 1.9", "[]", "[" + "a" * 61 + "]", "[a]b", "[a$b]", "[a;b]", "[a\nb]", "[a'b]"]
        for cond in bad:
            with self.subTest(cond=cond):
                self.refused(args("unignore-dep", "--dep", "ty", f"--condition={cond}"))

    def test_scopes_and_unexpected_arguments(self):
        self.refused(args("ignore-this"))
        self.refused(args("ignore-this", "--scope", "everything"))
        self.refused(args("ignore-dep", "--dep", "ty", "--scope", "dependency"))
        self.refused(args("rebase", "--scope", "major"))
        self.refused(args("rebase", "--dep", "ty"))
        self.refused(args("close", "--condition", "[< 1]"))
        self.refused(args("ignore-this", "--scope", "major", "--dep", "ty"))
        self.refused(args("ignore-dep"))
        self.refused(args("show-ignore-conditions"))
        self.refused(args("unignore-all", "--dep", "ty"))


class PreconditionRefusals(unittest.TestCase):
    def refused(self, fake, *needles):
        code, out = run_main(args("close"), fake)
        self.assertEqual(code, 3, out)
        self.assertFalse(out["ok"])
        for needle in needles:
            self.assertIn(needle, out["refused"])
        self.assertEqual(fake.action_calls(), [])

    def test_each_precondition_alone_refuses(self):
        bot = {"is_bot": True, "login": "app/dependabot"}
        self.refused(FakeRun(view=pr_json(state="CLOSED")), "CLOSED")
        self.refused(FakeRun(view=pr_json(state="MERGED")), "MERGED")
        self.refused(FakeRun(view=pr_json(isCrossRepository=True)), "fork")
        self.refused(FakeRun(view=pr_json(isCrossRepository=None)), "fork")
        self.refused(FakeRun(view=pr_json(author={**bot, "is_bot": False})), "Dependabot")
        self.refused(FakeRun(view=pr_json(author={**bot, "login": "someone"})), "Dependabot")
        self.refused(FakeRun(view=pr_json(author={**bot, "login": "dependabot"})), "Dependabot")
        self.refused(FakeRun(view=pr_json(headRefName="fix/something")), "dependabot/")
        self.refused(FakeRun(view=pr_json(headRefName="dependabot/")), "dependabot/")
        self.refused(FakeRun(view=pr_json(headRefName="dependabot/a b")), "dependabot/")
        self.refused(FakeRun(view=pr_json(headRefOid=OTHER_SHA)), "no longer the SHA")
        self.refused(FakeRun(view=pr_json(url="https://github.com/Other/repo/pull/482")), "repo")
        self.refused(FakeRun(view=pr_json(url=f"https://github.com/{REPO}/pull/999")), "repo")
        self.refused(
            FakeRun(view=pr_json(url="https://evil.example/OwnerX/repo-y/pull/482")), "repo"
        )

    def test_several_problems_are_all_reported(self):
        fake = FakeRun(view=pr_json(state="CLOSED", headRefOid=OTHER_SHA, isCrossRepository=True))
        self.refused(fake, "CLOSED", "fork", "no longer the SHA")

    def test_repository_names_compare_case_insensitively(self):
        url = "https://github.com/ownerx/REPO-Y/pull/482"
        code, out = run_main(args("rebase"), FakeRun(view=pr_json(url=url)))
        self.assertEqual(code, 0, out)


class ToolFailures(unittest.TestCase):
    def test_unreadable_origin_is_a_tool_error(self):
        for origin in ["", "https://gitlab.com/a/b.git", "ssh://git@gitlab.com/a/b", "not a url"]:
            with self.subTest(origin=origin):
                fake = FakeRun(origin=origin)
                code, out = run_main(args("rebase"), fake)
                self.assertEqual(code, 4, out)
                self.assertEqual(fake.action_calls(), [])

    def test_origin_forms_that_resolve(self):
        forms = [
            f"https://github.com/{REPO}.git",
            f"https://github.com/{REPO}",
            f"git@github.com:{REPO}.git",
            f"ssh://git@github.com/{REPO}.git",
        ]
        for origin in forms:
            with self.subTest(origin=origin):
                code, out = run_main(args("rebase"), FakeRun(origin=origin))
                self.assertEqual(code, 0, out)
                self.assertEqual(out["repo"], REPO)

    def test_gh_view_failure_and_bad_shape(self):
        fakes = [
            FakeRun(view_rc=1),
            FakeRun(view="not json"),
            FakeRun(view="{}"),
            FakeRun(view="[]"),
        ]
        for fake in fakes:
            code, out = run_main(args("rebase"), fake)
            self.assertEqual(code, 4, out)
            self.assertEqual(fake.action_calls(), [])

    def test_action_failure_reports_exit_4(self):
        code, out = run_main(args("rebase"), FakeRun(action_rc=1))
        self.assertEqual(code, 4)
        self.assertFalse(out["ok"])

    def test_missing_binary_on_path_is_a_tool_error_before_anything_runs(self):
        for missing in ("gh", "git"):
            with self.subTest(missing=missing):
                fake = FakeRun()
                code, out = run_main(
                    args("rebase"), fake, which=lambda n, m=missing: None if n == m else f"/x/{n}"
                )
                self.assertEqual(code, 4, out)
                self.assertIn("not found on PATH", out["refused"])
                self.assertEqual(fake.calls, [])

    def test_oserror_from_the_tool_is_a_tool_error(self):
        def boom(argv, **kwargs):
            raise FileNotFoundError(argv[0])

        code, out = run_main(args("rebase"), boom)
        self.assertEqual(code, 4, out)

    def test_timeout_reading_is_a_plain_tool_error(self):
        def slow(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, 1)

        code, out = run_main(args("rebase"), slow)
        self.assertEqual(code, 4, out)
        self.assertNotIn("outcome is unknown", out["refused"])

    def test_timeout_during_the_write_says_the_outcome_is_unknown(self):
        base = FakeRun()

        def slow_write(argv, **kwargs):
            if argv[1:3] in (["pr", "comment"], ["pr", "close"]):
                raise subprocess.TimeoutExpired(argv, 1)
            return base(argv, **kwargs)

        for words in (["rebase"], ["close"]):
            code, out = run_main(args(*words), slow_write)
            self.assertEqual(code, 4, out)
            self.assertIn("outcome is unknown", out["refused"])


class DryRun(unittest.TestCase):
    def test_dry_run_checks_everything_but_acts_on_nothing(self):
        fake = FakeRun()
        code, out = run_main(args("ignore-this", "--scope", "major", "--dry-run"), fake)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["dry_run"])
        self.assertEqual(out["body"], "@dependabot ignore this major version")
        self.assertEqual(fake.action_calls(), [])
        self.assertEqual(len(fake.calls), 2, "git remote get-url and gh pr view only")

    def test_dry_run_still_refuses(self):
        code, out = run_main(args("close", "--dry-run"), FakeRun(view=pr_json(state="CLOSED")))
        self.assertEqual(code, 3)


class ProcessLevel(unittest.TestCase):
    def run_script(self, *argv):
        return subprocess.run(
            ["python3", "-I", str(SCRIPT), *argv], capture_output=True, text=True, timeout=60
        )

    def test_script_runs_in_a_real_process_and_refuses_bad_input_without_touching_anything(self):
        done = self.run_script("rebase", "x", "--head-sha", SHA)
        self.assertEqual(done.returncode, 2)
        self.assertFalse(json.loads(done.stdout)["ok"])

    def test_unknown_action_is_an_argparse_usage_error(self):
        done = self.run_script("merge", "1", "--head-sha", SHA)
        self.assertEqual(done.returncode, 2)
        self.assertEqual(done.stdout, "")


if __name__ == "__main__":
    unittest.main()
