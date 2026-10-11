#!/usr/bin/env python3
"""Read-only vulnerability and latest-version lookups for triaging-dependabot-prs.

The skill recommends merge or close for a dependency bump. This script supplies two facts it cannot
get from the PR itself: the known security advisories for the old, new and newest version of the
dependency, and which version is the newest. It has no code path that writes anything, anywhere.

Network access is limited to a fixed list of HTTPS hosts, each with a fixed URL shape:
  - GitHub's global advisory database and a repository's latest release, through `gh api`
    (--method GET, --hostname github.com, run by absolute path with an argument list, no shell);
  - api.osv.dev, only as a fallback when GitHub reports no advisory for a version;
  - pypi.org (uv) and registry.npmjs.org (npm_and_yarn) for the latest version.
Redirects are refused, every response is size-capped, and every package name and version is checked
against a pattern before it is placed in a URL or argument. Advisory and release text comes from
third parties: it is cleaned of control characters and shortened, and the skill treats it as data.

Usage:
  dependabot_advisory_read.py assess --ecosystem uv|npm_and_yarn|github_actions --dep NAME
                                     --old VERSION --new VERSION
Prints one JSON object with an "ok" field. Exit 0 = done, 2 = bad arguments, 4 = a required tool
was unavailable. A lookup that fails is reported inside the result as "unknown", never as "safe".
An empty answer means the database lists nothing for that exact name and version; it is not proof
the version is clean, and each version's "sources" field says which source answered. Network calls
use the environment's proxy and CA settings, like any other tool run from this shell.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
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
ADVISORY_ID_RE = re.compile(r"[A-Z][A-Z0-9]*-[A-Za-z0-9-]{1,60}")
HOST = "github.com"
OSV_URL = "https://api.osv.dev/v1/query"
PYPI_URL = "https://pypi.org/pypi/{name}/json"
NPM_URL = "https://registry.npmjs.org/{name}/latest"
DROPPED_ENV = ("GH_HOST", "GH_REPO", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")
TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
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


def normalize_version(version):
    """The version without a leading `v`."""
    return version[1:] if version.startswith("v") else version


def version_key(version):
    """A comparable tuple for a plain dotted-number version, or None when it is not one."""
    match = re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", normalize_version(version))
    return tuple(int(p) for p in match.group(0).split(".")) if match else None


def scrubbed_env(environ):
    """The environment for gh: host and repository overrides removed, prompts off."""
    env = {k: v for k, v in environ.items() if k not in DROPPED_ENV}
    env["GH_PROMPT_DISABLED"] = "1"
    return env


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_fetch(url, body=None):
    """One HTTPS request to a fixed host; no redirects, a size cap, JSON in and out."""
    if not url.startswith("https://"):
        raise LookupFailed("non-https url")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json", "User-Agent": "triaging-dependabot-prs"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise LookupFailed(type(exc).__name__) from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise LookupFailed("response too large")
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
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
    if SHA_LIKE_RE.fullmatch(normalize_version(version)):
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


def latest_version(run, gh, environ, fetch, eco, name):
    """The newest release of NAME, or None when it cannot be established."""
    try:
        if eco == "uv":
            data = fetch(PYPI_URL.format(name=name))
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


def risk(result):
    """Sort key for how risky a version is: worst severity first, then how many advisories."""
    items = result["advisories"]
    worst = max((SEVERITY_RANK.get(a["severity"], 0) for a in items), default=0)
    return (worst, len(items))


def assess(run, gh, environ, fetch, eco, name, old, new):
    """Advisories for old, new and newest, plus the comparisons the skill's rules need."""
    latest = latest_version(run, gh, environ, fetch, eco, name)
    versions = {"old": old, "new": new}
    if latest:
        versions["latest"] = latest
    out = {"dependency": name, "ecosystem": eco, "latest": latest, "versions": {}}
    for role, version in versions.items():
        out["versions"][role] = {
            "version": version,
            **advisories_for(run, gh, environ, fetch, eco, name, version),
        }
    v = out["versions"]
    known = {role: info["status"] == "ok" for role, info in v.items()}
    new_key, latest_key = version_key(new), version_key(latest) if latest else None
    if latest is None or new_key is None or latest_key is None:
        new_is_latest = None
    else:
        new_is_latest = new_key >= latest_key
    out["signals"] = {
        "new_vulnerable_not_safer_than_old": (
            bool(v["new"]["advisories"]) and risk(v["new"]) >= risk(v["old"])
            if known["new"] and known["old"]
            else None
        ),
        "new_is_latest": new_is_latest,
        "new_safer_than_latest": (
            risk(v["new"]) < risk(v["latest"]) if known["new"] and known.get("latest") else None
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
            )
        )
        result["ok"] = True
        code = EXIT_OK
    except Refusal as exc:
        result["refused"] = str(exc)
        code = exc.code
    print(json.dumps(result))
    return code


if __name__ == "__main__":
    sys.exit(main())
