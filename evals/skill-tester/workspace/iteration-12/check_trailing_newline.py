"""Pass check for iteration 12: every JSON file an agent wrote must parse and end in a newline.

Usage: python check_trailing_newline.py <output-dir> [<expected-file-count>]

Walks <output-dir> for *.json files, prints one line per file, and exits 1 if any file is
invalid JSON or lacks a final newline (last byte 0x0A), or if the count differs from the
expected one when given.
"""

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__)
        return 2
    root = Path(argv[1])
    expected = int(argv[2]) if len(argv) == 3 else None
    files = sorted(root.rglob("*.json"))
    failed = False
    for path in files:
        data = path.read_bytes()
        try:
            json.loads(data)
            valid = True
        except ValueError:
            valid = False
        ends_with_newline = data.endswith(b"\n")
        failed = failed or not (valid and ends_with_newline)
        print(f"{path.relative_to(root)}: valid_json={valid} ends_with_newline={ends_with_newline}")
    if expected is not None and len(files) != expected:
        print(f"expected {expected} files, found {len(files)}")
        failed = True
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
