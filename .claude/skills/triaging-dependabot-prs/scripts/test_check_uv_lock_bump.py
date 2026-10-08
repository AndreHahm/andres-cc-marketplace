#!/usr/bin/env python3
"""Fixture tests for check_uv_lock_bump.py.

Lockfiles are built in memory (modeled on real dependabot uv bumps) and
written to a temporary directory; the script is run as a subprocess exactly
as the skill runs it. Hermetic: no network, nothing written outside the
temporary directory. Run: python3 -I scripts/test_check_uv_lock_bump.py
"""

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent / "check_uv_lock_bump.py"
REGISTRY = '{ registry = "https://pypi.org/simple" }'
HASH_A = "a" * 64
HASH_B = "b" * 64
PATH = "ab/cd/" + "e" * 60
WHEEL_PATH = "12/34/" + "f" * 60
STAMP = '"2026-01-01T00:00:00.000000Z"'


def url(filename, path=PATH, host="files.pythonhosted.org", scheme="https"):
    return f"{scheme}://{host}/packages/{path}/{filename}"


def entry_text(u, h=HASH_A, size="1234", stamp=STAMP, hash_prefix="sha256:"):
    tail = f", upload-time = {stamp}" if stamp else ""
    return f'{{ url = "{u}", hash = "{hash_prefix}{h}", size = {size}{tail} }}'


def package(
    name,
    version,
    *,
    source=REGISTRY,
    sdist="auto",
    wheels="auto",
    extra="",
    file_name=None,
    sdist_ext="tar.gz",
):
    file_name = file_name or name.lower().replace("-", "_")
    lines = ["[[package]]", f'name = "{name}"', f'version = "{version}"', f"source = {source}"]
    if extra:
        lines.append(extra)
    if sdist == "auto":
        sdist = entry_text(url(f"{file_name}-{version}.{sdist_ext}"))
    if sdist:
        lines.append(f"sdist = {sdist}")
    if wheels == "auto":
        # PEP 427: wheel names never contain hyphens inside the name part, unlike old-style
        # sdist names.
        wheel_name = file_name.replace("-", "_")
        wheels = [
            entry_text(url(f"{wheel_name}-{version}-py3-none-any.whl", path=WHEEL_PATH), HASH_B)
        ]
    if isinstance(wheels, str):  # raw TOML line, for malformed-shape tests
        lines.append(wheels)
    elif wheels is not None:
        lines.append("wheels = [")
        lines.extend(f"    {w}," for w in wheels)
        lines.append("]")
    return "\n".join(lines) + "\n"


def lock(*packages, requires_python=">=3.11", extra_top=""):
    head = f'version = 1\nrevision = 3\nrequires-python = "{requires_python}"\n{extra_top}\n'
    return head + "\n".join(packages)


def run(base, head, package_name="ty", old="1.0.0", new="2.0.0", raw=False):
    with tempfile.TemporaryDirectory() as tmp:
        base_path, head_path = pathlib.Path(tmp, "base.lock"), pathlib.Path(tmp, "head.lock")
        for path, content in ((base_path, base), (head_path, head)):
            if content is None:
                continue
            path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        proc = subprocess.run(
            [
                sys.executable,
                "-I",
                str(SCRIPT),
                "--base",
                str(base_path),
                "--head",
                str(head_path),
                f"--package={package_name}",
                f"--old={old}",
                f"--new={new}",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    if raw:
        return proc
    assert proc.returncode in (0, 1, 2), proc.stderr
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError(
            f"no JSON on stdout (exit {proc.returncode}): {proc.stderr[-300:]}"
        ) from None


OTHER = package("requests", "2.0.0")


@unittest.skipIf(sys.version_info < (3, 11), "check_uv_lock_bump.py needs tomllib (Python 3.11+)")
class Base(unittest.TestCase):
    def assert_passes(self, base, head, **kw):
        code, res = run(base, head, **kw)
        self.assertEqual((code, res["ok"], res["reasons"]), (0, True, []), res)
        return res

    def assert_rejected(self, base, head, expected_reasons, exact=True, **kw):
        """Every expected fragment must appear; with exact=True there must be no other reason."""
        code, res = run(base, head, **kw)
        self.assertEqual(code, 1, res)
        self.assertFalse(res["ok"])
        if exact:
            self.assertEqual(len(res["reasons"]), len(expected_reasons), res["reasons"])
        for fragment in expected_reasons:
            self.assertTrue(any(fragment in r for r in res["reasons"]), (fragment, res["reasons"]))

    def assert_unusable(self, base, head, fragment=None, **kw):
        code, res = run(base, head, **kw)
        self.assertEqual((code, res["ok"]), (2, False), res)
        self.assertTrue(res["reasons"][0].startswith("unusable input"), res)
        if fragment:
            self.assertIn(fragment, res["reasons"][0], res)


class AcceptTests(Base):
    def test_single_package_bump_passes(self):
        res = self.assert_passes(
            lock(package("ty", "1.0.0"), OTHER), lock(package("ty", "2.0.0"), OTHER)
        )
        self.assertEqual((res["wheels"], res["sdist"]), (1, True))

    def test_name_normalisation(self):
        base = lock(package("mkdocs-git-plugin", "1.0.0", file_name="mkdocs_git_plugin"))
        head = lock(package("mkdocs-git-plugin", "2.0.0", file_name="mkdocs_git_plugin"))
        self.assert_passes(base, head, package_name="Mkdocs_Git.Plugin")

    def test_uppercase_name_in_lock(self):
        self.assert_passes(
            lock(package("Ty", "1.0.0", file_name="ty")),
            lock(package("Ty", "2.0.0", file_name="ty")),
        )

    def test_old_style_hyphenated_sdist_name(self):
        base = lock(package("mkdocs-git-plugin", "1.0.0", file_name="mkdocs-git-plugin"))
        head = lock(package("mkdocs-git-plugin", "2.0.0", file_name="mkdocs-git-plugin"))
        self.assert_passes(base, head, package_name="mkdocs-git-plugin")

    def test_zip_sdist(self):
        self.assert_passes(
            lock(package("ty", "1.0.0", sdist_ext="zip")),
            lock(package("ty", "2.0.0", sdist_ext="zip")),
        )

    def test_release_candidate_version(self):
        self.assert_passes(
            lock(package("ty", "1.0.0")), lock(package("ty", "2.0.0rc1")), new="2.0.0rc1"
        )

    def test_wheel_with_build_tag_and_several_wheels(self):
        def wheel(tag):
            return entry_text(url(f"ty-2.0.0-{tag}.whl", path=WHEEL_PATH), HASH_B)

        head = lock(
            package(
                "ty",
                "2.0.0",
                wheels=[wheel("1-py3-none-any"), wheel("cp312-cp312-manylinux_2_17_x86_64")],
            )
        )
        res = self.assert_passes(lock(package("ty", "1.0.0")), head)
        self.assertEqual(res["wheels"], 2)

    def test_wheels_only_package(self):
        self.assert_passes(
            lock(package("ty", "1.0.0", sdist=None)), lock(package("ty", "2.0.0", sdist=None))
        )

    def test_wheels_key_absent_equals_empty_list(self):
        for wheels in (None, []):
            with self.subTest(wheels=wheels):
                self.assert_passes(
                    lock(package("ty", "1.0.0", wheels=wheels)),
                    lock(package("ty", "2.0.0", wheels=wheels)),
                )

    def test_wheels_empty_list_versus_absent_key(self):
        # `wheels` is a free key, so an empty list on one side and no key on the other is not a
        # change by itself (the sdist still counts as the entry's files).
        for base_wheels, head_wheels in ((None, []), ([], None)):
            with self.subTest(base=base_wheels, head=head_wheels):
                self.assert_passes(
                    lock(package("ty", "1.0.0", wheels=base_wheels)),
                    lock(package("ty", "2.0.0", wheels=head_wheels)),
                )

    def test_upload_time_is_optional(self):
        no_stamp = entry_text(url("ty-2.0.0.tar.gz"), stamp=None)
        self.assert_passes(
            lock(package("ty", "1.0.0")), lock(package("ty", "2.0.0", sdist=no_stamp))
        )

    def test_crlf_line_endings(self):
        base, head = lock(package("ty", "1.0.0")), lock(package("ty", "2.0.0"))
        self.assert_passes(base.replace("\n", "\r\n"), head.replace("\n", "\r\n"))

    def test_one_of_two_same_version_entries_replaced(self):
        # Two locked copies of one package (different resolution markers); only one is bumped.
        def marked(version, marker):
            return package("ty", version, extra=f'resolution-markers = ["{marker}"]')

        base = lock(
            marked("1.0.0", "sys_platform == 'linux'"), marked("1.0.0", "sys_platform == 'win32'")
        )
        head = lock(
            marked("2.0.0", "sys_platform == 'linux'"), marked("1.0.0", "sys_platform == 'win32'")
        )
        self.assert_passes(base, head)


class RejectTests(Base):
    def test_new_dependency_package(self):
        self.assert_rejected(
            lock(package("ty", "1.0.0")),
            lock(package("ty", "2.0.0"), OTHER),
            ["exactly one package"],
        )

    def test_dependency_edge_change(self):
        head = lock(package("ty", "2.0.0", extra='dependencies = [{ name = "packaging" }]'))
        self.assert_rejected(lock(package("ty", "1.0.0")), head, ["'dependencies' changed"])

    def test_other_entry_keys_changed(self):
        for key, value in (
            ("optional-dependencies", 'optional-dependencies = { extra = [{ name = "x" }] }'),
            ("dev-dependencies", 'dev-dependencies = { dev = [{ name = "x" }] }'),
            ("resolution-markers", "resolution-markers = [\"python_full_version >= '3.12'\"]"),
            ("metadata", 'metadata = { requires-dist = [{ name = "x" }] }'),
        ):
            with self.subTest(key=key):
                head = lock(package("ty", "2.0.0", extra=value))
                self.assert_rejected(lock(package("ty", "1.0.0")), head, [f"{key!r} changed"])

    def test_two_packages_bumped(self):
        base = lock(package("ty", "1.0.0"), package("requests", "1.0.0"))
        head = lock(package("ty", "2.0.0"), package("requests", "2.0.0"))
        self.assert_rejected(base, head, ["exactly one package"])

    def test_bump_of_a_different_package_than_named(self):
        base = lock(package("ty", "1.0.0"), package("requests", "1.0.0"))
        head = lock(package("ty", "1.0.0"), package("requests", "2.0.0"))
        # The wrong package also fails the filename checks, so several consistent reasons appear.
        self.assert_rejected(base, head, ["not the named package", "is not ty 2.0.0"], exact=False)

    def test_lines_moved_between_package_blocks(self):
        wheel = entry_text(url("ty-2.0.0-py3-none-any.whl", path=WHEEL_PATH), HASH_B)
        base = lock(
            package("ty", "2.0.0", wheels=[wheel]), package("requests", "2.0.0", wheels=None)
        )
        head = lock(
            package("ty", "2.0.0", wheels=None), package("requests", "2.0.0", wheels=[wheel])
        )
        self.assert_rejected(base, head, ["exactly one package"])

    def test_both_same_version_entries_replaced(self):
        def marked(version, marker):
            return package("ty", version, extra=f'resolution-markers = ["{marker}"]')

        base = lock(marked("1.0.0", "a"), marked("1.0.0", "b"))
        head = lock(marked("2.0.0", "a"), marked("2.0.0", "b"))
        self.assert_rejected(base, head, ["exactly one package"])

    def test_identical_entry_duplicated(self):
        self.assert_rejected(
            lock(package("ty", "1.0.0")),
            lock(package("ty", "1.0.0"), package("ty", "1.0.0")),
            ["exactly one package"],
        )

    def test_package_removed(self):
        self.assert_rejected(
            lock(package("ty", "1.0.0"), OTHER),
            lock(package("ty", "2.0.0")),
            ["exactly one package"],
        )

    def test_identical_lockfiles(self):
        text = lock(package("ty", "1.0.0"))
        self.assert_rejected(text, text, ["exactly one package"])

    def test_wrong_old_and_new_versions(self):
        self.assert_rejected(
            lock(package("ty", "1.0.0")),
            lock(package("ty", "2.0.0")),
            ["removed version"],
            old="0.9.0",
        )
        self.assert_rejected(
            lock(package("ty", "1.0.0")),
            lock(package("ty", "2.0.0")),
            ["added version", "is not ty 3.0.0"],
            exact=False,
            new="3.0.0",
        )

    def test_top_level_changes(self):
        base = lock(package("ty", "1.0.0"))
        self.assert_rejected(
            base,
            lock(package("ty", "2.0.0"), requires_python=">=3.9"),
            ["'requires-python' changed"],
        )
        self.assert_rejected(
            base,
            lock(package("ty", "2.0.0"), extra_top='[options]\nexclude-newer = "2026-01-01"\n'),
            ["'options' changed"],
        )
        self.assert_rejected(
            base, lock(package("ty", "2.0.0")).replace("revision = 3\n", ""), ["'revision' changed"]
        )

    def test_non_default_sources(self):
        for source in (
            '{ git = "https://example.invalid/ty" }',
            '{ editable = "." }',
            '{ path = "../ty" }',
            '{ registry = "https://evil.example/simple" }',
            '{ url = "https://example.invalid/ty.whl" }',
        ):
            with self.subTest(source=source):
                code, res = run(
                    lock(package("ty", "1.0.0")), lock(package("ty", "2.0.0", source=source))
                )
                self.assertEqual(code, 1, res)
                self.assertTrue(
                    any("added entry source is not the default" in r for r in res["reasons"]), res
                )

    def test_removed_side_with_non_default_source(self):
        code, res = run(
            lock(package("ty", "1.0.0", source='{ git = "https://example.invalid/ty" }')),
            lock(package("ty", "2.0.0")),
        )
        self.assertEqual(code, 1, res)
        self.assertTrue(
            any("removed entry source is not the default" in r for r in res["reasons"]), res
        )

    def test_sdist_removed(self):
        self.assert_rejected(
            lock(package("ty", "1.0.0")),
            lock(package("ty", "2.0.0", sdist=None)),
            ["sdist was removed"],
        )

    def test_all_wheels_removed(self):
        self.assert_rejected(
            lock(package("ty", "1.0.0")),
            lock(package("ty", "2.0.0", wheels=None)),
            ["all wheels were removed"],
        )

    def test_no_files_listed(self):
        self.assert_rejected(
            lock(package("ty", "1.0.0", sdist=None, wheels=None)),
            lock(package("ty", "2.0.0", sdist=None, wheels=None)),
            ["lists no files"],
        )

    def test_wheels_not_a_list(self):
        head = lock(package("ty", "2.0.0", wheels='wheels = "x"'))
        self.assert_rejected(
            lock(package("ty", "1.0.0")), head, ["wheels is not a list", "all wheels were removed"]
        )


class FileEntryTests(Base):
    def reject_sdist(self, sdist, *fragments):
        self.assert_rejected(
            lock(package("ty", "1.0.0")), lock(package("ty", "2.0.0", sdist=sdist)), list(fragments)
        )

    def test_url_for_another_project(self):
        self.reject_sdist(entry_text(url("evil-2.0.0.tar.gz")), "is not ty 2.0.0")

    def test_wheel_url_with_wrong_version(self):
        evil = entry_text(url("ty-9.9.9-py3-none-any.whl", path=WHEEL_PATH))
        self.assert_rejected(
            lock(package("ty", "1.0.0")),
            lock(package("ty", "2.0.0", wheels=[evil])),
            ["is not ty 2.0.0"],
        )

    def test_wheel_filename_with_too_few_parts(self):
        bad = entry_text(url("ty-2.0.0.whl", path=WHEEL_PATH))
        self.assert_rejected(
            lock(package("ty", "1.0.0")),
            lock(package("ty", "2.0.0", wheels=[bad])),
            ["unexpected shape"],
        )

    def test_url_variants_are_rejected(self):
        variants = {
            "other host": url("ty-2.0.0.tar.gz", host="files.pythonhosted.org.evil.example"),
            "plain http": url("ty-2.0.0.tar.gz", scheme="http"),
            "userinfo trick": url("ty-2.0.0.tar.gz", host="files.pythonhosted.org@evil.example"),
            "port": url("ty-2.0.0.tar.gz", host="files.pythonhosted.org:8443"),
            "query string": url("ty-2.0.0.tar.gz") + "?x=1",
            "fragment": url("ty-2.0.0.tar.gz") + "#x",
            "short hash path": url("ty-2.0.0.tar.gz", path="ab/cd/" + "e" * 10),
            "trailing newline": url("ty-2.0.0.tar.gz") + "\\n",
            "path traversal": url("../ty-2.0.0.tar.gz"),
        }
        for label, u in variants.items():
            with self.subTest(variant=label):
                self.reject_sdist(entry_text(u), "not a files.pythonhosted.org")

    def test_hash_problems(self):
        for label, kwargs in {
            "not hex": dict(h="xyz"),
            "uppercase hex": dict(h="A" * 64),
            "trailing newline": dict(h=HASH_A + "\\n"),
            "wrong algorithm": dict(h=HASH_A, hash_prefix="md5:"),
            "short": dict(h="a" * 63),
        }.items():
            with self.subTest(hash=label):
                self.reject_sdist(
                    entry_text(url("ty-2.0.0.tar.gz"), **kwargs), "not a lowercase sha256"
                )

    def test_size_problems(self):
        for label, size in {
            "zero": "0",
            "negative": "-5",
            "float": "1.5",
            "bool": "true",
            "string": '"12"',
        }.items():
            with self.subTest(size=label):
                self.reject_sdist(
                    entry_text(url("ty-2.0.0.tar.gz"), size=size), "size is not a positive integer"
                )

    def test_upload_time_not_a_string(self):
        self.reject_sdist(
            entry_text(url("ty-2.0.0.tar.gz"), stamp="5"), "upload-time is not a string"
        )

    def test_missing_key_and_unexpected_key(self):
        missing = f'{{ url = "{url("ty-2.0.0.tar.gz")}", size = 5 }}'
        self.reject_sdist(
            missing, "missing hash", "not a lowercase sha256"
        )  # a missing hash is also not a digest
        extra = entry_text(url("ty-2.0.0.tar.gz"))[:-2] + ', mirror = "elsewhere" }'
        self.reject_sdist(extra, "unexpected keys")

    def test_sdist_not_a_table(self):
        head = lock(package("ty", "2.0.0", sdist='"just a string"'))
        code, res = run(lock(package("ty", "1.0.0")), head)
        self.assertEqual(code, 1, res)
        self.assertTrue(any("not a table" in r for r in res["reasons"]), res)


class UnusableInputTests(Base):
    def test_malformed_toml(self):
        self.assert_unusable(lock(package("ty", "1.0.0")), "this is = = not toml [[")

    def test_missing_file(self):
        self.assert_unusable(None, lock(package("ty", "2.0.0")))

    def test_invalid_utf8(self):
        self.assert_unusable(lock(package("ty", "1.0.0")), b"version = 1\n\xff\xfe\n")

    def test_oversized_file(self):
        big = b"# " + b"x" * 20_000_100 + b"\nversion = 1\n"
        self.assert_unusable(lock(package("ty", "1.0.0")), big)

    def test_unquoted_datetime_does_not_crash(self):
        # A TOML datetime is not JSON-serialisable; it must read as unusable input, not a traceback.
        stamped = lock(
            package(
                "ty",
                "2.0.0",
                sdist=entry_text(url("ty-2.0.0.tar.gz"), stamp="2026-01-01T00:00:00Z"),
            )
        )
        self.assert_unusable(lock(package("ty", "1.0.0")), stamped)

    def test_package_is_not_a_list_of_tables(self):
        self.assert_unusable(lock(package("ty", "1.0.0")), 'version = 1\npackage = "abc"\n')
        self.assert_unusable(lock(package("ty", "1.0.0")), "version = 1\npackage = [1, 2]\n")

    def test_old_equals_new(self):
        # Same version with different file hashes would be a hash swap, not a bump.
        swapped = entry_text(url("ty-1.0.0.tar.gz"), h=HASH_B)
        self.assert_unusable(
            lock(package("ty", "1.0.0")),
            lock(package("ty", "1.0.0", sdist=swapped)),
            fragment="must differ",
            old="1.0.0",
            new="1.0.0",
        )

    def test_invalid_package_name(self):
        for name in ('ty"; rm -rf /', "-ty", "ty\n", ""):
            with self.subTest(name=name):
                self.assert_unusable(
                    lock(package("ty", "1.0.0")),
                    lock(package("ty", "2.0.0")),
                    fragment="package name failed validation",
                    package_name=name,
                )

    def test_invalid_versions(self):
        for new in ("2.0.0 extra", "-1.0", "2.0.0\n", ""):
            with self.subTest(new=new):
                self.assert_unusable(
                    lock(package("ty", "1.0.0")),
                    lock(package("ty", "2.0.0")),
                    fragment="version failed validation",
                    new=new,
                )

    def test_usage_errors_print_no_ok_json(self):
        proc = subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "--base", "x"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn('"ok": true', proc.stdout)
        help_proc = subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "-h"], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(help_proc.returncode, 2)  # -h is not a recognised option
        # Every required option is present, with `--pack` standing in for `--package`: only a
        # disabled abbreviation makes this a usage error (exit 2, nothing on stdout).
        with tempfile.TemporaryDirectory() as tmp:
            lockfile = pathlib.Path(tmp, "x.lock")
            lockfile.write_text(lock(package("ty", "1.0.0")), encoding="utf-8")
            abbrev = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(SCRIPT),
                    "--base",
                    str(lockfile),
                    "--head",
                    str(lockfile),
                    "--pack",
                    "ty",
                    "--old=1.0.0",
                    "--new=2.0.0",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual((abbrev.returncode, abbrev.stdout), (2, ""))


if __name__ == "__main__":
    unittest.main(verbosity=1)
