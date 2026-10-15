"""Shared utilities for skill-development scripts."""

import os
from pathlib import Path

# Variables a nested `claude -p` needs to start and authenticate. Everything else in the
# caller's environment (cloud keys, tokens for other services) is withheld, because the
# child reads the skill under test and that text is untrusted.
_CHILD_ENV_NAMES = frozenset(
    {
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "SHELL",
        "LANG",
        "TERM",
        "TMPDIR",
        "TEMP",
        "TMP",
        "SYSTEMROOT",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "COMSPEC",
        "PATHEXT",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "no_proxy",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "NODE_EXTRA_CA_CERTS",
    }
)
_CHILD_ENV_PREFIXES = ("LC_", "XDG_", "ANTHROPIC_", "CLAUDE_")


def child_env() -> dict[str, str]:
    """Return a minimal environment for a nested `claude -p`.

    Drops CLAUDECODE (the nesting guard, safe to bypass for a programmatic child) and any
    variable outside the allowlist above. A setup that authenticates through other
    variables (for example cloud-provider keys) must add them here deliberately.
    """
    return {
        k: v
        for k, v in os.environ.items()
        if k != "CLAUDECODE" and (k in _CHILD_ENV_NAMES or k.startswith(_CHILD_ENV_PREFIXES))
    }


def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:
    """Parse a SKILL.md file, returning (name, description, full_content)."""
    content = (skill_path / "SKILL.md").read_text(encoding="utf-8")
    lines = content.split("\n")

    if lines[0].strip() != "---":
        raise ValueError("SKILL.md missing frontmatter (no opening ---)")

    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        raise ValueError("SKILL.md missing frontmatter (no closing ---)")

    name = ""
    description = ""
    frontmatter_lines = lines[1:end_idx]
    i = 0
    while i < len(frontmatter_lines):
        line = frontmatter_lines[i]
        if line.startswith("name:"):
            name = line[len("name:") :].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            value = line[len("description:") :].strip()
            # Handle YAML multiline indicators (>, |, >-, |-)
            if value in (">", "|", ">-", "|-"):
                continuation_lines: list[str] = []
                i += 1
                while i < len(frontmatter_lines) and (
                    frontmatter_lines[i].startswith("  ") or frontmatter_lines[i].startswith("\t")
                ):
                    continuation_lines.append(frontmatter_lines[i].strip())
                    i += 1
                description = " ".join(continuation_lines)
                continue
            else:
                description = value.strip('"').strip("'")
        i += 1

    return name, description, content
