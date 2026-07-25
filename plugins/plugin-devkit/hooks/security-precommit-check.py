#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
# PreToolUse hook (matcher: Bash): deterministic, log-only subset of security-reviewer's
# checks against staged files, right before a `git commit` executes. This does NOT invoke
# security-reviewer live -- a PreToolUse hook script runs as a standalone process outside
# the conversation loop and cannot dispatch a subagent, the same relationship
# rulebook-check.py already has to the full plugin-rulebook skill. It implements only the
# two checks that reduce cleanly to static regex matching: unscoped Bash/shell-interpreter
# tool grants (mirrors plugin-rulebook R6) and hardcoded-credential patterns (mirrors R9)
# in staged plugin component files. security-reviewer's deeper checks (permission-risk vs.
# actual usage, prompt-injection surface, PII persistence patterns) require judgment this
# script cannot approximate -- those stay in plugin-lifecycle-downstream's Phase 1 dispatch.
#
# LOG-ONLY: this hook never blocks a commit. It only surfaces findings via systemMessage so
# real commits can be observed and the false-positive rate confirmed before a follow-up
# change flips it to a blocking (deny) decision on Critical findings.

import json
import re
import subprocess
import sys
from pathlib import Path

GIT_COMMIT_RE = re.compile(r"(^|[;&|]\s*)git\s+commit(\s|$)")

COMPONENT_PATTERNS = [
    re.compile(r"[/\\]skills[/\\][^/\\]+[/\\]SKILL\.md$"),
    re.compile(r"[/\\]agents[/\\][^/\\]+\.md$"),
    re.compile(r"[/\\]commands[/\\][^/\\]+\.md$"),
]

UNSCOPED_BASH_RE = re.compile(
    r"(?:allowed-tools|tools)\s*:.*?\b("
    r"Bash(?!\()"
    r"|Bash\(\*\)"
    r"|Bash\(\s*(sh|bash|cmd|powershell)\s*:"
    r")",
)

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r'(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*["\'][A-Za-z0-9/+_\-]{16,}["\']'),
]
PLACEHOLDER_HINTS = ("YOUR_", "EXAMPLE", "PLACEHOLDER", "<", "$")


def is_component_path(path_str):
    return any(p.search(path_str) for p in COMPONENT_PATTERNS)


def staged_files():
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return []
        return [line.strip() for line in out.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def scan_file(path_str):
    findings = []
    try:
        text = Path(path_str).read_text(encoding="utf-8")
    except Exception:
        return findings

    if UNSCOPED_BASH_RE.search(text):
        findings.append(f"{path_str}: unscoped Bash/shell-interpreter tool grant (mirrors R6)")

    for line_no, line in enumerate(text.splitlines(), start=1):
        if any(hint in line for hint in PLACEHOLDER_HINTS):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(f"{path_str}:{line_no}: possible hardcoded credential pattern (mirrors R9)")
                break

    return findings


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)

    command = (payload.get("tool_input") or {}).get("command", "")
    if not GIT_COMMIT_RE.search(command):
        sys.exit(0)

    files = [f for f in staged_files() if is_component_path(f)]
    if not files:
        sys.exit(0)

    all_findings = []
    for f in files:
        all_findings.extend(scan_file(f))

    if not all_findings:
        sys.exit(0)

    summary = "; ".join(all_findings[:5])
    if len(all_findings) > 5:
        summary += f"; +{len(all_findings) - 5} more"

    print(json.dumps({
        "systemMessage": f"security-precommit-check (log-only, does not block): {len(all_findings)} potential issue(s) in staged component files -- {summary}",
        "hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"},
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
