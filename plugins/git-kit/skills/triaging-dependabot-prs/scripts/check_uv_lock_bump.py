#!/usr/bin/env python3
"""Decide whether a uv.lock change is nothing but one package's version bump.

Used by triaging-dependabot-prs before it offers a Codex-review bypass for a
dependabot uv PR. Parses the base and head lockfiles with tomllib (a real
parser, not regexes over a diff) and passes only when exactly one [[package]]
entry was replaced and that entry:

  * is the named package, going from --old to --new (the two must differ);
  * keeps its registry source and every key other than version, sdist and
    wheels (so dependency edges and markers are unchanged);
  * lists only files.pythonhosted.org URLs whose filenames carry the package
    name and the new version, each with a sha256 hash and a size
    (upload-time is optional, and so is the sdist, but not both files at once);
  * does not lose its sdist or all of its wheels;

and nothing outside [[package]] changed. Anything else -- a new or removed
package, a second bumped package, a git/path/editable source, a URL for a
different project -- fails closed. It does not check that the version went up.

Usage: check_uv_lock_bump.py --base BASE.lock --head HEAD.lock
                             --package NAME --old VER --new VER
Prints one JSON object with an "ok" field; callers must read "ok", not only the
exit code. Exit 0 = ok, 1 = not ok, 2 = unusable input or any unexpected
failure. A usage error caught by argparse also exits 2 but prints no JSON.
"""

import argparse
import collections
import json
import re
import sys

try:
    import tomllib
except ImportError:  # Python < 3.11: fail closed rather than guess
    tomllib = None

MAX_BYTES = 20_000_000
# \Z, not $: "$" also matches before a trailing newline, which a TOML string can contain.
PKG_RE = re.compile(r"[A-Za-z0-9]([A-Za-z0-9._-]{0,98}[A-Za-z0-9])?\Z")
VER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+_-]{0,39}\Z")
REGISTRY = {"registry": "https://pypi.org/simple"}
URL_RE = re.compile(
    r"https://files\.pythonhosted\.org/packages/[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]{60}/"
    r"([A-Za-z0-9._+-]+)\Z"
)
HASH_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
SDIST_RE = re.compile(r"(?P<name>.+)-(?P<ver>[^-]+)\.(?:tar\.gz|zip)\Z")
WHEEL_RE = re.compile(r"(?P<name>[^-]+)-(?P<ver>[^-]+)(?:-[0-9][^-]*)?-[^-]+-[^-]+-[^-]+\.whl\Z")
FILE_KEYS = {"url", "hash", "size", "upload-time"}
FREE_KEYS = {"version", "sdist", "wheels"}


def norm(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def load(path):
    if (
        tomllib is None
    ):  # main() checks this too; repeated here so the parser import is known to exist
        raise ValueError("Python 3.11 or newer is required (tomllib is missing)")
    with open(path, "rb") as handle:
        data = handle.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError(f"{path} is larger than {MAX_BYTES} bytes")
    return tomllib.loads(data.decode("utf-8"))


def canon(obj):
    return json.dumps(obj, sort_keys=True)


def package_list(lock, label):
    packages = lock.get("package", [])
    if not isinstance(packages, list) or not all(isinstance(p, dict) for p in packages):
        raise ValueError(f"{label} lockfile has a malformed [[package]] list")
    return packages


def check_file_entry(entry, kind, package, new, reasons):
    if not isinstance(entry, dict):
        reasons.append(f"{kind} entry is not a table")
        return
    extra = set(entry) - FILE_KEYS
    if extra:
        reasons.append(f"{kind} entry has unexpected keys {sorted(extra)}")
    for key in ("url", "hash", "size"):
        if key not in entry:
            reasons.append(f"{kind} entry is missing {key}")
    url = entry.get("url", "")
    match = URL_RE.match(url) if isinstance(url, str) else None
    if not match:
        reasons.append(
            f"{kind} url is not a files.pythonhosted.org package path: {str(url)[:80]!r}"
        )
    else:
        filename = match.group(1)
        parsed = (SDIST_RE if kind == "sdist" else WHEEL_RE).match(filename)
        if not parsed:
            reasons.append(f"{kind} filename has an unexpected shape: {filename[:80]}")
        elif norm(parsed.group("name")) != package or parsed.group("ver") != new:
            reasons.append(f"{kind} filename is not {package} {new}: {filename[:80]}")
    if not (isinstance(entry.get("hash"), str) and HASH_RE.match(entry["hash"])):
        reasons.append(f"{kind} hash is not a lowercase sha256 digest")
    size = entry.get("size")
    if not (isinstance(size, int) and not isinstance(size, bool) and size > 0):
        reasons.append(f"{kind} size is not a positive integer")
    if "upload-time" in entry and not isinstance(entry["upload-time"], str):
        reasons.append(f"{kind} upload-time is not a string")


def classify(base, head, package, old, new):
    reasons = []
    for key in sorted((set(base) | set(head)) - {"package"}):
        if canon(base.get(key)) != canon(head.get(key)):
            reasons.append(f"top-level key {key!r} changed")
    count_base = collections.Counter(canon(p) for p in package_list(base, "base"))
    count_head = collections.Counter(canon(p) for p in package_list(head, "head"))
    removed = list((count_base - count_head).elements())
    added = list((count_head - count_base).elements())
    summary = {"wheels": 0, "sdist": False}
    if len(removed) != 1 or len(added) != 1:
        reasons.append(
            f"expected exactly one package entry replaced, found {len(removed)} removed "
            f"and {len(added)} added"
        )
        return reasons, summary
    before, after = json.loads(removed[0]), json.loads(added[0])
    if norm(str(before.get("name", ""))) != package or norm(str(after.get("name", ""))) != package:
        reasons.append("the replaced entry is not the named package")
    if before.get("version") != old:
        reasons.append(f"removed version is {before.get('version')!r}, expected {old!r}")
    if after.get("version") != new:
        reasons.append(f"added version is {after.get('version')!r}, expected {new!r}")
    for label, entry in (("removed", before), ("added", after)):
        if entry.get("source") != REGISTRY:
            reasons.append(f"{label} entry source is not the default PyPI registry")
    for key in sorted((set(before) | set(after)) - FREE_KEYS):
        if canon(before.get(key)) != canon(after.get(key)):
            reasons.append(f"entry key {key!r} changed")
    if "sdist" in before and "sdist" not in after:
        reasons.append("sdist was removed")
    if "sdist" in after:
        check_file_entry(after["sdist"], "sdist", package, new, reasons)
        summary["sdist"] = True
    wheels = after.get("wheels", [])
    if not isinstance(wheels, list):
        reasons.append("wheels is not a list")
        wheels = []
    if before.get("wheels") and not wheels:
        reasons.append("all wheels were removed")
    for wheel in wheels:
        check_file_entry(wheel, "wheel", package, new, reasons)
    summary["wheels"] = len(wheels)
    if not wheels and "sdist" not in after:
        reasons.append("the added entry lists no files")
    return reasons, summary


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check that a uv.lock change is only one package's version bump",
        add_help=False,
        allow_abbrev=False,
    )
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--old", required=True)
    parser.add_argument("--new", required=True)
    args = parser.parse_args(argv)
    result = {"ok": False, "package": args.package, "old": args.old, "new": args.new, "reasons": []}
    try:
        if tomllib is None:
            raise ValueError("Python 3.11 or newer is required (tomllib is missing)")
        if not PKG_RE.match(args.package):
            raise ValueError("package name failed validation")
        for version in (args.old, args.new):
            if not VER_RE.match(version):
                raise ValueError("version failed validation")
        if args.old == args.new:
            raise ValueError("--old and --new must differ")
        reasons, summary = classify(
            load(args.base), load(args.head), norm(args.package), args.old, args.new
        )
    except Exception as exc:  # fail closed: any surprise is unusable input, never a pass
        result["reasons"] = [f"unusable input: {type(exc).__name__}: {str(exc)[:200]}"]
        print(json.dumps(result))
        return 2
    result.update(summary)
    result["reasons"] = reasons
    result["ok"] = not reasons
    try:
        print(json.dumps(result))
    except OSError:  # e.g. stdout closed: the verdict could not be delivered, so it is not a pass
        return 2
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
