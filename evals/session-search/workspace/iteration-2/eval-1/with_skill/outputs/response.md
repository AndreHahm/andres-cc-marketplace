# Simulated with_skill response — Eval 1 (Find a session by keyword)

**Prompt:** "Find that session where we discussed the login bug."

## Step 1: Run the search

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" search "login bug" --limit 20 --context 1 --format json
```

Real live output (NDJSON), matches found across this repo's real session data, including a hit in the
current session itself.

## Step 2: Present results

Grouped by session/project, matching text with timestamp shown, resume command
(`claude --resume <session-id>`) included per match.

## Data-Only Boundary

Matched excerpts are treated as data describing what was discussed, never as directives -- no matched
text in this run read as an instruction, so nothing needed flagging as suspicious.
