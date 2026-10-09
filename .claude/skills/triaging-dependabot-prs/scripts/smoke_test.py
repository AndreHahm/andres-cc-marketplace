#!/usr/bin/env python3
"""Persisted smoke test for triaging-dependabot-prs: frontmatter validity,
referenced-file existence (including bare reference-file mentions inside the
reference files), orphan files, allowed-tools grants versus the gh/Skill/marker
commands the skill actually uses (both directions, with gh api commands matched
by endpoint path), and an exact expected grant set so no extra write-capable
grant can slip in -- structural checks only, since this is a conversational,
AskUserQuestion-driven skill with no executable logic of its own to
simulate."""

import fnmatch
import importlib.util
import pathlib
import re
import subprocess
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
PATH_RE = re.compile(r"`((?:references|scripts)/[\w./-]+)`")
BARE_MD_RE = re.compile(r"`([\w-]+\.md)`")

EXPECTED_BASH = {
    "gh pr list:*",
    "gh pr view:*",
    "gh pr checks:*",
    "gh pr comment:*",
    "gh pr close:*",
    "gh api repos/*/pulls/*/commits:*",
    "gh api repos/*/pulls/*/files:*",
    "gh api repos/*/contents/uv.lock:*",
    "python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/"
    "check_uv_lock_bump.py:*",
    "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh:*",
}
EXPECTED_OTHER = {"Read", "AskUserQuestion", "Skill(merge-pr)", "Skill(finishing-work)"}


def read(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def split_skill():
    """Return (frontmatter, body) or (None, text) if the frontmatter is bad."""
    text = read(SKILL_MD)
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    return text[4:end], text[end + 5 :]


def without_boundaries(body):
    """Drop the Boundaries section, where prohibited commands are named."""
    match = re.search(r"^## Boundaries\n.*?(?=^## |\Z)", body, re.S | re.M)
    return body[: match.start()] + body[match.end() :] if match else body


def reference_texts():
    return {md.name: read(md) for md in sorted((SKILL_DIR / "references").glob("*.md"))}


def allowed_tools(fm):
    """Split the allowed-tools line into Bash(...) grants and other tokens."""
    line = next((ln for ln in fm.splitlines() if ln.startswith("allowed-tools:")), "")
    parts = line.split(":", 1)
    value = parts[1].strip() if len(parts) > 1 else ""
    bash = set(re.findall(r"Bash\(([^)]*)\)", value))
    rest = re.sub(r"Bash\([^)]*\)", "", value)
    other = {t.strip() for t in rest.split(",") if t.strip()}
    return bash, other


def api_patterns(bash):
    return [g.split(":")[0][len("gh api ") :] for g in bash if g.startswith("gh api ")]


def api_path(span):
    """Endpoint token of a `gh api ...` span, with {placeholders} and <placeholders> normalised."""
    match = re.match(r"gh api\s+(?:-\S+\s+)*(\S+)", span)
    if not match:
        return None
    return re.sub(r"[{<][^}>]*[}>]", "x", match.group(1))


def gh_key(span):
    parts = span.split()
    return " ".join(parts[:3])


def span_granted(span, bash):
    if span.startswith("gh api"):
        path = api_path(span)
        return path is not None and any(fnmatch.fnmatch(path, p) for p in api_patterns(bash))
    return gh_key(span) in {g.split(":")[0] for g in bash if g.startswith("gh pr")}


def check_frontmatter():
    fm, _ = split_skill()
    if fm is None:
        return False, "SKILL.md frontmatter missing or unclosed"
    for field in ("name", "description", "allowed-tools"):
        if not re.search(rf"^{re.escape(field)}:", fm, re.M):
            return False, f"frontmatter missing a {field}: key"
    return True, "frontmatter present with name, description, allowed-tools"


def check_referenced_files():
    missing = []
    for md_name, text in [("SKILL.md", read(SKILL_MD)), *reference_texts().items()]:
        for rel in sorted(set(PATH_RE.findall(text))):
            if not (SKILL_DIR / rel).exists():
                missing.append(f"{md_name}: {rel}")
    for md_name, text in reference_texts().items():
        for name in sorted(set(BARE_MD_RE.findall(text)) - {"SKILL.md"}):
            if not (SKILL_DIR / "references" / name).exists():
                missing.append(f"{md_name}: {name}")
    if missing:
        return False, "referenced files missing: " + ", ".join(missing)
    return True, "every referenced file exists (prefixed and bare mentions)"


def check_no_orphans():
    mentioned = set(PATH_RE.findall(read(SKILL_MD)))
    orphans = []
    for sub in ("references", "scripts"):
        for f in sorted((SKILL_DIR / sub).glob("*")):
            if f.is_file() and f"{sub}/{f.name}" not in mentioned:
                orphans.append(f"{sub}/{f.name}")
    if orphans:
        return False, "files never mentioned in SKILL.md: " + ", ".join(orphans)
    return True, "every references/ and scripts/ file is mentioned in SKILL.md"


def check_grants_match_body():
    fm, body = split_skill()
    if fm is None:
        return False, "no frontmatter to check grants against"
    used = without_boundaries(body)
    bash, other = allowed_tools(fm)
    spans = re.findall(r"`(gh [^`]+)`", used)
    ref_spans = [s for t in reference_texts().values() for s in re.findall(r"`(gh [^`]+)`", t)]
    problems = []
    for grant in sorted(bash):
        base = grant.split(":")[0]
        if base.startswith("gh api "):
            pattern = base[len("gh api ") :]
            if not any(
                span.startswith("gh api") and fnmatch.fnmatch(api_path(span) or "", pattern)
                for span in spans + ref_spans
            ):
                problems.append(f"unused grant: {base}")
        elif base.startswith("gh "):
            if base not in used:
                problems.append(f"unused grant: {base}")
        else:
            target = base.split(" ", 1)[1] if base.startswith("python3 ") else base
            name = pathlib.PurePosixPath(target).name
            if name not in used and not any(name in t for t in reference_texts().values()):
                problems.append(f"unused grant: {grant}")
    for span in spans:
        if not span_granted(span, bash):
            problems.append(f"command with no grant: {span[:60]}")
    for tool in sorted(t for t in other if t.startswith("Skill(")):
        if tool not in used:
            problems.append(f"unused grant: {tool}")
    for skill in set(re.findall(r"`Skill\(([\w-]+)\)", used)):
        if f"Skill({skill})" not in other:
            problems.append(f"Skill call with no grant: {skill}")
    if problems:
        return False, "; ".join(sorted(set(problems)))
    return True, "allowed-tools grants and body commands agree in both directions"


def check_references_use_granted_commands():
    fm, _ = split_skill()
    if fm is None:
        return False, "no frontmatter to check"
    bash, _ = allowed_tools(fm)
    problems = []
    for md_name, text in reference_texts().items():
        for span in re.findall(r"`(gh [^`]+)`", text):
            if not span_granted(span, bash):
                problems.append(f"{md_name}: {span[:60]}")
    if problems:
        return False, "gh commands in references with no grant: " + "; ".join(sorted(set(problems)))
    return True, "every gh command named in the reference files has a grant"


def check_exact_grant_set():
    fm, _ = split_skill()
    if fm is None:
        return False, "no frontmatter to check"
    bash, other = allowed_tools(fm)
    problems = []
    if bash != EXPECTED_BASH:
        problems.append(
            f"Bash grants differ: extra={sorted(bash - EXPECTED_BASH)} "
            f"missing={sorted(EXPECTED_BASH - bash)}"
        )
    if other != EXPECTED_OTHER:
        problems.append(
            f"other tools differ: extra={sorted(other - EXPECTED_OTHER)} "
            f"missing={sorted(EXPECTED_OTHER - other)}"
        )
    if problems:
        return False, "; ".join(problems)
    return True, "allowed-tools equals the documented grant set exactly"


def check_name_matches_directory():
    fm, _ = split_skill()
    match = re.search(r"^name:\s*(\S+)", fm or "", re.M)
    if not match or match.group(1) != SKILL_DIR.name:
        return (
            False,
            f"frontmatter name {match.group(1) if match else None!r} "
            f"!= directory {SKILL_DIR.name!r}",
        )
    return True, "frontmatter name equals the directory name"


def check_gh_api_calls_are_get_only():
    _, body = split_skill()
    spans = re.findall(
        r"`(gh api [^`]+)`", without_boundaries(body) + "\n" + "\n".join(reference_texts().values())
    )
    if not spans:
        return False, "no gh api commands found to check (the scan would pass vacuously)"
    bad = [s[:60] for s in spans if "--method GET" not in s]
    if bad:
        return False, "gh api command without --method GET: " + "; ".join(bad)
    return True, "every gh api command carries --method GET"


SUPPORTED_COMMAND_WORDS = ("rebase", "recreate", "ignore", "unignore", "show")
DEPRECATED_COMMAND_WORDS = ("merge", "squash and merge", "cancel merge", "close", "reopen")


DEP_RE = r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}"
CONDITION_RE = r"\[[0-9A-Za-z<>=!~.,*+ -]{1,60}\]"


def listed_body_patterns():
    """Anchored regexes for every body in the supported-commands table, with the <dep> and
    <condition> placeholders replaced by their validation patterns."""
    path = SKILL_DIR / "references" / "dependabot-comments.md"
    if not path.exists():
        return []
    match = re.search(r"^## Supported commands\n.*?(?=^## |\Z)", read(path), re.S | re.M)
    rows = re.findall(r"^\| `(@dependabot [^`]+)` \|", match.group(0), re.M) if match else []
    patterns = []
    for row in rows:
        parts = re.split(r"(<dep>|<condition>)", row)
        patterns.append(
            "".join(
                DEP_RE if p == "<dep>" else CONDITION_RE if p == "<condition>" else re.escape(p)
                for p in parts
            )
        )
    return patterns


def check_comment_bodies_are_listed():
    _, body = split_skill()
    spans = re.findall(r"`(gh pr comment [^`]+)`", without_boundaries(body))
    if not spans:
        return False, "no gh pr comment commands found to check (the scan would pass vacuously)"
    patterns = listed_body_patterns()
    if not patterns:
        return False, "no supported command patterns could be built from the table"

    def body_listed(span):
        found = re.search(r'--body "([^"]*)"', span)
        return bool(found) and any(re.fullmatch(p, found.group(1)) for p in patterns)

    bad = [
        s[:70]
        for s in spans
        if not body_listed(s) or re.search(r"\s-R\b|--repo\b|--body-file|https?://", s)
    ]
    if bad:
        return False, (
            "gh pr comment with a body that is not a supported @dependabot command, or with -R, "
            "a URL or --body-file: " + "; ".join(bad)
        )
    return (
        True,
        "every gh pr comment command uses a supported @dependabot body "
        "and no -R, URL or --body-file",
    )


def check_supported_comment_table():
    path = SKILL_DIR / "references" / "dependabot-comments.md"
    if not path.exists():
        return False, "references/dependabot-comments.md not found"
    text = read(path)
    match = re.search(r"^## Supported commands\n.*?(?=^## |\Z)", text, re.S | re.M)
    if not match:
        return False, "'## Supported commands' section not found"
    bodies = re.findall(r"^\| `(@dependabot [^`]+)` \|", match.group(0), re.M)
    if not bodies:
        return False, "no supported command rows found (the scan would pass vacuously)"
    words = "|".join(SUPPORTED_COMMAND_WORDS)
    problems = [b for b in bodies if not re.match(rf"@dependabot ({words})\b", b)]
    problems += [
        b for b in bodies if re.match(rf"@dependabot ({'|'.join(DEPRECATED_COMMAND_WORDS)})\b", b)
    ]
    missing = [
        w for w in SUPPORTED_COMMAND_WORDS if not any(f"@dependabot {w}" in b for b in bodies)
    ]
    if problems:
        return False, "unsupported or deprecated command in the supported table: " + "; ".join(
            problems
        )
    if missing:
        return False, "supported table lacks a row for: " + ", ".join(missing)
    return (
        True,
        f"{len(bodies)} supported command rows, all supported words present, none deprecated",
    )


def check_close_command_is_plain():
    _, body = split_skill()
    spans = re.findall(r"`(gh pr close[^`]*)`", without_boundaries(body))
    if not spans:
        return False, "no gh pr close command found to check (the scan would pass vacuously)"
    plain = [s for s in spans if s.strip() == "gh pr close <validated-number>"]
    # A bare `gh pr close` is a prose mention of the command's name; anything carrying flags or
    # other arguments is a different invocation.
    bad = [
        s[:70] for s in spans if s.strip() not in ("gh pr close", "gh pr close <validated-number>")
    ]
    if bad:
        return False, "gh pr close in a form other than the plain one: " + "; ".join(bad)
    if not plain:
        return False, "no plain 'gh pr close <validated-number>' invocation found"
    if re.search(r"--body \"@dependabot close\"", body):
        return False, "the deprecated @dependabot close comment is posted by the skill"
    return True, "every gh pr close command is the plain <validated-number> form"


def check_marker_precedes_comment_in_posting_section():
    _, body = split_skill()
    match = re.search(r"^## Posting a comment\n.*?(?=^## |\Z)", body, re.S | re.M)
    if not match:
        return False, "'## Posting a comment' section not found"
    section = match.group(0)
    marker, comment = (
        section.find("git-write-marker.sh"),
        section.find("gh pr comment <validated-number>"),
    )
    if marker < 0 or comment < 0 or marker > comment:
        return False, "the posting section no longer writes the marker before the comment"
    if "never a parallel batch" not in section or "no other Bash command in between" not in section:
        return (
            False,
            "the posting section no longer requires sequential calls with nothing in between",
        )
    return True, "the posting section writes the marker first and requires sequential calls"


def check_classifier_tests_pass():
    test = SKILL_DIR / "scripts" / "test_check_uv_lock_bump.py"
    if not test.exists():
        return False, "scripts/test_check_uv_lock_bump.py not found"
    if importlib.util.find_spec("tomllib") is None:
        # The tests skip themselves (and unittest still exits 0) without tomllib, and the classifier
        # itself exits 2 there, so a pass on this interpreter would be a false one.
        return False, "Python 3.11 or newer is required to run the classifier and its tests"
    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(test)], capture_output=True, text=True, timeout=300
        )
    except subprocess.TimeoutExpired:
        return False, "classifier fixture tests did not finish within 300 seconds"
    if proc.returncode != 0:
        return False, "classifier fixture tests fail: " + (
            proc.stderr.strip().splitlines() or ["?"]
        )[-1]
    if "skipped" in proc.stderr:
        return False, "classifier fixture tests were skipped, not run"
    return True, "classifier fixture tests pass"


def main():
    checks = [
        check_frontmatter,
        check_name_matches_directory,
        check_referenced_files,
        check_no_orphans,
        check_grants_match_body,
        check_references_use_granted_commands,
        check_exact_grant_set,
        check_gh_api_calls_are_get_only,
        check_comment_bodies_are_listed,
        check_supported_comment_table,
        check_close_command_is_plain,
        check_marker_precedes_comment_in_posting_section,
        check_classifier_tests_pass,
    ]
    failed = 0
    for fn in checks:
        ok, msg = fn()
        print(("PASS" if ok else "FAIL"), fn.__name__, "-", msg)
        failed += not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
