#!/usr/bin/env python3
"""Memory scanning, auditing, and search across Claude Code projects.

Scans ~/.claude/projects/{project}/memory/ to discover, health-check, and search memory files.

Usage as CLI:
  python3 memory_scanner.py scan [--type TYPE] [--project FILTER] [--format table|json]
  python3 memory_scanner.py audit [--age-threshold N] [--projects-base PATH]
  python3 memory_scanner.py search "<query>" [--type TYPE] [--project FILTER] [--context N]
                                    [--limit N]
"""

from __future__ import annotations

import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

sys.path.insert(0, str(Path(__file__).resolve().parent))

from formatters import render_table, to_json, to_ndjson, truncate  # noqa: E402

DEFAULT_PROJECTS_BASE = str(Path.home() / ".claude" / "projects")

VALID_MEMORY_TYPES = {"user", "feedback", "project", "reference"}

# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------


def parse_frontmatter(content: str) -> dict:
    """
    Parse YAML-like frontmatter between --- delimiters.
    Extracts name, description, and type fields.
    Returns body without frontmatter. If no frontmatter, all fields are None and body is
    original content.
    """
    fm = {"name": None, "description": None, "type": None, "body": content}

    if not content.startswith("---"):
        return fm

    after_open = content[3:]
    close_idx = after_open.find("\n---")
    if close_idx == -1:
        return fm

    yaml_block = after_open[:close_idx]
    body = after_open[close_idx + 4 :]  # skip \n---

    for line in yaml_block.split("\n"):
        colon_idx = line.find(":")
        if colon_idx == -1:
            continue
        key = line[:colon_idx].strip()
        value = line[colon_idx + 1 :].strip()
        value = re.sub(r'^["\'](.*?)["\']$', r"\1", value)
        if key == "name":
            fm["name"] = value or None
        elif key == "description":
            fm["description"] = value or None
        elif key == "type":
            fm["type"] = value or None

    fm["body"] = body[1:] if body.startswith("\n") else body

    return fm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def readable_project_name(encoded: str) -> str:
    """Convert an encoded project directory name to a human-readable path.

    Strips the leading dash and replaces remaining dashes with slashes.
    """
    stripped = encoded[1:] if encoded.startswith("-") else encoded
    return stripped.replace("-", "/")


_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)]+\.md)\)")


def parse_memory_index(memory_dir: str) -> tuple[set[str], list[str]]:
    """Parse MEMORY.md in a memory directory.

    Returns a set of linked filenames and ordered entry list.
    """
    index_path = os.path.join(memory_dir, "MEMORY.md")
    linked: set[str] = set()
    entries: list[str] = []

    if not os.path.exists(index_path):
        return linked, entries

    try:
        with open(index_path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return linked, entries

    for match in _LINK_PATTERN.finditer(content):
        target = match.group(2)
        linked.add(target)
        entries.append(target)

    return linked, entries


def collect_memory_files(memory_dir: str) -> list[str]:
    """Recursively collect all .md files in a directory, excluding MEMORY.md."""
    results: list[str] = []

    if not os.path.isdir(memory_dir):
        return results

    for root, _dirs, files in os.walk(memory_dir):
        for name in files:
            if name.endswith(".md") and name != "MEMORY.md":
                results.append(os.path.join(root, name))

    return results


def is_valid_memory_type(t: str | None) -> bool:
    """Type guard: checks if a string is a valid memory type."""
    return t in VALID_MEMORY_TYPES


# ---------------------------------------------------------------------------
# scan_memories
# ---------------------------------------------------------------------------


def scan_memories(
    projects_base: str | None = None,
    type_filter: str | None = None,
    project_filter: str | None = None,
) -> dict:
    """
    Scan projects_base for all project dirs, find memory/ subdirs,
    read each .md file (not MEMORY.md), parse frontmatter, check if indexed.
    Supports type and project filtering.
    """
    base = projects_base or DEFAULT_PROJECTS_BASE

    result = {
        "projectsScanned": 0,
        "projectsWithMemories": 0,
        "totalMemories": 0,
        "byType": {},
        "memories": [],
    }

    if not os.path.isdir(base):
        return result

    now = datetime.now(UTC).timestamp()

    for entry in sorted(os.listdir(base)):
        entry_path = os.path.join(base, entry)
        if not os.path.isdir(entry_path):
            continue

        if project_filter:
            filt = project_filter.lower()
            readable = readable_project_name(entry).lower()
            if filt not in entry.lower() and filt not in readable:
                continue

        result["projectsScanned"] += 1

        memory_dir = os.path.join(entry_path, "memory")
        if not os.path.isdir(memory_dir):
            continue

        linked, _entries = parse_memory_index(memory_dir)
        files = collect_memory_files(memory_dir)

        if not files:
            continue

        result["projectsWithMemories"] += 1

        for file_path in files:
            file_name = os.path.basename(file_path)

            try:
                stat = os.stat(file_path)
                size_bytes = stat.st_size
                mtime = stat.st_mtime
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue

            age_days = int((now - mtime) / 86400)
            fm = parse_frontmatter(content)
            has_frontmatter = (
                fm["name"] is not None or fm["description"] is not None or fm["type"] is not None
            )
            mem_type = fm["type"] if is_valid_memory_type(fm["type"]) else "unknown"

            if type_filter and mem_type != type_filter:
                continue

            indexed = file_name in linked

            result["memories"].append(
                {
                    "project": entry,
                    "projectReadable": readable_project_name(entry),
                    "file": file_name,
                    "path": file_path,
                    "name": fm["name"],
                    "type": mem_type,
                    "description": fm["description"],
                    "ageDays": age_days,
                    "sizeBytes": size_bytes,
                    "hasFrontmatter": has_frontmatter,
                    "indexed": indexed,
                }
            )

            result["totalMemories"] += 1
            result["byType"][mem_type] = result["byType"].get(mem_type, 0) + 1

    return result


# ---------------------------------------------------------------------------
# audit_memories helpers
# ---------------------------------------------------------------------------

_ISO_DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_ABS_PATH_PATTERN = re.compile(r"(/(?:Users|home|tmp|var|etc|opt)/[^\s\"'`),;>\]]+)")

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def _find_expired_dates(content: str) -> list[datetime]:
    dates = []
    for m in _ISO_DATE_PATTERN.finditer(content):
        try:
            dates.append(datetime.fromisoformat(f"{m.group(1)}T00:00:00").replace(tzinfo=UTC))
        except ValueError:
            continue
    return dates


def _extract_absolute_paths(content: str) -> list[str]:
    paths = []
    for m in _ABS_PATH_PATTERN.finditer(content):
        p = re.sub(r"[.,:]+$", "", m.group(1))
        paths.append(p)
    seen = []
    for p in paths:
        if p not in seen:
            seen.append(p)
    return seen


# ---------------------------------------------------------------------------
# audit_memories
# ---------------------------------------------------------------------------


def audit_memories(projects_base: str | None = None, age_threshold: int = 60) -> dict:
    """Run 8 health checks across all memories and return an audit result."""
    base = projects_base or DEFAULT_PROJECTS_BASE
    now = datetime.now(UTC)

    findings: list[dict] = []

    if not os.path.isdir(base):
        return {
            "summary": {
                "totalMemories": 0,
                "healthy": 0,
                "issuesFound": 0,
                "bySeverity": {"critical": 0, "warning": 0, "info": 0},
                "projectsWithMemories": 0,
            },
            "findings": [],
        }

    project_dirs = [name for name in os.listdir(base) if os.path.isdir(os.path.join(base, name))]

    # --- Check 1 & 2: Broken links and orphans (per project) ---
    all_memories = scan_memories(projects_base=base)["memories"]

    for project in project_dirs:
        memory_dir = os.path.join(base, project, "memory")
        if not os.path.isdir(memory_dir):
            continue

        linked, entries = parse_memory_index(memory_dir)

        # Check 1: Broken links — MEMORY.md links to files that don't exist
        for linked_file in entries:
            linked_path = os.path.join(memory_dir, linked_file)
            if not os.path.exists(linked_path):
                findings.append(
                    {
                        "severity": "warning",
                        "category": "broken_link",
                        "fixType": "auto",
                        "file": linked_file,
                        "project": project,
                        "path": linked_path,
                        "message": f"MEMORY.md links to {linked_file} which does not exist",
                        "suggestion": f"Remove the broken link to {linked_file} from MEMORY.md",
                        "autoFixable": True,
                    }
                )

        # Check 2: Orphan files — .md files not in MEMORY.md
        all_files = collect_memory_files(memory_dir)
        for file_path in all_files:
            file_name = os.path.basename(file_path)
            if file_name not in linked:
                content = ""
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                except OSError:
                    pass
                fm = parse_frontmatter(content)
                has_fm = (
                    fm["name"] is not None
                    or fm["description"] is not None
                    or fm["type"] is not None
                )
                fix_type = "auto" if has_fm else "ai_assisted"
                entry_finding = {
                    "severity": "warning",
                    "category": "orphan",
                    "fixType": fix_type,
                    "file": file_name,
                    "project": project,
                    "path": file_path,
                    "message": f"{file_name} exists in memory directory but is not indexed in "
                    "MEMORY.md",
                    "suggestion": f"Add {file_name} to MEMORY.md index",
                    "autoFixable": has_fm,
                }
                if not has_fm:
                    entry_finding["aiAction"] = (
                        f"Read {file_name}, generate appropriate frontmatter, then add to MEMORY.md"
                    )
                findings.append(entry_finding)

    # --- Per-memory checks (checks 3-7) ---
    for mem in all_memories:
        try:
            with open(mem["path"], encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue

        # Check 3: Missing frontmatter
        if not mem["hasFrontmatter"]:
            findings.append(
                {
                    "severity": "warning",
                    "category": "missing_frontmatter",
                    "fixType": "ai_assisted",
                    "file": mem["file"],
                    "project": mem["project"],
                    "path": mem["path"],
                    "message": f"{mem['file']} has no YAML frontmatter",
                    "suggestion": "Add frontmatter with name, description, and type fields",
                    "autoFixable": False,
                    "aiAction": f"Read {mem['file']} and generate appropriate frontmatter "
                    "(name, description, type)",
                }
            )

        # Check 4: Expired dates — project/reference/unknown files where ALL ISO dates are in
        # the past
        if mem["type"] in ("project", "reference", "unknown"):
            dates = _find_expired_dates(content)
            if dates and all(d < now for d in dates):
                oldest = min(dates)
                findings.append(
                    {
                        "severity": "critical",
                        "category": "expired",
                        "fixType": "auto",
                        "file": mem["file"],
                        "project": mem["project"],
                        "path": mem["path"],
                        "message": f"{mem['file']} contains dates that have all passed "
                        f"(oldest: {oldest.date().isoformat()})",
                        "suggestion": "Delete or update this memory — it references past dates",
                        "autoFixable": True,
                    }
                )

        # Check 5: Stale file paths — absolute paths that don't exist on disk
        abs_paths = _extract_absolute_paths(content)
        missing_paths = [p for p in abs_paths if not os.path.exists(p)]
        if missing_paths:
            findings.append(
                {
                    "severity": "info",
                    "category": "stale_path",
                    "fixType": "ai_assisted",
                    "file": mem["file"],
                    "project": mem["project"],
                    "path": mem["path"],
                    "message": f"{mem['file']} references {len(missing_paths)} path(s) that "
                    f"do not exist: {', '.join(missing_paths[:3])}",
                    "suggestion": "Update or remove references to missing paths",
                    "autoFixable": False,
                    "aiAction": f"Verify and update the following paths in {mem['file']}: "
                    f"{', '.join(missing_paths)}",
                }
            )

        # Check 6: Age-based staleness — project/reference files older than or equal to
        # age_threshold
        if mem["type"] in ("project", "reference") and mem["ageDays"] >= age_threshold:
            findings.append(
                {
                    "severity": "info",
                    "category": "stale",
                    "fixType": "ai_assisted",
                    "file": mem["file"],
                    "project": mem["project"],
                    "path": mem["path"],
                    "message": f"{mem['file']} is {mem['ageDays']} days old "
                    f"(threshold: {age_threshold} days)",
                    "suggestion": "Review and update or remove this memory",
                    "autoFixable": False,
                    "aiAction": f"Review {mem['file']} for relevance and update or remove "
                    "if outdated",
                }
            )

        # Check 7: Index mismatch — MEMORY.md description differs from frontmatter description
        if mem["hasFrontmatter"] and mem["description"] is not None and mem["indexed"]:
            memory_dir = os.path.join(base, mem["project"], "memory")
            index_path = os.path.join(memory_dir, "MEMORY.md")
            try:
                with open(index_path, encoding="utf-8") as f:
                    index_content = f.read()
            except OSError:
                continue
            escaped_file = re.escape(mem["file"])
            desc_pattern = re.compile(rf"\[[^\]]*\]\({escaped_file}\)\s*—\s*(.+)")
            desc_match = desc_pattern.search(index_content)
            if desc_match:
                index_desc = desc_match.group(1).strip()
                if index_desc != mem["description"].strip():
                    findings.append(
                        {
                            "severity": "info",
                            "category": "index_mismatch",
                            "fixType": "auto",
                            "file": mem["file"],
                            "project": mem["project"],
                            "path": mem["path"],
                            "message": f"MEMORY.md description for {mem['file']} differs "
                            f'from frontmatter: "{index_desc}" vs "{mem["description"]}"',
                            "suggestion": f"Update MEMORY.md entry for {mem['file']} to match "
                            "frontmatter description",
                            "autoFixable": True,
                        }
                    )

    # Check 8: Duplicate names — same name (case-insensitive) across different projects
    name_to_files: dict[str, list[dict]] = {}
    for mem in all_memories:
        if mem["name"] is None:
            continue
        key = mem["name"].lower()
        name_to_files.setdefault(key, []).append(
            {"file": mem["file"], "project": mem["project"], "path": mem["path"]}
        )

    for group in name_to_files.values():
        if len(group) < 2:
            continue
        projects = {g["project"] for g in group}
        if len(projects) < 2:
            continue
        for entry_g in group:
            matching = next(
                (
                    m
                    for m in all_memories
                    if m["project"] == entry_g["project"] and m["file"] == entry_g["file"]
                ),
                None,
            )
            findings.append(
                {
                    "severity": "info",
                    "category": "duplicate",
                    "fixType": "ai_assisted",
                    "file": entry_g["file"],
                    "project": entry_g["project"],
                    "path": entry_g["path"],
                    "message": f"Duplicate memory name found across {len(projects)} projects: "
                    f'"{matching["name"] if matching else None}"',
                    "suggestion": "Merge or differentiate these memories",
                    "autoFixable": False,
                    "aiAction": "Review duplicates and merge into a single memory or rename "
                    "to disambiguate",
                }
            )

    # Sort by severity: critical first, then warning, then info
    findings.sort(key=lambda f: SEVERITY_ORDER[f["severity"]])

    # Summary
    files_with_findings = {f["path"] for f in findings}
    total_memories = len(all_memories)
    healthy = total_memories - len(files_with_findings)
    by_severity = {"critical": 0, "warning": 0, "info": 0}
    for f in findings:
        by_severity[f["severity"]] += 1
    projects_with_memories = len({m["project"] for m in all_memories})

    return {
        "summary": {
            "totalMemories": total_memories,
            "healthy": max(0, healthy),
            "issuesFound": len(findings),
            "bySeverity": by_severity,
            "projectsWithMemories": projects_with_memories,
        },
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# search_memories
# ---------------------------------------------------------------------------


def search_memories(
    query: str,
    projects_base: str | None = None,
    type_filter: str | None = None,
    project_filter: str | None = None,
    context: int = 0,
    limit: int = 50,
) -> list[dict]:
    """Search memory file contents using a case-insensitive literal query."""
    pattern = re.compile(re.escape(query), re.IGNORECASE)

    scan_result = scan_memories(
        projects_base=projects_base, type_filter=type_filter, project_filter=project_filter
    )

    results: list[dict] = []

    for mem in scan_result["memories"]:
        try:
            with open(mem["path"], encoding="utf-8") as f:
                lines = f.read().split("\n")
        except OSError:
            continue

        for i, line in enumerate(lines):
            if not pattern.search(line):
                continue

            ctx_before: list[str] = []
            ctx_after: list[str] = []

            if context > 0:
                for j in range(max(0, i - context), i):
                    ctx_before.append(truncate(lines[j], 100))
                for j in range(i + 1, min(len(lines), i + 1 + context)):
                    ctx_after.append(truncate(lines[j], 100))

            results.append(
                {
                    "project": mem["project"],
                    "file": mem["file"],
                    "path": mem["path"],
                    "type": mem["type"],
                    "line": i + 1,
                    "match": truncate(line, 200),
                    "contextBefore": ctx_before,
                    "contextAfter": ctx_after,
                }
            )

            if len(results) >= limit:
                return results

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _exit_with_error(err, code: int) -> NoReturn:
    sys.stderr.write(to_json({"error": str(err), "code": code}) + "\n")
    sys.exit(code)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # ty: ignore[unresolved-attribute]
    sys.stderr.reconfigure(encoding="utf-8")  # ty: ignore[unresolved-attribute]

    args = sys.argv[1:]

    def get_flag(flag: str) -> str | None:
        if flag in args:
            idx = args.index(flag)
            if idx + 1 < len(args):
                return args[idx + 1]
        return None

    def get_flag_int(flag: str, default: int) -> int:
        v = get_flag(flag)
        if v is None:
            return default
        try:
            return int(v)
        except ValueError:
            return default

    projects_base = get_flag("--projects-base")
    # The subcommand must be args[0] -- scanning for "the first token that doesn't
    # start with -" would misidentify a flag's own value as the subcommand.
    command = args[0] if args and not args[0].startswith("-") else None

    if not command:
        sys.stderr.write("Usage: python3 memory_scanner.py <scan|audit|search> ...\n")
        sys.exit(1)

    try:
        if command == "scan":
            type_filter = get_flag("--type")
            project_filter = get_flag("--project")
            fmt = get_flag("--format") or "json"
            scan_result = scan_memories(
                projects_base=projects_base, type_filter=type_filter, project_filter=project_filter
            )

            if fmt == "table":
                print(
                    render_table(
                        [
                            {
                                "project": m["project"],
                                "file": m["file"],
                                "type": m["type"],
                                "age_days": m["ageDays"],
                                "indexed": "yes" if m["indexed"] else "no",
                            }
                            for m in scan_result["memories"]
                        ],
                        [
                            {"key": "project", "label": "PROJECT"},
                            {"key": "file", "label": "FILE"},
                            {"key": "type", "label": "TYPE"},
                            {"key": "age_days", "label": "AGE", "align": "right"},
                            {"key": "indexed", "label": "INDEXED"},
                        ],
                    )
                )
            else:
                out = {
                    "projects_scanned": scan_result["projectsScanned"],
                    "projects_with_memories": scan_result["projectsWithMemories"],
                    "total_memories": scan_result["totalMemories"],
                    "by_type": scan_result["byType"],
                    "memories": [
                        {
                            "project": m["project"],
                            "project_readable": m["projectReadable"],
                            "file": m["file"],
                            "path": m["path"],
                            "name": m["name"],
                            "type": m["type"],
                            "description": m["description"],
                            "age_days": m["ageDays"],
                            "size_bytes": m["sizeBytes"],
                            "has_frontmatter": m["hasFrontmatter"],
                            "indexed": m["indexed"],
                        }
                        for m in scan_result["memories"]
                    ],
                }
                print(to_json(out))

        elif command == "audit":
            age_threshold = get_flag_int("--age-threshold", 60)
            audit_result = audit_memories(projects_base=projects_base, age_threshold=age_threshold)

            out = {
                "summary": {
                    "total_memories": audit_result["summary"]["totalMemories"],
                    "healthy": audit_result["summary"]["healthy"],
                    "issues_found": audit_result["summary"]["issuesFound"],
                    "by_severity": audit_result["summary"]["bySeverity"],
                    "projects_with_memories": audit_result["summary"]["projectsWithMemories"],
                },
                "findings": [
                    {
                        "severity": f["severity"],
                        "category": f["category"],
                        "fix_type": f["fixType"],
                        "file": f["file"],
                        "project": f["project"],
                        "path": f["path"],
                        "message": f["message"],
                        "suggestion": f["suggestion"],
                        "auto_fixable": f["autoFixable"],
                        **({"ai_action": f["aiAction"]} if "aiAction" in f else {}),
                    }
                    for f in audit_result["findings"]
                ],
            }
            print(to_json(out))

        elif command == "search":
            cmd_idx = args.index("search")
            query = args[cmd_idx + 1] if cmd_idx + 1 < len(args) else None
            if not query or query.startswith("-"):
                _exit_with_error("Missing search query", 2)

            type_filter = get_flag("--type")
            project_filter = get_flag("--project")
            context_lines = get_flag_int("--context", 0)
            limit = get_flag_int("--limit", 20)

            results = search_memories(
                query,
                projects_base=projects_base,
                type_filter=type_filter,
                project_filter=project_filter,
                context=context_lines,
                limit=limit,
            )

            out = [
                {
                    "project": r["project"],
                    "file": r["file"],
                    "path": r["path"],
                    "type": r["type"],
                    "line": r["line"],
                    "match": r["match"],
                    "context_before": r["contextBefore"],
                    "context_after": r["contextAfter"],
                }
                for r in results
            ]

            print(to_ndjson(out) if out else to_json([]))
        else:
            _exit_with_error(f"Unknown command: {command}", 1)
    except SystemExit:
        raise
    except Exception as err:  # noqa: BLE001
        _exit_with_error(err, 3)


if __name__ == "__main__":
    main()
