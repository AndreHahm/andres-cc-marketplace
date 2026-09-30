#!/usr/bin/env python3
"""Persisted smoke test for skill-refiner-interactive: layout, frontmatter validity,
referenced-file existence and orphans, Bash-grant usage, refinement step sequencing,
reference-to-reference directives, the R13/R18 size ceilings, and AskUserQuestion
header length.

Structural checks only. Whether the skill behaves correctly when followed is covered
by evals/skill-refiner-interactive/, not here. A check that raises is reported as a
FAIL instead of aborting the run, so one broken check never hides the others."""

import json
import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
REFS_DIR = SKILL_DIR / "references"

# A citation of a file in this skill's own references/, bare or with the explicit
# ${CLAUDE_SKILL_DIR}/ prefix. Cross-skill paths (${CLAUDE_PLUGIN_ROOT}/skills/...)
# are preceded by "/" and therefore never match.
CITATION = re.compile(r"(?:\$\{CLAUDE_SKILL_DIR\}/|(?<![\w/]))references/([\w.-]+\.md)")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")

# Used only when plugin-rulebook's settings.json cannot be read next to this skill.
DEFAULT_R13_CRITICAL = 500
DEFAULT_R18_CRITICAL = 30
MIN_REFINEMENT_STEPS = 10
HEADER_LIMIT = 12  # the limit stated in the AskUserQuestion tool's own description


def read(path):
    return path.read_text(encoding="utf-8-sig")


def split_frontmatter(text):
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    return text[4:end], text[end + 5 :]


def fence_state(text):
    """Yield (line_number, line, in_fence) using fence character and length, so a nested
    example inside a longer outer fence does not toggle the state."""
    opened = None
    for number, line in enumerate(text.splitlines(), 1):
        match = FENCE.match(line)
        if opened is None:
            if match:
                opened = match.group(1)
                yield number, line, True
            else:
                yield number, line, False
            continue
        closes = (
            match
            and match.group(1)[0] == opened[0]
            and len(match.group(1)) >= len(opened)
            and not match.group(2).strip()
        )
        yield number, line, True
        if closes:
            opened = None


def lines_outside_fences(text):
    return [(n, line) for n, line, inside in fence_state(text) if not inside]


def fenced_blocks(text):
    """Return (start_line, content_line_count, closed) for every fenced block."""
    blocks = []
    start, count, marker = 0, 0, ""
    for number, line, inside in fence_state(text):
        if not inside:
            continue
        match = FENCE.match(line)
        if match is None:
            count += 1
            continue
        if not marker:
            start, count, marker = number, 0, match.group(1)
            continue
        closes = (
            match.group(1)[0] == marker[0]
            and len(match.group(1)) >= len(marker)
            and not match.group(2).strip()
        )
        if closes:
            blocks.append((start, count, True))
            marker = ""
        else:
            count += 1
    if marker:
        blocks.append((start, count, False))
    return blocks


def size_thresholds():
    settings = SKILL_DIR.parent / "plugin-rulebook" / "assets" / "settings.json"
    try:
        rules = json.loads(read(settings))["rules"]
        r13 = rules["R13_skillmd_line_limit"]["config"]["thresholds"]["critical"]
        r18 = rules["R18_code_block_line_limit"]["config"]["thresholds"]["critical"]
        return r13, r18, "plugin-rulebook settings.json"
    except (OSError, KeyError, ValueError, TypeError):
        return DEFAULT_R13_CRITICAL, DEFAULT_R18_CRITICAL, "built-in defaults"


def cited_references():
    return set(CITATION.findall(read(SKILL_MD)))


def check_layout():
    if not SKILL_MD.is_file():
        return False, "SKILL.md is missing"
    if not REFS_DIR.is_dir():
        return False, "references/ directory is missing"
    return True, "SKILL.md and references/ are present"


def unterminated_flow_field(frontmatter):
    # Returns the first top-level field whose own value opens a flow collection ([ or {)
    # that never closes, else None. Only that opening is scanned: indented lines are read
    # only as continuation of an open collection, so an unmatched bracket inside a block
    # scalar (description: >-) or a quoted scalar stays valid.
    pairs = {"[": "]", "{": "}"}
    lines = frontmatter.splitlines()
    i = 0
    while i < len(lines):
        match = re.match(r"^([\w-]+):[ \t]*(.*)$", lines[i])
        i += 1
        if not match or not match.group(2).startswith(("[", "{")):
            continue
        text = match.group(2)
        while i < len(lines) and lines[i][:1] in (" ", "\t"):
            text += "\n" + lines[i]
            i += 1
        stack, quote = [], None
        for ch in text:
            if quote:
                quote = None if ch == quote else quote
            elif ch in "\"'":
                quote = ch
            elif ch in pairs:
                stack.append(pairs[ch])
            elif ch in pairs.values() and (not stack or stack.pop() != ch):
                return match.group(1)
        if stack or quote:
            return match.group(1)
    return None


def check_frontmatter():
    frontmatter, _ = split_frontmatter(read(SKILL_MD))
    if frontmatter is None:
        return False, "SKILL.md has no closed frontmatter block"
    name = re.search(r"^name:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
    if not name or name.group(1) != SKILL_DIR.name:
        return False, "frontmatter 'name' is missing or does not match the directory name"
    for field in ("description", "when_to_use", "allowed-tools"):
        if not re.search(rf"^{field}:", frontmatter, re.MULTILINE):
            return False, f"missing required frontmatter field '{field}'"
    description = re.search(r"^description:[ \t]*(.*)$", frontmatter, re.MULTILINE)
    if description is None or description.group(1).strip() != ">-":
        return False, "description must use the '>-' block scalar (R8)"
    if re.search(r"^version:", frontmatter, re.MULTILINE):
        return False, "'version' is not a valid skill frontmatter field (R5)"
    broken = unterminated_flow_field(frontmatter)
    if broken:
        return False, f"frontmatter field '{broken}' opens a flow collection that never closes"
    return True, "frontmatter present, closed, and within the R5/R8 basics"


def check_referenced_files():
    cited = cited_references()
    missing = sorted(name for name in cited if not (REFS_DIR / name).exists())
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(missing)
    return True, f"all {len(cited)} referenced files exist"


def check_no_orphans():
    cited = cited_references()
    orphans = sorted(p.name for p in REFS_DIR.glob("*.md") if p.name not in cited)
    if orphans:
        return False, "reference file(s) not linked from SKILL.md: " + ", ".join(orphans)
    return True, "no orphaned reference files"


def check_bash_grants():
    # An unused Bash(<cmd>:*) grant is an R6 least-privilege smell. The grant may be used
    # from a reference file, so search SKILL.md's body and references/ together, and only
    # inside backticks, so an ordinary English word cannot stand in for a real command.
    frontmatter, body = split_frontmatter(read(SKILL_MD))
    line = re.search(r"^allowed-tools:[ \t]*(.*)$", frontmatter or "", re.MULTILINE)
    if not line:
        return False, "no allowed-tools line found"
    value = line.group(1).strip()
    if not value or value.startswith((">", "|", "[")):
        return False, "allowed-tools is not a single-line list; this check cannot read it"
    granted = re.findall(r"Bash\(([\w.-]+)", value)
    if not granted:
        return True, "no scoped Bash grants to check"
    corpus = "\n".join([body, *(read(p) for p in sorted(REFS_DIR.glob("*.md")))])
    unused = [c for c in granted if not re.search(rf"`[^`\n]*\b{re.escape(c)}\b[^`\n]*`", corpus)]
    if unused:
        return False, "Bash grant(s) never invoked in a code span: " + ", ".join(
            sorted(set(unused))
        )
    return True, "every granted Bash command is used in a code span somewhere in the skill"


def check_step_sequence():
    text = read(SKILL_MD)
    start = text.find("## Core Workflow: Refinement")
    end = text.find("## Core Workflow: Validation")
    if start == -1 or end == -1 or end < start:
        return False, "could not find the Refinement and Validation workflow headings in order"
    numbers = []
    for _, line in lines_outside_fences(text[start:end]):
        match = re.match(r"^\s{0,3}(\d+)\.\s+\*\*", line)
        if match:
            numbers.append(int(match.group(1)))
    if numbers != list(range(1, len(numbers) + 1)) or len(numbers) < MIN_REFINEMENT_STEPS:
        return (
            False,
            f"refinement steps are not a clean 1..N sequence with N >= "
            f"{MIN_REFINEMENT_STEPS}: {numbers}",
        )
    cited = {int(n) for n in re.findall(r"\bstep (\d+)\b", text, re.IGNORECASE)}
    dangling = sorted(n for n in cited if n > len(numbers))
    if dangling:
        return False, "SKILL.md cites step number(s) beyond the last step: " + ", ".join(
            map(str, dangling)
        )
    return (
        True,
        f"refinement steps 1..{len(numbers)} are sequential and every 'step N' citation resolves",
    )


def check_no_reference_chains():
    # An imperative directive to read another references/ file is a chain violation. The
    # pattern is built from the real sibling file names, so prose such as "Read SKILL.md"
    # (the target skill's own file) or "see README.md" never matches; fenced examples are skipped.
    # Words between the verb and the file name are allowed up to the end of the sentence.
    names = sorted(p.name for p in REFS_DIR.glob("*.md"))
    if not names:
        return True, "no reference files to check"
    alternatives = "|".join(re.escape(n) for n in names)
    pattern = re.compile(
        r"\b(?:see|read|load|consult|open|refer to)\b[^\n.]*?\s+[`(\"']?"
        r"(?:\$\{CLAUDE_SKILL_DIR\}/)?(?:references/)?(" + alternatives + r")(?![\w-]|\.\w)",
        re.IGNORECASE,
    )
    hits = []
    for path in (REFS_DIR / n for n in names):
        for number, line in lines_outside_fences(read(path)):
            match = pattern.search(line)
            if match and match.group(1).lower() != path.name.lower():
                hits.append(f"{path.name}:{number}")
    if hits:
        return False, "imperative reference-to-reference directive(s): " + ", ".join(hits)
    return True, "no reference-to-reference directives"


def check_size_ceilings():
    r13, r18, source = size_thresholds()
    problems = []
    lines = len(read(SKILL_MD).splitlines())
    if lines > r13:
        problems.append(f"SKILL.md has {lines} lines (R13 critical > {r13})")
    for path in [SKILL_MD, *sorted(REFS_DIR.glob("*.md"))]:
        for start, count, closed in fenced_blocks(read(path)):
            if not closed:
                problems.append(f"{path.name}:{start} fenced block is never closed")
            elif count > r18:
                problems.append(
                    f"{path.name}:{start} code block of {count} lines (R18 critical > {r18})"
                )
    if problems:
        return False, "; ".join(problems)
    return (
        True,
        f"SKILL.md is {lines} lines and no code block exceeds {r18} lines "
        f"(thresholds from {source})",
    )


def check_askuserquestion_headers():
    # The tool's description states a 12-character limit for `header`, but its schema does
    # not reject a longer one, so this enforces a documented convention, not a rejection.
    # Dry-run evals cannot call the tool, so this is checked statically.
    problems = []
    for path in [SKILL_MD, *sorted(REFS_DIR.glob("*.md"))]:
        for number, line in enumerate(read(path).splitlines(), 1):
            match = re.search(r"[\"']?header[\"']?:\s*[\"']([^\"']+)[\"']", line)
            if match and len(match.group(1)) > HEADER_LIMIT:
                problems.append(f"{path.name}:{number} '{match.group(1)}' ({len(match.group(1))})")
    if problems:
        return False, f"AskUserQuestion header(s) over {HEADER_LIMIT} characters: " + ", ".join(
            problems
        )
    return True, f"every AskUserQuestion header is {HEADER_LIMIT} characters or fewer"


CHECKS = [
    check_layout,
    check_frontmatter,
    check_referenced_files,
    check_no_orphans,
    check_bash_grants,
    check_step_sequence,
    check_no_reference_chains,
    check_size_ceilings,
    check_askuserquestion_headers,
]


def main():
    failed = False
    for check in CHECKS:
        try:
            ok, message = check()
        except Exception as error:  # a crashing check must not hide the other checks' results
            ok, message = False, f"check raised {type(error).__name__}: {error}"
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
