# Debugging Guide: Evidence Intake for Existing Marketplaces

When editing an existing marketplace that has had prior failures, collect evidence
before making changes — do not rely on the default template or guesses from memory.

## Evidence Intake Steps

1. Read the current `.claude-plugin/marketplace.json`.
2. Read this repo's marketplace rules (`CLAUDE.md`, README install section, changelog).
3. Read official docs for marketplace/plugin path semantics.
4. Mine local Claude Code session history for prior failure patterns (see below).

## Mining Session History

Each project's sessions live under `~/.claude/projects/<escaped-cwd>/`:
- Top-level files: `<session-id>.jsonl`
- Subagent transcripts: `<session-id>/subagents/agent-*.jsonl`

Useful search patterns (adjust keywords to the failure you are debugging):

```bash
grep -lc "marketplace.json\|claude plugin validate\|claude plugin install" \
  ~/.claude/projects/<escaped-cwd>/*.jsonl
grep -lc "Unrecognized key\|Plugin not found\|No manifest found\|Duplicate plugin" \
  ~/.claude/projects/<escaped-cwd>/*.jsonl \
  ~/.claude/projects/<escaped-cwd>/*/subagents/*.jsonl
```

Extract lessons as evidence-backed rules: command attempted, observed output, root
cause, final working command/config. Do not encode guesses from memory.
