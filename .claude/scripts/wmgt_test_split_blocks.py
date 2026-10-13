#!/usr/bin/env python3
"""Fixture-based regression test for wmgt_split_blocks.py. Run:
    python scripts/wmgt_test_split_blocks.py

Runs the script as a subprocess against fixture files in a temporary directory and
asserts on exit code and JSON output. Exits 0 when every case passes, 1 otherwise.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent / "wmgt_split_blocks.py"


def run_script(*args):
    """Run the script with ``args``; return (exit code, parsed JSON or a non-JSON sentinel)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8"
    )
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError:
        return proc.returncode, {"_non_json_stdout": proc.stdout, "_stderr": proc.stderr}


def utf16_units(text):
    return len(text.encode("utf-16-le")) // 2


def all_blocks(path, *extra):
    """Fetch every block via the pagination flags, to also exercise --start/--count."""
    code, out = run_script("split", str(path), *extra, "--count", "1000")
    return code, out


def main():
    failures = []

    def check(name, condition, detail=""):
        if not condition:
            failures.append(f"{name}: {detail}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        def write(name, text):
            path = tmp / name
            path.write_text(text, encoding="utf-8", newline="")
            return path

        # 1. Short text is one block, unchanged.
        code, out = all_blocks(write("short.md", "Hello.\n\nWorld."))
        check("short exit", code == 0, str(out))
        check("short single block", out.get("blocks") == ["Hello.\n\nWorld."], str(out))
        check("short total", out.get("total") == 1, str(out))

        # 2. Many paragraphs split at paragraph boundaries and reassemble exactly.
        paragraphs = [f"Paragraph {i}: " + ("word " * 60).strip() for i in range(30)]
        original = "\n\n".join(paragraphs)
        code, out = all_blocks(write("paras.md", original))
        blocks = out.get("blocks", [])
        check("paras exit", code == 0, str(out))
        check("paras split into several", len(blocks) > 1, str(len(blocks)))
        check("paras within limit", all(utf16_units(b) <= 2000 for b in blocks), "block over 2000")
        check("paras reassemble", "\n\n".join(blocks) == original, "reassembly differs")
        check("paras total matches", out.get("total") == len(blocks), str(out.get("total")))

        # 3. One oversized paragraph is split at whitespace, never mid-word.
        words = [f"w{i:04d}" for i in range(1200)]
        big = " ".join(words)
        code, out = all_blocks(write("big.md", big))
        blocks = out.get("blocks", [])
        check("big within limit", all(utf16_units(b) <= 2000 for b in blocks), "block over 2000")
        check("big more than one", len(blocks) > 1, str(len(blocks)))
        check("big keeps every word", " ".join(blocks).split() == words, "words lost or cut")

        # 4. No whitespace at all falls back to a hard split that loses nothing.
        solid = "x" * 5000
        code, out = all_blocks(write("solid.md", solid))
        blocks = out.get("blocks", [])
        check("solid within limit", all(utf16_units(b) <= 2000 for b in blocks), "block over 2000")
        check("solid lossless", "".join(blocks) == solid, "content differs")

        # 5. Characters outside the BMP count as two units each.
        emoji = "\U0001f600" * 1500  # 3000 UTF-16 units
        code, out = all_blocks(write("emoji.md", emoji))
        blocks = out.get("blocks", [])
        check("emoji within limit", all(utf16_units(b) <= 2000 for b in blocks), "block over 2000")
        check("emoji lossless", "".join(blocks) == emoji, "content differs")
        check(
            "emoji no broken pair",
            all(b == b.encode("utf-16", "surrogatepass").decode("utf-16") for b in blocks),
            "split a pair",
        )

        # 6. --max lowers the limit; pagination slices the same list.
        code, small = run_script("split", str(tmp / "paras.md"), "--max", "300", "--count", "1000")
        check("max exit", code == 0, str(small))
        check(
            "max within limit",
            all(utf16_units(b) <= 300 for b in small.get("blocks", [])),
            "block over 300",
        )
        code, page = run_script(
            "split", str(tmp / "paras.md"), "--max", "300", "--start", "2", "--count", "3"
        )
        check("page slice", page.get("blocks") == small.get("blocks", [])[2:5], str(page))
        check("page total", page.get("total") == small.get("total"), str(page))
        check("page start", page.get("start") == 2, str(page))

        # 7. Typed failures.
        for name, args in {
            "max too large": ("split", str(tmp / "short.md"), "--max", "2001"),
            "max zero": ("split", str(tmp / "short.md"), "--max", "0"),
            "negative start": ("split", str(tmp / "short.md"), "--start", "-1"),
            "missing file": ("split", str(tmp / "nope.md")),
        }.items():
            code, out = run_script(*args)
            check(
                f"fail {name}",
                code == 1 and out.get("ok") is False and out.get("error"),
                f"{code} {out}",
            )

        code, out = run_script("split", str(write("blank.md", " \n\n \t")))
        check("fail blank", code == 1 and out.get("ok") is False, f"{code} {out}")

        bad = tmp / "bad.md"
        bad.write_bytes(b"\xff\xfe\xfa not utf8")
        code, out = run_script("split", str(bad))
        check("fail non-utf8", code == 1 and out.get("ok") is False, f"{code} {out}")

        code, out = run_script("split", str(tmp))
        check("fail directory", code == 1 and out.get("ok") is False, f"{code} {out}")

        link = tmp / "link.md"
        try:
            link.symlink_to(tmp / "short.md")
        except (OSError, NotImplementedError):
            link = None  # symlinks unavailable (e.g. Windows without privilege): skip that case
        if link is not None:
            code, out = run_script("split", str(link))
            check("fail symlink", code == 1 and out.get("ok") is False, f"{code} {out}")

    if failures:
        print(f"FAILED {len(failures)} check(s):")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("PASS all wmgt_split_blocks checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
