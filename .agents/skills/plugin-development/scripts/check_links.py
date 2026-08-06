#!/usr/bin/env python3
"""
Markdown Link Integrity Checker

Walks every .md file under a plugin directory and checks two patterns:

1. Markdown link targets ([text](path/to/file.md)) that don't resolve to a
   real file, relative to the linking file - reported as broken links.
2. Bare backtick-quoted filenames (`some-file.md`) with no path separator -
   the common "see `other-file.md`" prose-citation pattern. These are
   reported as advisory, not broken: the filename might legitimately live
   in a different skill's directory, so this only flags names that don't
   exist ANYWHERE under the given root.

External URLs (http/https) and anchor-only links (#heading) are skipped.
"""

import re
import sys
from pathlib import Path

LINK_PATTERN = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
BARE_FILENAME_PATTERN = re.compile(r'`([a-zA-Z0-9_-]+\.md)`')
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.temp', '.draft', '.backup'}


def find_markdown_files(root):
    for path in root.rglob('*.md'):
        if not any(part in SKIP_DIRS for part in path.parts):
            yield path


def extract_relative_targets(content):
    for match in LINK_PATTERN.finditer(content):
        target = match.group(2).strip()
        if target.startswith(('http://', 'https://', '#', 'mailto:')):
            continue
        line_num = content.count('\n', 0, match.start()) + 1
        yield line_num, target


def extract_bare_filenames(content):
    for match in BARE_FILENAME_PATTERN.finditer(content):
        line_num = content.count('\n', 0, match.start()) + 1
        yield line_num, match.group(1)


def check_links(md_file):
    broken = []
    content = md_file.read_text(encoding='utf-8')
    for line_num, target in extract_relative_targets(content):
        path_part = target.split('#', 1)[0]
        if not path_part:
            continue
        resolved = (md_file.parent / path_part).resolve()
        if not resolved.exists():
            broken.append((line_num, target, resolved))
    return broken


def check_bare_filenames(md_file, all_filenames_in_root):
    advisory = []
    content = md_file.read_text(encoding='utf-8')
    for line_num, name in extract_bare_filenames(content):
        if name == md_file.name:
            continue
        if name not in all_filenames_in_root:
            advisory.append((line_num, name))
    return advisory


def main():
    if len(sys.argv) != 2:
        print("Usage: python check_links.py <path/to/plugin-or-skill-dir>")
        sys.exit(1)

    sys.stdout.reconfigure(encoding='utf-8')
    root = Path(sys.argv[1]).resolve()
    if not root.exists():
        print(f"Error: {root} does not exist")
        sys.exit(1)

    md_files = sorted(find_markdown_files(root))
    all_filenames_in_root = {f.name for f in md_files}

    total_broken = 0
    total_advisory = 0
    for md_file in md_files:
        rel = md_file.relative_to(root)

        for line_num, target, resolved in check_links(md_file):
            print(f"{rel}:{line_num}: broken link '{target}' -> {resolved} does not exist")
            total_broken += 1

        for line_num, name in check_bare_filenames(md_file, all_filenames_in_root):
            print(f"{rel}:{line_num}: ⚠️ advisory: bare reference `{name}` not found anywhere under {root} - verify manually, may be a different skill's file")
            total_advisory += 1

    print(f"\nChecked {len(md_files)} markdown files: {total_broken} broken link(s), {total_advisory} advisory bare-reference(s)")
    sys.exit(1 if total_broken else 0)


if __name__ == "__main__":
    main()
