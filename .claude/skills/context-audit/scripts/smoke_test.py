#!/usr/bin/env python3
"""Persisted smoke test for context-audit: exercises scripts/audit-context.sh's real
CLI contract (--help, --top validation, --json output), matching this skill's own
documented Quality Gates in SKILL.md.

The --json/--flagged checks run against a small, isolated fixture (a throwaway $HOME
with one minimal skill, invoked from a throwaway cwd with no project-scope
.claude/skills/) rather than this real repo's own .claude/skills/ tree -- against the
real repo, this script takes well over 90 seconds to finish (one wc -c/wc -w subprocess
per reference file, across dozens of skills' worth of references/*.md), which is a real
scalability finding for the Audit phase to record, not something a smoke test should
have to wait out on every run.
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "audit-context.sh"


def run(*args, cwd=None, env=None):
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=cwd,
        env=env,
    )


def make_fixture_home(tmp_path):
    """A minimal $HOME with exactly one small skill -- enough to exercise the
    scan/scoring code paths without this real repo's own dozens-of-skills scale."""
    fake_home = tmp_path / "fake_home"
    skill_dir = fake_home / ".claude" / "skills" / "fixture-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: fixture-skill\ndescription: a minimal fixture skill.\n---\n\nBody.\n",
        encoding="utf-8",
    )
    return fake_home


def make_large_fixture_home(tmp_path):
    """10 small skills plus one deliberately oversized (>500 words) skill --
    enough entries that --top 08 actually has something to limit against, and
    a real LARGE-flagged entry alongside unflagged ones for --flagged to filter
    on (found by CodeRabbit, 2026-09-18: the single-skill fixture couldn't
    distinguish "ignores the option" from "correctly applies it")."""
    fake_home = tmp_path / "fake_home_large"
    skills_dir = fake_home / ".claude" / "skills"
    for i in range(10):
        skill_dir = skills_dir / f"fixture-skill-{i}"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: fixture-skill-{i}\ndescription: a minimal fixture skill.\n---\n\n"
            f"Body {i}.\n",
            encoding="utf-8",
        )
    large_dir = skills_dir / "fixture-skill-large"
    large_dir.mkdir(parents=True)
    (large_dir / "SKILL.md").write_text(
        "---\nname: fixture-skill-large\ndescription: an oversized fixture skill.\n---\n\n"
        + ("word " * 600),
        encoding="utf-8",
    )
    return fake_home


def check_help_exits_zero():
    result = run("--help")
    if result.returncode != 0:
        return False, f"--help exited {result.returncode}, expected 0"
    if "Usage" not in result.stdout:
        return False, "--help output does not contain a Usage line"
    return True, "--help exits 0 with usage text"


def check_top_missing_value_fails():
    result = run("--top")
    if result.returncode != 1:
        return False, f"--top with no value exited {result.returncode}, expected 1"
    if "requires a value" not in result.stderr:
        return False, "--top with no value did not report 'requires a value' on stderr"
    return True, "--top with no value exits 1 with a clear error"


def check_top_non_integer_fails():
    result = run("--top", "abc")
    if result.returncode != 1:
        return False, f"--top abc exited {result.returncode}, expected 1"
    return True, "--top abc (non-integer) exits 1"


def check_top_leading_zero_is_decimal(fixture_home, fixture_cwd):
    # Quality gate: "--top accepts a leading-zero value (e.g. 08) as decimal, not
    # octal, and never aborts on a missing value" -- the script's own TOP_N=$((10#$2))
    # forces base-10 interpretation; this confirms it doesn't crash or misbehave.
    env = {**os.environ, "HOME": str(fixture_home)}
    result = run("--top", "08", "--json", cwd=str(fixture_cwd), env=env)
    if result.returncode != 0:
        return (
            False,
            f"--top 08 --json exited {result.returncode}, expected 0: {result.stderr[:300]}",
        )
    try:
        json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return False, f"--top 08 --json did not produce valid JSON: {exc}"
    return True, "--top 08 treated as decimal 8, valid JSON produced (isolated fixture)"


def check_flagged_json_valid(fixture_home, fixture_cwd):
    env = {**os.environ, "HOME": str(fixture_home)}
    result = run("--flagged", "--json", cwd=str(fixture_cwd), env=env)
    if result.returncode != 0:
        return (
            False,
            f"--flagged --json exited {result.returncode}, expected 0: {result.stderr[:300]}",
        )
    try:
        json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return False, f"--flagged --json did not produce valid JSON: {exc}"
    return True, "--flagged --json exits 0 with valid JSON (isolated fixture)"


def check_top_actually_limits_results(large_fixture_home, fixture_cwd):
    # Regression guard (found by CodeRabbit, 2026-09-18): the prior check only
    # asserted valid JSON, so an implementation ignoring --top entirely could
    # still pass. Uses an 11-skill fixture -- --top 08 must return exactly 8
    # inventory entries, not all 11.
    env = {**os.environ, "HOME": str(large_fixture_home)}
    result = run("--top", "08", "--json", cwd=str(fixture_cwd), env=env)
    if result.returncode != 0:
        return False, f"--top 08 --json exited {result.returncode}: {result.stderr[:300]}"
    data = json.loads(result.stdout)
    entries = data.get("inventory", [])
    if len(entries) != 8:
        return False, f"--top 08 should return exactly 8 entries, got {len(entries)}"
    if data.get("total_entries", 0) <= 8:
        return (
            False,
            f"fixture should have more than 8 total entries, got {data.get('total_entries')}",
        )
    return True, "--top 08 correctly limits the inventory to exactly 8 entries"


def check_flagged_excludes_unflagged_entries(large_fixture_home, fixture_cwd):
    # Regression guard (found by CodeRabbit, 2026-09-18): the prior check only
    # asserted valid JSON, so an implementation ignoring --flagged entirely
    # could still pass. The fixture has one deliberately oversized (LARGE) skill
    # among 10 small ones -- --flagged must return only the flagged entry.
    env = {**os.environ, "HOME": str(large_fixture_home)}
    result = run("--flagged", "--json", cwd=str(fixture_cwd), env=env)
    if result.returncode != 0:
        return False, f"--flagged --json exited {result.returncode}: {result.stderr[:300]}"
    data = json.loads(result.stdout)
    entries = data.get("inventory", [])
    if not entries:
        return False, "expected at least one flagged entry (the oversized fixture skill), got none"
    non_dash_flags = [e for e in entries if e.get("flag") not in ("-", "")]
    if len(non_dash_flags) != len(entries):
        unflagged = [e for e in entries if e not in non_dash_flags]
        return False, f"--flagged returned unflagged entries too: {unflagged}"
    return True, "--flagged correctly excludes unflagged entries, returning only the flagged one(s)"


CHECKS = [
    check_help_exits_zero,
    check_top_missing_value_fails,
    check_top_non_integer_fails,
]

FIXTURE_CHECKS = [
    check_top_leading_zero_is_decimal,
    check_flagged_json_valid,
]

LARGE_FIXTURE_CHECKS = [
    check_top_actually_limits_results,
    check_flagged_excludes_unflagged_entries,
]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        fixture_home = make_fixture_home(tmp_path)
        fixture_cwd = tmp_path / "fake_project"
        fixture_cwd.mkdir()
        for check in FIXTURE_CHECKS:
            ok, message = check(fixture_home, fixture_cwd)
            print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
            failed = failed or not ok

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        large_fixture_home = make_large_fixture_home(tmp_path)
        fixture_cwd = tmp_path / "fake_project"
        fixture_cwd.mkdir()
        for check in LARGE_FIXTURE_CHECKS:
            ok, message = check(large_fixture_home, fixture_cwd)
            print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
            failed = failed or not ok

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
