#!/usr/bin/env python3
"""Persisted smoke test for agent-development: frontmatter validity, Bash-grant
usage, referenced-script existence, Additional-Resources table file existence,
and Frontmatter-Summary/documented-field cross-consistency -- structural checks
only, since this is a conversational, reference-driven skill with no executable
logic of its own to simulate beyond the two scripts it shells out to (which own
their own correctness)."""

import json
import pathlib
import re
import subprocess
import sys
import tempfile

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


def _frontmatter_and_body():
    text = SKILL_MD.read_text(encoding="utf-8")
    header_end = text.find("\n---\n", 4) + 5
    return text[:header_end], text[header_end:], text


def check_frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False, "SKILL.md does not start with a frontmatter block"
    end = text.find("\n---\n", 4)
    if end == -1:
        return False, "frontmatter block is never closed"
    fm = text[4:end]
    if not re.search(r"^name:", fm, re.MULTILINE) or not re.search(
        r"^description:", fm, re.MULTILINE
    ):
        return False, "missing required frontmatter field ('name' or 'description')"
    return True, "frontmatter present and closed"


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
    unused = []
    for t in tokens:
        needle = t.split("/")[-1] if "/" in t else t
        if not re.search(rf"\b{re.escape(needle)}\b", body):
            unused.append(t)
    if unused:
        return False, "Bash grant(s) never referenced anywhere in the body: " + ", ".join(
            sorted(set(unused))
        )
    return True, f"all {len(set(tokens))} distinct Bash grant(s) referenced in the body"


def check_scripts_exist():
    frontmatter, _, _ = _frontmatter_and_body()
    tokens = _granted_bash_tokens(frontmatter)
    if not tokens:
        return True, "no allowed-tools/Bash grants found (skip)"
    path_like = [t for t in tokens if "/" in t and re.search(r"\.(sh|py|mjs|js)$", t)]
    if not path_like:
        return True, "no file-path-shaped Bash grants found (skip)"
    missing = [
        p for p in path_like if not (SKILL_DIR / p.removeprefix("${CLAUDE_SKILL_DIR}/")).is_file()
    ]
    if missing:
        return False, "referenced script(s) do not exist: " + ", ".join(missing)
    return True, f"all {len(path_like)} referenced script(s) exist"


def check_reference_table_files_exist():
    _, _, text = _frontmatter_and_body()
    idx = text.find("## Reference Guide")
    if idx == -1:
        return True, "no '## Reference Guide' section found (skip)"
    section = text[idx:]
    link_targets = re.findall(r"\]\(([^)]+)\)", section)
    backtick_targets = re.findall(r"\|\s*`([^`]+)`\s*\|", section)
    targets = {
        t
        for t in set(link_targets) | set(backtick_targets)
        if "<" not in t and "." in t.rsplit("/", 1)[-1]
    }
    if not targets:
        return True, "no file paths found in '## Reference Guide' (skip)"
    missing = [t for t in targets if not (SKILL_DIR / t).is_file()]
    if missing:
        return False, "'## Reference Guide' file(s) do not exist: " + ", ".join(sorted(missing))
    return True, f"all {len(targets)} '## Reference Guide' file path(s) exist"


def check_frontmatter_fields_documented():
    _, _, text = _frontmatter_and_body()
    table_start = text.find("### Frontmatter Summary")
    if table_start == -1:
        return True, "no '### Frontmatter Summary' section found (skip)"
    table_end = text.find("\n### ", table_start + 10)
    table_section = text[table_start : table_end if table_end != -1 else None]
    rows = re.findall(r"^\|\s*(\w+)\s*\|", table_section, re.MULTILINE)
    field_names = [r for r in rows if r != "Field"]
    if not field_names:
        return True, "no field rows found in Frontmatter Summary table (skip)"
    before_table = text[:table_start]
    missing = [
        f
        for f in field_names
        if not re.search(rf"^### {re.escape(f)}\b", before_table, re.MULTILINE)
    ]
    if missing:
        return False, (
            "Frontmatter Summary table lists field(s) with no matching "
            "'### <field>' subsection above: " + ", ".join(missing)
        )
    return True, (
        f"all {len(field_names)} Frontmatter Summary field(s) have a "
        "matching '### <field>' subsection"
    )


def check_trigger_script_detection_helpers():
    script = SKILL_DIR / "scripts" / "test-agent-trigger.sh"
    if not script.is_file():
        return True, "scripts/test-agent-trigger.sh not found (skip)"
    body = script.read_text(encoding="utf-8").split("<<'PY'\n")[-1].split("\nPY\n", 1)[0]
    ns = {}
    exec(body.split("agent_path = Path(sys.argv[1])", 1)[0], ns)

    def rate_limit(status):
        return json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": status}})

    def tool_use(name, tool_input):
        block = {"type": "tool_use", "name": name, "input": tool_input}
        return json.dumps({"type": "assistant", "message": {"content": [block]}})

    init = json.dumps({"type": "system", "subtype": "init", "agents": ["my-agent"]})
    delegation = tool_use("Agent", {"subagent_type": "my-agent"})
    cases = {
        "allowed rate_limit_event ignored": not ns["requires_fallback"](rate_limit("allowed")),
        "allowed_warning rate_limit_event ignored": not ns["requires_fallback"](
            rate_limit("allowed_warning")
        ),
        "rejected rate_limit_event falls back": ns["requires_fallback"](rate_limit("rejected")),
        "plain rate-limit text falls back": ns["requires_fallback"]("Rate limit exceeded"),
        "init listing is not delegation": not ns["_delegated_to_agent"](
            init + "\n" + tool_use("Glob", {"pattern": "x"}), "my-agent"
        ),
        "matching Agent tool_use is delegation": ns["_delegated_to_agent"](
            init + "\n" + delegation, "my-agent"
        ),
        "other agent's delegation is no match": not ns["_delegated_to_agent"](
            delegation, "other-agent"
        ),
    }
    failed = [name for name, ok in cases.items() if not ok]
    if failed:
        return False, "failed: " + ", ".join(failed)
    return True, f"all {len(cases)} detection-helper cases pass"


def check_validator_accepts_list_form_tools():
    agent = (
        "---\nname: list-agent\n"
        "description: Use this agent when you need a list-form tools agent "
        "for testing the validator.\n"
        "model: inherit\ncolor: blue\ntools:\n  - Read\n  - Grep\n---\n\n"
        "You are a test agent. Do the thing carefully and report results "
        "clearly to the caller always.\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "list-agent.md"
        path.write_text(agent, encoding="utf-8")
        proc = subprocess.run(
            ["bash", str(SKILL_DIR / "scripts" / "validate-agent.sh"), str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    if "Missing required field: tools" in proc.stdout or "tools: Read, Grep" not in proc.stdout:
        return False, f"block-list tools: not recognized: {proc.stdout[-300:]!r}"
    return True, "validate-agent.sh reads a YAML block-list tools: field"


CHECKS = [
    check_validator_accepts_list_form_tools,
    check_frontmatter,
    check_bash_grants,
    check_scripts_exist,
    check_reference_table_files_exist,
    check_frontmatter_fields_documented,
    check_trigger_script_detection_helpers,
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
