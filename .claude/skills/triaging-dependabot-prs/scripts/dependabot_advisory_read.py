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

The only local files it reads are `--lock` and `--head-lock`: a `base-`/`head-` `uv.lock` or
`pnpm-lock.yaml` that dependabot_pr_read.py wrote into the system temp directory. Each is opened
once without following symlinks, must be a regular file of at most 8 MiB, and only derived package
names and version numbers are printed. With `--head-lock` (which needs a `base-` `--lock`), the
name and version pairs the head lockfile has and the base does not are looked up for advisories too
(at most 20, within a 60-second budget), as `added_packages`.

Usage:
  dependabot_advisory_read.py assess --ecosystem uv|npm_and_yarn|github_actions --dep NAME
                                     --old VERSION --new VERSION [--lock PATH [--head-lock PATH]]
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
# An optional PEP 440 epoch (`1!2.0`) may lead the version; `!` is allowed nowhere else.
VERSION_RE = re.compile(r"v?(?:[0-9]{1,64}!)?[0-9][0-9A-Za-z.+_-]{0,63}")
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
PYPI_SIMPLE = "https://pypi.org/simple"  # the registry uv.lock names for a package from PyPI
DROPPED_ENV = ("GH_HOST", "GH_REPO", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")
TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
# Release listings of a busy package are large (PyPI ruff 6 MB, npm typescript 9 MB, measured).
LISTING_MAX_BYTES = 16 * 1024 * 1024
MAX_LOCK_BYTES = 8 * 1024 * 1024
WALK_BACK_CAP = 20
# The packages a PR's head lockfile adds: at most this many lookups, none started after the budget.
ADDED_CAP = 20
ADDED_BUDGET_SECONDS = 60
NOT_GIVEN = object()
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


# A final PEP 440 release: optional epoch, release numbers, optional post-release in any spelling
# PEP 440 accepts (`.post1`, `-1`, `r1`, `_post.1`, a bare `.post` meaning post 0), in any case.
# Pre-releases, dev releases and local versions do not match. The numbers are not capped one by one;
# MAX_ORDERED_VERSION_CHARS bounds the whole string instead.
PEP440_FINAL_RE = re.compile(
    r"(?:([0-9]+)!)?([0-9]+(?:\.[0-9]+)*)(?:-([0-9]+)|[-_.]?(?:post|rev|r)[-_.]?([0-9]+)?)?",
    re.IGNORECASE | re.ASCII,
)
# A final release of the other ecosystems: plain dotted numbers, no per-number cap.
PLAIN_RELEASE_RE = re.compile(r"[0-9]+(?:\.[0-9]+)*")
MAX_ORDERED_VERSION_CHARS = 128


def order_key(eco, version):
    """A tuple that orders final releases of one ecosystem with plain `<` and `>`, or None.

    For uv it is PEP 440's (epoch, release, post) order; for the others plain dotted numbers. A
    release without a post segment ranks below any post-release of it. Trailing zeros of the release
    are dropped so that 1.0 and 1.0.0 are equal. A string longer than MAX_ORDERED_VERSION_CHARS is
    not ordered.
    """
    text = normalize_version(version)
    if len(text) > MAX_ORDERED_VERSION_CHARS:
        return None
    epoch, post = 0, -1
    if eco == "uv":
        match = PEP440_FINAL_RE.fullmatch(text)
        if not match:
            return None
        epoch = int(match.group(1) or 0)
        if match.end(2) < len(text):  # something follows the release: it is a post-release
            post = int(match.group(3) or match.group(4) or 0)
        release = [int(part) for part in match.group(2).split(".")]
    else:
        if not PLAIN_RELEASE_RE.fullmatch(text):
            return None
        release = [int(part) for part in text.split(".")]
    if not release:
        return None
    while release and release[-1] == 0:
        release.pop()
    return (epoch, tuple(release), post)


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


def fixed_version_text(value):
    """VALUE as a fixed-in version, or "" when it is not one.

    A value longer than 64 characters is refused, not cut to 64 first: a truncated prefix could
    pass VERSION_RE and be shown as a version the advisory never named.
    """
    text = clean(value, 65)
    return text if len(text) <= 64 and VERSION_RE.fullmatch(text) else ""


def _fixed_versions(events_owner):
    fixed = []
    for rng in events_owner.get("ranges") or []:
        for event in rng.get("events") or []:
            if isinstance(event, dict) and event.get("fixed"):
                value = fixed_version_text(event["fixed"])
                if value:
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
            patched = fixed_version_text(patched) if patched else ""
            if patched and str(package.get("name", "")).lower() == name.lower():
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
    """Whether a plain-release VERSION meets the PEP 440 specifier SPEC (True/False/None).

    Only plain dotted numbers are compared: a post-release or epoch version on either side gives
    None ("could not tell"), which callers count as unevaluated, never as a pass or a violation.
    """
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


# Each version segment is 1 to 9 digits or one wildcard; a mixed segment such as 1.xx is not a range
# we read.
NPM_SEGMENT = r"(?:[0-9]{1,9}|[xX*])"
NPM_TOKEN_RE = re.compile(
    r"(>=|<=|>|<|=|\^|~)?v?(" + NPM_SEGMENT + r"(?:\." + NPM_SEGMENT + r"){0,2})"
)


def _npm_token(have, token):
    match = NPM_TOKEN_RE.fullmatch(token)
    if not match:
        return None
    op, text = match.group(1) or "=", match.group(2)
    nums = []
    parts = text.split(".")
    for index, part in enumerate(parts):
        if part in ("x", "X", "*"):
            if any(later not in ("x", "X", "*") for later in parts[index + 1 :]):
                # npm ignores a number that follows a wildcard (x.1 means *, 1.x.3 means 1.x); this
                # module does not evaluate a range it would have to read that way, so it is unknown.
                # Wildcards after a wildcard (1.x.x, x.x.x) say nothing new and are fine.
                return None
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
    """{'versions': {name: [versions]}, 'requires_python': str|None} from a uv.lock.

    Also `unparsed` (package entries with no string name or version, as text) and `off_registry`
    (name, version pairs whose source is not PyPI: git, URL, path, editable, virtual or another
    index), which the added-package check reports as not looked up rather than as clean.
    """
    try:
        import tomllib
    except ImportError as exc:
        raise LookupFailed("tomllib is not available") from exc
    try:
        data = tomllib.loads(text)
    except ValueError as exc:
        raise LookupFailed("uv.lock is not valid TOML") from exc
    versions, unparsed, off_registry, source_ids = {}, [], [], {}
    for package in data.get("package") or []:
        name = package.get("name") if isinstance(package, dict) else None
        version = package.get("version") if isinstance(package, dict) else None
        if not isinstance(name, str) or not isinstance(version, str):
            unparsed.append(repr(package)[:MAX_CONSTRAINT_CHARS])
            continue
        versions.setdefault(python_name(name), []).append(version)
        source = package.get("source")
        registry = source.get("registry") if isinstance(source, dict) else None
        if not isinstance(registry, str) or registry.rstrip("/") != PYPI_SIMPLE:
            off_registry.append((python_name(name), version))
            source_ids[(python_name(name), version)] = json.dumps(
                source, sort_keys=True, default=str
            )
    requires = data.get("requires-python")
    return {
        "versions": versions,
        "requires_python": requires if isinstance(requires, str) else None,
        "unparsed": unparsed,
        "off_registry": off_registry,
        "source_ids": source_ids,
    }


# A packages: key, optionally with a peer-resolution suffix `(react@18.2.0)(...)` after the version.
PNPM_KEY_RE = re.compile(
    r"  '?/?(@?[^@'\s/]+(?:/[^@'\s/]+)?)@([0-9][^'\s:()]*)(?:\([^'\s:]*)?'?:\s*"
)
PNPM_LOCKFILE_RE = re.compile(r"""lockfileVersion:\s*['"]?([0-9]+)""")
PNPM_SUPPORTED_MAJORS = ("6", "9")  # pnpm 8 writes 6.x, pnpm 9 and 10 write 9.x


def parse_pnpm_lock(text):
    """{'versions': {name: [versions]}, 'requires_python': None} from a pnpm-lock.yaml.

    Also `unparsed`: package keys (two-space indent under `packages:`) that are not a plain
    registry `name@version` (a tarball, git, `file:` or `link:` key) or that are too long to parse,
    as text, so the added-package check can count only the ones the base does not have; and
    `off_registry`: pairs whose resolution names a `tarball:` URL, which pnpm writes only when the
    URL is not the registry's standard layout (a plain key records no registry at all).
    """
    versions, inside, unparsed, off_registry, current = {}, False, [], [], None
    source_ids = {}
    declared = PNPM_LOCKFILE_RE.search(text[:2000])
    if not declared or declared.group(1) not in PNPM_SUPPORTED_MAJORS:
        raise LookupFailed("unsupported or missing pnpm lockfileVersion")
    for line in text.splitlines():
        if line.startswith("packages:"):
            inside = True
        elif line and not line.startswith(" "):
            inside = False
        elif inside and line.startswith("  ") and not line.startswith("   "):
            match = PNPM_KEY_RE.fullmatch(line) if len(line) <= MAX_CONSTRAINT_CHARS else None
            current = (match.group(1), match.group(2)) if match else None
            if not match:
                unparsed.append(line)
            elif match.group(2) not in versions.setdefault(match.group(1), []):
                versions[match.group(1)].append(match.group(2))
        elif inside and current and "tarball:" in line:
            # flow-style `resolution: {..., tarball: ...}` or a block `tarball:` line
            if current not in off_registry:
                off_registry.append(current)
            source_ids[current] = source_ids.get(current, "") + line.strip()
    if not versions:
        raise LookupFailed("no packages found in the pnpm lockfile")
    return {
        "versions": versions,
        "requires_python": None,
        "unparsed": unparsed,
        "off_registry": off_registry,
        "source_ids": source_ids,
    }


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
        locked = lock["versions"].get(python_name(dependency))
        if marker is not None and EXTRA_MARKER_RE.fullmatch(marker.strip()):
            # Which extras the project requests is not read from the lockfile, so a constraint
            # behind one may be active: when it touches the lock it is unevaluated, not inactive.
            if locked and spec:
                verdict["unevaluated"] += 1
            continue
        applies = marker_applies(marker, min_python)
        if applies is False:
            continue
        if applies is None:
            verdict["unevaluated"] += 1
            continue
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
    # `engines` needs the Node version we run on, which is not known here. It is outside the
    # lockfile
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
    """Whether VERSION's declared constraints fit the lockfile.

    The status is compatible, incompatible or unknown.
    """
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
            "reason": (
                "a dependency is locked at several versions and only some satisfy the constraint"
            ),
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
    """The final releases of NAME this module can order, newest first.

    Yanked and deprecated releases are left out, and so are pre-releases and dev releases. A
    release that is final but too long to order raises LookupFailed: leaving it out could report an
    older version as the newest, so the answer is unknown instead.
    """
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
    ordered = []
    for v in names:
        if order_key(eco, v) is not None:
            ordered.append(v)
        elif (PEP440_FINAL_RE if eco == "uv" else PLAIN_RELEASE_RE).fullmatch(normalize_version(v)):
            raise LookupFailed("a final release is too long to order")
    return sorted(ordered, key=lambda v: order_key(eco, v), reverse=True)


def newest_compatible(fetch, cache, eco, name, new, new_compat, lock, deadline=None):
    """Walk the releases newer than NEW, newest first, to the first one that fits the lockfile.

    `version` is the newest compatible version, or None when that cannot be established: no
    lockfile, an unreadable listing, a version whose metadata could not be read (it might be the
    compatible one), or more than WALK_BACK_CAP newer releases with none compatible.
    """
    if eco not in LOCK_FOR or lock is None:
        return {"status": "unknown", "version": None, "newer_incompatible": []}
    new_key = order_key(eco, new)
    try:
        newer = [
            v
            for v in stable_releases(fetch, cache, eco, name)
            if new_key and order_key(eco, v) > new_key
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


def comparable(a, b):
    """Whether risk() may rank results A and B against each other.

    Ranking two non-empty advisory lists needs every advisory's severity to be recognized: an
    unknown severity is not the lowest one, it is unknown. A list compared with an empty one needs
    no severity.
    """
    if a["advisories"] and b["advisories"]:
        return all(item["severity"] in SEVERITY_RANK for item in a["advisories"] + b["advisories"])
    return True


def risk(result):
    """Sort key for how risky a version is: worst severity first, then how many advisories."""
    items = result["advisories"]
    worst = max((SEVERITY_RANK.get(a["severity"], 0) for a in items), default=0)
    return (worst, len(items))


def added_pairs(eco, dep, new, base, head):
    """(name, version) pairs the head lockfile has and the base lockfile does not, sorted.

    Only the bumped dependency at its new version is left out (it is looked up as
    `versions.new`); another version of it that the head adds counts. A package whose version
    changed counts too, because its new version is new code.
    """
    norm = python_name if eco == "uv" else str
    skip = (norm(dep), normalize_version(new))
    pairs = []
    for name, versions in sorted(head["versions"].items()):
        before = set(base["versions"].get(name, []))
        pairs += [
            (name, version)
            for version in versions
            if version not in before and (norm(name), normalize_version(version)) != skip
        ]
    return pairs


def merged_with_osv(fetch, eco, name, version, advisories):
    """ADVISORIES plus OSV's for NAME at VERSION, by id; OSV failing keeps ADVISORIES as they are.

    uv.lock stores normalized (lowercase) names and GitHub's pip matching is partly
    case-sensitive (live, 2026-11-18: `Pillow@8.0.0` 46 advisories, `pillow@8.0.0` 26), so a
    non-empty GitHub answer for a normalized name can be a subset. OSV normalizes names. The same
    vulnerability can appear twice under a GHSA and a PYSEC id.
    """
    try:
        extra = osv_advisories(fetch, eco, name, version)
    except (LookupFailed, AttributeError, TypeError):
        return advisories
    seen = {item["id"] for item in advisories}
    return advisories + [item for item in extra if item["id"] not in seen]


def added_packages(run, gh, environ, fetch, eco, dep, new, base, head):
    """Known advisories for the packages the PR's head lockfile adds, compared with the base.

    At most ADDED_CAP pairs are looked up, and none is started after ADDED_BUDGET_SECONDS; the
    rest leave `truncated` set. A pair whose name or version fails the pattern check, whose source
    is not a registry, or whose lookup fails, is listed under `unknown`, never as clean, and so is
    a pair the base already has whose source moved off the registry in the head
    (`source_changed`); head package entries the parser could not read, and the base does not
    have, are counted in `unparsed`.
    """
    if base is None or head is None:
        return {"status": "unknown", "reason": "the base or head lockfile could not be read"}
    pairs = added_pairs(eco, dep, new, base, head)
    off_registry = set(head.get("off_registry") or [])
    out = {
        "status": "ok",
        "count": len(pairs),
        "checked": 0,
        "truncated": len(pairs) > ADDED_CAP,
        "unparsed": len(set(head.get("unparsed") or []) - set(base.get("unparsed") or [])),
        "vulnerable": [],
        "unknown": [],
    }
    deadline = time.monotonic() + ADDED_BUDGET_SECONDS
    for name, version in pairs[:ADDED_CAP]:
        if time.monotonic() > deadline:
            out["truncated"] = True
            break
        out["checked"] += 1
        if (
            not ECOSYSTEMS[eco][2].fullmatch(name)
            or not VERSION_RE.fullmatch(version)
            or (name, version) in off_registry
        ):
            out["unknown"].append({"name": clean(name, 100), "version": clean(version, 64)})
            continue
        try:
            info = advisories_for(run, gh, environ, fetch, eco, name, version)
            if eco == "uv" and info["sources"].get("github") == "hit":
                info["advisories"] = merged_with_osv(fetch, eco, name, version, info["advisories"])
        except Exception:  # noqa: BLE001 - one failed lookup is unknown, never clean
            info = {"status": "unknown", "advisories": []}
        if info["advisories"]:
            out["vulnerable"].append(
                {"name": name, "version": version, "advisories": info["advisories"]}
            )
        elif info["status"] != "ok" or info.get("truncated"):
            out["unknown"].append({"name": name, "version": version})
    # A pair the base already has, whose source in the head is off the registry and differs from
    # the base's (moved off the registry, or another git revision or tarball URL), is new code under
    # an old name and version: it is never looked up and never clean.
    base_ids, head_ids = base.get("source_ids") or {}, head.get("source_ids") or {}
    for name, version in sorted(off_registry):
        if version in base["versions"].get(name, []) and base_ids.get(
            (name, version)
        ) != head_ids.get((name, version), (name, version)):
            out["unknown"].append({"name": name, "version": version, "source_changed": True})
    return out


def adds_vulnerable(added):
    """True when an added package has an advisory, False only when every one was checked clean."""
    if added.get("vulnerable"):
        return True
    if (
        added.get("status") == "ok"
        and not added["truncated"]
        and not added["unknown"]
        and not added["unparsed"]
    ):
        return False
    return None


def assess(run, gh, environ, fetch, eco, name, old, new, lock=None, head_lock=NOT_GIVEN):
    """Advisories for old, new and the newest compatible version, plus the signals the rules need.

    The advisory lookups for old and new run first and the compatibility stage is contained, so a
    failure or a hostile registry answer there can cost the compatibility answer but never the
    advisory result. HEAD_LOCK (the PR's head lockfile, compared with LOCK) adds the advisories of
    the packages the PR newly adds; NOT_GIVEN means it was not requested.
    """
    cache = {}
    new_key = order_key(eco, new)
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
    if target and (new_key is None or order_key(eco, target) != new_key):
        out["versions"]["newest_compatible"] = {
            "version": target,
            **advisories_for(run, gh, environ, fetch, eco, name, target),
        }
    if head_lock is NOT_GIVEN:
        out["added_packages"] = {"status": "not_checked"}
    else:
        out["added_packages"] = added_packages(
            run, gh, environ, fetch, eco, name, new, lock, head_lock
        )
    latest = out["latest"]
    v = out["versions"]
    # A truncated list (a full first page) is not the whole answer, so no comparison may rest on it.
    known = {role: info["status"] == "ok" and not info.get("truncated") for role, info in v.items()}
    latest_key = order_key(eco, latest) if latest else None
    if target is None or new_key is None or order_key(eco, target) is None:
        new_is_newest_compatible = None
    else:
        new_is_newest_compatible = new_key >= order_key(eco, target)
    out["signals"] = {
        "new_vulnerable_not_safer_than_old": (
            bool(v["new"]["advisories"]) and risk(v["new"]) >= risk(v["old"])
            if known["new"] and known["old"] and comparable(v["new"], v["old"])
            else None
        ),
        "new_compatible": {"compatible": True, "incompatible": False}.get(compat["status"]),
        "new_is_newest_compatible": new_is_newest_compatible,
        "new_safer_than_newest_compatible": (
            risk(v["new"]) < risk(v["newest_compatible"])
            if known["new"]
            and known.get("newest_compatible")
            and comparable(v["new"], v["newest_compatible"])
            else None
        ),
        "new_is_latest": (None if new_key is None or latest_key is None else new_key >= latest_key),
        "adds_vulnerable_package": adds_vulnerable(out["added_packages"]),
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
    one.add_argument(
        "--head-lock",
        help="head-uv.lock or head-pnpm-lock.yaml from dependabot_pr_read.py; needs a base --lock",
    )
    return parser.parse_args(argv)


def check_lock_roles(lock, head_lock):
    """--head-lock is compared with --lock, so it needs a base- --lock and must be a head- file."""
    if head_lock is None:
        return
    if (
        lock is None
        or not os.path.basename(lock).startswith("base-")
        or not os.path.basename(head_lock).startswith("head-")
    ):
        raise Refusal("--head-lock must be a head- lockfile and needs --lock to be a base- one")


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
        check_lock_roles(args.lock, args.head_lock)
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
                NOT_GIVEN if args.head_lock is None else load_lock(args.head_lock, args.ecosystem),
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
