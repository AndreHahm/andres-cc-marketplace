#!/usr/bin/env python3
"""PreToolUse guard for notion-knowledge-management's two Bootstrap grants.

Registered in that skill's frontmatter `hooks:` block, so it runs only while the skill is active.
It allows exactly the calls the skill documents and denies everything else on these two tools:

* ``notion-update-data-source``: only ``data_source_id`` plus ``title`` (a rename) and/or
  ``statements`` holding ONE ``ALTER COLUMN "repo" SET SELECT(...)`` statement whose option names
  use a safe character set. No DROP COLUMN, ADD COLUMN, type change, description, page layout,
  inline flag or ``in_trash``.
* ``notion-move-pages``: exactly one page or database id, moved under a ``page_id`` parent. Never
  the workspace, a database or a data source as the parent.

An allow-list, not a deny-list: a call that does not match is denied, including malformed input.
Limits it cannot cover (it sees one call, not Notion's state): whether the option list sent is a
superset of the current one, and whether the page parent is the right organization-level page. The
skill's Bootstrap steps carry those checks; this hook only removes the destructive shapes.

Signaling: structured JSON on stdout with exit 0 for every outcome (a deny prints a decision, an
allow prints nothing). Any unexpected error is a deny, so a bug here fails closed.
"""

import json
import re
import sys

UPDATE_TOOL = "mcp__claude_ai_Notion__notion-update-data-source"
MOVE_TOOL = "mcp__claude_ai_Notion__notion-move-pages"

# Option names: letters, digits, space, underscore, dot, slash, hyphen. No quote, semicolon,
# parenthesis or backslash, so a name cannot close the string or the statement. Whitespace between
# tokens is the literal space only (never \s, which would also admit newlines and Unicode spaces),
# and "--" is rejected separately in check_update, so a name cannot start an SQL comment.
_COLORS = r"(?:default|gray|brown|orange|yellow|green|blue|purple|pink|red)"
_OPTION = r"'[A-Za-z0-9 _./-]{1,100}'(?::" + _COLORS + r")?"
ALTER_REPO = re.compile(
    r'ALTER COLUMN "repo" SET SELECT\( *' + _OPTION + r"(?: *, *" + _OPTION + r")* *\) *;?"
)
NOTION_ID = re.compile(r"[0-9a-fA-F-]{32,36}")
DATA_SOURCE_ID = re.compile(r"(?:collection://)?[0-9a-fA-F-]{32,36}")

UPDATE_ALLOWED_KEYS = {"data_source_id", "title", "statements"}
HELP = (
    "Allowed here: notion-update-data-source with a data_source_id plus a title (rename) and/or "
    "ONE statement `ALTER COLUMN \"repo\" SET SELECT('existing', 'new')` whose option names use "
    "only letters, digits, spaces, _ . / -, listing every existing option plus the new one; "
    "notion-move-pages of exactly one id under a page_id parent. "
    "Stop and ask the user for anything else."
)


def deny(reason):
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Notion Bootstrap guard: {reason} {HELP}",
                }
            }
        )
    )


def check_update(tool_input):
    extra = sorted(set(tool_input) - UPDATE_ALLOWED_KEYS)
    if extra:
        return (
            "notion-update-data-source was called with parameter(s) not used by Bootstrap: "
            f"{', '.join(extra)}."
        )
    data_source_id = tool_input.get("data_source_id")
    if not isinstance(data_source_id, str) or not DATA_SOURCE_ID.fullmatch(data_source_id):
        return "data_source_id is missing or is not a Notion id."
    has_statements = "statements" in tool_input
    has_title = "title" in tool_input
    if not (has_statements or has_title):
        return "the call changes nothing (no statements and no title)."
    if has_title:
        title = tool_input["title"]
        if not isinstance(title, str) or not title.strip() or len(title) > 300:
            return "title must be a non-empty string of at most 300 characters."
    if has_statements:
        statements = tool_input["statements"]
        if (
            not isinstance(statements, str)
            or "--" in statements
            or not ALTER_REPO.fullmatch(statements.strip(" "))
        ):
            return (
                'statements must be exactly one ALTER COLUMN "repo" SET SELECT(...) statement '
                "on a single line with single spaces and safe option names "
                "(no quote, semicolon, parenthesis or -- inside a name)."
            )
    return None


def check_move(tool_input):
    extra = sorted(set(tool_input) - {"page_or_database_ids", "new_parent"})
    if extra:
        return f"notion-move-pages was called with unexpected parameter(s): {', '.join(extra)}."
    ids = tool_input.get("page_or_database_ids")
    if not isinstance(ids, list) or len(ids) != 1:
        return "exactly one page or database id may be moved per call."
    if not isinstance(ids[0], str) or not NOTION_ID.fullmatch(ids[0]):
        return "the id to move is not a Notion id."
    parent = tool_input.get("new_parent")
    if (
        not isinstance(parent, dict)
        or set(parent) != {"type", "page_id"}
        or parent["type"] != "page_id"
    ):
        return (
            "the new parent must be a page (type page_id), never the workspace, "
            "a database or a data source."
        )
    if not isinstance(parent["page_id"], str) or not NOTION_ID.fullmatch(parent["page_id"]):
        return "the new parent page_id is not a Notion id."
    return None


def decide(payload):
    if not isinstance(payload, dict):
        return "the hook input was not a JSON object."
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_name, str) or not tool_name:
        return "the hook input had no tool_name, so the call cannot be identified."
    if tool_name not in (UPDATE_TOOL, MOVE_TOOL):
        return None  # a named tool this guard does not govern
    if not isinstance(tool_input, dict):
        return "tool_input was missing or not an object."
    return check_update(tool_input) if tool_name == UPDATE_TOOL else check_move(tool_input)


def main():
    try:
        reason = decide(json.loads(sys.stdin.read()))
    except Exception as error:  # fail closed on any bug or malformed input
        reason = f"the guard could not verify this call ({type(error).__name__})."
    if reason:
        deny(reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
