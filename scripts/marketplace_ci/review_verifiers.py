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

First verifier: `r6-bash-scope`, the frontmatter half of the grant-to-body family.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Sequence
from dataclasses import dataclass

import yaml

from scripts.marketplace_ci.git_state import ChangedPath
from scripts.marketplace_ci.review import Finding, _run_git

VERIFIER_REVIEWER = "script-verifiers"
GRANT_TO_BODY = "grant-to-body"
RULE_BASH_SCOPE = "r6-bash-scope"
RULE_BASH_SCOPE_UNVERIFIABLE = "r6-bash-scope-unverifiable"

# plugin-rulebook R6 `forbidden_bash_scopes` (assets/settings.json): the interpreters whose grant
# is equivalent to unrestricted Bash. A test keeps this equal to that setting (R20).
SHELL_INTERPRETERS = ("sh", "bash", "cmd", "powershell")

MAX_BLOB_BYTES = 1_000_000
MAX_FRONTMATTER_CHARS = 100_000
MAX_ENTRIES = 2_000
MAX_TOTAL_BYTES = 20_000_000
MAX_FLOW_DEPTH = 100
MAX_CONTEXT_LINES = 200
_MAX_QUOTED_CHARS = 200
_REGULAR_FILE_MODES = (b"100644", b"100755")
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
    if any(k.tag == _MERGE_TAG for k, _ in root.value):
        raise VerifierError("the frontmatter uses a YAML merge key")
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
    kind = component_kind(path)
    if kind is None:
        return ()
    key = "tools" if kind == "agent" else "allowed-tools"
    root, block = _frontmatter(text)
    if root is None:
        return ()
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
        rule=RULE_BASH_SCOPE_UNVERIFIABLE,
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


# --- running the verifiers over a change set --------------------------------------------------


@dataclass(frozen=True)
class VerifierOutcome:
    name: str
    findings: tuple[Finding, ...]
    checked: tuple[str, ...]  # the files read and judged; every other candidate has a finding


def _read_blobs(repo, paths: Sequence[str]) -> tuple[dict[str, str], dict[str, str]]:
    """({path: text}, {path: why it cannot be read}) for `paths` as committed at HEAD. Reads git
    objects, so a symlink is never followed and the working tree is ignored. A path that is not in
    HEAD's tree raises: both come from the same checkout, so that is an infrastructure fault, not a
    file to skip."""
    if not paths:
        return {}, {}
    tree = _run_git(repo, "--literal-pathspecs", "ls-tree", "-z", "HEAD", "--", *paths)
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
            raise RuntimeError(f"changed path is not in HEAD's tree: {path!r}")
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


def run_verifiers(repo, changed: Sequence[ChangedPath]) -> tuple[VerifierOutcome, ...]:
    """Run every verifier over the files `changed` leaves at HEAD. Any unexpected failure raises,
    so the caller reports the run as `could_not_run` instead of clean."""
    candidates = sorted(
        {c.new_path for c in changed if c.new_path is not None and component_kind(c.new_path)}
    )
    texts, problems = _read_blobs(repo, candidates)
    findings: list[Finding] = []
    checked: list[str] = []
    for path in candidates:
        if path in problems:
            findings.append(unverifiable_finding(path, problems[path]))
            continue
        try:
            findings.extend(check_bash_scope(path, texts[path]))
        except VerifierError as exc:
            findings.append(unverifiable_finding(path, str(exc)))
            continue
        checked.append(path)
    return (VerifierOutcome(name=GRANT_TO_BODY, findings=tuple(findings), checked=tuple(checked)),)
