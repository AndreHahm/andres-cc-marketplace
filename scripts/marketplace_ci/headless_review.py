"""The test comparison of two headless routes for the Claude delta review
(`.github/workflows/test-headless-claude-review-ci.yml`).

The same reviewer prompt runs through two routes, so a real run shows how each is billed:

- `sdk`: the Claude Agent SDK (`claude-agent-sdk`), with Read/Grep/Glob only, no settings
  sources, no MCP servers, hooks off and reads confined to the PR checkout.
- `api`: the Messages API (`anthropic`), in a loop this module drives, with its own read-only
  Read/Grep/Glob tools confined to the PR checkout, and turn, token and cost caps.

Each pass writes the record shape `.github/workflows/claude-review-ci.yml`'s record step writes,
so `claude_review.parse_pass` reads both routes. The workflow posts nothing to the pull request:
`summarize` writes a comparison table to the job summary only.

Nothing an API error says is kept: a failed pass records only its HTTP status code.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess  # nosec B404  # one fixed inline program under sys.executable, no shell
import sys
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path

ROUTES = ("sdk", "api")
PASSES = ("general", "security")
MAX_TURNS = {"general": 50, "security": 25}
# R9 of docs/ci-claude-review-user-requirements.md: $1.00 per pass.
MAX_BUDGET_USD = 1.00
# The api route's own token cap per pass (input, cache and output tokens together).
MAX_TOTAL_TOKENS = 2_000_000
MAX_OUTPUT_TOKENS = 16_000

# USD per million tokens: input, output, 5-minute cache write, cache read (the claude-api
# reference, cached 2026-10-06). The api route refuses a model missing here: it cannot cap
# a cost it cannot compute.
PRICES: dict[str, tuple[float, float, float, float]] = {
    "claude-sonnet-5-5": (2.00, 10.00, 2.50, 0.20),
    "claude-opus-5-5": (4.00, 20.00, 5.00, 0.20),
}

# The schema claude-review-ci.yml gives claude-code-action; the sdk route uses it as is.
REVIEW_SCHEMA: dict = {
    "type": "object",
    "required": ["verdict", "findings"],
    "additionalProperties": False,
    "properties": {
        "verdict": {"type": "string", "enum": ["LGTM", "Changes Requested"]},
        "findings": {
            "type": "array",
            "maxItems": 30,
            "items": {
                "type": "object",
                "required": ["severity", "path", "line", "title", "body"],
                "additionalProperties": False,
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["Critical", "Major", "Minor", "Informational"],
                    },
                    "path": {"type": "string", "maxLength": 300, "pattern": "^[^`<>\\x00-\\x1f]+$"},
                    "line": {"type": "integer", "minimum": 1},
                    "title": {"type": "string", "maxLength": 200},
                    "body": {"type": "string", "maxLength": 2000},
                },
            },
        },
    },
}
_UNSUPPORTED = frozenset({"maxItems", "maxLength", "minimum", "pattern"})


def api_schema(schema: object = REVIEW_SCHEMA) -> object:
    """`schema` without the constraints the Messages API's structured outputs refuse
    (maxItems, maxLength, minimum, pattern); parse_pass checks the count and the line."""
    if isinstance(schema, dict):
        return {k: api_schema(v) for k, v in schema.items() if k not in _UNSUPPORTED}
    if isinstance(schema, list):
        return [api_schema(v) for v in schema]
    return schema


# The settings claude-review-ci.yml gives claude-code-action: hooks off, reads confined to the
# working directory (the PR checkout), no .git, /proc or /sys.
SDK_SETTINGS = {
    "disableAllHooks": True,
    "permissions": {
        "blockReadsOutsideWorkingDirectories": True,
        "deny": ["Read(//proc/**)", "Read(//sys/**)", "Read(.git/**)"],
    },
}
READ_ONLY_TOOLS = ["Read", "Grep", "Glob"]


# --- the api route's read-only file tools --------------------------------------------------

MAX_READ_LINES = 2000
MAX_LINE_CHARS = 2000
MAX_FILE_BYTES = 2_000_000
MAX_GLOB_RESULTS = 500
MAX_GREP_LINES = 300
MAX_GREP_FILES = 5000
MAX_TOOL_RESULT_CHARS = 100_000
# All tool results of one turn together. Every tool call still needs a result, so a call past
# the cap gets the short SKIPPED text: the rest is bounded by how many calls fit in one response.
MAX_TURN_RESULT_CHARS = 200_000
SKIPPED = "skipped: turn result cap"
# A model-chosen pattern can backtrack for hours on a short line; the search runs in a child
# process that is killed at this deadline.
GREP_TIMEOUT_SECONDS = 10.0

# The child: reads {pattern, files: [[rel, path]], max_chars, max_lines} as JSON on stdin and
# writes {lines, truncated}. It gets only paths the parent already confined to the checkout.
_GREP_WORKER = r"""
import json, re, sys
req = json.load(sys.stdin)
rx = re.compile(req["pattern"])
out = []
for rel, path in req["files"]:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        continue
    for n, line in enumerate(text.splitlines(), 1):
        line = line[: req["max_chars"]]
        if rx.search(line):
            out.append(f"{rel}:{n}:{line}")
            if len(out) >= req["max_lines"]:
                json.dump({"lines": out, "truncated": True}, sys.stdout)
                sys.exit(0)
json.dump({"lines": out, "truncated": False}, sys.stdout)
"""


class ToolError(ValueError):
    """A tool call the model can correct: returned to it as an error result."""


class CheckoutFiles:
    """Read-only access to one directory tree, the PR checkout. Every path is resolved,
    symlinks included, and refused unless it stays inside the root; anything under a `.git`
    directory is refused too (as claude-review-ci.yml's `Read(.git/**)` deny)."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve(strict=True)

    def _inside(self, path: Path) -> bool:
        try:
            rel = path.relative_to(self.root)
        except ValueError:
            return False
        return ".git" not in rel.parts

    def resolve(self, raw: str) -> Path:
        if not isinstance(raw, str) or not raw or "\x00" in raw:
            raise ToolError("path must be a non-empty string")
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        resolved = Path(os.path.realpath(candidate))
        if not self._inside(resolved):
            raise ToolError(f"{raw}: outside the checkout or under .git")
        return resolved

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def read(self, file_path: str, offset: int = 1, limit: int = MAX_READ_LINES) -> str:
        path = self.resolve(file_path)
        if not path.is_file():
            raise ToolError(f"{file_path}: not a file")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ToolError(f"{file_path}: larger than {MAX_FILE_BYTES} bytes")
        offset = max(1, int(offset))
        limit = max(1, min(int(limit), MAX_READ_LINES))
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        shown = lines[offset - 1 : offset - 1 + limit]
        out = [f"{n:>6}\t{line[:MAX_LINE_CHARS]}" for n, line in enumerate(shown, start=offset)]
        if offset - 1 + limit < len(lines):
            out.append(f"... {len(lines) - (offset - 1 + limit)} more lines")
        return "\n".join(out) or "(empty)"

    def _walk(self, base: Path) -> Iterator[Path]:
        """Regular files under `base`, never following a symlink out of the root."""
        for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
            dirnames[:] = sorted(d for d in dirnames if d != ".git")
            for name in sorted(filenames):
                path = Path(dirpath) / name
                real = Path(os.path.realpath(path))
                if self._inside(real) and real.is_file():
                    yield path

    def glob(self, pattern: str, path: str = ".") -> str:
        if not isinstance(pattern, str) or not pattern:
            raise ToolError("pattern must be a non-empty string")
        base = self.resolve(path)
        matches = []
        for file in self._walk(base):
            rel = file.relative_to(base).as_posix()
            if fnmatch.fnmatchcase(rel, pattern) or fnmatch.fnmatchcase(file.name, pattern):
                matches.append(self.rel(file))
                if len(matches) >= MAX_GLOB_RESULTS:
                    matches.append(f"... stopped at {MAX_GLOB_RESULTS} results")
                    break
        return "\n".join(matches) or "(no matches)"

    def grep(self, pattern: str, path: str = ".", glob: str = "") -> str:
        try:
            re.compile(pattern)
        except (re.error, TypeError) as exc:
            raise ToolError(f"invalid regular expression: {exc}") from exc
        base = self.resolve(path)
        candidates = [base] if base.is_file() else self._walk(base)
        files: list[list[str]] = []
        note = ""
        for count, file in enumerate(candidates):
            if count >= MAX_GREP_FILES:
                note = f"... stopped after {MAX_GREP_FILES} files"
                break
            if glob and not fnmatch.fnmatchcase(file.name, glob):
                continue
            if file.stat().st_size <= MAX_FILE_BYTES:
                files.append([self.rel(file), os.path.realpath(file)])
        request = {
            "pattern": pattern,
            "files": files,
            "max_chars": MAX_LINE_CHARS,
            "max_lines": MAX_GREP_LINES,
        }
        try:
            # An empty environment: the child never sees ANTHROPIC_API_KEY.
            done = subprocess.run(  # nosec B603  # sys.executable, fixed program, no shell
                [sys.executable, "-I", "-c", _GREP_WORKER],
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=GREP_TIMEOUT_SECONDS,
                env={},
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolError(
                f"search stopped after {GREP_TIMEOUT_SECONDS:g} s; use a simpler pattern"
            ) from exc
        if done.returncode != 0:
            raise ToolError("search failed")
        result = json.loads(done.stdout)
        out = list(result["lines"])
        if result["truncated"]:
            out.append(f"... stopped at {MAX_GREP_LINES} matching lines")
        elif note:
            out.append(note)
        return "\n".join(out) or "(no matches)"


API_TOOLS = [
    {
        "name": "Read",
        "description": "Read a text file in the checkout, with line numbers. Paths are relative "
        "to the checkout root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "offset": {"type": "integer", "description": "first line, 1-based"},
                "limit": {"type": "integer", "description": f"at most {MAX_READ_LINES} lines"},
            },
            "required": ["file_path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "Grep",
        "description": "Search file contents in the checkout with a Python regular expression; "
        "returns path:line:text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "description": "file or directory, default the root"},
                "glob": {"type": "string", "description": "file-name filter, e.g. *.py"},
            },
            "required": ["pattern"],
            "additionalProperties": False,
        },
    },
    {
        "name": "Glob",
        "description": "List files in the checkout whose relative path or name matches a glob "
        "pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "description": "directory, default the root"},
            },
            "required": ["pattern"],
            "additionalProperties": False,
        },
    },
]


def run_tool(files: CheckoutFiles, name: str, args: object) -> tuple[str, bool]:
    """A tool call's result text and whether it is an error. `args` is the model's input,
    unchecked until here."""
    try:
        if not isinstance(args, Mapping):
            raise ToolError("input must be an object")
        if name == "Read":
            text = files.read(
                args.get("file_path", ""), args.get("offset", 1), args.get("limit", MAX_READ_LINES)
            )
        elif name == "Grep":
            text = files.grep(args.get("pattern", ""), args.get("path", "."), args.get("glob", ""))
        elif name == "Glob":
            text = files.glob(args.get("pattern", ""), args.get("path", "."))
        else:
            raise ToolError(f"unknown tool {name!r}")
    except (ToolError, OSError, ValueError, TypeError, OverflowError, RecursionError) as exc:
        return str(exc)[:500], True
    return text[:MAX_TOOL_RESULT_CHARS], False


# --- the two routes ------------------------------------------------------------------------


def _usage_value(usage: object, key: str) -> int:
    value = usage.get(key) if isinstance(usage, Mapping) else getattr(usage, key, 0)
    return int(value or 0)


# Conservative: code and prose run about 3 to 4 characters per token, so 0.5 overestimates.
NEW_TEXT_TOKENS_PER_CHAR = 0.5
# The tool definitions, the schema and the per-turn tool-result framing.
PROMPT_OVERHEAD_TOKENS = 5_000


def request_bound_usd(model: str, input_tokens: float) -> float:
    """The most one request can cost: all input billed as a cache write, all output used."""
    _inp, out, write, _read = PRICES[model]
    return (input_tokens * write + MAX_OUTPUT_TOKENS * out) / 1_000_000


def cost_usd(model: str, usage: object) -> float:
    """One response's cost from its usage block, at PRICES."""
    inp, out, write, read = PRICES[model]
    return (
        _usage_value(usage, "input_tokens") * inp
        + _usage_value(usage, "output_tokens") * out
        + _usage_value(usage, "cache_creation_input_tokens") * write
        + _usage_value(usage, "cache_read_input_tokens") * read
    ) / 1_000_000


@dataclass
class PassResult:
    """What one pass returned, in claude-review-ci.yml's result shape, plus token totals."""

    subtype: str
    is_error: bool
    num_turns: int
    total_cost_usd: float | None
    api_error_status: int | None = None
    structured_output: str = ""
    usage: dict[str, int] = field(default_factory=dict)

    def result(self) -> dict:
        return {
            "subtype": self.subtype,
            "is_error": self.is_error,
            "num_turns": self.num_turns,
            "total_cost_usd": self.total_cost_usd,
            "api_error_status": self.api_error_status,
        }


USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def run_api_pass(
    create: Callable[..., object],
    files: CheckoutFiles,
    *,
    status_error: type[Exception],
    api_error: type[Exception],
    prompt: str,
    model: str,
    max_turns: int,
    max_budget_usd: float = MAX_BUDGET_USD,
    max_total_tokens: int = MAX_TOTAL_TOKENS,
) -> PassResult:
    """The api route: `create` is `anthropic.Anthropic().messages.create`, `status_error` and
    `api_error` are `anthropic.APIStatusError` and `anthropic.APIError` (fakes in tests). A turn
    is one Messages request. The pass stops at the first response without a tool call, or when
    a cap is reached; an API error stops it with only its HTTP status kept."""
    if model not in PRICES:
        raise ValueError(f"no price for {model!r}: the api route cannot cap its cost")
    messages: list[dict] = [{"role": "user", "content": prompt}]
    totals = dict.fromkeys(USAGE_KEYS, 0)
    spent = 0.0
    turns = 0
    # The next request's input in tokens, estimated before it is sent: exact for what the last
    # request carried, NEW_TEXT_TOKENS_PER_CHAR for text added since, plus the tool definitions.
    next_input = PROMPT_OVERHEAD_TOKENS + len(prompt) * NEW_TEXT_TOKENS_PER_CHAR

    def done(subtype: str, output: str = "", status: int | None = None) -> PassResult:
        return PassResult(
            subtype=subtype,
            is_error=subtype != "success",
            num_turns=turns,
            total_cost_usd=round(spent, 6),
            api_error_status=status,
            structured_output=output,
            usage=totals,
        )

    while True:
        # The budget holds before a request, not only after: the worst case is the whole input
        # written to the cache uncached and the full output, priced before it can be spent.
        if spent + request_bound_usd(model, next_input) > max_budget_usd:
            return done("error_max_budget_usd")
        try:
            response = create(
                model=model,
                max_tokens=MAX_OUTPUT_TOKENS,
                tools=API_TOOLS,
                output_config={"format": {"type": "json_schema", "schema": api_schema()}},
                # Each turn re-sends the conversation; caching reads the earlier prefix back.
                cache_control={"type": "ephemeral"},
                messages=messages,
            )
        except status_error as exc:
            return done("error_during_execution", status=getattr(exc, "status_code", None))
        except api_error:
            return done("error_during_execution")
        turns += 1
        usage = getattr(response, "usage", None)
        for key in USAGE_KEYS:
            totals[key] += _usage_value(usage, key)
        spent += cost_usd(model, usage)
        stop = getattr(response, "stop_reason", None)
        content = list(getattr(response, "content", []) or [])
        if stop != "tool_use":
            if stop != "end_turn":
                return done("error_during_execution")
            text = "".join(b.text for b in content if getattr(b, "type", "") == "text")
            return done("success", text)
        if spent >= max_budget_usd:
            return done("error_max_budget_usd")
        if sum(totals.values()) >= max_total_tokens:
            return done("error_max_budget_usd")
        if turns >= max_turns:
            return done("error_max_turns")
        results = []
        turn_chars = 0
        for block in content:
            if getattr(block, "type", "") != "tool_use":
                continue
            if turn_chars >= MAX_TURN_RESULT_CHARS:
                text, is_error = SKIPPED, True
            else:
                text, is_error = run_tool(files, block.name, block.input)
                text = text[: MAX_TURN_RESULT_CHARS - turn_chars]
            turn_chars += len(text)
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": text,
                    "is_error": is_error,
                }
            )
        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": results})
        carried = sum(_usage_value(usage, k) for k in USAGE_KEYS)
        added = turn_chars * NEW_TEXT_TOKENS_PER_CHAR
        next_input = carried + added + PROMPT_OVERHEAD_TOKENS


async def run_sdk_pass(
    query: Callable, options_type: Callable, result_type: type, *, prompt: str, model: str,
    max_turns: int, checkout: Path,
) -> PassResult:  # fmt: skip
    """The sdk route: `query`, `options_type` and `result_type` are claude_agent_sdk's `query`,
    `ClaudeAgentOptions` and `ResultMessage` (fakes in tests)."""
    options = options_type(
        model=model,
        tools=list(READ_ONLY_TOOLS),
        allowed_tools=list(READ_ONLY_TOOLS),
        disallowed_tools=["mcp__*"],
        mcp_servers={},
        strict_mcp_config=True,
        setting_sources=[],
        settings=json.dumps(SDK_SETTINGS),
        max_turns=max_turns,
        max_budget_usd=MAX_BUDGET_USD,
        output_format={"type": "json_schema", "schema": REVIEW_SCHEMA},
        cwd=str(checkout),
        # Nothing an API error says is kept: Claude Code's stderr would go to the job log.
        stderr=lambda _line: None,
        # Anything not pre-approved is denied, never prompted for.
        permission_mode="dontAsk",
    )
    final = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, result_type):
            final = message
    if final is None:
        return PassResult("error_during_execution", True, 0, None)
    output = final.structured_output
    usage = final.usage if isinstance(final.usage, Mapping) else {}
    return PassResult(
        subtype=final.subtype,
        is_error=bool(final.is_error),
        num_turns=int(final.num_turns or 0),
        total_cost_usd=final.total_cost_usd,
        api_error_status=final.api_error_status,
        structured_output="" if output is None else json.dumps(output),
        usage={k: _usage_value(usage, k) for k in USAGE_KEYS},
    )


def pass_record(
    route: str, review_pass: str, outcome: str, result: PassResult | None, api_key: str,
    started_at: str, finished_at: str,
) -> dict:  # fmt: skip
    """The record claude-review-ci.yml's record step writes, plus the route, the token totals
    and when the pass ran. Output that holds the API key is dropped, as there."""
    from scripts.marketplace_ci.claude_review import _redact_secrets

    structured = result.structured_output if result else ""
    leak = bool(api_key) and api_key in structured
    # Anything else shaped like a credential is redacted before the artifact has it.
    structured = _redact_secrets(structured)
    return {
        "route": route,
        "pass": review_pass,
        "outcome": outcome,
        "result": result.result() if result else None,
        "secret_found": leak,
        "structured_output": "" if leak else structured,
        "usage": result.usage if result else {},
        "started_at": started_at,
        "finished_at": finished_at,
    }


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def run_pass(route: str, review_pass: str, *, prompt: str, model: str, checkout: Path) -> dict:
    """Run one pass of one route with the real SDKs and return its record. The API key comes
    from ANTHROPIC_API_KEY, which both SDKs read themselves."""
    if route not in ROUTES or review_pass not in PASSES:
        raise ValueError(f"unknown route or pass: {route} {review_pass}")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    started = utc_now()
    try:
        if route == "api":
            import anthropic

            client = anthropic.Anthropic(max_retries=2)
            result = run_api_pass(
                client.messages.create,
                CheckoutFiles(checkout),
                status_error=anthropic.APIStatusError,
                api_error=anthropic.APIError,
                prompt=prompt,
                model=model,
                max_turns=MAX_TURNS[review_pass],
            )
        else:
            import anyio
            from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

            result = anyio.run(
                lambda: run_sdk_pass(
                    query, ClaudeAgentOptions, ResultMessage, prompt=prompt, model=model,
                    max_turns=MAX_TURNS[review_pass], checkout=checkout,
                )
            )  # fmt: skip
        outcome = "success"
    except Exception as exc:  # noqa: BLE001  # the record keeps only the exception's type
        print(f"::warning::the {route} {review_pass} pass failed: {type(exc).__name__}")
        result, outcome = None, "failure"
    return pass_record(route, review_pass, outcome, result, api_key, started, utc_now())


# --- the comparison ------------------------------------------------------------------------


def _cell(text: object) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def summarize(raws: Mapping[str, Mapping], reviewed: frozenset[str], model: str) -> str:
    """The job-summary table: per route and pass, the status, verdict, findings by severity,
    turns, reported cost, tokens and when it ran. `raws` maps a route to its collected record
    file ({skipped, passes}); a missing route did not run."""
    from scripts.marketplace_ci.claude_review import SEVERITIES, InvalidReview, parse_pass

    lines = [
        "## Headless Claude review comparison",
        "",
        f"Model `{_cell(model)}`. Nothing is posted to the pull request. Match the times below "
        "against the Anthropic Console's usage and credit pages to see which credit pool paid.",
        "",
        "| Route | Pass | Status | Verdict | Findings | Turns | Cost (USD) "
        "| Tokens in/out/cache w/r | Ran (UTC) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for route in ROUTES:
        raw = raws.get(route)
        if raw is None:
            lines.append(f"| {route} | - | did not run | | | | | | |")
            continue
        if raw.get("skipped"):
            lines.append(f"| {route} | - | skipped ({_cell(raw['skipped'])}) | | | | | | |")
        for record in raw.get("passes", []):
            result = record.get("result") if isinstance(record.get("result"), Mapping) else {}
            try:
                verdict, findings = parse_pass(record, reviewed)
                status = "ok"
                counts = ", ".join(
                    f"{sum(f['severity'] == s for f in findings)} {s}" for s in SEVERITIES
                )
            except InvalidReview as exc:
                verdict, counts, status = "", "", f"invalid: {exc}"
            cost = result.get("total_cost_usd")
            ran = f"{_cell(record.get('started_at', ''))} to {_cell(record.get('finished_at', ''))}"
            usage = record.get("usage") or {}
            tokens = "/".join(str(usage.get(k, 0)) for k in USAGE_KEYS)
            lines.append(
                f"| {route} | {_cell(record.get('pass'))} | {_cell(status)} | {_cell(verdict)} "
                f"| {counts} | {_cell(result.get('num_turns', ''))} "
                f"| {'' if cost is None else f'{cost:.4f}'} | {tokens} "
                f"| {ran} |"
            )
    return "\n".join(lines) + "\n"
