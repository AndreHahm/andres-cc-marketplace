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
    """Run the script with ``args``; return (exit code, parsed JSON or a non-JSON sentinel).

    A run that exceeds 30 seconds is reported as exit code -1, so a hang fails instead of
    freezing the test.
    """
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return -1, {"_timeout": True}
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

        # 6b. The 2,000 boundary: exactly 2,000 units is one block, 2,001 is two, lossless.
        code, out = all_blocks(write("edge2000.md", "a" * 2000))
        check("edge 2000 one block", out.get("total") == 1, str(out.get("total")))
        code, out = all_blocks(write("edge2001.md", "a" * 2001))
        edge_blocks = out.get("blocks", [])
        check("edge 2001 two blocks", out.get("total") == 2, str(out.get("total")))
        check("edge 2001 lossless", "".join(edge_blocks) == "a" * 2001, "content differs")

        # 6c. A surrogate pair that would straddle a cut: an odd limit with one leading unit
        # puts the pair boundary at the limit, and 1,999 units plus an emoji does the same at
        # the default limit. Cuts must land before the pair, never inside it.
        straddle = "a" + "\U0001f600" * 400  # 801 UTF-16 units, odd limit 301 straddles
        code, out = all_blocks(write("straddle.md", straddle), "--max", "301")
        blocks = out.get("blocks", [])
        check("straddle exit", code == 0, str(out))
        check("straddle within limit", all(utf16_units(b) <= 301 for b in blocks), "block over 301")
        check("straddle lossless", "".join(blocks) == straddle, "content differs")
        edge_pair = "a" * 1999 + "\U0001f600"  # 2,001 units: the emoji cannot fit in the block
        code, out = all_blocks(write("edgepair.md", edge_pair))
        blocks = out.get("blocks", [])
        check("edge pair within limit", all(utf16_units(b) <= 2000 for b in blocks), "over 2000")
        check("edge pair lossless", "".join(blocks) == edge_pair, "content differs")

        # 6d. A line break is preferred over a later space: newline at 1500, space at 1990.
        prio = "a" * 1500 + "\n" + "b" * 489 + " " + "c" * 300
        code, out = all_blocks(write("prio.md", prio))
        blocks = out.get("blocks", [])
        check("priority first block", blocks[:1] == ["a" * 1500], str([len(b) for b in blocks]))

        # 6e. CRLF input splits into paragraphs and no carriage return survives.
        crlf = ("p" * 1500) + "\r\n\r\n" + ("q" * 1500)
        code, out = all_blocks(write("crlf.md", crlf))
        blocks = out.get("blocks", [])
        check("crlf blocks", blocks == ["p" * 1500, "q" * 1500], str([len(b) for b in blocks]))
        check("crlf no CR", not any("\r" in b for b in blocks), "carriage return left")

        # 6f. Paging: the default --count is 10, and a start past the end is empty but ok.
        many = "\n\n".join("m" * 1500 for _ in range(15))
        code, out = run_script("split", str(write("many.md", many)))
        check("default count", out.get("count") == 10 and out.get("total") == 15, str(out))
        code, out = run_script("split", str(tmp / "many.md"), "--start", "999")
        check(
            "page past end",
            code == 0 and out.get("count") == 0 and out.get("blocks") == [] and out.get("ok"),
            str(out),
        )

        # 6g. A very large single paragraph finishes promptly and keeps every word.
        word_list = ["word"] * 200_000  # ~1 MB with no blank line
        code, out = all_blocks(write("huge.md", " ".join(word_list)))
        blocks = out.get("blocks", [])
        check("huge exit", code == 0, str(out)[:200])
        check("huge keeps words", " ".join(blocks).split() == word_list, "words lost or cut")

        # 7. Typed failures.
        for name, args in {
            "max too large": ("split", str(tmp / "short.md"), "--max", "2001"),
            "max zero": ("split", str(tmp / "short.md"), "--max", "0"),
            "max one": ("split", str(tmp / "short.md"), "--max", "1"),
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

        code, out = run_script("split", str(write("zero.md", "")))
        check("fail zero-byte", code == 1 and out.get("ok") is False, f"{code} {out}")

        code, out = run_script("split", str(tmp / "short.md"), "--count", "0")
        check("fail count zero", code == 1 and out.get("ok") is False, f"{code} {out}")

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
