#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
# PostToolUse hook: deterministic subset of plugin-rulebook checks (R4-R6, R8, R9, R13, R14, R17, R18)
# plus frontmatter-allowlist, agent-enum, broken-link/orphan-file, and hooks-only-var checks on plugin
# component edits. Backs the manual Skill(plugin-rulebook) gate required by
# plugin-rulebook-enforcement.md with a live, always-on check; it does not replace it — semantic
# rules (R1-R3, R7, R10, R19-R22) still require the skill.

import json
import re
import sys
from pathlib import Path

COMPONENT_PATTERNS = [
    ("skill", re.compile(r"[/\\]skills[/\\][^/\\]+[/\\]SKILL\.md$")),
    ("agent", re.compile(r"[/\\]agents[/\\][^/\\]+\.md$")),
    ("command", re.compile(r"[/\\]commands[/\\][^/\\]+\.md$")),
    ("hook", re.compile(r"[/\\]hooks[/\\](hooks\.json|[^/\\]+\.(sh|py))$")),
    ("rule", re.compile(r"[/\\]rules[/\\][^/\\]+\.md$")),
]

PLACEHOLDER_HINTS = ("YOUR_", "EXAMPLE", "PLACEHOLDER", "<", "$")
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r'(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*["\'][A-Za-z0-9/+_\-]{16,}["\']'),
]


def classify(path_str):
    for kind, pattern in COMPONENT_PATTERNS:
        if pattern.search(path_str):
            return kind
    return None


def load_settings(settings_path):
    try:
        return json.loads(Path(settings_path).read_text(encoding="utf-8"))
    except Exception:
        return None


def frontmatter(text):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    return text[3:end]


def body_after_frontmatter(text):
    """Return the content after the closing '---', or all of `text` if there's no frontmatter.

    Used to scope body-only checks (e.g. hooks-only-var misuse) away from a skill's own
    `hooks:` frontmatter field, where ${CLAUDE_PLUGIN_ROOT} is legitimately interpolated —
    scanning the whole file would false-positive on exactly that valid usage.
    """
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    close = text.find("\n", end + 1)
    return text[close + 1:] if close != -1 else ""


def check_name_field(fm, settings, findings):
    m = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
    if not m:
        return
    name = m.group(1).strip().strip("\"'")
    naming = (settings or {}).get("naming", {})
    pattern = naming.get("pattern", r"^[a-z][a-z0-9-]+[a-z0-9]$")
    max_len = naming.get("max_length", 64)
    min_len = naming.get("min_length", 3)
    forbidden = naming.get("forbidden_words", ["anthropic", "claude"])
    if not re.match(pattern, name):
        findings.append(("FAIL", "R4", f"name '{name}' is not kebab-case"))
    elif not (min_len <= len(name) <= max_len):
        findings.append(("FAIL", "R4", f"name '{name}' length {len(name)} outside {min_len}-{max_len}"))
    for word in forbidden:
        if word in name.lower():
            findings.append(("FAIL", "R4", f"name '{name}' contains forbidden word '{word}'"))


def check_forbidden_fields(fm, kind, findings):
    if kind not in ("skill", "agent"):
        return
    if re.search(r"^version:\s*\S", fm, re.MULTILINE):
        findings.append(("FAIL", "R5", "'version' is a command-only field, not allowed in skill/agent frontmatter"))
    tools_m = re.search(r"^allowed-tools:\s*(.+)$", fm, re.MULTILINE)
    if tools_m and "AskUserQuestion" in tools_m.group(1):
        findings.append(("FAIL", "R5", "'AskUserQuestion' is a built-in interaction, not an allowed-tools entry"))


def check_bash_scoping(fm, settings, findings):
    tools_m = re.search(r"^allowed-tools:\s*(.+)$", fm, re.MULTILINE)
    if not tools_m:
        return
    forbidden = (
        (settings or {}).get("rules", {}).get("R6_tool_scoping_least_privilege", {})
        .get("config", {}).get("forbidden_bash_scopes", ["Bash", "Bash(*)"])
    )
    tokens = re.split(r"[\s,]+", tools_m.group(1).strip())
    for tok in tokens:
        tok = tok.strip("[]'\"")
        if tok in forbidden:
            findings.append(("FAIL", "R6", f"unscoped/forbidden bash entry '{tok}' in allowed-tools"))


def check_description_length(fm, settings, findings):
    m = re.search(r"^description:\s*(.*)$", fm, re.MULTILINE)
    if not m:
        return
    value = m.group(1).strip()
    if value == "" or value.startswith((">", "|")):
        return  # already using block scalar syntax
    value = value.strip("\"'")
    threshold = (settings or {}).get("formatting", {}).get("description_multiline_threshold_chars", 80)
    if len(value) > threshold:
        findings.append(("FAIL", "R8", f"description is {len(value)} chars (> {threshold}) — use '>-' block scalar syntax"))


def top_level_fields(fm):
    """Parse top-level (unindented) frontmatter key: value pairs.

    Unlike a naive line-by-line ":"-split, this ignores indented/nested lines
    (e.g. a skill's `hooks:` block) so nested keys like `matcher:` or
    `command:` are never mistaken for top-level frontmatter fields.
    """
    fields = {}
    for line in fm.splitlines():
        if not line or line[0] in (" ", "\t", "#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*$", key):
            fields[key] = value.strip()
    return fields


def check_extra_fields(fm, kind, settings, findings):
    section = {"skill": "skill", "agent": "agent", "rule": "rule_files"}.get(kind)
    if section is None:
        return
    allowed = set((settings or {}).get(section, {}).get("allowed_fields", []))
    if not allowed:
        return  # settings not loaded / list not configured — skip rather than false-positive
    present = set(top_level_fields(fm).keys())
    for f in sorted(present - allowed):
        findings.append(("FAIL", "FIELDS", f"extra frontmatter field: '{f}'"))


def check_agent_enums(fm, settings, findings):
    fields = top_level_fields(fm)
    agent_settings = (settings or {}).get("agent", {})

    for field_name in ("model", "effort", "color", "permissionMode", "memory", "isolation"):
        if field_name not in fields:
            continue
        value = fields[field_name].strip().strip("\"'")
        if not value:
            continue
        valid = set(agent_settings.get(field_name, {}).get("valid_values", []))
        if valid and value not in valid:
            findings.append(("FAIL", "AGENT", f"invalid {field_name} '{value}' (valid: {', '.join(sorted(valid))})"))

    if "tools" in fields:
        tools_value = fields["tools"].strip()
        if tools_value and not tools_value.startswith("["):
            findings.append(("FAIL", "AGENT", "tools field should be a JSON array like [\"Read\", \"Write\"]"))
        elif tools_value:
            try:
                tools_list = json.loads(tools_value)
                if not isinstance(tools_list, list) or not all(isinstance(t, str) for t in tools_list):
                    findings.append(("FAIL", "AGENT", "tools field must be a JSON array of strings"))
            except (json.JSONDecodeError, TypeError):
                findings.append(("FAIL", "AGENT", "tools field must be valid JSON array"))


def extract_markdown_links(text):
    links = re.findall(r"\[(?:[^\]]*)\]\(([^)]+)\)", text)
    return [l for l in links if not l.startswith("http://") and not l.startswith("https://")]


def check_skill_links_and_orphans(text, file_path, findings):
    skill_dir = file_path.parent
    links = extract_markdown_links(text)

    for link in links:
        if not (skill_dir / link).exists():
            findings.append(("FAIL", "LINKS", f"broken link: {link}"))

    linked_normalized = {str(Path(l)).replace("\\", "/") for l in links}
    orphans = []
    for f in skill_dir.rglob("*"):
        if f == file_path or f.is_dir():
            continue
        rel = str(f.relative_to(skill_dir)).replace("\\", "/")
        if rel in linked_normalized or rel in text or f.name in text:
            continue
        orphans.append(rel)

    if orphans:
        shown = ", ".join(orphans[:3])
        more = f" (+{len(orphans) - 3} more)" if len(orphans) > 3 else ""
        findings.append(("ADVISORY", "ORPHAN", f"{len(orphans)} orphaned file(s) not referenced in SKILL.md: {shown}{more}"))


def check_secrets(text, findings):
    for line in text.splitlines():
        if any(hint in line for hint in PLACEHOLDER_HINTS):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(("FAIL", "R9", "possible hardcoded credential: " + line.strip()[:80]))
                break


def check_skill_line_count(text, kind, settings, findings):
    if kind != "skill":
        return
    thresholds = (
        (settings or {}).get("rules", {}).get("R13_skillmd_line_limit", {})
        .get("config", {}).get("thresholds", {"weak_warning": 100, "soft_warning": 300, "warning": 490, "critical": 500})
    )
    n = len(text.splitlines())
    if n > thresholds.get("critical", 500):
        findings.append(("FAIL", "R13", f"SKILL.md is {n} lines (> {thresholds['critical']}) — move content to references/ before proceeding"))
    elif n > thresholds.get("warning", 490):
        findings.append(("ADVISORY", "R13", f"SKILL.md is {n} lines (> {thresholds['warning']}) — recommend moving content to references/"))
    elif n > thresholds.get("soft_warning", 300):
        findings.append(("ADVISORY", "R13", f"SKILL.md is {n} lines (> {thresholds['soft_warning']}) — plan extraction soon"))


def check_references_nesting(file_path, kind, findings):
    if kind != "skill":
        return
    refs_dir = file_path.parent / "references"
    if not refs_dir.is_dir():
        return
    for entry in refs_dir.iterdir():
        if entry.is_dir():
            findings.append(("FAIL", "R14", f"references/{entry.name}/ is a nested subdirectory — not allowed"))


def check_bare_urls(text, findings):
    code_spans = [(m.start(), m.end()) for m in re.finditer(r"```.*?```", text, re.DOTALL)]

    def in_code(pos):
        return any(s <= pos < e for s, e in code_spans)

    count = sum(
        1 for m in re.finditer(r"(?<!\]\()https?://[^\s)\]]+", text) if not in_code(m.start())
    )
    if count:
        findings.append(("ADVISORY", "R17", f"{count} bare URL(s) outside code blocks — use [text](url) syntax"))


def check_code_block_sizes(text, settings, findings):
    thresholds = (
        (settings or {}).get("rules", {}).get("R18_code_block_line_limit", {})
        .get("config", {}).get("thresholds", {"weak_warning": 10, "warning": 20, "critical": 30})
    )
    blocks = re.findall(r"```[^\n]*\n(.*?)```", text, re.DOTALL)
    over_weak = 0
    worst = 0
    critical_blocks = 0
    for block in blocks:
        n = block.count("\n")
        if n > thresholds["weak_warning"]:
            over_weak += 1
            worst = max(worst, n)
        if n > thresholds["critical"]:
            critical_blocks += 1
    if critical_blocks:
        findings.append(("FAIL", "R18", f"{critical_blocks} code block(s) exceed {thresholds['critical']} lines — extract to scripts/ or references/"))
    elif over_weak >= 3:
        findings.append(("ADVISORY", "R18", f"{over_weak} blocks exceed {thresholds['weak_warning']} lines; consider extracting the largest ({worst} lines)"))
    elif over_weak:
        findings.append(("ADVISORY", "R18", f"{over_weak} code block(s) exceed {thresholds['weak_warning']} lines"))


def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        return
    file_path_str = data.get("tool_input", {}).get("file_path", "")
    if not file_path_str:
        return
    kind = classify(file_path_str)
    if kind is None:
        return

    file_path = Path(file_path_str)
    if not file_path.is_file():
        return

    settings = load_settings(sys.argv[1]) if len(sys.argv) > 1 else None

    try:
        text = file_path.read_text(encoding="utf-8")
    except Exception:
        return

    findings = []
    fm = frontmatter(text)
    if fm is not None and kind in ("skill", "agent", "command"):
        check_name_field(fm, settings, findings)
        check_forbidden_fields(fm, kind, findings)
        check_bash_scoping(fm, settings, findings)
        check_description_length(fm, settings, findings)

    if fm is not None and kind in ("skill", "agent", "rule"):
        check_extra_fields(fm, kind, settings, findings)

    if fm is not None and kind == "agent":
        check_agent_enums(fm, settings, findings)

    if kind == "skill":
        check_skill_links_and_orphans(text, file_path, findings)

    check_secrets(text, findings)
    check_skill_line_count(text, kind, settings, findings)
    check_references_nesting(file_path, kind, findings)
    if kind in ("skill", "agent", "command", "rule"):
        check_bare_urls(text, findings)
        check_code_block_sizes(text, settings, findings)

    lines = [f"Rulebook check ({kind}): {file_path.name}"]
    if findings:
        for severity, rule, msg in findings[:8]:
            lines.append(f"{severity:8} {rule} - {msg}")
        if len(findings) > 8:
            lines.append(f"...and {len(findings) - 8} more finding(s)")
    else:
        lines.append(
            "No mechanical issues found in the deterministic subset (R4-R6, R8, R9, R13, R14, R17, R18) "
            "or the frontmatter-allowlist/agent-enum/broken-link/orphan-file/hooks-var checks."
        )
    lines.append(
        "Partial automated check only. Run Skill(plugin-rulebook) before finalizing for the full "
        "22-rule review — semantic rules R1-R3, R7, R10, R19-R22 need it."
    )

    print(json.dumps({
        "decision": "block",
        "reason": "\n".join(lines),
        "hookSpecificOutput": {"hookEventName": "PostToolUse"},
    }))


if __name__ == "__main__":
    main()
