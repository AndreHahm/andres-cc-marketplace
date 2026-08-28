#!/usr/bin/env python3
"""Persisted smoke test for rule-development: frontmatter validity, referenced-file
existence (references/ and examples/), Reference Guide table file existence, and
Bash-scope grant usage consistency -- structural checks only, since this is a
conversational, reference-driven skill with no executable logic of its own to
simulate."""

import pathlib
import re
import sys

import yaml

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


def _frontmatter_end_index(text):
    """Validated end-of-frontmatter index (position of the closing '---' line's own
    newline), or -1 if the block never opens/closes -- the single source of truth
    check_frontmatter and _frontmatter_and_body both build on, so a malformed file
    can't split silently into a bogus frontmatter/body pair in one of them while the
    other correctly reports FAIL."""
    if not text.startswith("---\n"):
        return -1
    return text.find("\n---\n", 4)


def _frontmatter_and_body():
    text = SKILL_MD.read_text(encoding="utf-8")
    end = _frontmatter_end_index(text)
    if end == -1:
        # Malformed frontmatter: check_frontmatter already reports this as FAIL:
        # fall back to an empty frontmatter / whole-file-as-body split so the other
        # checks degrade to their own "not found" branches instead of building on an
        # arbitrary, unguarded slice.
        return "", text, text
    header_end = end + 5
    return text[:header_end], text[header_end:], text


def check_frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False, "SKILL.md does not start with a frontmatter block"
    end = _frontmatter_end_index(text)
    if end == -1:
        return False, "frontmatter block is never closed"
    fm = text[4:end]
    try:
        parsed = yaml.safe_load(fm)
    except yaml.YAMLError as exc:
        return False, f"frontmatter is not valid YAML: {exc}"
    if not isinstance(parsed, dict) or "name" not in parsed or "description" not in parsed:
        return False, "missing required frontmatter field ('name' or 'description')"
    return True, "frontmatter present, closed, and valid YAML"


def check_referenced_files():
    # This skill's body cites `references/foo.md`/`examples/foo.md` paths both
    # backtick-fenced and as markdown links (e.g. `[foo.md](references/foo.md)`, per
    # SKILL.md's Rule Structure section) -- both forms must be checked, or a link-style
    # citation like references/rule-file-skeleton.md silently goes unverified.
    _, body, _ = _frontmatter_and_body()
    pattern = r"`((?:references|examples)/[\w.-]+\.md)`|\]\(((?:references|examples)/[\w.-]+\.md)\)"
    missing = []
    for match in re.finditer(pattern, body):
        target = match.group(1) or match.group(2)
        if not (SKILL_DIR / target).is_file():
            missing.append(target)
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def _granted_bash_tokens(frontmatter):
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not fm_line_match:
        return None
    bash_blocks = re.findall(r"Bash\(([^)]+)\)", fm_line_match.group(1))
    tokens = []
    for block in bash_blocks:
        for token in block.split():
            tokens.append(token.split(":")[0])
    return tokens


def check_bash_grants():
    frontmatter, body, _ = _frontmatter_and_body()
    tokens = _granted_bash_tokens(frontmatter)
    if tokens is None:
        return True, "no allowed-tools line found (skip)"
    if not tokens:
        return True, "no Bash(...) grants found (skip)"
    unused = [t for t in tokens if not re.search(r"\b" + re.escape(t.split("/")[-1]) + r"\b", body)]
    if unused:
        return False, "Bash grant(s) never referenced anywhere in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, f"all {len(set(tokens))} distinct Bash grant(s) referenced in the body"


def check_reference_guide_files_exist():
    _, _, text = _frontmatter_and_body()
    idx = text.find("## Reference Guide")
    if idx == -1:
        return True, "no '## Reference Guide' section found (skip)"
    section = text[idx:]
    backtick_targets = re.findall(r"`((?:references|examples|scripts)/[\w./-]+)`", section)
    targets = set(backtick_targets)
    if not targets:
        return True, "no file paths found in '## Reference Guide' (skip)"
    missing = [t for t in targets if not (SKILL_DIR / t).is_file()]
    if missing:
        return False, "'## Reference Guide' file(s) do not exist: " + ", ".join(sorted(missing))
    return True, f"all {len(targets)} '## Reference Guide' file path(s) exist"


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_reference_guide_files_exist,
]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
