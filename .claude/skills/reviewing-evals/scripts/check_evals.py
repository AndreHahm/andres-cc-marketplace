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
import json
import re
import subprocess
import sys
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


def _extract_call_arg_text(source: str, arg_start: int) -> str:
    """From just after a matched pattern's closing quote, scan to the
    matching close-paren of the enclosing re.findall(...)/re.search(...) call
    -- balancing nested parens (e.g. `wf.read_text(encoding="utf-8")`) -- and
    return the remaining argument text. String-literal-aware: a paren inside
    a quoted string argument (e.g. `comment="see docs (section 2"`) doesn't
    count toward paren depth, since it isn't a real call-structure paren."""
    depth = 1
    i = arg_start
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
    return source[arg_start:i].lstrip(", \t\n")


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


def _extract_flags(arg_text: str) -> tuple[list[str], list[str]]:
    """Return (recognized_flag_names, unrecognized_flag_names) found in a
    call's trailing arguments, e.g. `re.MULTILINE` in
    `re.findall(pattern, text, re.MULTILINE)`."""
    recognized = []
    unrecognized = []
    for name in FLAG_RE.findall(arg_text):
        (recognized if name in SUPPORTED_FLAGS else unrecognized).append(name)
    return recognized, unrecognized


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

    literal_call_starts = set()

    findall_matches = list(FINDALL_RE.finditer(source))
    for m in findall_matches:
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
        if "skill" not in arg_text.lower():
            findings.append(
                f"SKIP (haystack unclear): re.findall(r'{pattern}') is applied to "
                f"'{arg_text[:60]}', not confirmed as SKILL.md content -- this tool "
                "doesn't execute the target script, so testing it against SKILL.md "
                "instead would risk a false FAIL (e.g. a check that scans "
                "workflows/*.md, not SKILL.md). Verify manually."
            )
            continue

        trailing_args = _split_top_level_args(arg_text)[1:]
        flags, unrecognized_flags = _extract_flags(arg_text)
        if trailing_args and not flags and not unrecognized_flags:
            findings.append(
                f"SKIP (manual review): re.findall(r'{pattern}') has a trailing "
                f"argument ({trailing_args[-1]!r}) this checker can't statically "
                "resolve to known flags -- evaluating with zero flags could be "
                "wrong if it's an indirect flags reference. Verify manually."
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
        if count == 0:
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
        branches = _split_top_level_alternation(pattern)
        weak_branches = []
        for branch in branches:
            left_anchored = branch.startswith(r"\b") or branch.startswith("^")
            right_anchored = branch.endswith(r"\b") or branch.endswith("$")
            is_anchored = left_anchored and right_anchored
            bare_needle = re.sub(r"[\\^$.*+?()\[\]{}|]", "", branch)
            if not is_anchored and len(bare_needle) <= 4:
                weak_branches.append(branch)
        if weak_branches:
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
