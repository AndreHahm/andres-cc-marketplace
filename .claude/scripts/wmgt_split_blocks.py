#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Split long text into blocks of at most 2,000 UTF-16 units, for Notion page content.

Notion's API limits a text block or text property to 2,000 characters (a live probe found the
connector accepts longer text, so the limit is kept as a conservative contract). The
notion-knowledge-management skill therefore writes a long record body (a Report, for example) as
page content split into blocks, with the record's own `body` property holding only a short note.

Usage:
    wmgt_split_blocks.py split <file> [--max N] [--start I] [--count K]

Prints one JSON object: {"ok": true, "max_units": N, "total": <all blocks>, "start": I,
"count": <blocks returned>, "has_more": bool, "next_start": <int or null>, "blocks": [...]}
with the blocks in [start, start + count) (count defaults to 10). A caller pages through a
long text by passing "next_start" as --start while "has_more" is true. On a failure,
including a bad command line, it prints {"ok": false, "error": "..."} and exits 1.

Splitting prefers a blank line between paragraphs, then a line break, then a space or tab,
and cuts hard only where a stretch has no whitespace. Length is counted in UTF-16 units, so a
character outside the Basic Multilingual Plane counts as two and is never cut in half; --max
therefore has to be at least 2. Line endings are normalized to LF before splitting, and a run of
three or more newlines becomes one blank line, so the caller's reassembly with a blank line
between blocks never differs from the split text by extra blank lines. The
whitespace character at a cut is dropped, and blocks cut from one paragraph are rejoined with a
blank line by the caller, so a mid-paragraph cut reads as a paragraph break after reassembly.
Limitation: it does not understand markdown tables or code fences, so a split can land inside
one, and the blank-line normalization also applies inside a code fence.

The file must be a regular (non-symlink), strictly UTF-8 (a leading byte-order mark is ignored),
non-blank file of at most 5 MB. The
symlink check covers only the final path component and is a convenience, not a security
boundary.
"""

import argparse
import json
import re
import sys
from pathlib import Path

LIMIT = 2000
MAX_FILE_BYTES = 5 * 1024 * 1024
DEFAULT_COUNT = 10


class SplitError(Exception):
    """A typed, user-facing failure."""


def units(text):
    """Length in UTF-16 units, the measure Notion's 2,000-character limit is applied in."""
    return len(text.encode("utf-16-le", "surrogatepass")) // 2


def prefix_within(text, max_units):
    """Longest prefix of ``text`` of at most ``max_units`` units, never cutting a character."""
    total = 0
    for index, char in enumerate(text):
        width = 2 if ord(char) > 0xFFFF else 1
        if total + width > max_units:
            return text[:index]
        total += width
    return text


def split_paragraph(paragraph, max_units):
    """Split one over-long paragraph at a line break, then whitespace, then hard.

    ``max_units`` must be at least 2 so every character fits, which guarantees progress. Only a
    window of at most ``max_units`` characters is measured per step, so the work stays linear.
    """
    pieces = []
    pos = 0
    while True:
        if len(paragraph) - pos <= max_units:
            rest = paragraph[pos:]
            if units(rest) <= max_units:
                pieces.append(rest)
                return pieces
        head = prefix_within(paragraph[pos : pos + max_units], max_units)
        cut = head.rfind("\n")
        if cut <= 0:
            cut = max(head.rfind(" "), head.rfind("\t"))
        if cut > 0:
            pieces.append(head[:cut])
            pos += cut + 1
        else:
            pieces.append(head)
            pos += len(head)


def split_blocks(text, max_units):
    """Return the blocks of ``text``, each at most ``max_units`` units, none empty."""
    parts = []
    for paragraph in text.split("\n\n"):
        parts.extend(
            split_paragraph(paragraph, max_units) if units(paragraph) > max_units else [paragraph]
        )
    blocks, current = [], ""
    for part in parts:
        candidate = part if not current else current + "\n\n" + part
        if current and units(candidate) > max_units:
            blocks.append(current)
            current = part
        else:
            current = candidate
    blocks.append(current)
    cleaned = [block.strip("\n") for block in blocks]
    return [block for block in cleaned if block.strip()]


def read_text(path_text):
    path = Path(path_text)
    if path.is_symlink():
        raise SplitError("the file is a symlink; pass the real file")
    if not path.is_file():
        raise SplitError("the path is not a regular file")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise SplitError(f"the file is larger than {MAX_FILE_BYTES} bytes")
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise SplitError("the file is not valid UTF-8") from None
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    if not text.strip():
        raise SplitError("the file is empty or only whitespace")
    return text


def run(args):
    if not 2 <= args.max <= LIMIT:
        raise SplitError(f"--max must be between 2 and {LIMIT}")
    if args.start < 0:
        raise SplitError("--start must be 0 or more")
    if args.count < 1:
        raise SplitError("--count must be 1 or more")
    blocks = split_blocks(read_text(args.file), args.max)
    window = blocks[args.start : args.start + args.count]
    end = args.start + len(window)
    return {
        "ok": True,
        "max_units": args.max,
        "total": len(blocks),
        "start": args.start,
        "count": len(window),
        "has_more": end < len(blocks),
        "next_start": end if end < len(blocks) else None,
        "blocks": window,
    }


class _JsonArgumentParser(argparse.ArgumentParser):
    """Report a bad command line as the documented JSON failure instead of argparse's exit 2."""

    def error(self, message):
        raise SplitError(f"bad arguments: {message}")


def main(argv):
    parser = _JsonArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    split = sub.add_parser("split", help="split a file into blocks")
    split.add_argument("file")
    split.add_argument("--max", type=int, default=LIMIT)
    split.add_argument("--start", type=int, default=0)
    split.add_argument("--count", type=int, default=DEFAULT_COUNT)
    try:
        result = run(parser.parse_args(argv))
    except SplitError as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
