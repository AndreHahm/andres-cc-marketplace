#!/usr/bin/env python3
"""Persisted smoke test for example-skill: SKILL.md frontmatter validity."""
import pathlib
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


def check_frontmatter(text):
    if not text.startswith("---\n"):
        return False, "SKILL.md does not start with a frontmatter block"
    end = text.find("\n---\n", 4)
    if end == -1:
        return False, "frontmatter block is never closed"
    fm = text[4:end]
    fields = {}
    for line in fm.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    if not fields.get("name"):
        return False, "frontmatter missing non-empty 'name' field"
    if not fields.get("description"):
        return False, "frontmatter missing non-empty 'description' field"
    if fields["name"] != SKILL_DIR.name:
        return False, f"frontmatter name '{fields['name']}' does not match directory '{SKILL_DIR.name}'"
    return True, "frontmatter present, closed, and name matches directory"


def main():
    target = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else SKILL_MD
    text = target.read_text(encoding="utf-8")
    ok, message = check_frontmatter(text)
    print(("PASS  " if ok else "FAIL  ") + "check_frontmatter: " + message)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
