# Results File Schema

Location: `~/.claude/skills/skill-stocktake/results.json`

## Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `evaluated_at` | ISO 8601 UTC | Actual UTC time of evaluation completion. **Never** approximate with `T00:00:00Z` — obtain via `date -u +%Y-%m-%dT%H:%M:%SZ`. |
| `mode` | string | `"full"` or `"quick"` |
| `batch_progress.total` | number | Total skills discovered |
| `batch_progress.evaluated` | number | Skills evaluated so far |
| `batch_progress.status` | string | `"in_progress"` or `"completed"` |
| `skills[name].path` | string | Full path to the SKILL.md file |
| `skills[name].verdict` | string | Keep / Improve / Update / Retire / Merge into [X] |
| `skills[name].reason` | string | Self-contained rationale — see `evaluation-guide.md` for quality rules |
| `skills[name].mtime` | ISO 8601 UTC | File modification time at evaluation |

## Example

```json
{
  "evaluated_at": "2026-02-21T10:00:00Z",
  "mode": "full",
  "batch_progress": {
    "total": 80,
    "evaluated": 80,
    "status": "completed"
  },
  "skills": {
    "skill-name": {
      "path": "~/.claude/skills/skill-name/SKILL.md",
      "verdict": "Keep",
      "reason": "Concrete, actionable, unique value for X workflow",
      "mtime": "2026-01-15T08:30:00Z"
    }
  }
}
```
