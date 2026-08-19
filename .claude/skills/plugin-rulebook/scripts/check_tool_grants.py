#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""Mechanical backing check for R6's "tool completeness" sub-rule: does every
shell command a SKILL.md/command file's body instructs running have a
matching `Bash(<prefix>:*)` grant in its `allowed-tools` frontmatter?

This exists because "scan the body for tool references" was, until now, a
purely narrative instruction in plugin-rulebook/SKILL.md -- and the exact
defect it's meant to catch (a new Bash command added to a skill body without
its matching grant, in the same edit) recurred four independent times in one
week (PR #54's `cd`, PR #51's `sleep`, PR #52's `grep`/`echo`, PR #61's
`git diff`) despite the rule already existing. A human re-reading a body by
eye keeps missing it; a mechanical scan won't.

Usage:
    python check_tool_grants.py --file <path-to-SKILL.md-or-command.md>

Known false-positive classes (read before treating every finding as real) --
validated live against 5 real skills in this repo (reviewing-evals, commit,
git-rebase-sync, merge-pr, starting-work): precision improved from ~1% to
roughly 95%+ during that validation, and every remaining residual finding
traces to one of these:
  - A documentation file that *teaches* the Bash-grant syntax by quoting
    example strings without the `Bash(...)` wrapper itself (plugin-rulebook/
    SKILL.md's own R6 section is the worst case for this).
  - A command quoted with *extra* arguments beyond what a longer, already-
    granted wrapped prefix covers (e.g. `ruff format --check` quoted in prose
    describing what CI runs, when this skill only ever invokes it via
    `uv run ruff format <path>`).
  - A word that is simultaneously a real Unix command name and ordinary
    English/domain vocabulary (`cat` used as a short regex example, `test`
    used as a conventional-commit type name).
  - A prose ellipsis/wildcard standing in for "any command like this"
    (`` `git rebase ...` ``, `` `git push --force*` ``) rather than a literal
    invocation.
  - A cross-reference to what a *different* skill does (starting-work's own
    prose mentions `git worktree remove`, which is git-cleanup's action, not
    starting-work's own).
  - A command quoted with human-readable placeholder notation (`gh api
    repos/{owner}/{repo}/labels/...`) that doesn't textually match the
    grant's own literal glob syntax for the same real invocation (`Bash(gh
    api repos/*/labels/:*)`) -- same underlying command, different spelling.
  - A negative reference phrased as "rather than adding a local `X` grant"
    (explaining a deliberate design choice not to use X) rather than
    "do not"/"never"/"don't" -- NEGATIVE_INSTRUCTION_RE doesn't recognize
    this phrasing (merge-pr's own SKILL.md is the real instance found).
This is a full-file scan, not a diff against what changed, so it re-surfaces
these on every run rather than only on new lines. Verify each finding against
the surrounding prose before fixing it -- this script finds candidates, it
doesn't replace reading the diff.
"""

import argparse
import re
import sys
from pathlib import Path

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
ALLOWED_TOOLS_LINE_RE = re.compile(r"^allowed-tools:[ \t]*(.*)$", re.MULTILINE)
ALLOWED_TOOLS_LIST_ITEM_RE = re.compile(r"^\s*-\s*(.+?)\s*$", re.MULTILINE)
BASH_GRANT_RE = re.compile(r"Bash\(([^)]*)\)")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")

# A finding-suppressing prefix this repo commonly uses to label a
# documentation *example* line -- covers both "what NOT to do" labels
# (Wrong/Bad/Forbidden/Violation(s)) and "what a correct invocation looks
# like" labels (Correct/Good/Example(s)); either way it's illustrative
# prose, not a real instruction this skill itself follows, so a command
# shown under any of these labels is suppressed rather than flagged. Cheap,
# not exhaustive -- see the module docstring's known-limitation note.
EXAMPLE_LINE_PREFIX_RE = re.compile(
    r"^\s*(?:[-*]\s+)?(?:\*\*)?(Wrong|Bad|Forbidden|Correct|Good|Violations?|Examples?)\b:?(?:\*\*)?",
    re.IGNORECASE,
)

# Bare grant-scope notation used to *discuss* a Bash(...) grant without the
# Bash(...) wrapper itself -- e.g. "the `gh repo:*` grant was narrowed to
# `gh repo view:*`". A real shell command never ends in a literal `:*`.
META_GRANT_SYNTAX_RE = re.compile(r":\*$")

# A whole-line (not prefix-anchored) phrase this repo commonly uses to name a
# command specifically to say it must NOT be run without confirmation/never
# be run at all -- e.g. "Do not run destructive commands (e.g., `git reset
# --hard`)" or "Never runs a destructive command like `git reset --hard`
# without explicit AskUserQuestion". Distinct from EXAMPLE_LINE_PREFIX_RE
# (which anchors to a line-starting label) since this idiom shows up
# mid-sentence.
NEGATIVE_INSTRUCTION_RE = re.compile(r"\b(do not|don't|never)\b", re.IGNORECASE)

# Executable names actually seen granted via Bash(<name> ...) somewhere in
# this repo (surveyed 2026-08-19 across every plugins/*/skills/*/SKILL.md and
# plugins/*/commands/*.md). This repo's own inline-code convention (single
# backticks) is used generically for *any* code-like token -- filenames,
# field names, status words, Python identifiers -- not just commands, so a
# permissive "looks like an identifier" filter produces overwhelming noise
# (measured: 100 findings on reviewing-evals/SKILL.md, ~99 of them spurious).
# Requiring an exact match against real prior grants is a deliberate,
# disclosed precision-over-recall tradeoff: a genuinely novel tool name this
# list hasn't seen yet is a false negative (same as before this script
# existed), which is a far safer failure mode than drowning every real
# finding in noise. Extend this list as new tools get granted repo-wide.
KNOWN_EXECUTABLES = {
    "git",
    "gh",
    "python",
    "python3",
    "node",
    "npm",
    "npx",
    "yarn",
    "pnpm",
    "bun",
    "uv",
    "pip",
    "cargo",
    "go",
    "bundle",
    "composer",
    "pytest",
    "ruff",
    "ty",
    "jq",
    "date",
    "sleep",
    "cd",
    "claude",
    "shellcheck",
    "export",
    "realpath",
    "umask",
    "printf",
    "wc",
    "head",
    "tail",
    "sort",
    "uniq",
    "tree",
    "mktemp",
    "test",
    "pwd",
    "bash",
    "sh",
    "powershell",
    "pwsh",
    "curl",
    "wget",
    "docker",
    "grep",
    "find",
    "ls",
    "cat",
    "echo",
    "mkdir",
    "rm",
    "cp",
    "mv",
    "chmod",
    "sed",
    "awk",
    "tar",
    "unzip",
    "ssh",
    "diff",
}


def extract_frontmatter_body(text):
    """Split a SKILL.md/command file into (frontmatter_text, body_text). If
    no frontmatter block is found, frontmatter_text is empty and body_text is
    the whole file -- callers still get a best-effort scan rather than an
    error."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return "", text
    return m.group(1), text[m.end() :]


def parse_allowed_tools_value(frontmatter_text):
    """Return the raw `allowed-tools` value as a single string, handling the
    three documented forms: space-separated on the same line, comma-separated
    on the same line, or a YAML list on following indented `- ` lines."""
    m = ALLOWED_TOOLS_LINE_RE.search(frontmatter_text)
    if not m:
        return ""
    same_line_value = m.group(1).strip()
    if same_line_value:
        return same_line_value
    # Same-line value empty -- look for a following YAML list block.
    rest = frontmatter_text[m.end() :]
    items = []
    for line in rest.splitlines():
        if not line.strip():
            continue
        item_m = ALLOWED_TOOLS_LIST_ITEM_RE.match(line)
        if item_m:
            items.append(item_m.group(1))
            continue
        break  # first non-list-item line ends the block
    return " ".join(items)


def _split_multi_scope(grant_content):
    """A single Bash(...) call can hold multiple space- or comma-separated
    scopes -- R6's own documented "multiple named tools, each explicit" form
    (`Bash(git:* mkdir:*)`, `Bash(npm:*, git:*)`). Split the raw content into
    one string per scope, while keeping a genuine multi-word prefix like
    `git diff:*` together as ONE scope: only the *last* word of a real
    multi-word prefix carries the `:*`/`*` suffix, whereas each sibling scope
    in a multi-grant call carries its own suffix individually -- accumulate
    tokens until one ends in that suffix, then close out that scope and start
    the next."""
    raw_tokens = [t for t in re.split(r"[,\s]+", grant_content.strip()) if t]
    scopes = []
    current = []
    for tok in raw_tokens:
        current.append(tok)
        if tok.endswith(":*") or tok.endswith("*"):
            scopes.append(" ".join(current))
            current = []
    if current:
        scopes.append(" ".join(current))
    return scopes or [grant_content.strip()]


def extract_bash_grant_prefixes(allowed_tools_value):
    """Return (prefixes, universal) -- `prefixes` is a set of granted Bash
    prefixes as lowercase token tuples (e.g. Bash(git diff:*) -> ("git",
    "diff")); `universal` is True if a `Bash(*)` or bare unscoped `Bash` grant
    was found, meaning every command is trivially "covered" (a separate,
    already-existing R6 sub-check flags that grant itself as overly broad --
    this script doesn't re-flag it)."""
    prefixes = set()
    universal = False
    for grant in BASH_GRANT_RE.findall(allowed_tools_value):
        for scope in _split_multi_scope(grant):
            if scope in ("", "*"):
                universal = True
                continue
            scope = scope[:-2] if scope.endswith(":*") else scope
            scope = scope.rstrip("*").strip()
            if not scope:
                universal = True
                continue
            prefixes.add(tuple(scope.lower().split()))
    # A malformed scoped attempt like `Bash (git:*)` (space before the
    # paren) doesn't match BASH_GRANT_RE at all, so it never reaches the
    # loop above -- but its bare "Bash" token would still be present in a
    # naive whitespace split, and treating that as a real unscoped grant
    # would silently report the whole file as universally covered instead
    # of surfacing the parse failure. Only trust a bare "Bash" token when
    # there's no "Bash(" (with optional space before the paren) anywhere in
    # the value at all -- a real, intentional unscoped grant never appears
    # alongside a scoped-looking attempt.
    if re.search(r"\bBash\s*\(", allowed_tools_value) is None:
        tokens = allowed_tools_value.replace(",", " ").split()
        if "Bash" in tokens:
            universal = True
    return prefixes, universal


def is_candidate_command_span(clause, span_text):
    """Is this inline-code span's first token an *exact-case* match for a
    known executable name (KNOWN_EXECUTABLES)? Exact-case, not
    case-insensitive: a real command reference in this repo's prose is
    always written in its actual lowercase invocation form (`git`, `ruff`,
    ...) -- matching case-insensitively would treat git's own `HEAD` ref or
    an all-caps status word as a command, since they happen to lowercase to
    a real executable name (`head`, `sh`-shaped words, etc.).

    This check also naturally excludes flags (`-x`), template placeholders
    (`{var}`), meta-syntax quoting the grant syntax itself (`Bash(git:*)`),
    bare shell-variable references (`$ARGUMENTS`), and path-based script
    invocations (`${CLAUDE_PLUGIN_ROOT}/...`) -- none of those tokenize to a
    bare lowercase word matching the list. `clause` (a `;`-delimited segment
    of the full line, not the whole line -- see check_file) flagged by
    EXAMPLE_LINE_PREFIX_RE (a documentation "Wrong:"/"Bad:"/"Correct:"/
    "Good:"/"Example(s):" labeled line), or a span matching
    META_GRANT_SYNTAX_RE (bare `tool:*` notation discussing a grant rather
    than invoking a command), is suppressed regardless of whether its first
    token matches. Scoping the negative-instruction check to the clause
    rather than the whole line means "Run `git diff` to inspect; do not
    modify files" no longer suppresses the unrelated `git diff` reference
    just because "do not" appears later in the same compound sentence."""
    text = span_text.strip()
    if not text:
        return False
    if EXAMPLE_LINE_PREFIX_RE.search(clause):
        return False
    if NEGATIVE_INSTRUCTION_RE.search(clause):
        return False
    if META_GRANT_SYNTAX_RE.search(text):
        return False
    first_token = text.split()[0] if text.split() else ""
    return first_token in KNOWN_EXECUTABLES


def _clause_containing(line, pos):
    """Return the `;`-delimited clause of `line` that character offset `pos`
    falls within, so a negative-instruction phrase ("do not"/"never") in one
    clause of a compound sentence doesn't suppress a command reference in a
    *different* clause of the same line."""
    start = 0
    for part in line.split(";"):
        end = start + len(part)
        if start <= pos <= end:
            return part
        start = end + 1  # +1 for the ";" separator this split() consumed
    return line


def is_covered(span_text, granted_prefixes):
    """A span is covered if either: it starts with a granted prefix, checked
    at the *string* level so a grant that intentionally ends mid-token (e.g.
    `Bash(git rebase origin/:*)`, ending at a trailing `/`) still covers a
    real invocation like `git rebase origin/{base_branch}` even though the
    token right after the `/` differs -- a token-only prefix check would
    require an exact token match and miss this; or its tokens appear as a
    contiguous subsequence anywhere within a broader granted prefix (the
    indirect case -- a bare `ruff format` mentioned in background/reference
    prose about what CI itself runs, when this skill always actually invokes
    it via a longer wrapped prefix like Bash(uv run ruff format:*)).

    The string-level startswith check requires a boundary right after the
    matched prefix -- either the span ends exactly there, the next character
    is whitespace, or the prefix's own last character is already
    non-alphanumeric (the intentional mid-token case above). Without this, a
    `Bash(sh:*)` grant would wrongly "cover" an unrelated `shellcheck ...`
    span just because the string "sh" is a literal prefix of "shellcheck"."""
    span_norm = " ".join(span_text.strip().lower().split())
    tokens = tuple(span_norm.split())
    n = len(tokens)
    for prefix in granted_prefixes:
        prefix_str = " ".join(prefix)
        if span_norm.startswith(prefix_str):
            at_boundary = (
                len(span_norm) == len(prefix_str)
                or span_norm[len(prefix_str)] == " "
                or not prefix_str[-1].isalnum()
            )
            if at_boundary:
                return True
        if n <= len(prefix):
            for start in range(len(prefix) - n + 1):
                if prefix[start : start + n] == tokens:
                    return True
    return False


def check_file(path):
    """Return a list of (line_number, span_text, granted_prefixes) findings
    for uncovered command spans; empty list means clean (or a universal Bash
    grant made every command trivially covered)."""
    text = path.read_text(encoding="utf-8")
    frontmatter_text, body_text = extract_frontmatter_body(text)
    allowed_tools_value = parse_allowed_tools_value(frontmatter_text)
    granted_prefixes, universal = extract_bash_grant_prefixes(allowed_tools_value)
    if universal:
        return [], granted_prefixes

    findings = []
    body_start_line = text[: len(text) - len(body_text)].count("\n") + 1
    for i, line in enumerate(body_text.splitlines()):
        line_number = body_start_line + i
        for m in INLINE_CODE_RE.finditer(line):
            span_text = m.group(1)
            clause = _clause_containing(line, m.start())
            if not is_candidate_command_span(clause, span_text):
                continue
            if not is_covered(span_text, granted_prefixes):
                findings.append((line_number, span_text.strip(), granted_prefixes))
    return findings, granted_prefixes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, type=Path)
    args = parser.parse_args()

    if not args.file.exists():
        print(f"FAIL (blocking): file not found: {args.file}", file=sys.stderr)
        return 2

    findings, granted_prefixes = check_file(args.file)
    granted_display = ", ".join(" ".join(p) for p in sorted(granted_prefixes)) or "(none)"

    if not findings:
        print("PASS (tool grants): every candidate command span is covered by allowed-tools")
        print(f"  Granted Bash prefixes: {granted_display}")
        return 0

    for line_number, span_text, _ in findings:
        print(
            f"{args.file}:{line_number}: MISSING GRANT -- command `{span_text}` has no "
            f"matching Bash(<prefix>:*) grant in allowed-tools (granted: {granted_display})"
        )
    print(
        f"\n{len(findings)} finding(s). Verify each against surrounding prose before fixing --"
        " a full-file scan can misclassify a documentation example as a real instruction."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
