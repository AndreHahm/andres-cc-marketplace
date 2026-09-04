#!/bin/bash
# Test whether an agent should trigger for a set of phrases.

set -euo pipefail

TIMEOUT_SECONDS=30
POSITIONAL=()

while [ $# -gt 0 ]; do
  case "$1" in
    --timeout)
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

if [ "${#POSITIONAL[@]}" -lt 1 ]; then
  echo "Usage: $0 <agent.md> [test-phrases-file] [--timeout N]"
  echo ""
  echo "Phrase file format:"
  echo "  + phrase text   -> should trigger"
  echo "  - phrase text   -> should NOT trigger"
  echo "  plain text      -> defaults to should trigger"
  exit 1
fi

AGENT_FILE="${POSITIONAL[0]}"
PHRASES_FILE="${POSITIONAL[1]:-}"

if [ ! -f "$AGENT_FILE" ]; then
  echo "ERROR: Agent file not found: $AGENT_FILE"
  exit 1
fi

if [ -z "$PHRASES_FILE" ]; then
  PHRASES_FILE="$(mktemp)"
  python3 - "$AGENT_FILE" > "$PHRASES_FILE" <<'PY'
from pathlib import Path
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

path = Path(sys.argv[1])
content = path.read_text(encoding="utf-8")
lines = content.splitlines()
end_idx = next((idx for idx, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)

def parse_frontmatter(text):
    data = {}
    current_key = None
    current_lines = []

    def flush_current():
        nonlocal current_key, current_lines
        if current_key is not None:
            data[current_key] = "\n".join(current_lines).strip()
        current_key = None
        current_lines = []

    for raw_line in text.splitlines():
        if not raw_line.strip():
            if current_key is not None:
                current_lines.append("")
            continue
        if raw_line.startswith((" ", "\t")) and current_key is not None:
            current_lines.append(raw_line.strip())
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw_line)
        if not match:
            continue
        flush_current()
        current_key = match.group(1)
        value = match.group(2).strip()
        if value.rstrip("+-") in {"|", ">"}:
            current_lines = []
        else:
            current_lines = [value.strip("\"'")] if value else []
    flush_current()
    return data

frontmatter = parse_frontmatter("\n".join(lines[1:end_idx])) if end_idx is not None else {}
body = "\n".join(lines[end_idx + 1:]) if end_idx is not None else "\n".join(lines)

# Current convention (see agent-development/references/delegation.md): trigger
# phrases live in the body's "## When to invoke" section as 2-4 prose bullets,
# not as `user: "..."` transcript shapes in the description (that convention
# is deprecated and no compliant agent description matches it anymore). Also
# accept "## When to Use" since some agents in this plugin use that heading.
section_match = re.search(
    r"^##\s*When to (?:invoke|Use)\s*$(.*?)(?=^##\s|\Z)", body, re.MULTILINE | re.DOTALL
)
if section_match:
    for raw_line in section_match.group(1).splitlines():
        stripped = raw_line.strip().lstrip("-*").strip()
        if stripped:
            print(f"+ {stripped}")
else:
    # Many agents (e.g. the *-reviewer family) have no dedicated body section
    # at all -- their trigger phrases are instead quoted inline in the
    # frontmatter description ("Use when the user asks to '...', '...'").
    # Extract those. Guard against apostrophes used as contractions (e.g.
    # "what's", "doesn't") rather than as quote delimiters, since a naive
    # split on every "'" mis-pairs phrases containing one. Also scope the
    # scan to the quoted-list clause right after "asks" rather than the
    # whole description -- an unrelated later sentence can contain its own
    # stray apostrophe (e.g. a plural possessive like "components'") that
    # would otherwise mis-pair with a real phrase's quote.
    description = frontmatter.get("description", "")
    flat = re.sub(r"\s+", " ", description)
    placeholder = "\x00APOS\x00"
    protected = re.sub(r"'(s|t|re|ll|ve|d|m)\b", placeholder + r"\1", flat)
    clause_match = re.search(r"asks[^']*?((?:'[^']*?'(?:,\s*|\s+or\s+)?)+)", protected)
    clause = clause_match.group(1) if clause_match else ""
    for phrase in re.findall(r"'([^']{3,80})'", clause):
        print(f"+ {phrase.replace(placeholder, chr(39)).strip()}")
PY
  if [ ! -s "$PHRASES_FILE" ]; then
    echo "ERROR: Could not infer test phrases from description; provide a phrases file."
    exit 1
  fi
fi

if [ ! -f "$PHRASES_FILE" ]; then
  echo "ERROR: Phrases file not found: $PHRASES_FILE"
  exit 1
fi

TMPDIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

python3 - "$AGENT_FILE" "$PHRASES_FILE" "$TIMEOUT_SECONDS" <<'PY'
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


RETRYABLE_PATTERNS = (
    "rate limit",
    "rate_limit",
    "too many requests",
    "not logged in",
    "please run /login",
    "authentication_failed",
)


class LLMProviderError(RuntimeError):
    """Raised when no usable LLM runner is available or invocation fails."""


class LLMResult:
    def __init__(self, text: str, provider: str) -> None:
        self.text = text
        self.provider = provider


def parse_frontmatter(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    def flush_current() -> None:
        nonlocal current_key, current_lines
        if current_key is not None:
            data[current_key] = "\n".join(current_lines).strip()
        current_key = None
        current_lines = []

    for raw_line in text.splitlines():
        if not raw_line.strip():
            if current_key is not None:
                current_lines.append("")
            continue

        if raw_line.startswith((" ", "\t")) and current_key is not None:
            current_lines.append(raw_line.strip())
            continue

        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw_line)
        if not match:
            continue

        flush_current()
        current_key = match.group(1)
        value = match.group(2).strip()
        if value.rstrip("+-") in {"|", ">"}:
            current_lines = []
        else:
            current_lines = [value.strip("\"'")] if value else []

    flush_current()
    return data


def parse_agent_md(agent_file: Path) -> dict[str, object]:
    text = agent_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    frontmatter: dict[str, str] = {}
    body = text.strip()

    if lines and lines[0].strip() == "---":
        end_idx = next((idx for idx, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
        if end_idx is not None:
            frontmatter = parse_frontmatter("\n".join(lines[1:end_idx]))
            body = "\n".join(lines[end_idx + 1 :]).strip()

    return {"frontmatter": frontmatter, "system_prompt": body}


def run_with_fallback(prompt: str, *, system_prompt: str, timeout: int, **_kwargs) -> LLMResult:
    command_text = os.environ.get("AGENT_TRIGGER_LLM_COMMAND") or os.environ.get("LLM_RUNNER_COMMAND")
    if command_text:
        command = shlex.split(command_text)
        provider = "env-command"
    elif shutil.which("claude"):
        command = ["claude", "-p"]
        provider = "claude"
    else:
        raise LLMProviderError(
            "No LLM command is available. Install claude or set AGENT_TRIGGER_LLM_COMMAND."
        )

    full_prompt = f"{system_prompt.rstrip()}\n\n{prompt}"
    if provider == "claude":
        command = [*command, full_prompt]
        stdin_text = None
    else:
        stdin_text = full_prompt

    try:
        completed = subprocess.run(
            command,
            input=stdin_text,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise LLMProviderError(f"LLM command timed out after {timeout}s") from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise LLMProviderError(f"LLM command exited with status {completed.returncode}: {stderr}")

    return LLMResult((completed.stdout or "").strip(), provider)


def parse_phrase_line(line: str) -> tuple[bool, str] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("+ "):
        return True, line[2:].strip()
    if line.startswith("- "):
        return False, line[2:].strip()
    return True, line


def requires_fallback(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in RETRYABLE_PATTERNS)


def run_claude_native(agent_file: Path, agent_name: str, phrase: str, timeout_seconds: int) -> bool | None:
    if shutil.which("claude") is None:
        return None

    temp_dir = Path(tempfile.mkdtemp(prefix="agent-trigger-"))
    try:
        agent_dir = temp_dir / ".claude" / "agents"
        agent_dir.mkdir(parents=True, exist_ok=True)
        target = agent_dir / agent_file.name
        target.write_text(agent_file.read_text(encoding="utf-8"), encoding="utf-8")

        cmd = [
            "claude",
            "-p",
            phrase,
            "--output-format",
            "stream-json",
            "--include-partial-messages",
            "--verbose",
            "--append-system-prompt",
            "Do not invoke unrelated skills. Only delegate when the local project agent clearly matches the request.",
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=temp_dir,
                timeout=timeout_seconds,
                env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"},
            )
        except subprocess.TimeoutExpired:
            return None
        output = "\n".join(part for part in (result.stdout, result.stderr) if part)
        if requires_fallback(output):
            return None
        normalized = output.lower()
        return agent_name.lower() in normalized or target.name.lower() in normalized
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_semantic_fallback(agent_name: str, description: str, phrase: str, timeout_seconds: int) -> tuple[bool, str]:
    system_prompt = (
        "You are a routing evaluator. Decide whether the provided agent should "
        "trigger for the provided user request. Return JSON only with keys "
        '"triggered" (boolean) and "reason" (string).'
    )
    prompt = f"""
Agent name: {agent_name}

Agent description:
{description}

User request:
{phrase}

Trigger the agent only if the request is clearly within scope.
""".strip()
    result = run_with_fallback(
        prompt,
        system_prompt=system_prompt,
        timeout=max(timeout_seconds, 60),
        providers=("codex", "gemini", "qwen"),
        cwd=Path.cwd(),
    )
    match = re.search(r"\{.*\}", result.text, re.DOTALL)
    payload = json.loads(match.group(0) if match else result.text)
    return bool(payload.get("triggered", False)), result.provider


agent_path = Path(sys.argv[1]).resolve()
phrases_path = Path(sys.argv[2]).resolve()
timeout_seconds = int(sys.argv[3])

parsed = parse_agent_md(agent_path)
frontmatter = parsed["frontmatter"]
agent_name = str(frontmatter.get("name", agent_path.stem))
description = str(frontmatter.get("description", ""))

total = 0
passed = 0

for raw_line in phrases_path.read_text(encoding="utf-8").splitlines():
    parsed_line = parse_phrase_line(raw_line)
    if parsed_line is None:
        continue
    expected, phrase = parsed_line
    total += 1

    native_result = run_claude_native(agent_path, agent_name, phrase, timeout_seconds)
    if native_result is None:
        actual, provider = run_semantic_fallback(agent_name, description, phrase, timeout_seconds)
        mode = f"fallback:{provider}"
    else:
        actual = native_result
        mode = "claude-native"

    ok = actual == expected
    if ok:
        passed += 1
    status = "PASS" if ok else "FAIL"
    expectation = "should trigger" if expected else "should not trigger"
    actual_text = "triggered" if actual else "not triggered"
    print(f"[{status}] {mode} | {expectation} | {actual_text} | {phrase}")

print("")
print(f"Summary: {passed}/{total} passed")
sys.exit(0 if passed == total else 1)
PY
