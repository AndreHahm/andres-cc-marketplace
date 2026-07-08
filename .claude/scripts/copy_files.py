#!/usr/bin/env python3
"""Safely copy or move a file or directory from src to dst inside the repo.

Handles both files and directories:
  - File src: copies with shutil.copy2 (preserves metadata).
  - Directory src: copies recursively with shutil.copytree. No --recursive flag needed.

Exit codes:
  0  — success (all copied or moved)
  1  — skipped (destination already exists and --overwrite not set; or some skips in manifest mode)
  2  — error (source missing or I/O failure)
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def copy_one(src: Path, dst: Path, overwrite: bool, move: bool, dry_run: bool) -> int:
    if not src.exists():
        print(f"ERROR: source not found: {src}", file=sys.stderr)
        return 2

    if dst.exists() and not overwrite:
        print(f"SKIP: destination already exists: {dst}")
        return 1

    if dry_run:
        action = "MOVE" if move else "COPY"
        suffix = " (overwrite)" if dst.exists() else ""
        print(f"[dry-run] {action}{suffix}: {src} -> {dst}")
        return 0

    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        if src.is_dir():
            if dst.exists() and overwrite:
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: copy failed: {exc}", file=sys.stderr)
        return 2

    if move:
        try:
            if src.is_dir():
                shutil.rmtree(src)
            else:
                src.unlink()
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: source cleanup failed after copy: {exc}", file=sys.stderr)
            return 2
        print(f"MOVED: {src} -> {dst}")
    else:
        print(f"COPIED: {src} -> {dst}")

    return 0


def main() -> int:
    desc = "Safely copy (or move) a file or directory. Skips existing destinations by default."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("src", nargs="?", help="Source file or directory (omit when using --manifest)")
    parser.add_argument("dst", nargs="?", help="Destination file or directory (omit when using --manifest)")
    parser.add_argument(
        "--manifest", metavar="FILE",
        help="Path to a manifest file with one 'src -> dst' or 'src\\tdst' pair per line",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite destination if it exists"
    )
    parser.add_argument(
        "--move", action="store_true", help="Delete source after successful copy"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print actions without writing anything"
    )
    args = parser.parse_args()

    if args.manifest:
        manifest_path = Path(args.manifest)
        if not manifest_path.exists():
            print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
            return 2
        pairs: list[tuple[Path, Path]] = []
        for lineno, raw in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if " -> " in line:
                parts = line.split(" -> ", 1)
            elif "\t" in line:
                parts = line.split("\t", 1)
            else:
                print(
                    f"ERROR: manifest line {lineno} is not a valid 'src -> dst' or 'src\\tdst' pair: {raw!r}",
                    file=sys.stderr,
                )
                return 2
            pairs.append((Path(parts[0].strip()), Path(parts[1].strip())))

        worst = 0
        for src, dst in pairs:
            code = copy_one(src, dst, args.overwrite, args.move, args.dry_run)
            if code > worst:
                worst = code
        return worst

    if args.src is None or args.dst is None:
        parser.error("src and dst are required when --manifest is not used")

    return copy_one(Path(args.src), Path(args.dst), args.overwrite, args.move, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
