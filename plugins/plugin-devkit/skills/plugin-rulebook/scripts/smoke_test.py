#!/usr/bin/env python3
"""Persisted smoke test for plugin-rulebook: settings.json parses, rule counts agree between
settings.json and SKILL.md, every reference file is catalogued, SKILL.md stays under R13's
warning line, and the .claude/ mirror (when present) is identical."""

import filecmp
import json
import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
SETTINGS = SKILL_DIR / "assets" / "settings.json"
CATALOG = SKILL_DIR / "references" / "skill-file-catalog.md"
SKILL_LINE_LIMIT = 490


def load_rules():
    return json.loads(SETTINGS.read_text(encoding="utf-8"))["rules"]


def check_settings_parse():
    try:
        rules = load_rules()
    except (OSError, ValueError, KeyError) as exc:
        return False, f"assets/settings.json does not load with a 'rules' object: {exc}"
    return True, f"settings.json parses, {len(rules)} rule keys"


def check_rule_counts():
    rules = load_rules()
    enabled = {key.split("_")[0] for key, cfg in rules.items() if cfg.get("enabled")}
    sections = set(re.findall(r"^### (R\d+)\b", SKILL_MD.read_text(encoding="utf-8"), re.MULTILINE))
    if enabled != sections:
        return False, (
            "enabled rules and SKILL.md '### R' sections differ: "
            + ", ".join(sorted(enabled ^ sections))
        )
    return True, f"{len(enabled)} enabled rules match SKILL.md's rule sections"


def check_catalog_complete():
    catalog = CATALOG.read_text(encoding="utf-8")
    missing = [
        path.name
        for path in sorted((SKILL_DIR / "references").glob("*.md"))
        if path.name != CATALOG.name and path.name not in catalog
    ]
    if missing:
        return False, "reference file(s) not in skill-file-catalog.md: " + ", ".join(missing)
    return True, "every references/*.md file is catalogued"


def check_skill_md_size():
    lines = len(SKILL_MD.read_text(encoding="utf-8").splitlines())
    if lines > SKILL_LINE_LIMIT:
        return False, f"SKILL.md is {lines} lines, above R13's {SKILL_LINE_LIMIT}-line warning"
    return True, f"SKILL.md is {lines} lines, within R13's {SKILL_LINE_LIMIT}-line warning"


def check_mirror():
    # Only meaningful inside this marketplace repo's plugins/<plugin>/skills/<skill> layout.
    if SKILL_DIR.parents[2].name != "plugins":
        return True, "skipped: not in a plugins/ layout"
    mirror = SKILL_DIR.parents[3] / ".claude" / "skills" / SKILL_DIR.name
    if not mirror.is_dir():
        return True, "skipped: no .claude/ mirror present"
    differing = []

    def walk(cmp, prefix=""):
        differing.extend(prefix + name for name in cmp.left_only + cmp.right_only + cmp.diff_files)
        for name, sub in cmp.subdirs.items():
            walk(sub, prefix + name + "/")

    walk(filecmp.dircmp(SKILL_DIR, mirror, ignore=["__pycache__"]))
    if differing:
        return False, "mirror differs: " + ", ".join(sorted(differing))
    return True, ".claude/ mirror is identical"


CHECKS = [
    check_settings_parse,
    check_rule_counts,
    check_catalog_complete,
    check_skill_md_size,
    check_mirror,
]


def main():
    failed = False
    for check in CHECKS:
        try:
            ok, message = check()
        except OSError as exc:
            ok, message = False, f"could not read a required file: {exc}"
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
