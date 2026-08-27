#!/usr/bin/env python3
"""Mechanical portion of Checks 1-2 from reviewing-evals/SKILL.md.

Usage:
    python scripts/check_evals.py [--smoke-test PATH] [--skill-md PATH]
        [--evals-json PATH] [--regex-timeout SECONDS]

Any argument may be omitted; the check it feeds is skipped (matching the
skill's own "skip any check whose target artifact doesn't exist" rule) rather
than treated as a failure. This script only covers the parts of Checks 1-2
that are mechanical (regex extraction/arithmetic) -- the semantic judgment
calls (e.g. "does this eval prompt actually exercise this scenario") stay
agent-performed, per SKILL.md.
"""

import argparse
import ast
import io
import json
import re
import subprocess
import sys
import tokenize
from pathlib import Path

# (?:[^\\]|\\.)*? -- escape-aware lazy match: a backslash-escaped delimiter
# (e.g. \" inside a "..."-quoted literal) doesn't terminate the capture the
# way a bare (.*?) would, which stops at the first literal occurrence of the
# quote character even when it's escaped and semantically part of the string.
# The leading (r?) is now its own capture group -- needed to tell a raw
# literal (source spelling == runtime value) from a non-raw one (source
# spelling needs Python's own escape decoding, e.g. "\\s" -> \s) apart.
FINDALL_RE = re.compile(r"re\.findall\(\s*(r?)([\"'])((?:[^\\]|\\.)*?)\2")
SEARCH_RE = re.compile(r"re\.search\(\s*(r?)([\"'])((?:[^\\]|\\.)*?)\2")
CALL_RE = re.compile(r"re\.(findall|search)\(")

DEFAULT_REGEX_TIMEOUT_SECONDS = 2.0

# re module flag names this checker knows how to forward. Anything else found
# in a call's trailing arguments is reported for manual review instead of
# silently evaluated with different semantics than the original call.
SUPPORTED_FLAGS = {"MULTILINE", "DOTALL", "IGNORECASE", "VERBOSE", "ASCII", "UNICODE"}
FLAG_RE = re.compile(r"\bre\.([A-Z]+)\b")

# Runs re.findall in a throwaway subprocess so a pathological target-authored
# pattern (catastrophic backtracking) can't hang this checker itself.
_CHILD_SCRIPT = (
    "import json, re, sys\n"
    "data = json.loads(sys.stdin.read())\n"
    "flags = 0\n"
    "for name in data.get('flags', []):\n"
    "    flags |= getattr(re, name)\n"
    "try:\n"
    "    hits = re.findall(data['pattern'], data['text'], flags)\n"
    "    print(json.dumps({'ok': True, 'count': len(hits)}))\n"
    "except re.error as e:\n"
    "    print(json.dumps({'ok': False, 'error': str(e)}))\n"
)


def _line_number(source: str, pos: int) -> int:
    return source.count("\n", 0, pos) + 1


def _noncode_spans(source: str) -> list[tuple[int, int]]:
    """Absolute character-offset (start, end) spans of every COMMENT and
    STRING token in source, via tokenize -- positions that are commentary
    or string-literal content, not live executable code. A re.findall/
    re.search occurrence whose own call text ("re.findall(" / "re.search(",
    not its string argument) starts inside one of these spans is example
    text inside a comment or docstring, not a real call the target script
    executes -- e.g. a commented-out `# re.search(r"cat", skill_md_text)`
    or a docstring showing `re.findall(r"...", skill_md_text)` as example
    usage."""
    line_starts = [0]
    for line in source.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line))

    def offset(row: int, col: int) -> int:
        return line_starts[row - 1] + col

    spans = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                spans.append((offset(*tok.start), offset(*tok.end)))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Malformed/unparseable source -- fall back to no exclusions rather
        # than silently hiding every call in a file this checker can't
        # tokenize.
        return []
    return spans


def _in_noncode(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= pos < end for start, end in spans)


def _decode_literal(prefix: str, quote: str, raw_text: str) -> tuple[bool, str]:
    """Reconstruct the original Python string-literal token (prefix + quotes
    + captured text) and decode it via ast.literal_eval, so a non-raw
    literal's escape sequences (\\s, \\n, \\\\, etc.) resolve to their real
    runtime value rather than the source spelling -- "^target\\s*$" (a plain
    string) means \\s (whitespace) at runtime, not the two-character
    backslash-s sequence its source text shows. A raw literal's value equals
    its source spelling either way, so this is a no-op for those. Returns
    (ok, decoded_or_raw_text); ok=False means the token couldn't be decoded
    faithfully (caller should not evaluate it with confidence)."""
    token = f"{prefix}{quote}{raw_text}{quote}"
    try:
        value = ast.literal_eval(token)
    except (SyntaxError, ValueError):
        return False, raw_text
    if not isinstance(value, str):
        return False, raw_text
    return True, value


def _is_complete_literal_arg(source: str, end_pos: int) -> bool:
    """True if the captured literal ending at end_pos is the *complete*
    first argument to the call -- i.e. immediately followed by a comma or
    the call's closing paren. False means the literal is only part of a
    concatenated/constructed pattern (e.g. `r"\\b" + re.escape(needle) +
    r"\\b"`), so the captured text alone doesn't reflect the real pattern."""
    i = end_pos
    while i < len(source) and source[i] in " \t\n":
        i += 1
    return i < len(source) and source[i] in (",", ")")


def _scan_to_close_paren(source: str, start: int) -> int:
    """From just inside an already-open paren (depth 1), scan to its matching
    close-paren -- balancing nested parens (e.g. `wf.read_text(encoding="utf-8")`)
    -- and return that close-paren's index. String-literal-aware: a paren
    inside a quoted string argument (e.g. `comment="see docs (section 2"`)
    doesn't count toward paren depth, since it isn't a real call-structure
    paren. Returns `len(source)` if the paren never closes (malformed/
    truncated input) rather than raising."""
    depth = 1
    i = start
    in_string = None
    while i < len(source) and depth > 0:
        c = source[i]
        if in_string:
            if c == "\\" and i + 1 < len(source):
                i += 2
                continue
            if c == in_string:
                in_string = None
            i += 1
            continue
        if c in ("'", '"'):
            in_string = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                break
        i += 1
    return i


def _extract_call_arg_text(source: str, arg_start: int) -> str:
    """From just after a matched pattern's closing quote, scan to the
    matching close-paren of the enclosing re.findall(...)/re.search(...) call
    and return the remaining argument text."""
    end = _scan_to_close_paren(source, arg_start)
    return source[arg_start:end].lstrip(", \t\n")


def _split_top_level_alternation(pattern: str) -> list[str]:
    """Split a regex pattern on top-level '|' -- e.g. "cat|dog" -> ["cat",
    "dog"], but "(cat|dog)" -> ["(cat|dog)"] (the | is inside a group, so
    it's one branch, not two) and "a\\|b" -> ["a\\|b"] (escaped, literal).
    Character classes (`[...]`) are tracked too, since `|` inside one is a
    literal pipe character, not alternation."""
    branches = []
    depth = 0
    in_class = False
    current = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\" and i + 1 < len(pattern):
            current.append(pattern[i : i + 2])
            i += 2
            continue
        if in_class:
            if c == "]":
                in_class = False
            current.append(c)
        elif c == "[":
            in_class = True
            current.append(c)
        elif c == "(":
            depth += 1
            current.append(c)
        elif c == ")":
            depth = max(0, depth - 1)
            current.append(c)
        elif c == "|" and depth == 0:
            branches.append("".join(current))
            current = []
        else:
            current.append(c)
        i += 1
    branches.append("".join(current))
    return branches


def _extract_group_contents(text: str) -> list[str]:
    """Return the inner text of every parenthesized group found in text
    (paren/bracket/escape-aware, including nested groups), so a branch can
    be checked for alternation hidden inside a group without re-deriving
    paren tracking."""
    groups = []
    starts = []
    in_class = False
    i = 0
    while i < len(text):
        c = text[i]
        if c == "\\" and i + 1 < len(text):
            i += 2
            continue
        if in_class:
            if c == "]":
                in_class = False
            i += 1
            continue
        if c == "[":
            in_class = True
        elif c == "(":
            starts.append(i + 1)
        elif c == ")" and starts:
            start = starts.pop()
            groups.append(text[start:i])
        i += 1
    return groups


def _trailing_backslash_count(text: str, end: int) -> int:
    """Count consecutive backslash characters in text immediately before
    index `end` (exclusive)."""
    count = 0
    i = end - 1
    while i >= 0 and text[i] == "\\":
        count += 1
        i -= 1
    return count


def _is_real_end_anchor(text: str) -> bool:
    """True if text ends with a genuine right-anchor -- an unescaped '$'
    or an unescaped '\\b' -- rather than an escaped literal character that
    merely happens to look like one. "cat\\$" ends with the *literal*
    character '$' (an odd number of backslashes escapes it), matched
    anywhere in the haystack, not a real end-of-string anchor -- it still
    matches "cat$egory", the exact false-anchored case this guards
    against."""
    if text.endswith("$"):
        return _trailing_backslash_count(text, len(text) - 1) % 2 == 0
    if text.endswith(r"\b"):
        # The backslash forming \b sits at index len-2; it's a real
        # anchor only if *that* backslash isn't itself escaped by an odd
        # number of backslashes before it.
        return _trailing_backslash_count(text, len(text) - 2) % 2 == 0
    return False


def _strip_full_group_wrap(branch: str) -> tuple[str, str, str] | None:
    """If `branch` is exactly OUTER_LEFT + '(' + inner + ')' + OUTER_RIGHT,
    where OUTER_LEFT is an optional leading '^'/'\\b', OUTER_RIGHT is an
    optional trailing '$'/'\\b', and the '(' immediately after OUTER_LEFT
    matches the ')' immediately before OUTER_RIGHT (the group spans the
    branch's entire remaining content, not just part of it) -- return
    (outer_left, inner, outer_right). Otherwise return None.

    This detects the safe case where a branch's own anchors wrap one whole
    group, so every alternative inside it inherits the same anchoring
    (e.g. "^(cat|dog)$" == "^cat$|^dog$") -- as opposed to a group that
    doesn't span the branch's full remaining text (e.g. "^(cat|dog$)",
    where "$" sits only inside the group and never anchors "cat")."""
    outer_left = ""
    rest = branch
    for prefix in (r"\b", "^"):
        if rest.startswith(prefix):
            outer_left = prefix
            rest = rest[len(prefix) :]
            break
    outer_right = ""
    if _is_real_end_anchor(rest):
        outer_right = "$" if rest.endswith("$") else r"\b"
        rest = rest[: len(rest) - len(outer_right)]
    if not rest.startswith("("):
        return None
    depth = 0
    in_class = False
    close_pos = None
    i = 0
    while i < len(rest):
        c = rest[i]
        if c == "\\" and i + 1 < len(rest):
            i += 2
            continue
        if in_class:
            if c == "]":
                in_class = False
        elif c == "[":
            in_class = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                close_pos = i
                break
        i += 1
    if close_pos is None or close_pos != len(rest) - 1:
        return None
    return outer_left, rest[1:close_pos], outer_right


def _branch_anchoring_verdict(branch: str) -> tuple[str, str]:
    """Recursively classify a single alternation branch as "anchored",
    "weak" (short and unanchored -- false-positive-prone, e.g. matches
    "catalog"), or "unresolved" (contains alternation nested inside a
    group whose anchoring can't be established with confidence). Returns
    (verdict, the specific sub-pattern responsible for a non-"anchored"
    verdict)."""
    wrap = _strip_full_group_wrap(branch)
    if wrap is not None:
        outer_left, inner, outer_right = wrap
        inner_branches = _split_top_level_alternation(inner)
        if len(inner_branches) > 1:
            # e.g. "^(cat|dog)$" == "^cat$|^dog$" -- the branch's own
            # anchors wrap the *entire* group, so each inner alternative
            # inherits them. Recurse in case a sub-branch is itself
            # wrapped again.
            for sub in inner_branches:
                verdict, detail = _branch_anchoring_verdict(outer_left + sub + outer_right)
                if verdict != "anchored":
                    return verdict, detail
            return "anchored", ""
    if any(len(_split_top_level_alternation(g)) > 1 for g in _extract_group_contents(branch)):
        # Alternation nested inside a group, but not in the clean "the
        # whole branch is one anchored group" shape above -- e.g.
        # "^(cat|dog$)", where "$" only anchors the "dog" alternative and
        # "cat" is left unanchored. Too risky to assess with confidence.
        return "unresolved", branch

    left_anchored = branch.startswith(r"\b") or branch.startswith("^")
    right_anchored = _is_real_end_anchor(branch)
    is_anchored = left_anchored and right_anchored
    bare_needle = re.sub(r"[\\^$.*+?()\[\]{}|]", "", branch)
    if not is_anchored and len(bare_needle) <= 4:
        return "weak", branch
    return "anchored", ""


def _split_top_level_args(arg_text: str) -> list[str]:
    """Split a call's trailing-argument text on top-level commas (respecting
    parens/brackets and string literals) into individual argument
    expressions, e.g. 'skill_md_text, comment="a, b"' ->
    ['skill_md_text', 'comment="a, b"']."""
    args = []
    depth = 0
    in_string = None
    current = []
    i = 0
    while i < len(arg_text):
        c = arg_text[i]
        if in_string:
            current.append(c)
            if c == "\\" and i + 1 < len(arg_text):
                current.append(arg_text[i + 1])
                i += 2
                continue
            if c == in_string:
                in_string = None
            i += 1
            continue
        if c in ("'", '"'):
            in_string = c
            current.append(c)
        elif c in "([":
            depth += 1
            current.append(c)
        elif c in ")]":
            depth = max(0, depth - 1)
            current.append(c)
        elif c == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(c)
        i += 1
    tail = "".join(current).strip()
    if tail:
        args.append(tail)
    return args


def _extract_flags(arg_text: str) -> tuple[list[str], list[str], bool]:
    """Parse a call's trailing-argument text for `re.X` flag tokens.
    Returns (recognized_flag_names, unrecognized_flag_names, has_residual).

    has_residual is True when something besides recognized/unrecognized
    `re.X` tokens and `|`/whitespace remains after removing every `re.X`
    token found -- e.g. a bare variable mixed in via `|`
    (`re.MULTILINE | FLAGS`). Finding only "MULTILINE" and silently
    dropping the unresolvable "FLAGS" component would change the call's
    real semantics, so the whole expression must be treated as
    unresolved rather than partially trusted."""
    recognized = []
    unrecognized = []
    for name in FLAG_RE.findall(arg_text):
        (recognized if name in SUPPORTED_FLAGS else unrecognized).append(name)
    residual = FLAG_RE.sub("", arg_text)
    residual = re.sub(r"[|\s]", "", residual)
    return recognized, unrecognized, bool(residual)


def _safe_findall_count(
    pattern: str, text: str, timeout: float, flags: list[str] | None = None
) -> tuple[bool, int, str]:
    """Run re.findall(pattern, text, flags) in an isolated subprocess with a
    hard timeout. Returns (ok, count, error_or_empty)."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", _CHILD_SCRIPT],
            input=json.dumps({"pattern": pattern, "text": text, "flags": flags or []}),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
        )
    except subprocess.TimeoutExpired:
        return False, 0, f"did not complete within {timeout}s (possible catastrophic backtracking)"
    if result.returncode != 0 or not result.stdout.strip():
        return False, 0, f"subprocess failed: {result.stderr.strip()[:200]}"
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, 0, f"subprocess produced unparseable output: {result.stdout[:200]}"
    if not payload.get("ok"):
        return False, 0, payload.get("error", "unknown regex error")
    return True, payload.get("count", 0), ""


def _is_absence_check_usage(source: str, call_start: int, args_start: int) -> bool:
    """Best-effort heuristic (issue #56): does this re.findall(...) result look
    like it's assigned to a variable and then used to check for *absence*
    (`if <var>:`, `if not <var>:`, `assert not <var>`) rather than iterated?
    If so, zero matches is the check's own intended passing outcome, not a
    vacuous-iteration bug. `args_start` is the position just inside the call's
    open paren (e.g. `m.end()` from a FINDALL_RE match), used to locate the
    call's own close paren via `_scan_to_close_paren` before looking ahead.

    Not real data-flow analysis -- just a narrow, bounded textual scan for the
    exact shapes named in issue #56's suggested fix. A false negative here
    (a real absence check this heuristic doesn't recognize) just leaves the
    zero-match guard reporting FAIL as it always has -- no regression. A false
    positive would wrongly downgrade a real vacuous-iteration bug, so this
    stays deliberately narrow rather than trying to cover every idiom."""
    line_start = source.rfind("\n", 0, call_start) + 1
    prefix_on_line = source[line_start:call_start]
    assign_m = re.match(r"^\s*(\w+)\s*=\s*$", prefix_on_line)
    if not assign_m:
        return False
    var = re.escape(assign_m.group(1))

    close_paren = _scan_to_close_paren(source, args_start)
    newline_after_call = source.find("\n", close_paren)
    if newline_after_call == -1:
        return False
    lookahead_lines = source[newline_after_call + 1 :].splitlines()[:5]
    absence_re = re.compile(
        rf"^\s*(?:if|elif|while)\s+(?:not\s+)?{var}\s*:"
        rf"|^\s*assert\s+not\s+{var}\b"
    )
    return any(absence_re.match(line) for line in lookahead_lines)


def check_zero_match_and_anchoring(
    smoke_test_path: Path, skill_md_text: str | None, regex_timeout: float
) -> list[str]:
    """Best-effort static scan: extract literal re.findall/re.search patterns
    from smoke_test.py and flag zero-match iteration and unanchored short
    needles. A pattern applied to something other than SKILL.md content, a
    non-literal pattern (f-string/variable-built), or a pattern that can't be
    evaluated within the timeout is reported for manual review rather than
    silently skipped or confidently asserted -- this script does not execute
    the target script, so it can't know the real haystack with certainty."""
    findings = []
    try:
        source = smoke_test_path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"FAIL: could not read {smoke_test_path}: {e}"]

    noncode_spans = _noncode_spans(source)
    literal_call_starts = set()

    findall_matches = list(FINDALL_RE.finditer(source))
    for m in findall_matches:
        if _in_noncode(m.start(), noncode_spans):
            # Example text inside a comment or docstring, not a real call
            # the target script executes -- ignore it entirely.
            continue
        prefix, quote, raw_text = m.group(1), m.group(2), m.group(3)

        if not _is_complete_literal_arg(source, m.end()):
            # Concatenated/constructed pattern (e.g. r"\b" + re.escape(x) +
            # r"\b") -- the captured literal is only a fragment, not the real
            # pattern. Leave it out of literal_call_starts so CALL_RE's own
            # pass below reports it for manual review instead of confidently
            # (and wrongly) evaluating just the fragment.
            continue

        literal_call_starts.add(m.start())
        decode_ok, pattern = _decode_literal(prefix, quote, raw_text)
        if not decode_ok:
            findings.append(
                f"SKIP (manual review): re.findall({prefix}{quote}{raw_text}{quote}, ...) "
                "-- this literal couldn't be decoded to its real runtime value. "
                "Verify manually."
            )
            continue
        if skill_md_text is None:
            findings.append(
                f"SKIP: re.findall(r'{pattern}') found but no --skill-md given "
                "to test it against -- cannot check for zero-match vacuity"
            )
            continue

        arg_text = _extract_call_arg_text(source, m.end())
        call_args = _split_top_level_args(arg_text)
        haystack_arg = call_args[0] if call_args else arg_text
        if "skill" not in haystack_arg.lower():
            findings.append(
                f"SKIP (haystack unclear): re.findall(r'{pattern}') is applied to "
                f"'{haystack_arg[:60]}', not confirmed as SKILL.md content -- this tool "
                "doesn't execute the target script, so testing it against SKILL.md "
                "instead would risk a false FAIL (e.g. a check that scans "
                "workflows/*.md, not SKILL.md). Verify manually."
            )
            continue

        trailing_args = call_args[1:]
        flags, unrecognized_flags, has_residual = _extract_flags(", ".join(trailing_args))
        if trailing_args and has_residual:
            findings.append(
                f"SKIP (manual review): re.findall(r'{pattern}') has a trailing "
                f"argument ({trailing_args[-1]!r}) this checker can't fully resolve "
                "to known flags -- evaluating with only the recognized portion "
                "could be wrong if the rest is an indirect flags reference. "
                "Verify manually."
            )
            continue
        if unrecognized_flags:
            findings.append(
                f"SKIP (manual review): re.findall(r'{pattern}') uses flag(s) "
                f"{', '.join(unrecognized_flags)} this checker doesn't support -- "
                "evaluating without them could change match semantics. Verify manually."
            )
            continue

        ok, count, error = _safe_findall_count(pattern, skill_md_text, regex_timeout, flags)
        if not ok:
            findings.append(f"SKIP: pattern '{pattern}' could not be evaluated: {error}")
            continue
        if count == 0 and _is_absence_check_usage(source, m.start(), m.end()):
            findings.append(
                f"SKIP (manual review): re.findall(r'{pattern}') matches nothing, but the "
                "result appears to be used in an absence check (`if`/`if not`/`assert not` "
                "on the assigned variable), not iterated -- zero matches may be this check's "
                "own intended passing outcome. Verify manually rather than confidently FAIL."
            )
        elif count == 0:
            findings.append(
                f"FAIL (zero-match guard): re.findall(r'{pattern}') matches nothing "
                "against the target's SKILL.md -- any check iterating this result is vacuous"
            )
        else:
            findings.append(
                f"PASS (zero-match guard): re.findall(r'{pattern}') found {count} match(es)"
            )

    search_matches = list(SEARCH_RE.finditer(source))
    for m in search_matches:
        if _in_noncode(m.start(), noncode_spans):
            continue
        prefix, quote, raw_text = m.group(1), m.group(2), m.group(3)

        if not _is_complete_literal_arg(source, m.end()):
            continue  # concatenated/constructed -- let CALL_RE's fallback catch it

        literal_call_starts.add(m.start())
        decode_ok, pattern = _decode_literal(prefix, quote, raw_text)
        if not decode_ok:
            findings.append(
                f"SKIP (manual review): re.search({prefix}{quote}{raw_text}{quote}, ...) "
                "-- this literal couldn't be decoded to its real runtime value. "
                "Verify manually."
            )
            continue

        arg_text = _extract_call_arg_text(source, m.end())
        call_args = _split_top_level_args(arg_text)
        haystack_arg = call_args[0] if call_args else arg_text
        if "skill" not in haystack_arg.lower():
            findings.append(
                f"SKIP (haystack unclear): re.search(r'{pattern}') is applied to "
                f"'{haystack_arg[:60]}', not confirmed as SKILL.md content -- this tool "
                "doesn't execute the target script, so evaluating anchoring against SKILL.md "
                "semantics would risk a false FAIL on a pattern intentionally designed for a "
                "different haystack (e.g. a shell-metacharacter detector applied to an "
                "extracted command line, where '&&'/'|'/';' must match anywhere by design, "
                "not a SKILL.md trigger-phrase assertion). Verify manually."
            )
            continue

        branches = _split_top_level_alternation(pattern)
        weak_branches = []
        unresolved_branches = []
        for branch in branches:
            verdict, detail = _branch_anchoring_verdict(branch)
            if verdict == "unresolved":
                unresolved_branches.append(detail)
            elif verdict == "weak":
                weak_branches.append(detail)
        if unresolved_branches:
            findings.append(
                f"SKIP (manual review): re.search(r'{pattern}') contains an "
                "alternation nested inside a group whose anchoring can't be "
                f"established with confidence ({', '.join(repr(b) for b in unresolved_branches)}). "
                "Verify manually."
            )
        elif weak_branches:
            if len(branches) > 1:
                findings.append(
                    f"FAIL (anchored matching): re.search(r'{pattern}') is an unanchored "
                    "alternation with at least one short, unanchored branch "
                    f"({', '.join(repr(b) for b in weak_branches)}) -- each branch matches "
                    "independently, so a short unanchored branch is exactly as "
                    r"false-positive-prone as a single short pattern (e.g. \bcat still matches "
                    "'catalog')"
                )
            else:
                findings.append(
                    f"FAIL (anchored matching): re.search(r'{pattern}') is a short, unanchored "
                    "needle, or anchored on only one side -- likely to false-positive on "
                    r"unrelated prose (e.g. \bcat still matches 'catalog')"
                )
        else:
            findings.append(
                f"PASS (anchored matching): re.search(r'{pattern}') is anchored on "
                "both sides or long enough to be specific"
                + (" (every alternation branch checked independently)" if len(branches) > 1 else "")
            )

    any_call_found = False
    for m in CALL_RE.finditer(source):
        if _in_noncode(m.start(), noncode_spans):
            continue
        any_call_found = True
        if m.start() not in literal_call_starts:
            findings.append(
                f"SKIP (manual review): re.{m.group(1)}(...) at "
                f"{smoke_test_path.name}:{_line_number(source, m.start())} uses a "
                "non-literal pattern (f-string/variable/expression) this static "
                "scan can't parse -- check its vacuousness manually."
            )

    if not any_call_found:
        findings.append(
            "INFO: no re.findall/re.search calls found via static scan "
            "-- nothing to check mechanically"
        )

    return findings


def check_coverage_arithmetic(evals_json_path: Path) -> list[str]:
    try:
        raw = evals_json_path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"FAIL: could not read {evals_json_path}: {e}"]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return [f"FAIL (blocking): {evals_json_path} is not valid JSON: {e}"]

    if not isinstance(data, dict):
        return [
            f"FAIL (blocking): {evals_json_path}'s root value is a "
            f"{type(data).__name__}, expected a JSON object"
        ]

    coverage = data.get("testing_validation_coverage")
    if coverage is None:
        return ["INFO: no testing_validation_coverage field present -- nothing to check"]

    if not isinstance(coverage, dict):
        return [
            f"FAIL (blocking): testing_validation_coverage is a "
            f"{type(coverage).__name__}, expected a JSON object"
        ]

    total = coverage.get("declared_scenarios_total")
    covered = coverage.get("declared_scenarios_covered")
    uncovered = coverage.get("uncovered", [])

    if total is None or covered is None:
        return ["SKIP: declared_scenarios_total/declared_scenarios_covered not both present"]

    if not isinstance(total, int) or isinstance(total, bool):
        return [
            f"FAIL (blocking): declared_scenarios_total is a {type(total).__name__}, "
            "expected an integer"
        ]
    if not isinstance(covered, int) or isinstance(covered, bool):
        return [
            f"FAIL (blocking): declared_scenarios_covered is a {type(covered).__name__}, "
            "expected an integer"
        ]
    if not isinstance(uncovered, list):
        return [
            f"FAIL (blocking): uncovered is a {type(uncovered).__name__}, expected a JSON array"
        ]
    if total < 0:
        return [f"FAIL (blocking): declared_scenarios_total is negative ({total})"]
    if covered < 0:
        return [f"FAIL (blocking): declared_scenarios_covered is negative ({covered})"]

    findings = []
    if covered + len(uncovered) != total:
        findings.append(
            f"FAIL (counting): declared_scenarios_covered ({covered}) + len(uncovered) "
            f"({len(uncovered)}) = {covered + len(uncovered)}, "
            f"expected declared_scenarios_total ({total})"
        )
    else:
        findings.append(
            f"PASS (counting): {covered} covered + {len(uncovered)} uncovered == {total} total"
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-test", type=Path, default=None)
    parser.add_argument("--skill-md", type=Path, default=None)
    parser.add_argument("--evals-json", type=Path, default=None)
    parser.add_argument("--regex-timeout", type=float, default=DEFAULT_REGEX_TIMEOUT_SECONDS)
    args = parser.parse_args()

    if not any([args.smoke_test, args.evals_json]):
        parser.error("at least one of --smoke-test or --evals-json is required")

    exit_code = 0
    skill_md_text = None
    if args.skill_md is not None:
        try:
            skill_md_text = args.skill_md.read_text(encoding="utf-8")
        except OSError as e:
            print(f"FAIL: could not read --skill-md {args.skill_md}: {e}")
            exit_code = 1

    if args.smoke_test is not None:
        print(f"\n== Check 1: {args.smoke_test} ==")
        for line in check_zero_match_and_anchoring(
            args.smoke_test, skill_md_text, args.regex_timeout
        ):
            print(line)
            if line.startswith("FAIL"):
                exit_code = 1

    if args.evals_json is not None:
        print(f"\n== Check 2: {args.evals_json} ==")
        for line in check_coverage_arithmetic(args.evals_json):
            print(line)
            if line.startswith("FAIL"):
                exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
