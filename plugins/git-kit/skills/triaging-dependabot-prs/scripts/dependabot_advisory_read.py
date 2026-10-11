#!/usr/bin/env python3
"""Read-only vulnerability, compatibility and newest-version lookups for triaging-dependabot-prs.

The skill recommends merge or close for a dependency bump. This script supplies facts it cannot get
from the PR itself: the known security advisories for the old, new and newest compatible version of
the dependency, whether the new version's own declared constraints fit the versions in the base
branch's lockfile, and which is the newest release that does. It has no code path that writes
anything, anywhere.

Network access is limited to a fixed list of HTTPS hosts, each with a fixed URL shape:
  - GitHub's global advisory database and a repository's latest release, through `gh api`
    (--method GET, --hostname github.com, run by absolute path with an argument list, no shell);
  - api.osv.dev, only as a fallback when GitHub lists no advisory for a version;
  - pypi.org (release list, per-version requires_python/requires_dist) and registry.npmjs.org
    (abbreviated metadata with every version's peerDependencies, and the `latest` tag).
Redirects are refused, every response is size-capped (16 MiB for release listings, 2 MiB otherwise),
and every package name and version is checked against a pattern before it is placed in a URL or
argument. Advisory, release and constraint text comes from third parties: it is cleaned of control
characters and shortened, strings over 300 characters are not parsed, and the skill treats it all
as data.

The one local file it reads is `--lock`: a `base-`/`head-` `uv.lock` or `pnpm-lock.yaml` that
dependabot_pr_read.py wrote into the system temp directory. It is opened once without following
symlinks, must be a regular file of at most 8 MiB, and only derived version numbers are printed.

Usage:
  dependabot_advisory_read.py assess --ecosystem uv|npm_and_yarn|github_actions --dep NAME
                                     --old VERSION --new VERSION [--lock PATH]
Prints one JSON object with an "ok" field. Exit 0 = done, 2 = bad arguments, 4 = a required tool
was unavailable or an unexpected internal error. A lookup that fails is reported inside the result
as "unknown", never as "safe" or "compatible". An empty advisory answer means the database lists
nothing for that exact name and version; it is not proof the version is clean, and each version's
"sources" field says which source answered. "Compatible" is a partial check, not a resolver: it
covers PyPI requires-python/requires_dist and npm peerDependencies against the lockfile, counts
what it cannot parse or decide as "unevaluated", and reports a version with no constraint touching
the lock as compatible with "checked" 0. The compatibility stage cannot cost the advisory result:
the advisories for old and new are looked up first and the stage runs under a time budget.
Network calls use the environment's proxy and CA settings, like any other tool run from this shell.
"""

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ECOSYSTEMS = {
    # branch segment: (GitHub advisory ecosystem, OSV ecosystem, name pattern)
    "uv": ("pip", "PyPI", re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")),
    "npm_and_yarn": (
        "npm",
        "npm",
        re.compile(r"(?:@[a-z0-9][a-z0-9._-]{0,99}/)?[a-z0-9][a-z0-9._~-]{0,99}"),
    ),
    "github_actions": (
        "actions",
        "GitHub Actions",
        re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}/[A-Za-z0-9][A-Za-z0-9._-]{0,99}"),
    ),
}
VERSION_RE = re.compile(r"v?[0-9][0-9A-Za-z.+_-]{0,63}")
SHA_LIKE_RE = re.compile(r"[0-9a-f]{7,40}")
HEX_LETTER_RE = re.compile(r"[a-f]")
ADVISORY_ID_RE = re.compile(r"[A-Z][A-Z0-9]*-[A-Za-z0-9-]{1,60}")
HOST = "github.com"
OSV_URL = "https://api.osv.dev/v1/query"
PYPI_URL = "https://pypi.org/pypi/{name}/json"
NPM_URL = "https://registry.npmjs.org/{name}/latest"
NPM_PACKUMENT_URL = "https://registry.npmjs.org/{name}"
NPM_ABBREVIATED = "application/vnd.npm.install-v1+json"
PYPI_VERSION_URL = "https://pypi.org/pypi/{name}/{version}/json"
DROPPED_ENV = ("GH_HOST", "GH_REPO", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")
TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
# Release listings of a busy package are large (PyPI ruff 6 MB, npm typescript 9 MB, measured).
LISTING_MAX_BYTES = 16 * 1024 * 1024
MAX_LOCK_BYTES = 8 * 1024 * 1024
WALK_BACK_CAP = 20
# The compatibility stage as a whole (listing, per-version requests, evaluation) gets this long.
COMPAT_BUDGET_SECONDS = 60
# Registry and lockfile strings are third-party; anything longer is not parsed and is counted as
# unevaluated. Parsing below that length is linear (no nested or adjacent open-ended patterns).
MAX_CONSTRAINT_CHARS = 300
LOCK_NAME_RE = re.compile(r"(?:base|head)-(uv\.lock|pnpm-lock\.yaml)")
LOCK_FOR = {"uv": "uv.lock", "npm_and_yarn": "pnpm-lock.yaml"}
PAGE_SIZE = 100
SUMMARY_LIMIT = 160
SEVERITY_RANK = {"critical": 4, "high": 3, "moderate": 2, "medium": 2, "low": 1}
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")

EXIT_OK, EXIT_USAGE, EXIT_TOOL = 0, 2, 4


class Refusal(Exception):
    """A request this script will not carry out; `code` is the exit code to use."""

    def __init__(self, message, code=EXIT_USAGE):
        super().__init__(message)
        self.code = code


class LookupFailed(Exception):
    """One lookup did not produce usable data; the caller reports it as unknown."""


def clean(text, limit=SUMMARY_LIMIT):
    """Third-party text reduced to one short printable line."""
    one_line = CONTROL_RE.sub(" ", str(text or "")).strip()
    return one_line[:limit]


def commit_like(version):
    """Whether VERSION looks like a commit hash: 40 hex characters, or 7 to 40 with a letter.

    A dot-less all-digit value such as a date-style 20240101 is a version, not a commit.
    """
    text = normalize_version(version)
    return bool(SHA_LIKE_RE.fullmatch(text)) and (
        len(text) == 40 or bool(HEX_LETTER_RE.search(text))
    )


def normalize_version(version):
    """The version without a leading `v`."""
    return version[1:] if version.startswith("v") else version


def version_key(version):
    """A comparable tuple for a plain dotted-number version, or None when it is not one."""
    match = re.fullmatch(r"[0-9]{1,9}(?:\.[0-9]{1,9}){0,15}", normalize_version(version))
    return tuple(int(p) for p in match.group(0).split(".")) if match else None


def scrubbed_env(environ):
    """The environment for gh: host and repository overrides removed, prompts off."""
    env = {k: v for k, v in environ.items() if k not in DROPPED_ENV}
    env["GH_PROMPT_DISABLED"] = "1"
    return env


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_fetch(url, body=None, accept="application/json", max_bytes=MAX_RESPONSE_BYTES):
    """One HTTPS request to a fixed host; no redirects, a size cap, JSON in and out."""
    if not url.startswith("https://"):
        raise LookupFailed("non-https url")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": accept, "User-Agent": "triaging-dependabot-prs"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read(max_bytes + 1)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise LookupFailed(type(exc).__name__) from exc
    if len(raw) > max_bytes:
        raise LookupFailed("response too large")
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise LookupFailed("response was not JSON") from exc


def gh_get(run, gh, environ, endpoint, *fields):
    """One `gh api` GET against github.com, parsed as JSON."""
    argv = [gh, "api", "--hostname", HOST, "--method", "GET", endpoint]
    for field in fields:
        argv += ["-f", field]
    try:
        done = run(
            argv,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            check=False,
            env=scrubbed_env(environ),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise LookupFailed(type(exc).__name__) from exc
    if done.returncode != 0 or len(done.stdout) > MAX_RESPONSE_BYTES:
        raise LookupFailed("gh api failed")
    try:
        return json.loads(done.stdout)
    except ValueError as exc:
        raise LookupFailed("gh api returned non-JSON") from exc


def _fixed_versions(events_owner):
    fixed = []
    for rng in events_owner.get("ranges") or []:
        for event in rng.get("events") or []:
            if isinstance(event, dict) and event.get("fixed"):
                value = clean(event["fixed"], 64)
                if VERSION_RE.fullmatch(value):
                    fixed.append(value)
    return fixed


def safe_id(value):
    """An advisory identifier of the usual PREFIX-... shape, or an empty string."""
    text = clean(value, 70)
    return text if ADVISORY_ID_RE.fullmatch(text) else ""


def github_advisories(run, gh, environ, eco, name, version):
    """Advisories GitHub lists as affecting NAME at VERSION (withdrawn ones dropped), and whether
    the first page was full (more may exist)."""
    gh_eco = ECOSYSTEMS[eco][0]
    data = gh_get(
        run,
        gh,
        environ,
        "advisories",
        f"ecosystem={gh_eco}",
        f"affects={name}@{normalize_version(version)}",
        f"per_page={PAGE_SIZE}",
    )
    if not isinstance(data, list):
        raise LookupFailed("unexpected advisory shape")
    found = []
    for item in data:
        if not isinstance(item, dict) or item.get("withdrawn_at"):
            continue
        fixed = []
        for vuln in item.get("vulnerabilities") or []:
            vuln = vuln if isinstance(vuln, dict) else {}
            raw_package = vuln.get("package")
            package = raw_package if isinstance(raw_package, dict) else {}
            patched = vuln.get("first_patched_version")
            patched = clean(patched, 64) if patched else ""
            if (
                VERSION_RE.fullmatch(patched)
                and str(package.get("name", "")).lower() == name.lower()
            ):
                fixed.append(patched)
        found.append(
            {
                "id": safe_id(item.get("ghsa_id")),
                "severity": clean(item.get("severity"), 16).lower() or "unknown",
                "summary": clean(item.get("summary")),
                "fixed_in": fixed,
                "source": "github",
            }
        )
    return found, len(data) >= PAGE_SIZE


def osv_advisories(fetch, eco, name, version):
    """Advisories OSV lists for NAME at VERSION (withdrawn ones dropped)."""
    body = {
        "package": {"name": name, "ecosystem": ECOSYSTEMS[eco][1]},
        "version": normalize_version(version),
    }
    data = fetch(OSV_URL, body)
    if not isinstance(data, dict):
        raise LookupFailed("unexpected osv shape")
    found = []
    for item in data.get("vulns") or []:
        if not isinstance(item, dict) or item.get("withdrawn"):
            continue
        fixed = []
        for affected in item.get("affected") or []:
            fixed += _fixed_versions(affected if isinstance(affected, dict) else {})
        severity = (item.get("database_specific") or {}).get("severity")
        found.append(
            {
                "id": safe_id(item.get("id")),
                "severity": clean(severity, 16).lower() or "unknown",
                "summary": clean(item.get("summary")),
                "fixed_in": fixed,
                "source": "osv",
            }
        )
    return found


def advisories_for(run, gh, environ, fetch, eco, name, version):
    """GitHub first, OSV only when GitHub lists none; `status` says what could be established.

    A version is "ok" (possibly with no advisories) only when a source that answered covers the
    question: GitHub answered, or GitHub failed and OSV answered. Both failing is "unknown", and so
    is a version that looks like a commit SHA, which neither database can match. `sources` records
    what each source did, so an empty "ok" is never mistaken for a confirmed-clean version.
    """
    if commit_like(version):
        return {
            "status": "unknown",
            "advisories": [],
            "sources": {},
            "reason": "commit-like version",
        }
    sources = {"github": "failed", "osv": "not_queried"}
    truncated = False
    try:
        found, truncated = github_advisories(run, gh, environ, eco, name, version)
        sources["github"] = "hit" if found else "empty"
        if found:
            return {"status": "ok", "advisories": found, "sources": sources, "truncated": truncated}
    except (LookupFailed, AttributeError, TypeError):
        pass
    try:
        found = osv_advisories(fetch, eco, name, version)
        sources["osv"] = "hit" if found else "empty"
        return {"status": "ok", "advisories": found, "sources": sources, "truncated": truncated}
    except (LookupFailed, AttributeError, TypeError):
        sources["osv"] = "failed"
    # OSV failed. An empty GitHub answer still stands; a failed one leaves nothing to stand on.
    status = "unknown" if sources["github"] == "failed" else "ok"
    return {"status": status, "advisories": [], "sources": sources, "truncated": truncated}


def cached(cache, key, make):
    """Call `make()` once per key per run; a failure is cached too, so it is not retried."""
    if key not in cache:
        try:
            cache[key] = ("ok", make())
        except (LookupFailed, AttributeError, TypeError) as exc:
            cache[key] = ("failed", exc)
    state, value = cache[key]
    if state == "failed":
        raise LookupFailed(str(value))
    return value


def pypi_document(fetch, cache, name):
    """PyPI's JSON for NAME: info plus every release's files (large for busy packages)."""
    return cached(
        cache,
        ("pypi", name),
        lambda: fetch(PYPI_URL.format(name=name), max_bytes=LISTING_MAX_BYTES),
    )


def npm_packument(fetch, cache, name):
    """npm's abbreviated metadata for NAME: every version with its peerDependencies."""
    url = NPM_PACKUMENT_URL.format(name=name.replace("/", "%2F"))
    return cached(
        cache,
        ("npm", name),
        lambda: fetch(url, accept=NPM_ABBREVIATED, max_bytes=LISTING_MAX_BYTES),
    )


def latest_version(run, gh, environ, fetch, eco, name, cache=None):
    """The newest release of NAME, or None when it cannot be established."""
    cache = {} if cache is None else cache
    try:
        if eco == "uv":
            data = pypi_document(fetch, cache, name)
            value = (data.get("info") or {}).get("version")
        elif eco == "npm_and_yarn":
            data = fetch(NPM_URL.format(name=name.replace("/", "%2F")))
            value = data.get("version")
        else:
            data = gh_get(run, gh, environ, f"repos/{name}/releases/latest")
            value = data.get("tag_name")
    except (LookupFailed, AttributeError):
        return None
    value = clean(value, 64)
    return value if VERSION_RE.fullmatch(value) else None


# --- compatibility: does a version's own declared constraints fit the versions in our lockfile? ---
# Everything below is three-valued: True, False, or None ("could not tell"). None is never read as
# compatible; it is counted as "unevaluated" and shown to the user.


def pad(release, size):
    """RELEASE (a tuple of ints) zero-padded or cut to SIZE segments."""
    return (tuple(release) + (0,) * size)[:size]


def cmp_release(a, b):
    """-1, 0 or 1 comparing two release tuples with missing segments counted as zero."""
    size = max(len(a), len(b))
    a, b = pad(a, size), pad(b, size)
    return (a > b) - (a < b)


PEP440_CLAUSE_RE = re.compile(r"(~=|==|!=|<=|>=|<|>)\s*([0-9][0-9.]*?)(\.\*)?")


def _pep440_clause(op, have, want, star):
    if star:
        if op not in ("==", "!="):
            return None
        same = pad(have, len(want)) == tuple(want)
        return same if op == "==" else not same
    order = cmp_release(have, want)
    if op == "~=":
        if len(want) < 2:
            return None
        return order >= 0 and pad(have, len(want) - 1) == tuple(want[:-1])
    return {
        "==": order == 0,
        "!=": order != 0,
        ">=": order >= 0,
        "<=": order <= 0,
        ">": order > 0,
        "<": order < 0,
    }[op]


def pep440_satisfies(version, spec):
    """Whether a plain-release VERSION meets the PEP 440 specifier SPEC (True/False/None)."""
    have = version_key(version)
    if have is None or len(spec) > MAX_CONSTRAINT_CHARS:
        return None
    results = []
    for clause in spec.split(","):
        clause = clause.strip()
        if not clause:
            continue
        match = PEP440_CLAUSE_RE.fullmatch(clause)
        want = version_key(match.group(2)) if match else None
        if match is None or want is None:
            results.append(None)
        else:
            results.append(_pep440_clause(match.group(1), have, want, bool(match.group(3))))
    if any(r is False for r in results):
        return False
    return True if results and all(r is True for r in results) else None


NPM_TOKEN_RE = re.compile(r"(>=|<=|>|<|=|\^|~)?v?([0-9xX*]{1,9}(?:\.[0-9xX*]{1,9}){0,2})")


def _npm_token(have, token):
    match = NPM_TOKEN_RE.fullmatch(token)
    if not match:
        return None
    op, text = match.group(1) or "=", match.group(2)
    nums = []
    for part in text.split("."):
        if part in ("x", "X", "*"):
            break
        nums.append(int(part))
    count = len(nums)
    if count == 0:
        return True if op == "=" else None
    low = pad(nums, 3)
    mid = {1: (nums[0] + 1, 0, 0), 2: (nums[0], nums[1] + 1, 0) if count > 1 else None}.get(count)
    upper = mid if count < 3 else (low[0], low[1], low[2] + 1)
    if op == "=":
        return cmp_release(have, low) >= 0 and cmp_release(have, upper) < 0
    if op == ">=":
        return cmp_release(have, low) >= 0
    if op == "<":
        return cmp_release(have, low) < 0
    if op == ">":
        return cmp_release(have, upper) >= 0
    if op == "<=":
        return cmp_release(have, upper) < 0
    if op == "~":
        return (
            cmp_release(have, low) >= 0
            and cmp_release(have, upper if count < 3 else (low[0], low[1] + 1, 0)) < 0
        )
    # caret
    if low[0] > 0 or count == 1:
        ceiling = (low[0] + 1, 0, 0)
    elif low[1] > 0 or count == 2:
        ceiling = (0, low[1] + 1, 0)
    else:
        ceiling = (0, 0, low[2] + 1)
    return cmp_release(have, low) >= 0 and cmp_release(have, ceiling) < 0


def _npm_alternative(have, alternative):
    alternative = re.sub(r"(>=|<=|>|<|=|\^|~)\s+", r"\1", alternative.strip())
    if " - " in alternative:
        low, _, high = alternative.partition(" - ")
        lo, hi = version_key(low), version_key(high)
        if lo is None or hi is None or len(lo) != 3 or len(hi) != 3:
            return None
        return cmp_release(have, lo) >= 0 and cmp_release(have, hi) <= 0
    results = [_npm_token(have, token) for token in alternative.split()]
    if any(r is False for r in results):
        return False
    return None if any(r is None for r in results) else True


def npm_satisfies(version, node_range):
    """Whether a plain-release VERSION meets the npm semver range (True/False/None)."""
    have = version_key(version)
    if have is None or len(node_range) > MAX_CONSTRAINT_CHARS:
        return None
    node_range = node_range.strip()
    if node_range in ("", "*", "x", "X", "latest"):
        return True
    results = [_npm_alternative(have, alt) for alt in node_range.split("||")]
    if any(r is True for r in results):
        return True
    return False if all(r is False for r in results) else None


def python_name(name):
    """PEP 503 normalized project name."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_uv_lock(text):
    """{'versions': {name: [versions]}, 'requires_python': str|None} from a uv.lock."""
    try:
        import tomllib
    except ImportError as exc:
        raise LookupFailed("tomllib is not available") from exc
    try:
        data = tomllib.loads(text)
    except ValueError as exc:
        raise LookupFailed("uv.lock is not valid TOML") from exc
    versions = {}
    for package in data.get("package") or []:
        if isinstance(package, dict) and isinstance(package.get("name"), str):
            if isinstance(package.get("version"), str):
                versions.setdefault(python_name(package["name"]), []).append(package["version"])
    requires = data.get("requires-python")
    return {
        "versions": versions,
        "requires_python": requires if isinstance(requires, str) else None,
    }


# A packages: key, optionally with a peer-resolution suffix `(react@18.2.0)(...)` after the version.
PNPM_KEY_RE = re.compile(
    r"  '?/?(@?[^@'\s/]+(?:/[^@'\s/]+)?)@([0-9][^'\s:()]*)(?:\([^'\s:]*)?'?:\s*"
)
PNPM_LOCKFILE_RE = re.compile(r"""lockfileVersion:\s*['"]?([0-9]+)""")
PNPM_SUPPORTED_MAJORS = ("6", "9")  # pnpm 8 writes 6.x, pnpm 9 and 10 write 9.x


def parse_pnpm_lock(text):
    """{'versions': {name: [versions]}, 'requires_python': None} from a pnpm-lock.yaml."""
    versions, inside = {}, False
    declared = PNPM_LOCKFILE_RE.search(text[:2000])
    if not declared or declared.group(1) not in PNPM_SUPPORTED_MAJORS:
        raise LookupFailed("unsupported or missing pnpm lockfileVersion")
    for line in text.splitlines():
        if line.startswith("packages:"):
            inside = True
        elif line and not line.startswith(" "):
            inside = False
        elif inside and len(line) <= MAX_CONSTRAINT_CHARS:
            match = PNPM_KEY_RE.fullmatch(line)
            if match and match.group(2) not in versions.setdefault(match.group(1), []):
                versions[match.group(1)].append(match.group(2))
    if not versions:
        raise LookupFailed("no packages found in the pnpm lockfile")
    return {"versions": versions, "requires_python": None}


def load_lock(path, eco):
    """Parse the lockfile at PATH (a file the read script wrote into the temp dir), or None."""
    if path is None:
        return None
    match = LOCK_NAME_RE.fullmatch(os.path.basename(path))
    if not match or LOCK_FOR.get(eco) != match.group(1):
        raise Refusal("--lock must be base-/head- uv.lock or pnpm-lock.yaml matching the ecosystem")
    temp_root = os.path.realpath(tempfile.gettempdir())
    try:
        inside = (
            os.path.isabs(path)
            and os.path.commonpath([os.path.realpath(path), temp_root]) == temp_root
        )
    except ValueError:
        inside = False
    if not inside:
        raise Refusal("--lock must be an absolute path inside the system temp directory")
    if os.path.islink(path):  # O_NOFOLLOW is missing on Windows, so refuse a symlink here as well
        raise Refusal("--lock must be a readable regular file, not a symlink")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise Refusal("--lock must be a readable regular file, not a symlink") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_LOCK_BYTES:
            raise Refusal("--lock must be a regular file of at most 8 MiB")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            raw = handle.read(MAX_LOCK_BYTES + 1)
    except OSError:
        return None
    finally:
        os.close(fd)
    try:
        text = raw.decode("utf-8")
        return parse_uv_lock(text) if eco == "uv" else parse_pnpm_lock(text)
    except (UnicodeDecodeError, LookupFailed):
        return None


REQUIREMENT_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
EXTRA_MARKER_RE = re.compile(r"extra\s*==\s*['\"][^'\"]*['\"]")
PYTHON_MARKER_RE = re.compile(r"python_version\s*(<=|>=|<|>)\s*['\"]([0-9]+\.[0-9]+)['\"]")


def parse_requirement(raw):
    """(name, specifier, marker) from a PEP 508 string, or None. Linear: no backtracking regex."""
    head, separator, marker = raw.partition(";")
    head = head.strip()
    match = REQUIREMENT_NAME_RE.match(head)
    if not match:
        return None
    rest = head[match.end() :].strip()
    if rest.startswith("["):
        close = rest.find("]")
        if close < 0:
            return None
        rest = rest[close + 1 :].strip()
    if rest.startswith("("):
        if not rest.endswith(")"):
            return None
        rest = rest[1:-1].strip()
    if rest and rest[0] not in "<>=!~":
        return None
    return match.group(0), rest, (marker.strip() if separator else None)


def minimum_python(requires_python):
    """The lowest Python the project supports, from a `>=X.Y` requires-python, or None."""
    text = requires_python if isinstance(requires_python, str) else ""
    match = re.search(r">=\s*([0-9]+(?:\.[0-9]+)*)", text[:MAX_CONSTRAINT_CHARS])
    return version_key(match.group(1)) if match else None


def marker_applies(marker, min_python):
    """Whether a requirement's environment marker holds for every Python we support."""
    if marker is None:
        return True
    marker = marker.strip()
    if len(marker) > MAX_CONSTRAINT_CHARS:
        return None
    if EXTRA_MARKER_RE.fullmatch(marker):
        return False  # an optional extra is installed only when asked for
    match = PYTHON_MARKER_RE.fullmatch(marker)
    if not match or min_python is None:
        return None
    op, bound = match.group(1), version_key(match.group(2))
    order = cmp_release(pad(min_python, 2), bound)
    if op == "<":
        return False if order >= 0 else None
    if op == "<=":
        return False if order > 0 else None
    if op == ">=":
        return True if order >= 0 else None
    return True if order > 0 else None


def _judge(requirement, dependency, locked, results, verdict):
    """Fold one requirement's per-locked-version results into the running verdict.

    With several locked copies we do not know which one the candidate would use, so one satisfying
    copy cannot prove compatibility: a mix of satisfied and violated is ambiguous, not a pass.
    """
    if all(r is True for r in results):
        verdict["checked"] += 1
    elif any(r is True for r in results) and any(r is False for r in results):
        verdict["ambiguous"] += 1
    elif any(r is True for r in results):
        verdict["unevaluated"] += 1
    elif all(r is False for r in results):
        verdict["checked"] += 1
        verdict["violations"].append(
            {
                "kind": "dependency",
                "dependency": clean(dependency, 60),
                "requirement": clean(requirement, 80),
                "locked": [clean(v, 32) for v in locked[:3]],
            }
        )
    else:
        verdict["unevaluated"] += 1


def check_pypi(meta, lock):
    """Check a PyPI version's requires-python and requires-dist against the uv.lock versions."""
    verdict = {"violations": [], "checked": 0, "unevaluated": 0, "ambiguous": 0}
    min_python = minimum_python(lock["requires_python"])
    requires_python = meta.get("requires_python")
    if isinstance(requires_python, str) and requires_python.strip() and not min_python:
        verdict["unevaluated"] += (
            1  # the project's lowest Python is unknown, so nothing to compare to
        )
    elif isinstance(requires_python, str) and requires_python.strip():
        fits = pep440_satisfies(".".join(str(n) for n in min_python), requires_python)
        if fits is False:
            verdict["checked"] += 1
            verdict["violations"].append(
                {
                    "kind": "requires-python",
                    "requirement": clean(requires_python, 80),
                    "locked": [clean(lock["requires_python"], 32)],
                }
            )
        elif fits is None:
            verdict["unevaluated"] += 1
        else:
            verdict["checked"] += 1
    for raw in (meta.get("requires_dist") or [])[:500]:
        short = isinstance(raw, str) and len(raw) <= MAX_CONSTRAINT_CHARS
        parsed = parse_requirement(raw) if short else None
        if not parsed:
            verdict["unevaluated"] += 1
            continue
        dependency, spec, marker = parsed
        applies = marker_applies(marker, min_python)
        if applies is False:
            continue
        if applies is None:
            verdict["unevaluated"] += 1
            continue
        locked = lock["versions"].get(python_name(dependency))
        if locked and spec:
            _judge(spec, dependency, locked, [pep440_satisfies(v, spec) for v in locked], verdict)
    return verdict


def check_npm(meta, lock):
    """Check an npm version's peerDependencies against the pnpm-lock.yaml versions."""
    verdict = {"violations": [], "checked": 0, "unevaluated": 0, "ambiguous": 0}
    for dependency, wanted in list((meta.get("peerDependencies") or {}).items())[:500]:
        locked = lock["versions"].get(dependency)
        if not locked or not isinstance(wanted, str):
            continue
        _judge(wanted, dependency, locked, [npm_satisfies(v, wanted) for v in locked], verdict)
    # `engines` needs the Node version we run on, which is not known here. It is outside the lockfile
    # check, so it is reported on its own and does not turn a version with no peer conflict unknown.
    verdict["engines_not_checked"] = bool(meta.get("engines"))
    return verdict


def version_meta(fetch, cache, eco, name, version):
    """The declared constraints of one registry version."""
    if eco == "uv":
        url = PYPI_VERSION_URL.format(name=name, version=version)
        info = cached(cache, ("pypi-version", name, version), lambda: fetch(url)).get("info")
        if not isinstance(info, dict):
            raise LookupFailed("no info in the registry answer")
        return {
            "requires_python": info.get("requires_python"),
            "requires_dist": info.get("requires_dist")
            if isinstance(info.get("requires_dist"), list)
            else [],
        }
    versions = npm_packument(fetch, cache, name).get("versions")
    entry = versions.get(version) if isinstance(versions, dict) else None
    if not isinstance(entry, dict):
        raise LookupFailed("version not in the registry metadata")
    return {
        key: entry.get(key) if isinstance(entry.get(key), dict) else {}
        for key in ("peerDependencies", "peerDependenciesMeta", "engines")
    }


def compatibility(fetch, cache, eco, name, version, lock):
    """Whether VERSION's declared constraints fit the lockfile: status compatible/incompatible/unknown."""
    if eco not in LOCK_FOR:
        return {"status": "unknown", "reason": "no dependency metadata for this ecosystem"}
    if lock is None:
        return {"status": "unknown", "reason": "no readable lockfile was given"}
    try:
        meta = version_meta(fetch, cache, eco, name, version)
        verdict = (check_pypi if eco == "uv" else check_npm)(meta, lock)
    except (LookupFailed, AttributeError, TypeError, ValueError):
        return {"status": "unknown", "reason": "the registry metadata could not be read"}
    if verdict["violations"]:
        return {"status": "incompatible", **verdict}
    if verdict["ambiguous"]:
        return {
            "status": "unknown",
            "reason": "a dependency is locked at several versions and only some satisfy the constraint",
            **verdict,
        }
    if verdict["checked"] == 0 and verdict["unevaluated"] > 0:
        return {
            "status": "unknown",
            "reason": "no declared constraint could be evaluated",
            **verdict,
        }
    return {"status": "compatible", **verdict}


def stable_releases(fetch, cache, eco, name):
    """Plain-number releases of NAME, newest first (yanked and deprecated ones left out)."""
    if eco == "uv":
        releases = pypi_document(fetch, cache, name).get("releases")
        if not isinstance(releases, dict):
            raise LookupFailed("no release list in the registry answer")
        names = [
            v
            for v, files in releases.items()
            if isinstance(files, list)
            and files
            and not all(isinstance(f, dict) and f.get("yanked") for f in files)
        ]
    else:
        versions = npm_packument(fetch, cache, name).get("versions")
        if not isinstance(versions, dict):
            raise LookupFailed("no version list in the registry answer")
        names = [
            v
            for v, entry in versions.items()
            if isinstance(entry, dict) and not entry.get("deprecated")
        ]
    plain = [v for v in names if re.fullmatch(r"[0-9.]{1,64}", v) and version_key(v) is not None]
    return sorted(plain, key=version_key, reverse=True)


def newest_compatible(fetch, cache, eco, name, new, new_compat, lock, deadline=None):
    """Walk the releases newer than NEW, newest first, to the first one that fits the lockfile.

    `version` is the newest compatible version, or None when that cannot be established: no
    lockfile, an unreadable listing, a version whose metadata could not be read (it might be the
    compatible one), or more than WALK_BACK_CAP newer releases with none compatible.
    """
    if eco not in LOCK_FOR or lock is None:
        return {"status": "unknown", "version": None, "newer_incompatible": []}
    new_key = version_key(new)
    try:
        newer = [
            v
            for v in stable_releases(fetch, cache, eco, name)
            if new_key and cmp_release(version_key(v), new_key) > 0
        ]
    except (LookupFailed, AttributeError, TypeError, ValueError):
        return {"status": "unknown", "version": None, "newer_incompatible": []}
    incompatible = []
    for version in newer[:WALK_BACK_CAP]:
        if deadline is not None and time.monotonic() > deadline:
            return {"status": "unknown", "version": None, "newer_incompatible": incompatible[:3]}
        result = compatibility(fetch, cache, eco, name, version, lock)
        if result["status"] == "unknown":
            return {"status": "unknown", "version": None, "newer_incompatible": incompatible[:3]}
        if result["status"] == "compatible":
            return {"status": "found", "version": version, "newer_incompatible": incompatible[:3]}
        incompatible.append({"version": version, "violations": result["violations"][:2]})
    if len(newer) > WALK_BACK_CAP:
        return {"status": "unknown", "version": None, "newer_incompatible": incompatible[:3]}
    if new_compat == "compatible":
        return {"status": "found", "version": new, "newer_incompatible": incompatible[:3]}
    return {
        "status": "none" if new_compat == "incompatible" else "unknown",
        "version": None,
        "newer_incompatible": incompatible[:3],
    }


def risk(result):
    """Sort key for how risky a version is: worst severity first, then how many advisories."""
    items = result["advisories"]
    worst = max((SEVERITY_RANK.get(a["severity"], 0) for a in items), default=0)
    return (worst, len(items))


def assess(run, gh, environ, fetch, eco, name, old, new, lock=None):
    """Advisories for old, new and the newest compatible version, plus the signals the rules need.

    The advisory lookups for old and new run first and the compatibility stage is contained, so a
    failure or a hostile registry answer there can cost the compatibility answer but never the
    advisory result.
    """
    cache = {}
    new_key = version_key(new)
    out = {"dependency": name, "ecosystem": eco, "versions": {}}
    for role, version in (("old", old), ("new", new)):
        out["versions"][role] = {
            "version": version,
            **advisories_for(run, gh, environ, fetch, eco, name, version),
        }
    try:
        out["latest"] = latest_version(run, gh, environ, fetch, eco, name, cache)
    except Exception:  # noqa: BLE001 - nothing about "latest" may cost the advisory result
        out["latest"] = None
    unknown = {"status": "unknown", "version": None, "newer_incompatible": []}
    try:
        deadline = time.monotonic() + COMPAT_BUDGET_SECONDS
        compat = compatibility(fetch, cache, eco, name, new, lock)
        newest = newest_compatible(fetch, cache, eco, name, new, compat["status"], lock, deadline)
    except Exception:  # noqa: BLE001 - same containment for the whole compatibility stage
        compat = {"status": "unknown", "reason": "the compatibility check failed"}
        newest = unknown
    out["compatibility"] = compat
    out["newest_compatible"] = newest
    target = newest["version"]
    if target and (new_key is None or version_key(target) != new_key):
        out["versions"]["newest_compatible"] = {
            "version": target,
            **advisories_for(run, gh, environ, fetch, eco, name, target),
        }
    latest = out["latest"]
    v = out["versions"]
    known = {role: info["status"] == "ok" for role, info in v.items()}
    latest_key = version_key(latest) if latest else None
    if target is None or new_key is None or version_key(target) is None:
        new_is_newest_compatible = None
    else:
        new_is_newest_compatible = cmp_release(new_key, version_key(target)) >= 0
    out["signals"] = {
        "new_vulnerable_not_safer_than_old": (
            bool(v["new"]["advisories"]) and risk(v["new"]) >= risk(v["old"])
            if known["new"] and known["old"]
            else None
        ),
        "new_compatible": {"compatible": True, "incompatible": False}.get(compat["status"]),
        "new_is_newest_compatible": new_is_newest_compatible,
        "new_safer_than_newest_compatible": (
            risk(v["new"]) < risk(v["newest_compatible"])
            if known["new"] and known.get("newest_compatible")
            else None
        ),
        "new_is_latest": (
            None if new_key is None or latest_key is None else cmp_release(new_key, latest_key) >= 0
        ),
    }
    return out


def parse_args(argv):
    """Parse the command line; argparse's own errors exit 2 with no JSON, as documented."""
    parser = argparse.ArgumentParser(description="Read-only advisory and version lookups.")
    sub = parser.add_subparsers(dest="kind", required=True)
    one = sub.add_parser("assess")
    one.add_argument("--ecosystem", required=True, choices=sorted(ECOSYSTEMS))
    one.add_argument("--dep", required=True)
    one.add_argument("--old", required=True)
    one.add_argument("--new", required=True)
    one.add_argument(
        "--lock", help="base-uv.lock or base-pnpm-lock.yaml written by dependabot_pr_read.py"
    )
    return parser.parse_args(argv)


def main(argv=None, run=subprocess.run, which=shutil.which, fetch=http_fetch, environ=None):
    """Validate, look the data up, and print one JSON object."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = {"ok": False, "kind": args.kind}
    try:
        if not ECOSYSTEMS[args.ecosystem][2].fullmatch(args.dep):
            raise Refusal("--dep does not look like a package name for this ecosystem")
        for flag in ("old", "new"):
            if not VERSION_RE.fullmatch(getattr(args, flag)):
                raise Refusal(f"--{flag} does not look like a version")
        gh = which("gh")
        if not gh or not os.path.isabs(gh):
            raise Refusal("gh was not found on PATH", EXIT_TOOL)
        result.update(
            assess(
                run,
                gh,
                os.environ if environ is None else environ,
                fetch,
                args.ecosystem,
                args.dep,
                args.old,
                args.new,
                load_lock(args.lock, args.ecosystem),
            )
        )
        result["ok"] = True
        code = EXIT_OK
    except Refusal as exc:
        result["refused"] = str(exc)
        code = exc.code
    except Exception as exc:  # noqa: BLE001 - always print JSON, never a bare traceback
        result["refused"] = f"internal error ({type(exc).__name__})"
        code = EXIT_TOOL
    print(json.dumps(result))
    return code


if __name__ == "__main__":
    sys.exit(main())
