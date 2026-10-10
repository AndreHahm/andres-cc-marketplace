#!/usr/bin/env python3
"""Persisted smoke test for triaging-dependabot-prs: frontmatter validity,
referenced-file existence (including bare reference-file mentions inside the
reference files), orphan files, allowed-tools grants versus the gh/Skill/marker
commands the skill actually uses (both directions), and an exact expected grant
set so no extra write-capable grant (and no raw gh api grant) can slip in --
structural checks only, since this is a conversational, AskUserQuestion-driven
skill with no executable logic of its own to simulate."""

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
    "python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/"
    "check_uv_lock_bump.py:*",
    "python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/"
    "dependabot_pr_read.py:*",
    "python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/"
    "dependabot_pr_action.py --dry-run:*",
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
            py = next((tok for tok in base.split() if tok.endswith(".py")), base)
            name = pathlib.PurePosixPath(py).name
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


def check_no_raw_gh_api():
    """The skill reads through scripts/dependabot_pr_read.py; no raw `gh api` command or grant."""
    fm, body = split_skill()
    if fm is None:
        return False, "no frontmatter to check"
    text = without_boundaries(body) + "\n" + "\n".join(reference_texts().values())
    problems = [f"raw command: {s[:50]}" for s in re.findall(r"`(gh api[^`]*)`", text)]
    bash, _ = allowed_tools(fm)
    problems += [f"grant: {g}" for g in sorted(bash) if g.startswith("gh api")]
    if "dependabot_pr_read.py" not in text:
        problems.append("the read script is not named in the instructions or references")
    if problems:
        return False, "; ".join(problems)
    return True, "no raw gh api command or grant; reads go through dependabot_pr_read.py"


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


def _load_action_module():
    path = SKILL_DIR / "scripts" / "dependabot_pr_action.py"
    spec = importlib.util.spec_from_file_location("dependabot_pr_action", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_script_covers_supported_table():
    """Every body the action script builds is a table row, and every table row can be built."""
    patterns = listed_body_patterns()
    if not patterns:
        return False, "no supported command patterns could be built from the table"
    try:
        module = _load_action_module()
    except (ImportError, OSError, SyntaxError) as exc:
        return False, f"cannot load scripts/dependabot_pr_action.py: {exc}"
    if module.DEP_RE.pattern != DEP_RE or module.CONDITION_RE.pattern != CONDITION_RE:
        return False, "the script's dependency/condition patterns differ from this test's copies"
    dep, cond = "ty", "[< 1.9, > 1.8.0]"
    samples = [
        ("rebase", {}),
        ("recreate", {}),
        ("unignore-all", {}),
        ("show-ignore-conditions", {"dep": dep}),
        ("ignore-dep", {"dep": dep}),
        ("unignore-dep", {"dep": dep}),
        ("unignore-dep", {"dep": dep, "condition": cond}),
    ]
    samples += [("ignore-this", {"scope": s}) for s in module.THIS_SCOPES]
    samples += [("ignore-dep", {"dep": dep, "scope": s}) for s in module.DEP_SCOPES]
    untried = set(module.ACTIONS) - {"close"} - {action for action, _ in samples}
    if untried:
        return False, "actions with no sample in this check: " + ", ".join(sorted(untried))
    bodies = []
    for action, kwargs in samples:
        try:
            bodies.append(module.build_body(action, **kwargs))
        except module.Refusal as exc:
            return False, f"the script refused a documented action {action} {kwargs}: {exc}"
    unlisted = [b for b in bodies if not any(re.fullmatch(p, b) for p in patterns)]
    unreachable = [p for p in patterns if not any(re.fullmatch(p, b) for b in bodies)]
    if unlisted:
        return False, "script builds bodies missing from the table: " + "; ".join(unlisted)
    if unreachable:
        return False, "table rows the script cannot build: " + "; ".join(unreachable)
    return True, f"{len(bodies)} sample bodies all match a table row and every row is buildable"


def check_supported_comment_table():
    """The supported-commands table lists only supported words, never a deprecated one."""
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


def check_no_raw_comment_close_or_marker():
    """Outside Boundaries, SKILL.md never runs raw gh comment/close or the marker script."""
    fm, body = split_skill()
    if fm is None:
        return False, "no frontmatter to check"
    used = without_boundaries(body)
    problems = [
        f"raw command in the instructions: {s[:50]}"
        for s in re.findall(r"`(gh pr (?:comment|close)[^`]*)`", used)
    ]
    if "git-write-marker" in used:
        problems.append("the instructions mention the marker script outside Boundaries")
    bash, _ = allowed_tools(fm)
    problems += [
        f"grant that should be gone: {g}"
        for g in sorted(bash)
        if g.startswith(("gh pr comment", "gh pr close")) or "git-write-marker" in g
    ]
    if re.search(r'--body "@dependabot close"', body):
        problems.append("the deprecated @dependabot close comment is posted by the skill")
    if problems:
        return False, "; ".join(problems)
    return True, "no raw gh comment/close, no marker script, no grants for either"


def check_no_gh_pr_read_grants():
    """PR reads go through dependabot_pr_read.py: no `gh pr` grant of any kind, and every read
    subcommand the instructions rely on exists in the script."""
    fm, body = split_skill()
    if fm is None:
        return False, "no frontmatter to check"
    bash, _ = allowed_tools(fm)
    problems = [f"gh pr grant: {g}" for g in sorted(bash) if g.startswith("gh ")]
    used = without_boundaries(body) + "\n" + "\n".join(reference_texts().values())
    problems += [f"raw gh pr command: {s[:50]}" for s in re.findall(r"`(gh pr [^`]*)`", used)]
    script = read(SKILL_DIR / "scripts" / "dependabot_pr_read.py")
    for sub in ("pr-list", "pr-view", "pr-checks", "files", "commits", "uv-lock"):
        if f'"{sub}"' not in script:
            problems.append(f"read script has no {sub} subcommand")
    if problems:
        return False, "; ".join(problems)
    return True, "no gh grant or raw gh pr command; the read script has all six subcommands"


def check_real_run_form_stays_ungranted():
    """Only the --dry-run form of dependabot_pr_action.py is granted, and the instructions say
    the real-run form is deliberately ungranted (so every real write raises its own prompt)."""
    fm, body = split_skill()
    if fm is None:
        return False, "no frontmatter to check"
    bash, _ = allowed_tools(fm)
    grants = [g for g in sorted(bash) if "dependabot_pr_action.py" in g]
    problems = [f"real-run grant: {g}" for g in grants if "--dry-run" not in g]
    if len(grants) != 1:
        problems.append(f"expected exactly one action-script grant, found {len(grants)}")
    if "deliberately absent from `allowed-tools`" not in body:
        problems.append("the instructions do not say the real-run form is deliberately ungranted")
    if problems:
        return False, "; ".join(problems)
    return True, "only the --dry-run action grant exists and the omission is stated as deliberate"


def check_reply_author_rule_is_exact():
    """The reply-reading section names both Dependabot logins and requires a whole-string match."""
    path = SKILL_DIR / "references" / "dependabot-comments.md"
    if not path.exists():
        return False, "references/dependabot-comments.md not found"
    match = re.search(r"^## Reading Dependabot's replies\n.*?(?=^## |\Z)", read(path), re.S | re.M)
    if not match:
        return False, "'## Reading Dependabot's replies' section not found"
    section = " ".join(match.group(0).split())
    problems = []
    for login in ("`dependabot`", "`dependabot[bot]`"):
        if login not in section:
            problems.append(f"does not name the accepted login {login}")
    if "whole string, not a prefix" not in section:
        problems.append("does not require a whole-string comparison")
    if "any other login" not in section:
        problems.append("does not say any other login is ignored")
    if problems:
        return False, "reply-author rule: " + "; ".join(problems)
    return True, "reply-author rule names both Dependabot logins and requires an exact match"


def check_posting_section_uses_script():
    """The posting section routes every comment and close through the script, dry run first."""
    _, body = split_skill()
    match = re.search(r"^## Posting a comment or closing\n.*?(?=^## |\Z)", body, re.S | re.M)
    if not match:
        return False, "'## Posting a comment or closing' section not found"
    section = " ".join(match.group(0).split())
    needed = [
        "scripts/dependabot_pr_action.py",
        "--dry-run",
        "--head-sha",
        "never pass a body",
        "never fall back to a raw `gh` command",
    ]
    missing = [n for n in needed if n not in section]
    if missing:
        return False, "the posting section no longer says: " + ", ".join(missing)
    return True, "the posting section routes everything through the script, dry run first"


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


def _run_script_tests(name, label):
    test = SKILL_DIR / "scripts" / name
    if not test.exists():
        return False, f"scripts/{name} not found"
    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(test)], capture_output=True, text=True, timeout=300
        )
    except subprocess.TimeoutExpired:
        return False, f"{label} tests did not finish within 300 seconds"
    if proc.returncode != 0:
        return False, f"{label} tests fail: " + (proc.stderr.strip().splitlines() or ["?"])[-1]
    return True, f"{label} tests pass"


def check_action_tests_pass():
    """The comment/close script's own fixture tests pass (fake gh and git, no network)."""
    return _run_script_tests("test_dependabot_pr_action.py", "comment/close script")


def check_read_tests_pass():
    """The read script's own fixture tests pass (fake gh and git, no network)."""
    return _run_script_tests("test_dependabot_pr_read.py", "read script")


def main():
    checks = [
        check_frontmatter,
        check_name_matches_directory,
        check_referenced_files,
        check_no_orphans,
        check_grants_match_body,
        check_references_use_granted_commands,
        check_exact_grant_set,
        check_no_raw_gh_api,
        check_script_covers_supported_table,
        check_supported_comment_table,
        check_no_raw_comment_close_or_marker,
        check_no_gh_pr_read_grants,
        check_real_run_form_stays_ungranted,
        check_reply_author_rule_is_exact,
        check_posting_section_uses_script,
        check_classifier_tests_pass,
        check_action_tests_pass,
        check_read_tests_pass,
    ]
    failed = 0
    for fn in checks:
        ok, msg = fn()
        print(("PASS" if ok else "FAIL"), fn.__name__, "-", msg)
        failed += not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
