"""Script verifiers behind the review gate (issue #576, #568 Phase 2).

A verifier decides a mechanical review rule from the PR's committed files, deterministically, so
the same head gives the same answer on every run. Its findings carry `source="script"`: the
computed gate (`review.gate_decision`) can block on them, and the exceptions registry can suppress
them, which it never does for a model finding.

This module is Tier 1 (review-dispatch-critical): `run-codex-review` imports it, so it imports only
Tier-1 modules and the standard library plus PyYAML. It reads the PR's files as data from the
checked-out commit's git objects (never the working tree, never following a symlink) and never
executes or imports anything from them. The frontmatter is composed into a YAML node tree and never
constructed into Python objects, so no tag, timestamp or alias in a PR file can run code or expand
in memory. Rule ids are stable strings listed in `docs/review-rule-inventory.md`; the registry
matches `Finding.rule` exactly.

A file a verifier cannot read is never reported clean: it becomes a blocking `-unverifiable`
finding, because otherwise a PR could keep a violation by making its file unreadable.

Verifiers so far: `r6-bash-scope` (the frontmatter half of the grant-to-body family), the
measurement family (`r13-skillmd-line-count`, `r21-description-length`,
`r18-code-block-line-count`), `r34-escaping-path` (the path family) and `r37-executable-bit`
(the structure family). A measurement is compared with the base, so only a PR that makes a value
worse across a blocking threshold is blocked.
"""

from __future__ import annotations

import bisect
import json
import posixpath
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from urllib.parse import unquote

import yaml

from scripts.marketplace_ci.git_state import ChangedPath
from scripts.marketplace_ci.review import Finding, _run_git

VERIFIER_REVIEWER = "script-verifiers"
GRANT_TO_BODY = "grant-to-body"
RULE_BASH_SCOPE = "r6-bash-scope"
RULE_UNVERIFIABLE = "frontmatter-unverifiable"
MEASUREMENT = "measurement"
RULE_SKILLMD_LINES = "r13-skillmd-line-count"
RULE_DESCRIPTION_LENGTH = "r21-description-length"
RULE_CODE_BLOCK_LINES = "r18-code-block-line-count"
RULE_ESCAPING_PATH = "r34-escaping-path"
PATH_AND_MIRROR = "path-and-mirror"
STRUCTURE = "structure"
RULE_EXECUTABLE_BIT = "r37-executable-bit"

# plugin-rulebook R6 `forbidden_bash_scopes` (assets/settings.json): the interpreters whose grant
# is equivalent to unrestricted Bash. A test keeps this equal to that setting (R20).
SHELL_INTERPRETERS = ("sh", "bash", "cmd", "powershell")

MAX_BLOB_BYTES = 1_000_000
MAX_FRONTMATTER_CHARS = 100_000
MAX_ENTRIES = 2_000
MAX_TOTAL_BYTES = 20_000_000

# plugin-rulebook R13 and R21 thresholds (assets/settings.json), kept equal by a test (R20). A value
# above `*_WARNING` is a Major finding and above `*_CRITICAL` a Critical one; the Weak and Soft
# Warning tiers are never reported. The combined description + when_to_use limit is not checked:
# it can only be exceeded together with one of the two individual limits.
R13_WARNING = 490
R13_CRITICAL = 500
DESCRIPTION_LOW_WARNING = 80  # shorter than this is a Major finding
DESCRIPTION_LOW_CRITICAL = 20  # shorter than this is a Critical one
DESCRIPTION_HIGH_WARNING = 1018
DESCRIPTION_HIGH_CRITICAL = 1024
WHEN_TO_USE_WARNING = 506
WHEN_TO_USE_CRITICAL = 512
R18_WARNING = 20
R18_CRITICAL = 30
MAX_FLOW_DEPTH = 100
MAX_CONTEXT_LINES = 200
_MAX_QUOTED_CHARS = 200
_REGULAR_FILE_MODES = (b"100644", b"100755")
_OBJECT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_MERGE_TAG = "tag:yaml.org,2002:merge"
_COMPONENT_PATH = re.compile(
    r"^(?:plugins/[^/]+|\.claude)/(?:(skills)/[^/]+/SKILL\.md|(commands)/.+\.md|(agents)/.+\.md)$",
    re.IGNORECASE,  # a case-insensitive install may still load `skill.md` or `x.MD`
)
_LINE_BREAKS_GIT_IGNORES = ("\r", "\x85", "\u2028", "\u2029")
_KIND_BY_GROUP = ("skill", "command", "agent")


class VerifierError(Exception):
    """A file a verifier cannot read as the component it looks like. The message is written by this
    module and never repeats text from the file."""


def component_kind(path: str) -> str | None:
    """`skill`, `command` or `agent` for a plugin or `.claude/` component file, else None."""
    match = _COMPONENT_PATH.match(path)
    if match is None:
        return None
    for kind, group in zip(_KIND_BY_GROUP, match.groups(), strict=True):
        if group:
            return kind
    return None


# --- frontmatter ------------------------------------------------------------------------------


def _frontmatter(text: str) -> tuple[yaml.MappingNode | None, list[str]]:
    """(root mapping node or None, frontmatter lines). `(None, [])` means the file has no
    frontmatter at all. Anything this check cannot read exactly raises VerifierError: an unusual
    fence, a line break git does not count (it would shift every reported line), a YAML alias or an
    explicit tag, a second document, a non-mapping or non-scalar key."""
    lines = text.removeprefix("\ufeff").replace("\r\n", "\n").split("\n")
    opening = lines[0].rstrip(" \t")
    if opening != "---":
        if opening.startswith("---"):
            raise VerifierError("the frontmatter fence is not exactly `---`")
        first = next((line for line in lines if line.strip()), "")
        if first.rstrip(" \t") == "---":
            raise VerifierError("the frontmatter fence is not on the first line")
        return None, []
    for end in range(1, len(lines)):
        if lines[end].rstrip(" \t") == "---":
            break
    else:
        raise VerifierError("the frontmatter block is not closed")
    block = lines[1:end]
    source = "\n".join(block)
    if len(source) > MAX_FRONTMATTER_CHARS:
        raise VerifierError(f"the frontmatter is larger than {MAX_FRONTMATTER_CHARS} characters")
    if any(char in source for char in _LINE_BREAKS_GIT_IGNORES):
        raise VerifierError("the frontmatter has a line break that git does not count")
    depth = deepest = 0
    for (
        char
    ) in source:  # cheap and crude, so a bracket bomb never reaches the slow pure-Python parser
        if char in "[{":
            depth += 1
            deepest = max(deepest, depth)
        elif char in "]}" and depth:
            depth -= 1
    if deepest > MAX_FLOW_DEPTH:
        raise VerifierError(f"the frontmatter nests flow collections deeper than {MAX_FLOW_DEPTH}")
    try:
        # Events first: an alias can reach a key or a value from elsewhere, and an explicit tag can
        # change how a consumer reads a value, so neither is accepted. Composing builds no Python
        # objects, so nothing expands.
        for event in yaml.parse(source):
            if isinstance(event, yaml.AliasEvent):
                raise VerifierError("the frontmatter uses a YAML alias")
            if (
                isinstance(
                    event, (yaml.ScalarEvent, yaml.SequenceStartEvent, yaml.MappingStartEvent)
                )
                and event.tag is not None
            ):
                raise VerifierError("the frontmatter uses an explicit YAML tag")
        root = yaml.compose(source)
    except (yaml.YAMLError, RecursionError) as exc:
        raise VerifierError(f"the frontmatter is not valid YAML ({type(exc).__name__})") from exc
    if root is None:
        return None, block
    if not isinstance(root, yaml.MappingNode):
        raise VerifierError("the frontmatter is not a mapping")
    if any(not isinstance(key, yaml.ScalarNode) for key, _ in root.value):
        raise VerifierError("the frontmatter has a key that is not a plain scalar")
    if any(key.tag == _MERGE_TAG for key, _ in root.value):
        raise VerifierError("the frontmatter uses a YAML merge key")
    return root, block


def _split_tokens(value: str) -> list[str]:
    """Split on whitespace and commas outside parentheses, so `Bash(git log --format=a,b:*)` stays
    one token. Raises VerifierError on an unbalanced parenthesis: where such a token ends depends on
    the consumer, so it cannot be judged."""
    tokens: list[str] = []
    current: list[str] = []
    depth = 0
    for char in value:
        if char == "(":
            depth += 1
        elif char == ")":
            if not depth:
                raise VerifierError("a tool entry has an unbalanced parenthesis")
            depth -= 1
        if depth == 0 and (char.isspace() or char == ","):
            if current:
                tokens.append("".join(current))
                current = []
            continue
        current.append(char)
    if depth:
        raise VerifierError("a tool entry has an unbalanced parenthesis")
    if current:
        tokens.append("".join(current))
    return tokens


def _line_of(node: yaml.Node) -> int | None:
    """The file line (1-based; the opening `---` is line 1) a single-line scalar sits on, or None
    for a multi-line one: the position of a token inside it cannot be pinned down exactly, and a
    wrong line would turn a real violation into a notice."""
    if node.start_mark is None or node.end_mark is None:
        raise VerifierError("a frontmatter node has no position")
    if node.start_mark.line != node.end_mark.line:
        return None
    return node.start_mark.line + 2


_KEY_LOOKALIKE = re.compile(r"""^["']?(allowed-tools|tools)["']?\s*:""")


def _grant_entries(
    root: yaml.MappingNode, block: list[str], key: str
) -> tuple[list[tuple[str, int | None]], int | None]:
    """((token, file line or None) for every entry of the `key` field, the key's own file line). An
    entry's line is the line it is written on, or None when that cannot be determined exactly; a
    finding without a line counts as changed whenever its file is. Editing only the key line or a
    fence can also activate an entry, so `check_bash_scope` cites those lines too."""
    fields = [(k, v) for k, v in root.value if k.value == key]
    if len(fields) > 1:
        raise VerifierError(f"the frontmatter repeats the `{key}` key")
    key_line = fields[0][0].start_mark.line if fields and fields[0][0].start_mark else None
    for index, line in enumerate(block):
        lookalike = _KEY_LOOKALIKE.match(line)
        if lookalike and lookalike.group(1) == key and index != key_line:
            raise VerifierError(f"a line looks like the `{key}` key but is not the key")
    if not fields:
        return [], None
    value_node = fields[0][1]
    entries: list[tuple[str, int | None]] = []

    def add(node: yaml.Node) -> None:
        if not isinstance(node, yaml.ScalarNode):
            raise VerifierError(f"`{key}` is not a string or a list of strings")
        if node.tag == "tag:yaml.org,2002:null":
            return
        line = _line_of(node)
        entries.extend((token, line) for token in _split_tokens(node.value))
        if len(entries) > MAX_ENTRIES:
            raise VerifierError(f"`{key}` has more than {MAX_ENTRIES} entries")

    if isinstance(value_node, yaml.SequenceNode):
        for item in value_node.value:
            add(item)
    else:
        add(value_node)
    return entries, None if key_line is None else key_line + 2


# --- r6-bash-scope ----------------------------------------------------------------------------

_BASH_TOKEN = re.compile(r"Bash(?:\((.*)\))?", re.DOTALL)


def _quote(token: str) -> str:
    """The token as inert, bounded text for a finding: no control characters or newlines, no
    backticks that could close the surrounding code span, at most `_MAX_QUOTED_CHARS` characters."""
    clean = "".join(" " if not c.isprintable() else c for c in token).replace("`", "'")
    if len(clean) > _MAX_QUOTED_CHARS:
        return clean[:_MAX_QUOTED_CHARS] + "..."
    return clean


def _canonical(name: str) -> str:
    return name.replace("'", "").replace('"', "").lower().removesuffix(".exe")


def _is_interpreter(word: str) -> bool:
    """Whether a command word names a shell interpreter however it is spelled: a path, a Windows
    path, a shell escape such as `b\\ash`, quoted fragments, a case variant or an `.exe` suffix. The
    word is read both as a Windows path (`\\` separates) and as a shell word (`\\` escapes)."""
    as_path = word.replace("\\", "/").rsplit("/", 1)[-1]
    as_shell = word.replace("\\", "").rsplit("/", 1)[-1]
    return any(_canonical(name) in SHELL_INTERPRETERS for name in (as_path, as_shell))


_SCRIPT_EXTENSIONS = (".sh", ".bash", ".ps1", ".cmd", ".bat")
_PLUGIN_VARIABLE = re.compile(r"\$\{(?:CLAUDE_PLUGIN_ROOT|CLAUDE_SKILL_DIR|CLAUDE_PROJECT_DIR)\}/")
_LITERAL_PATH = re.compile(r"[A-Za-z0-9_./-]+")
_SLASH_OPTION = re.compile(r"/[A-Za-z?][A-Za-z0-9:?]*")  # `cmd /c`, `cmd /k`
_UNSAFE_NAME_CHARS = "$`{}"  # shell expansion in a program name cannot be judged


def _pins_script(argument: str) -> bool:
    """Whether the first argument after an interpreter is one script path (so the grant permits
    that script only) and not an option, a device, an expansion or a pattern. A variable is accepted
    only as a leading `${CLAUDE_PLUGIN_ROOT}/`, `${CLAUDE_SKILL_DIR}/` or `${CLAUDE_PROJECT_DIR}/`;
    the rest is a literal path that ends in a script extension."""
    argument = argument.strip("'\"")
    if not argument or argument[0] in "-+" or _SLASH_OPTION.fullmatch(argument):
        return False
    variable = _PLUGIN_VARIABLE.match(argument)
    literal = argument[variable.end() :] if variable else argument
    if _LITERAL_PATH.fullmatch(literal) is None:
        return False
    normal = posixpath.normpath(re.sub(r"^/+", "/", literal))
    if normal.startswith(("/dev/", "/proc/", "/sys/")):
        return False
    return normal.lower().endswith(_SCRIPT_EXTENSIONS)


def _bash_grant_problem(token: str) -> str | None:
    """Why a skill or command `allowed-tools` entry is an unrestricted Bash grant, or None. Raises
    VerifierError for an entry that starts like a Bash grant but is not one this check can read."""
    match = _BASH_TOKEN.fullmatch(token)
    if match is None:
        if token.startswith("Bash("):
            raise VerifierError("a Bash entry is not well formed")
        return None
    inner = match.group(1)
    if inner is None:
        return "grants `Bash`, unrestricted Bash"
    command = inner.strip().removesuffix(":*").strip()
    if not command.strip("*? \t"):
        return f"grants `{_quote(token)}`, unrestricted Bash"
    words = command.split()
    first = words[0].rstrip(":")
    variable = _PLUGIN_VARIABLE.match(first)
    plain = first[variable.end() :] if variable else first  # `${CLAUDE_PLUGIN_ROOT}/scripts/x.sh`
    program = first.replace("\\", "/").rsplit("/", 1)[-1]
    if any(char in plain for char in _UNSAFE_NAME_CHARS):
        return f"grants `{_quote(token)}`, shell expansion in the program name"
    if any(char in program for char in "*?["):
        # A wildcard directory (`*/scan.sh`) still pins the script by name; one in the program name
        # itself (`bash*`, `*sh`) does not.
        return f"grants `{_quote(token)}`, a wildcard in the program name"
    if not _is_interpreter(first):
        return None
    if len(words) > 1 and _pins_script(words[1]):
        return None  # an interpreter that pins one script permits that script only
    return f"grants `{_quote(token)}`, a shell interpreter with no pinned script"


def check_bash_scope(path: str, text: str) -> tuple[Finding, ...]:
    """R6: a skill or command may not grant unrestricted Bash; an agent's `tools` has no Bash
    scoping syntax at all, so a scoped `Bash(...)` there is the violation. Raises VerifierError when
    the file's frontmatter cannot be read exactly."""
    if component_kind(path) is None:
        return ()
    return _bash_scope_findings(path, *_frontmatter(text))


def _bash_scope_findings(
    path: str, root: yaml.MappingNode | None, block: list[str]
) -> tuple[Finding, ...]:
    kind = component_kind(path)
    if kind is None or root is None:
        return ()
    key = "tools" if kind == "agent" else "allowed-tools"
    findings: list[Finding] = []
    entries, key_file_line = _grant_entries(root, block, key)
    closing_fence = len(block) + 2
    for token, line in entries:
        if kind == "agent":
            if not token.startswith("Bash("):
                continue
            evidence = (
                f"`tools` lists `{_quote(token)}`; an agent's `tools` field has no Bash scoping"
            )
            fix = "Replace the entry with bare `Bash`, the only form that grants Bash to an agent."
        else:
            problem = _bash_grant_problem(token)
            if problem is None:
                continue
            evidence = f"`{key}` {problem}"
            fix = (
                "Scope Bash to a named tool such as `Bash(git:*)`, or pin one script after the "
                "interpreter."
            )
        # An edit to the key line, a fence, or a line between them can activate an entry whose own
        # line is untouched, so those lines are cited: changing any of them makes the finding the
        # PR's. A context too long to cite gives the finding no line (changed whenever its file is).
        components: tuple[str, ...] = ()
        if line is not None:
            span = range(min(key_file_line or line, line), line + 1)
            if len(span) > MAX_CONTEXT_LINES:
                line = None
            else:
                cited = sorted({1, closing_fence, *span} - {line})
                components = tuple(f"{path}:{n}" for n in cited)
        findings.append(
            Finding(
                reviewer=VERIFIER_REVIEWER,
                severity="Critical",
                rule=RULE_BASH_SCOPE,
                path=path,
                evidence=evidence,
                remediation=fix,
                line=line,
                components=components,
                confidence="high",
                evidence_type="verifier_output",
                rule_class="line",
                source="script",
            )
        )
    return tuple(findings)


def unverifiable_finding(path: str, reason: str) -> Finding:
    """A blocking finding for a component file the verifier could not read exactly. Without it, a
    PR could keep a Bash grant by making the file unreadable (invalid frontmatter, a symlink, an
    oversized file)."""
    return Finding(
        reviewer=VERIFIER_REVIEWER,
        severity="Major",
        rule=RULE_UNVERIFIABLE,
        path=path,
        evidence=f"the Bash grants of this file could not be verified: {reason}",
        remediation=(
            "Make the frontmatter a plain YAML mapping this check can read (one `allowed-tools` or "
            "`tools` key, no merge key, balanced parentheses), or replace the symlink or oversized "
            "file with a regular one."
        ),
        line=None,
        confidence="high",
        evidence_type="verifier_output",
        rule_class="line",
        source="script",
    )


# --- measurements: R13 and R21 -----------------------------------------------------------------

_SEVERITY_BY_RANK = {1: "Major", 2: "Critical"}


def _above(value: int, warning: int, critical: int) -> int:
    return 2 if value > critical else 1 if value > warning else 0


_LINE_BREAK = re.compile(r"\r\n|\r|\n")


def count_lines(text: str) -> int:
    """Lines as `wc -l` and git count them, with a lone carriage return counted as a break too so a
    body cannot hide its length behind old-Mac line endings: line breaks, plus an unterminated last
    line."""
    breaks = len(_LINE_BREAK.findall(text))
    return breaks + (0 if not text or text.endswith(("\n", "\r")) else 1)


def line_tier(lines: int) -> int:
    """0 = fine, 1 = Warning (Major), 2 = Critical, for a SKILL.md of `lines` lines (R13)."""
    return _above(lines, R13_WARNING, R13_CRITICAL)


def description_low_tier(length: int) -> int:
    return 2 if length < DESCRIPTION_LOW_CRITICAL else 1 if length < DESCRIPTION_LOW_WARNING else 0


def description_high_tier(length: int) -> int:
    return _above(length, DESCRIPTION_HIGH_WARNING, DESCRIPTION_HIGH_CRITICAL)


def description_tier(length: int) -> int:
    return max(description_low_tier(length), description_high_tier(length))


def when_to_use_tier(length: int) -> int:
    return _above(length, WHEN_TO_USE_WARNING, WHEN_TO_USE_CRITICAL)


def _field_length(root: yaml.MappingNode | None, key: str) -> int | None:
    """The length of the folded string value of a frontmatter field, or None when it is absent."""
    if root is None:
        return None
    fields = [value for k, value in root.value if k.value == key]
    if len(fields) > 1:
        raise VerifierError(f"the frontmatter repeats the `{key}` key")
    if not fields:
        return None
    node = fields[0]
    if not isinstance(node, yaml.ScalarNode):
        raise VerifierError(f"`{key}` is not a string")
    return 0 if node.tag == "tag:yaml.org,2002:null" else len(node.value)


def description_length(text: str) -> int | None:
    """The length of a skill's folded `description`, None when it has none or cannot be read."""
    try:
        root, _ = _frontmatter(text)
        return _field_length(root, "description")
    except VerifierError:
        return None


_Parsed = tuple["yaml.MappingNode | None", list[str]]


def _skill_measures(
    text: str,
    parsed: _Parsed | None = None,
    *,
    parse_failed: bool = False,
    strict: bool = False,
) -> dict[str, int | None]:
    """{metric: value} for one SKILL.md. The line count never needs readable frontmatter. A missing
    `description` is length 0 (as bad as an empty one, so deleting it dodges nothing); `when_to_use`
    is optional. Frontmatter that cannot be parsed leaves the lengths None (the caller reports the
    file as unverifiable). With `strict`, a field this check cannot read (a repeated key, a
    non-string) raises VerifierError; the base side is not strict and never raises."""
    measures: dict[str, int | None] = {
        "lines": count_lines(text),
        "description_low": None,
        "description_high": None,
        "when_to_use": None,
    }
    if parse_failed:
        return measures
    if parsed is None:
        try:
            parsed = _frontmatter(text)
        except VerifierError:
            return measures
    try:
        description = _field_length(parsed[0], "description") or 0
        measures["description_low"] = measures["description_high"] = description
        measures["when_to_use"] = _field_length(parsed[0], "when_to_use")
    except VerifierError:
        if strict:
            raise
        measures["description_low"] = measures["description_high"] = None
    return measures


def _rank(metric: str, value: int | None) -> int:
    if value is None:
        return 0
    if metric == "lines":
        return line_tier(value)
    if metric == "description_low":
        return description_low_tier(value)
    if metric == "description_high":
        return description_high_tier(value)
    return when_to_use_tier(value)


_METRIC_RULES = {
    "lines": RULE_SKILLMD_LINES,
    "description_low": RULE_DESCRIPTION_LENGTH,
    "description_high": RULE_DESCRIPTION_LENGTH,
    "when_to_use": RULE_DESCRIPTION_LENGTH,
}
_METRIC_LABELS = {
    "lines": "SKILL.md",
    "description_low": "description",
    "description_high": "description",
    "when_to_use": "when_to_use",
}


def check_measurements(
    path: str,
    text: str,
    base_text: str | None,
    parsed: _Parsed | None = None,
    *,
    parse_failed: bool = False,
) -> tuple[Finding, ...]:
    """R13 and R21 for one SKILL.md: a finding for each metric whose tier is worse than in the base
    (`base_text` None means the file is new, so any blocking tier counts). A value that is no worse
    than the base is never reported, so a PR that only touches an already oversized file is not
    blocked by it."""
    if component_kind(path) != "skill":
        return ()
    head = _skill_measures(text, parsed, parse_failed=parse_failed, strict=True)
    base = _skill_measures(base_text) if base_text is not None else {}
    findings: list[Finding] = []
    for metric, value in head.items():
        rank = _rank(metric, value)
        if rank == 0 or value is None or rank <= _rank(metric, base.get(metric)):
            continue
        previous = base.get(metric)
        unit = "lines" if metric == "lines" else "characters"
        label = _METRIC_LABELS[metric]
        was = (
            "new file"
            if base_text is None
            else f"was {previous}"
            if previous is not None
            else "was unmeasured"
        )
        tier = _SEVERITY_BY_RANK[rank].lower()
        findings.append(
            Finding(
                reviewer=VERIFIER_REVIEWER,
                severity=_SEVERITY_BY_RANK[rank],
                rule=_METRIC_RULES[metric],
                path=path,
                evidence=f"{label} is {value} {unit} ({was}), past the {tier} threshold",
                remediation=(
                    "Move content out of SKILL.md into references/ or scripts/."
                    if metric == "lines"
                    else "Bring the field back inside its documented length."
                ),
                line=None,
                confidence="high",
                evidence_type="verifier_output",
                rule_class=MEASUREMENT,
                source="script",
            )
        )
    return tuple(findings)


# --- R18: fenced code block size -----------------------------------------------------------------

_R18_KINDS = ("skill", "command", "agent")
_MAX_LISTED_BLOCKS = 5  # blocks named in one finding's evidence
_BLOCK_LINE_BREAK = re.compile(r"\r\n|\r|\n")
_MAX_NESTING_PREFIX = 100  # container markers read before a fence; more is not a fence


@dataclass(frozen=True)
class FencedBlock:
    start: int  # 1-based line of the opening fence (counting lone CRs as breaks)
    end: int  # 1-based line of the closing fence (the last line when unclosed)
    size: int  # content lines between the fences
    closed: bool
    content: tuple[str, ...]


@dataclass(frozen=True)
class _Fence:
    depth: int  # blockquote markers before the fence
    column: int  # display column of the fence characters (tabs to multiples of 4)
    marker: bool  # a list marker came before the fence
    char: str
    length: int
    rest: str  # what follows the fence characters


def block_tier(lines: int) -> int:
    """0 = fine, 1 = Warning (Major), 2 = Critical, for a fenced block of `lines` lines (R18)."""
    return _above(lines, R18_WARNING, R18_CRITICAL)


def _scan_prefix(line: str) -> tuple[int, int]:
    """(index after the blockquote markers and spaces, blockquote depth) for a line. A plain
    left-to-right scan, never a backtracking pattern, so hostile whitespace cannot make it slow."""
    index, depth, size = 0, 0, len(line)
    while index < size and depth <= _MAX_NESTING_PREFIX:
        if line[index] == ">":
            depth += 1
            index += 1
            if index < size and line[index] in " \t":
                index += 1
        elif line[index] in " \t":
            index += 1
        else:
            break
    return index, depth


def _indent(line: str) -> int:
    """Display columns of the whitespace that starts the line."""
    stripped = line.lstrip(" \t")
    return len(line[: len(line) - len(stripped)].expandtabs(4))


def _fence(line: str) -> _Fence | None:
    """The fence a line starts, after blockquote markers and one list marker, or None."""
    index, depth = _scan_prefix(line)
    size = len(line)
    marker = False
    if index < size and line[index] in "-+*" and line[index + 1 : index + 2] in (" ", "\t"):
        marker, index = True, index + 1
    elif index < size and line[index].isdigit():
        end = index
        while end < size and line[end].isdigit() and end - index < 9:
            end += 1
        if end < size and line[end] in ".)" and line[end + 1 : end + 2] in (" ", "\t"):
            marker, index = True, end + 1
    while index < size and line[index] in " \t":
        index += 1
    if index >= size or line[index] not in "`~":
        return None
    char = line[index]
    run = index
    while run < size and line[run] == char:
        run += 1
    if run - index < 3:
        return None
    column = len(line[:index].expandtabs(4))
    return _Fence(depth, column, marker, char, run - index, line[run:])


def _is_closer(candidate: _Fence | None, opener: _Fence) -> bool:
    return (
        candidate is not None
        and not candidate.marker
        and candidate.depth == opener.depth
        and candidate.char == opener.char
        and candidate.length >= opener.length
        and not candidate.rest.strip()
        and candidate.column <= opener.column + 3  # four or more columns deeper is content
    )


def _container_ended(line: str, opener: _Fence) -> bool:
    """Whether `line` ends the blockquote or list item that holds the fence: a line with fewer
    blockquote markers, or (for a fence after a list marker) a non-blank line indented less than the
    item's content. The block then ends before it, unclosed, so what follows is read afresh."""
    if _scan_prefix(line)[1] < opener.depth:
        return True
    return opener.marker and bool(line.strip()) and _indent(line) < opener.column


def _parse_blocks(lines: list[str], *, indented_is_code: bool = False) -> list[FencedBlock]:
    blocks: list[FencedBlock] = []
    index = 0
    while index < len(lines):
        opener = _fence(lines[index])
        if (
            opener is None
            or (opener.char == "`" and "`" in opener.rest)
            or (indented_is_code and opener.depth == 0 and not opener.marker and opener.column >= 4)
        ):
            index += 1
            continue
        end: int | None = None
        stop = len(lines)  # first line that is no longer part of the block
        for i in range(index + 1, len(lines)):
            if _container_ended(lines[i], opener):
                stop = i
                break
            if _is_closer(_fence(lines[i]), opener):
                end = i
                break
        if end is None:
            content = tuple(lines[index + 1 : stop])
            last = stop - 1
            next_index = stop
        else:
            content = tuple(lines[index + 1 : end])
            last = end
            next_index = end + 1
        blocks.append(FencedBlock(index + 1, last + 1, len(content), end is not None, content))
        index = max(next_index, index + 1)
    return blocks


def fenced_blocks(text: str, *, indented_is_code: bool = False) -> list[FencedBlock]:
    """The fenced code blocks of a markdown file, as CommonMark reads them: a fence of three or more
    backticks or tildes (after blockquote markers and a list marker), closed at the same blockquote
    depth by a fence of the same character that is at least as long, with no other text and not
    indented four or more columns past the opener; so a longer fence holds shorter ones as content.
    A block ends, unclosed, where its blockquote or list item ends, or at the end of the file. A
    lone carriage return is a line break. With `indented_is_code`, an unindented-context line
    indented four or more columns is indented code, not a fence."""
    lines = _BLOCK_LINE_BREAK.split(text)
    if lines and lines[-1] == "":
        lines.pop()
    return _parse_blocks(lines, indented_is_code=indented_is_code)


def _counted_blocks(text: str) -> list[FencedBlock]:
    """The blocks R18 judges: Warning tier or worse. One reading of the file, not two: merging a
    lenient and a strict reading double-counted a region and could block a legitimate PR. R18 is a
    size heuristic, not a security boundary (blocks of 20 lines or fewer are never reported, so
    splitting a block always avoids it); what this reading cannot see is listed in docs/ci.md.
    The rulebook's in-file `R18 exception` note is deliberately not honored: a PR could type one
    above its own block and waive its own finding, so a waiver must be an entry in the Tier-1
    exceptions registry."""
    return [b for b in fenced_blocks(text) if block_tier(b.size) > 0]


def check_code_blocks(path: str, text: str, base_text: str | None) -> tuple[Finding, ...]:
    """R18 for one skill, command or agent file: at most one finding, with no line. A block counts
    when it is in the Warning tier or worse and is not an identical block already in the base; the
    file is reported when the PR raised the number of blocks at some tier or worse (so editing a
    block without crossing a threshold, or moving it, is not reported). A finding only exists when
    the PR made the file worse against the real base, so it is the PR's by construction and carries
    no line: a line would let an edit that leaves the fences alone (filling a block in the middle)
    fall outside the diff."""
    if component_kind(path) not in _R18_KINDS:
        return ()
    head = _counted_blocks(text)
    base = _counted_blocks(base_text) if base_text is not None else []
    head_at = [sum(block_tier(b.size) >= rank for b in head) for rank in (1, 2)]
    base_at = [sum(block_tier(b.size) >= rank for b in base) for rank in (1, 2)]
    unmatched: dict[tuple[str, ...], int] = {}
    for block in base:
        unmatched[block.content] = unmatched.get(block.content, 0) + 1
    new: list[FencedBlock] = []
    for block in head:
        if unmatched.get(block.content, 0) > 0:
            unmatched[block.content] -= 1
        else:
            new.append(block)
    reported = [b for b in new if head_at[block_tier(b.size) - 1] > base_at[block_tier(b.size) - 1]]
    if not reported:
        return ()
    rank = max(block_tier(b.size) for b in reported)
    listed = ", ".join(f"line {b.start} ({b.size} lines)" for b in reported[:_MAX_LISTED_BLOCKS])
    more = len(reported) - _MAX_LISTED_BLOCKS
    severity = _SEVERITY_BY_RANK[rank]
    return (
        Finding(
            reviewer=VERIFIER_REVIEWER,
            severity=severity,
            rule=RULE_CODE_BLOCK_LINES,
            path=path,
            evidence=(
                f"{len(reported)} fenced code block(s) past the threshold, the worst in the "
                f"{severity.lower()} tier: {listed}" + (f" and {more} more" if more > 0 else "")
            ),
            remediation=(
                "Move the block to scripts/ or references/, or add an exception for this rule "
                "and path to scripts/marketplace_ci/review_exceptions.yaml (a Tier-1 file); a "
                "note typed above the block does not waive this check."
            ),
            line=None,
            confidence="high",
            evidence_type="verifier_output",
            rule_class=MEASUREMENT,
            source="script",
        ),
    )


# --- R34: paths that leave the skill folder ---------------------------------------------------

_SKILL_DOC = re.compile(
    r"^plugins/([^/]+)/skills/([^/]+)/(?:SKILL\.md|references/[^/]+\.md)$", re.IGNORECASE
)
# Every quantifier below is bounded and possessive (no backtracking), and every pattern starts at a
# fixed anchor, so a hostile line cannot make a scan quadratic. Paths longer than the bound are not
# read as links, which no real path reaches.
_LINK_DEST = re.compile(
    r"\]\(\s{0,20}+(<[^>\n]{0,300}+>|[^)\s]{1,300}+)"
    r"(?:\s{1,20}+(?:\"[^\"\n]{0,300}+\"|'[^'\n]{0,300}+'|\([^)\n]{0,300}+\)))?+\s{0,20}+\)"
)
_REF_DEF = re.compile(r"^ {0,3}+\[[^\]\n]{1,300}+\]:\s{0,20}+(<[^>\n]{0,300}+>|\S{1,300}+)")
_HTML_ATTR = re.compile(r"\b(?:href|src)\s{0,5}+=\s{0,5}+[\"']?+([^\"'\s>]{1,300}+)")
_SKILL_DIR_PATH = re.compile(r"\$\{CLAUDE_SKILL_DIR\}/([A-Za-z0-9._~/%+@-]{0,300}+)")
_BACKTICK_RUN = re.compile(r"`+")
_SKILL_DIR_PREFIX = "${CLAUDE_SKILL_DIR}/"
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_MIRRORED_ROOT_FOLDERS = ("references", "assets")


class RepoTree:
    """The files (and so the folders) of a commit, for existence checks, kept as one sorted list so
    a tree of very deep paths costs no more memory than its file names."""

    def __init__(self, files: Iterable[str]) -> None:
        self._files = sorted(set(files))

    def exists(self, path: str) -> bool:
        index = bisect.bisect_left(self._files, path)
        if index < len(self._files) and self._files[index] == path:
            return True
        below = bisect.bisect_left(self._files, path + "/")
        return below < len(self._files) and self._files[below].startswith(path + "/")


def _strip_code_spans(line: str) -> str:
    """The line with inline code spans blanked out. A span opens at a run of backticks and closes at
    the next run of exactly the same length (CommonMark), found in one pass over the runs."""
    runs = [(m.start(), m.end()) for m in _BACKTICK_RUN.finditer(line)]
    if not runs:
        return line
    next_same: list[int | None] = [None] * len(runs)
    latest: dict[int, int] = {}
    for position in range(len(runs) - 1, -1, -1):
        length = runs[position][1] - runs[position][0]
        next_same[position] = latest.get(length)
        latest[length] = position
    pieces: list[str] = []
    cursor = 0
    position = 0
    while position < len(runs):
        closing = next_same[position]
        if closing is None:
            position += 1
            continue
        pieces.append(line[cursor : runs[position][0]])
        pieces.append(" ")
        cursor = runs[closing][1]
        position = closing + 1
    pieces.append(line[cursor:])
    return "".join(pieces)


def _obfuscated(written: str, *, from_skill_dir: bool, lands_inside: bool) -> bool:
    """A path that climbs only to come back: a `..` that follows a real segment
    (`references/../SKILL.md`, wherever it lands), or a `${CLAUDE_SKILL_DIR}` path that starts with
    `..` and still ends up inside the skill folder. Leading `..` segments are normal navigation."""
    segments = [part for part in written.split("/") if part not in ("", ".")]
    if from_skill_dir and lands_inside and segments[:1] == [".."]:
        return True
    return any(
        part == ".." and index > 0 and segments[index - 1] != ".."
        for index, part in enumerate(segments)
    )


def _resolve(
    path: str, target: str, skill_dir: str, tree: RepoTree
) -> tuple[str, str, bool] | None:
    """(resolved path, normalized target, written through ${CLAUDE_SKILL_DIR}) for a target that
    points at something that exists, else None: URLs, anchors, placeholders and dead links are not
    this rule's business. A target is read the way a person following it would: an angle-bracket
    destination is unwrapped, percent escapes and backslash separators are undone, the fragment and
    query are dropped, and a leading `/` is a repo-root path."""
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    target = unquote(target).replace("\\", "/")
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target or _SCHEME.match(target) or any(c in target for c in "<>*"):
        return None
    if "..." in target.split("/"):
        return None
    if target.startswith(_SKILL_DIR_PREFIX):
        rest = target[len(_SKILL_DIR_PREFIX) :]
        resolved = posixpath.normpath(f"{skill_dir}/{rest}")
        found = not resolved.startswith("..") and tree.exists(resolved)
        return (resolved, rest, True) if found else None
    if any(c in target for c in "{}$"):
        return None
    if target.startswith("/"):
        at_root = posixpath.normpath(target.lstrip("/"))
        found = not at_root.startswith("..") and tree.exists(at_root)
        return (at_root, target.lstrip("/"), False) if found else None
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
    if not resolved.startswith("..") and tree.exists(resolved):
        return resolved, target, False
    at_root = posixpath.normpath(target)  # a repo-root path such as `.github/x.md`
    if not at_root.startswith("..") and tree.exists(at_root):
        return at_root, target, False
    return None


def _unreadable_finding(path: str, reason: str, rule: str = RULE_ESCAPING_PATH) -> Finding:
    """A blocking finding for a skill document the path check could not read: otherwise a PR could
    keep an escaping link by making its file a symlink or oversized."""
    return Finding(
        reviewer=VERIFIER_REVIEWER,
        severity="Major",
        rule=rule,
        path=path,
        evidence=f"this file could not be checked: {reason}",
        remediation="Replace the symlink or oversized file with a regular file of normal size.",
        line=None,
        confidence="high",
        evidence_type="verifier_output",
        rule_class="graph",
        source="script",
    )


def check_escaping_paths(
    path: str, text: str, tree: RepoTree, scripts_mirrors: frozenset[str]
) -> tuple[Finding, ...]:
    """R34 (`r34-escaping-path`): a link or `${CLAUDE_SKILL_DIR}` path in a skill's SKILL.md or
    references/*.md that resolves outside the skill folder may land only in the plugin root's
    references/ or assets/, or scripts/ for a plugin in `scripts_mirrors` (the base's list).
    Anything else, and a path that climbs only to come back, is a Critical finding on the line that
    holds it. Links are read in their Markdown forms (inline with a title, `<...>`, reference
    definitions), HTML `href`/`src` and `${CLAUDE_SKILL_DIR}` paths. Dead links are deliberately not
    checked: on the real tree 10 of 11 were illustrative examples that only a human can tell from a
    real miss. Fenced blocks and inline code spans are skipped (a `${CLAUDE_SKILL_DIR}` path is read
    even in code, as the rulebook says)."""
    scope = _SKILL_DOC.match(path)
    if scope is None:
        return ()
    plugin_root = f"plugins/{scope.group(1)}"
    skill_dir = f"{plugin_root}/skills/{scope.group(2)}"
    folders = [f"{plugin_root}/{name}" for name in _MIRRORED_ROOT_FOLDERS]
    if scope.group(1) in scripts_mirrors:
        folders.append(f"{plugin_root}/scripts")
    fenced: set[int] = set()
    for block in fenced_blocks(text, indented_is_code=True):
        fenced.update(range(block.start, block.end + 1))
    unnumbered = re.search(r"\r(?!\n)", text) is not None  # lone CRs make line numbers unreliable
    findings: list[Finding] = []
    seen: set[tuple[int, str]] = set()
    for number, line in enumerate(_BLOCK_LINE_BREAK.split(text), 1):
        if number in fenced:
            continue
        prose = _strip_code_spans(line)
        targets = [m.group(1) for m in _LINK_DEST.finditer(prose)]
        targets += [m.group(1) for m in _HTML_ATTR.finditer(prose)]
        targets += [m.group(1) for m in _REF_DEF.finditer(line)]
        targets += [
            _SKILL_DIR_PREFIX + m.group(1).rstrip(".,;:!?") for m in _SKILL_DIR_PATH.finditer(line)
        ]
        for target in targets:
            found = _resolve(path, target, skill_dir, tree)
            if found is None or (number, found[0]) in seen:
                continue
            resolved, written, from_skill_dir = found
            inside = resolved == skill_dir or resolved.startswith(skill_dir + "/")
            allowed = any(resolved == f or resolved.startswith(f + "/") for f in folders)
            if _obfuscated(written, from_skill_dir=from_skill_dir, lands_inside=inside):
                why = "climbs only to come back (an obfuscated path)"
            elif not inside and not allowed:
                why = "leaves the skill folder for a place the .claude/ mirror does not carry"
            else:
                continue
            seen.add((number, resolved))
            findings.append(
                Finding(
                    reviewer=VERIFIER_REVIEWER,
                    severity="Critical",
                    rule=RULE_ESCAPING_PATH,
                    path=path,
                    evidence=f"`{_quote(target)}` resolves to {_quote(resolved)} and {why}",
                    remediation=(
                        "Point at the plugin-root references/, assets/ or scripts/ folder, or move "
                        "the shared file there; do not reach into docs/, a repo-root file or "
                        "another skill's folder."
                    ),
                    line=None if unnumbered else number,
                    confidence="high",
                    evidence_type="verifier_output",
                    rule_class="graph",
                    source="script",
                )
            )
    return tuple(findings)


def _scripts_mirrors(repo, ref: str) -> frozenset[str]:
    """The plugins whose scripts/ folder the `.claude/` mirror carries, read from `ref`'s copy of
    `.claude/marketplace-sync.json` (the base, so a PR cannot widen its own allowed folders). A
    missing or unreadable file allows none, which only produces more findings."""
    texts, _ = _read_blobs(repo, [".claude/marketplace-sync.json"], ref, missing_ok=True)
    try:
        names = json.loads(texts[".claude/marketplace-sync.json"])["scripts_mirrors"]
        return frozenset(n for n in names if isinstance(n, str))
    except (KeyError, TypeError, ValueError):
        return frozenset()


# --- R37: executable bit of directly-run scripts ------------------------------------------------

_GRANT_DOC = re.compile(
    r"^plugins/([^/]+)/(?:skills/([^/]+)/SKILL\.md|commands/.+\.md)$", re.IGNORECASE
)
_PLUGIN_ROOT_PREFIX = "${CLAUDE_PLUGIN_ROOT}/"


@dataclass(frozen=True)
class ScriptGrant:
    script: str  # repo path of the script a grant runs directly
    line: int | None  # file line of the grant, None when it cannot be pinned down


_RUN_WRAPPERS = ("env", "exec", "command", "time")  # run the next word directly all the same
_PLUGIN_ROOT_FORMS = ("${CLAUDE_PLUGIN_ROOT}/", "$CLAUDE_PLUGIN_ROOT/")
_SKILL_DIR_FORMS = ("${CLAUDE_SKILL_DIR}/", "$CLAUDE_SKILL_DIR/")


def script_grants(path: str, root: yaml.MappingNode | None, block: list[str]) -> list[ScriptGrant]:
    """The scripts a skill or command grants by path as the command itself
    (`Bash(${CLAUDE_PLUGIN_ROOT}/scripts/x.sh:*)`, `Bash(${CLAUDE_SKILL_DIR}/scripts/x.sh:*)`),
    quoted or unbraced, after an `env`/`exec`/`command`/`time` word. A script an interpreter runs
    (`Bash(bash ${...}/x.sh:*)`) is not listed: it needs no executable bit. A glob names no single
    script, and a path that climbs out of its plugin names nothing."""
    scope = _GRANT_DOC.match(path)
    if scope is None or root is None:
        return []
    plugin_root = f"plugins/{scope.group(1)}"
    skill_dir = f"{plugin_root}/skills/{scope.group(2)}" if scope.group(2) else None
    grants: list[ScriptGrant] = []
    for token, line in _grant_entries(root, block, "allowed-tools")[0]:
        match = _BASH_TOKEN.fullmatch(token)
        if match is None or match.group(1) is None:
            continue
        words = match.group(1).strip().removesuffix(":*").split()
        if words and words[0] in _RUN_WRAPPERS:
            words = words[1:]
        if not words:
            continue
        word = words[0].replace('"', "").replace("'", "")
        if word.startswith(_PLUGIN_ROOT_FORMS):
            folder, rest = plugin_root, word.split("/", 1)[1]
        elif skill_dir is not None and word.startswith(_SKILL_DIR_FORMS):
            folder, rest = skill_dir, word.split("/", 1)[1]
        else:
            continue
        if any(char in rest for char in "*?["):
            continue
        script = posixpath.normpath(f"{folder}/{rest}")
        if script.startswith(plugin_root + "/"):
            grants.append(ScriptGrant(script, line))
    return grants


_MODE_WORDS = {
    b"100644": "is committed with git mode 100644",
    b"120000": "is a symlink",
    b"160000": "is a submodule",
    b"040000": "is a directory",
}


def check_executable_bits(
    path: str, grants: Sequence[ScriptGrant], modes: dict[str, bytes]
) -> tuple[Finding, ...]:
    """R37 (`r37-executable-bit`): a script run directly by path must be committed as mode 100755.
    Anything else at that path is reported with the reason: mode 100644, a symlink or submodule
    (a shell follows the link, and the rulebook wants the real file), or no such file (the rulebook
    calls a missing file a FAIL too). Each grant line is reported, so a new grant of an already
    bad script is never hidden behind an old line. The script's own path is cited, so a PR that
    only drops the bit (a chmod with no content change) makes the finding its own even though the
    grant line is untouched."""
    findings: list[Finding] = []
    reported: set[tuple[str, int | None]] = set()
    for grant in grants:
        mode = modes.get(grant.script)
        if mode == b"100755" or (grant.script, grant.line) in reported:
            continue
        reported.add((grant.script, grant.line))
        why = (
            "does not exist at HEAD"
            if mode is None
            else _MODE_WORDS.get(mode, f"has git mode {mode.decode('ascii', 'replace')}")
        )
        findings.append(
            Finding(
                reviewer=VERIFIER_REVIEWER,
                severity="Critical",
                rule=RULE_EXECUTABLE_BIT,
                path=path,
                evidence=(
                    f"`{_quote(grant.script)}` is run directly by this file's allowed-tools grant "
                    f"but {why}"
                ),
                remediation=(
                    "Commit the script as a regular file with mode 100755 (`git update-index "
                    "--chmod=+x <path>`); a shell running a non-executable path fails with "
                    "`Permission denied`."
                ),
                line=grant.line,
                components=(grant.script,),
                confidence="high",
                evidence_type="verifier_output",
                rule_class="graph",
                source="script",
            )
        )
    return tuple(findings)


def _modes(repo, paths: Sequence[str]) -> dict[str, bytes]:
    """{path: git mode} for the paths present in HEAD's tree."""
    if not paths:
        return {}
    tree = _run_git(repo, "--literal-pathspecs", "ls-tree", "-z", "HEAD", "--", *paths)
    modes: dict[str, bytes] = {}
    for entry in tree.split(b"\0"):
        meta, _, raw_path = entry.partition(b"\t")
        fields = meta.split()
        if len(fields) == 3:
            modes[raw_path.decode("utf-8", errors="surrogateescape")] = fields[0]
    return modes


# --- running the verifiers over a change set --------------------------------------------------


@dataclass(frozen=True)
class VerifierOutcome:
    name: str
    findings: tuple[Finding, ...]
    checked: tuple[str, ...]  # the files read and judged; every other candidate has a finding


def _read_blobs(
    repo, paths: Sequence[str], ref: str = "HEAD", *, missing_ok: bool = False
) -> tuple[dict[str, str], dict[str, str]]:
    """({path: text}, {path: why it cannot be read}) for `paths` as committed at `ref`. Reads git
    objects, so a symlink is never followed and the working tree is ignored. A path that is not in
    the tree raises, unless `missing_ok` (a base that does not have the file yet): HEAD's own paths
    come from the same checkout, so a miss there is an infrastructure fault, not a file to skip."""
    if not paths:
        return {}, {}
    tree = _run_git(repo, "--literal-pathspecs", "ls-tree", "-z", ref, "--", *paths)
    entries: dict[str, tuple[bytes, str]] = {}
    for entry in tree.split(b"\0"):
        meta, _, raw_path = entry.partition(b"\t")
        fields = meta.split()
        if len(fields) == 3:
            entries[raw_path.decode("utf-8", errors="surrogateescape")] = (
                fields[0],
                fields[2].decode("ascii"),
            )
    problems: dict[str, str] = {}
    wanted: list[tuple[str, str]] = []
    for path in paths:
        if path not in entries:
            if missing_ok:
                continue
            raise RuntimeError(f"changed path is not in {ref}'s tree: {path!r}")
        mode, sha = entries[path]
        if mode == b"120000":
            problems[path] = "it is a symlink, which is not followed"
        elif mode not in _REGULAR_FILE_MODES:
            problems[path] = f"it has git mode {mode.decode('ascii', 'replace')}"
        else:
            wanted.append((path, sha))
    if not wanted:
        return {}, problems
    request = ("\n".join(sha for _, sha in wanted) + "\n").encode("ascii")
    sizes = _run_git(repo, "cat-file", "--batch-check", stdin=request).splitlines()
    if len(sizes) != len(wanted):
        raise RuntimeError("cat-file --batch-check answered a different number of objects")
    readable: list[tuple[str, str]] = []
    total = 0
    for (path, sha), line in zip(wanted, sizes, strict=True):
        parts = line.split()
        if len(parts) != 3 or parts[0] != sha.encode("ascii") or parts[1] != b"blob":
            raise RuntimeError(f"unexpected cat-file --batch-check answer for blob {sha}")
        size = int(parts[2])
        if size > MAX_BLOB_BYTES:
            problems[path] = f"it is larger than {MAX_BLOB_BYTES} bytes"
        elif total + size > MAX_TOTAL_BYTES:
            problems[path] = (
                f"the total size of the files read would exceed {MAX_TOTAL_BYTES} bytes"
            )
        else:
            total += size
            readable.append((path, sha))
    texts: dict[str, str] = {}
    if readable:
        request = ("\n".join(sha for _, sha in readable) + "\n").encode("ascii")
        output = _run_git(repo, "cat-file", "--batch", stdin=request)
        position = 0
        for path, sha in readable:
            newline = output.index(b"\n", position)
            header = output[position:newline].split()
            if len(header) != 3 or header[0] != sha.encode("ascii") or header[1] != b"blob":
                raise RuntimeError(f"unexpected cat-file --batch header for blob {sha}")
            size = int(header[2])
            # Stray bytes in a body must not make the file unreadable, so decode leniently.
            texts[path] = output[newline + 1 : newline + 1 + size].decode("utf-8", errors="replace")
            position = newline + 2 + size
    return texts, problems


def run_verifiers(
    repo, changed: Sequence[ChangedPath], base_sha: str | None = None
) -> tuple[VerifierOutcome, ...]:
    """Run every verifier over the files `changed` leaves at HEAD, comparing measurements with
    `base_sha` (None treats every file as new). Any unexpected failure raises, so the caller
    reports the run as `could_not_run` instead of clean."""
    if base_sha is not None and not _OBJECT_ID.fullmatch(base_sha):
        raise RuntimeError(f"base is not a full object id: {base_sha!r}")
    candidates = sorted(
        {c.new_path for c in changed if c.new_path is not None and component_kind(c.new_path)}
    )
    texts, problems = _read_blobs(repo, candidates)
    # A base counts only when the old path is itself a component of the right kind: a rename of a
    # large reference file into a SKILL.md must not lend its size to the new skill (R13 and R21
    # need a skill as the old path, R18 any skill, command or agent).
    old_of = {
        c.new_path: (c.old_path or c.new_path)
        for c in changed
        if c.new_path in candidates and c.status != "A"
    }
    base_texts: dict[str, str] = {}
    if base_sha is not None and old_of:
        old_paths = sorted({old for old in old_of.values() if component_kind(old) is not None})
        old_texts, _ = _read_blobs(repo, old_paths, base_sha, missing_ok=True)
        base_texts = {p: old_texts[old] for p, old in old_of.items() if old in old_texts}

    grant_findings: list[Finding] = []
    grant_checked: list[str] = []
    measure_findings: list[Finding] = []
    measure_checked: list[str] = []
    for path in candidates:
        is_skill = component_kind(path) == "skill"
        if path in problems:
            finding = unverifiable_finding(path, problems[path])
            grant_findings.append(finding)
            if is_skill:
                measure_findings.append(finding)  # identical, so the aggregate keeps one
            continue
        parsed = None
        try:
            parsed = _frontmatter(texts[path])
            grant_findings.extend(_bash_scope_findings(path, *parsed))
            grant_checked.append(path)
        except VerifierError as exc:
            grant_findings.append(unverifiable_finding(path, str(exc)))
            if is_skill:
                measure_findings.append(grant_findings[-1])  # the same; the aggregate keeps one
        base_text = base_texts.get(path) if base_sha is not None else None
        measure_findings.extend(check_code_blocks(path, texts[path], base_text))
        if not is_skill:
            measure_checked.append(path)
            continue
        if component_kind(old_of.get(path, path)) != "skill":
            base_text = None  # R13 and R21 compare only with an old skill
        try:
            measure_findings.extend(
                check_measurements(
                    path, texts[path], base_text, parsed, parse_failed=parsed is None
                )
            )
            if parsed is not None:  # a file whose lengths could not be read was not fully measured
                measure_checked.append(path)
        except VerifierError as exc:
            measure_findings.append(unverifiable_finding(path, str(exc)))
    path_findings: list[Finding] = []
    path_checked: list[str] = []
    doc_paths = sorted(
        {c.new_path for c in changed if c.new_path is not None and _SKILL_DOC.match(c.new_path)}
    )
    if doc_paths:
        doc_texts, doc_problems = _read_blobs(repo, doc_paths)
        tree = RepoTree(
            name.decode("utf-8", errors="surrogateescape")
            for name in _run_git(repo, "ls-tree", "-r", "-z", "--name-only", "HEAD").split(b"\0")
            if name
        )
        mirrors = _scripts_mirrors(repo, base_sha or "HEAD")
        for path in doc_paths:
            if path in doc_problems:
                path_findings.append(_unreadable_finding(path, doc_problems[path]))
                continue
            path_findings.extend(check_escaping_paths(path, doc_texts[path], tree, mirrors))
            path_checked.append(path)
    structure_findings: list[Finding] = []
    structure_checked: list[str] = []
    touched = sorted(
        {
            name.split("/")[1]
            for c in changed
            for name in (c.new_path, c.old_path)
            if name is not None and name.startswith("plugins/") and name.count("/") >= 2
        }
        - {".", ".."}
    )
    if touched:
        listing = _run_git(
            repo,
            "--literal-pathspecs",
            "ls-tree",
            "-r",
            "-z",
            "--name-only",
            "HEAD",
            "--",
            *[f"plugins/{plugin}/" for plugin in touched],
        )
        grant_docs = sorted(
            n
            for n in (raw.decode("utf-8", errors="surrogateescape") for raw in listing.split(b"\0"))
            if _GRANT_DOC.match(n)
        )
        doc_texts, doc_problems = _read_blobs(repo, grant_docs)
        found: dict[str, list[ScriptGrant]] = {}
        for doc in grant_docs:
            if doc in doc_problems:
                if "total size" in doc_problems[doc]:
                    # Skipping a doc past the budget would let a chmod through unseen: fail closed.
                    raise RuntimeError(
                        "the grant documents of the touched plugins exceed the read budget"
                    )
                structure_findings.append(
                    _unreadable_finding(doc, doc_problems[doc], RULE_EXECUTABLE_BIT)
                )
                continue
            try:
                found[doc] = script_grants(doc, *_frontmatter(doc_texts[doc]))
            except VerifierError:
                continue  # the grant verifier already reports an unreadable changed file
            structure_checked.append(doc)
        modes = _modes(repo, sorted({g.script for grants in found.values() for g in grants}))
        for doc, grants in found.items():
            structure_findings.extend(check_executable_bits(doc, grants, modes))
    return (
        VerifierOutcome(
            name=GRANT_TO_BODY, findings=tuple(grant_findings), checked=tuple(grant_checked)
        ),
        VerifierOutcome(
            name=MEASUREMENT, findings=tuple(measure_findings), checked=tuple(measure_checked)
        ),
        VerifierOutcome(
            name=PATH_AND_MIRROR, findings=tuple(path_findings), checked=tuple(path_checked)
        ),
        VerifierOutcome(
            name=STRUCTURE, findings=tuple(structure_findings), checked=tuple(structure_checked)
        ),
    )
