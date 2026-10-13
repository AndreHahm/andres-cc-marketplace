#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Split long text into blocks of at most 2,000 UTF-16 units, for Notion page content.

Notion rejects a text block or text property longer than 2,000 characters, so the
notion-knowledge-management skill writes a long record body (a Report, for example) as page
content split into blocks, with the record's own `body` property holding only a short note.

Usage:
    wmgt_split_blocks.py split <file> [--max N] [--start I] [--count K]

Prints one JSON object: {"ok": true, "max_units": N, "total": <all blocks>, "start": I,
"count": <blocks returned>, "blocks": [...]} with the blocks in [start, start + count)
(count defaults to 10). A caller pages through a long text with --start. On a failure it
prints {"ok": false, "error": "..."} and exits 1.

Splitting prefers a blank line between paragraphs, then a line break, then a space or tab,
and cuts hard only where a stretch has no whitespace. Length is counted in UTF-16 units, so a
character outside the Basic Multilingual Plane counts as two and is never cut in half.
Limitation: it does not understand markdown tables or code fences, so a split can land inside
one.

The file must be a regular (non-symlink), strictly UTF-8, non-blank file of at most 5 MB.
"""

import argparse
import json
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
    """Split one over-long paragraph at a line break, then whitespace, then hard."""
    pieces = []
    while units(paragraph) > max_units:
        head = prefix_within(paragraph, max_units)
        cut = max(head.rfind("\n"), head.rfind(" "), head.rfind("\t"))
        if cut > 0:
            pieces.append(head[:cut])
            paragraph = paragraph[cut + 1 :]
        else:
            pieces.append(head)
            paragraph = paragraph[len(head) :]
    pieces.append(paragraph)
    return pieces


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
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise SplitError("the file is not valid UTF-8") from None
    if not text.strip():
        raise SplitError("the file is empty or only whitespace")
    return text


def run(args):
    if not 1 <= args.max <= LIMIT:
        raise SplitError(f"--max must be between 1 and {LIMIT}")
    if args.start < 0:
        raise SplitError("--start must be 0 or more")
    if args.count < 1:
        raise SplitError("--count must be 1 or more")
    blocks = split_blocks(read_text(args.file), args.max)
    window = blocks[args.start : args.start + args.count]
    return {
        "ok": True,
        "max_units": args.max,
        "total": len(blocks),
        "start": args.start,
        "count": len(window),
        "blocks": window,
    }


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
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
