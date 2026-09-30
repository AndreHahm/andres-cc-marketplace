#!/usr/bin/env python3
"""Tests for smoke_test.py. Run directly: python3 scripts/test_smoke_test.py

The real skill must pass. Each deliberately broken copy (made in a temp directory,
never in the real skill) must be rejected by exactly the checks that own that
breakage, and each benign copy must still pass. Every mutation is asserted to have
actually changed the file, so a drifted fixture string reports as a stale test,
not as a regression in the smoke test."""

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

SKILL = pathlib.Path(__file__).resolve().parent.parent
TIMEOUT_SECONDS = 60


def run(skill_dir):
    proc = subprocess.run(
        [sys.executable, str(skill_dir / "scripts" / "smoke_test.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
        timeout=TIMEOUT_SECONDS,
    )
    fails = {
        line[len("FAIL  ") :].split(":")[0]
        for line in proc.stdout.splitlines()
        if line.startswith("FAIL")
    }
    return proc.returncode, fails, proc.stderr


def edit(path, fn):
    before = path.read_text(encoding="utf-8")
    after = fn(before)
    if after == before:
        raise AssertionError(
            f"mutation did not change {path.name}: the fixture string drifted, update this test"
        )
    path.write_text(after, encoding="utf-8")


def append(path, text):
    edit(path, lambda t: t + text)


def skill_md(d):
    return d / "SKILL.md"


def refs(d, name):
    return d / "references" / name


# name -> (set of checks that must fail, mutation applied to a copy of the skill directory)
MUTATIONS = {
    "broken-ref": (
        {"check_referenced_files", "check_no_orphans"},
        lambda d: edit(
            skill_md(d),
            lambda t: t.replace(
                "references/pre-analysis-checklist.md", "references/nonexistent-file.md"
            ),
        ),
    ),
    "prefixed-ghost": (
        {"check_referenced_files"},
        lambda d: append(skill_md(d), "\nSee `${CLAUDE_SKILL_DIR}/references/ghost-file.md`.\n"),
    ),
    "orphan": (
        {"check_no_orphans"},
        lambda d: (d / "references" / "orphan-file.md").write_text("# x\n", encoding="utf-8"),
    ),
    "chain": (
        {"check_no_reference_chains"},
        lambda d: append(
            refs(d, "common-scenarios.md"),
            "\nRead references/goal-derivation.md for the mapping.\n",
        ),
    ),
    "chain-prefixed": (
        {"check_no_reference_chains"},
        lambda d: append(
            refs(d, "common-scenarios.md"),
            "\nFor the scans, read ${CLAUDE_SKILL_DIR}/references/goal-derivation.md first.\n",
        ),
    ),
    "chain-mid-sentence": (
        {"check_no_reference_chains"},
        lambda d: append(
            refs(d, "common-scenarios.md"), "\nFor the mapping, see `goal-derivation.md`.\n"
        ),
    ),
    "chain-intervening": (
        {"check_no_reference_chains"},
        lambda d: append(
            refs(d, "common-scenarios.md"),
            "\nRead the instructions in references/goal-derivation.md.\n",
        ),
    ),
    "malformed-flow": (
        {"check_frontmatter"},
        lambda d: edit(
            skill_md(d),
            lambda t: t.replace("when_to_use: >-\n", "when_to_use: [unterminated\n", 1),
        ),
    ),
    "big-block": (
        {"check_size_ceilings"},
        lambda d: append(refs(d, "common-scenarios.md"), "\n```\n" + "line\n" * 35 + "```\n"),
    ),
    "big-block-nested": (
        {"check_size_ceilings"},
        lambda d: append(
            refs(d, "common-scenarios.md"), "\n````\n```\n" + "line\n" * 34 + "```\n````\n"
        ),
    ),
    "unclosed-fence": (
        {"check_size_ceilings"},
        lambda d: append(refs(d, "common-scenarios.md"), "\n```\nline\n"),
    ),
    "over-r13": ({"check_size_ceilings"}, lambda d: append(skill_md(d), "filler\n" * 400)),
    "bad-step": (
        {"check_step_sequence"},
        lambda d: edit(
            skill_md(d),
            lambda t: re.sub(r"^8\. \*\*Measure goals", "9. **Measure goals", t, flags=re.M),
        ),
    ),
    "version-field": (
        {"check_frontmatter"},
        lambda d: edit(
            skill_md(d), lambda t: t.replace("allowed-tools:", "version: 1.0.0\nallowed-tools:", 1)
        ),
    ),
    "name-mismatch": (
        {"check_frontmatter"},
        lambda d: edit(
            skill_md(d),
            lambda t: t.replace("name: skill-refiner-interactive", "name: some-other-name", 1),
        ),
    ),
    "long-header": (
        {"check_askuserquestion_headers"},
        lambda d: edit(
            skill_md(d),
            lambda t: t.replace('header: "Action"', 'header: "A header well over the limit"', 1),
        ),
    ),
    "long-header-json": (
        {"check_askuserquestion_headers"},
        lambda d: edit(
            refs(d, "ask-user-question-patterns.md"),
            lambda t: t.replace(
                '"header": "Action"', '"header": "A header well over the limit"', 1
            ),
        ),
    ),
    "unused-grant": (
        {"check_bash_grants"},
        lambda d: edit(skill_md(d), lambda t: t.replace("Bash(wc:*)", "Bash(wc:*) Bash(zzz:*)", 1)),
    ),
    # The other checks pass vacuously with no references/ files;
    # check_layout and the cited-file check own this breakage.
    "no-references-dir": (
        {"check_layout", "check_referenced_files"},
        lambda d: shutil.rmtree(d / "references"),
    ),
    # Benign changes: these must NOT be flagged (false-positive guards).
    "read-skill-md-ok": (
        set(),
        lambda d: append(refs(d, "common-scenarios.md"), "\nRead SKILL.md first.\n"),
    ),
    "sentence-boundary-ok": (
        set(),
        lambda d: append(
            refs(d, "common-scenarios.md"),
            "\nRead the target SKILL.md first. The goal-derivation.md table is a sibling.\n",
        ),
    ),
    "bracket-in-block-scalar-ok": (
        set(),
        lambda d: edit(
            skill_md(d),
            lambda t: t.replace(
                "description: >-\n",
                "description: >-\n  Unmatched [ bracket and 'quote in a block scalar.\n",
                1,
            ),
        ),
    ),
    "nested-fence-ok": (
        set(),
        lambda d: append(refs(d, "common-scenarios.md"), "\n````\n```\na\nb\nc\n```\n````\n"),
    ),
    "fenced-directive-ok": (
        set(),
        lambda d: append(
            refs(d, "common-scenarios.md"), "\n```\nRead references/goal-derivation.md\n```\n"
        ),
    ),
}


def main():
    code, fails, stderr = run(SKILL)
    ok = code == 0 and not fails
    print(
        f"real skill: exit={code} fails={sorted(fails)} -> {'OK' if ok else 'UNEXPECTED FAILURE'}"
    )
    if not ok and stderr:
        print(stderr)
    with tempfile.TemporaryDirectory() as tmp:
        for name, (expected, mutate) in MUTATIONS.items():
            copy = pathlib.Path(tmp) / name / SKILL.name
            shutil.copytree(SKILL, copy, ignore=shutil.ignore_patterns("__pycache__"))
            mutate(copy)
            code, fails, stderr = run(copy)
            good = fails == expected and code == (1 if expected else 0)
            ok = ok and good
            verdict = "OK" if good else f"WRONG (expected {sorted(expected)})"
            print(f"{name:20s} exit={code} fails={sorted(fails)} -> {verdict}")
            if not good and stderr:
                print(stderr)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
