# Date-Range Scope Convention

Canonical Phase 1 scope-resolution procedure shared by all 5 date-range report-producing skills
(`analyzing-plugin-components`, `analyzing-tool-and-framework-use`, `analyzing-actor-behavior`,
`analyzing-governance-and-conflicts`, `mining-recurring-patterns`). This file is the source of truth —
if this procedure changes, sweep every site listed below (R20-style) rather than editing one copy and
leaving the rest stale.

## Procedure

If a scope was supplied as an argument (a date string, `"today"`, `"this conversation"`, or similar),
skip the question UI and proceed directly to the next phase using that argument as the scope.

Ask for the session range only when no argument was provided:

```
questions: [
  {
    question: "What should this analysis cover?",
    header: "Session scope",
    options: [
      { label: "This conversation", description: "Analyze only the current conversation context" },
      { label: "From a start date", description: "Provide a YYYY-MM-DD start date; analysis runs through today" },
      { label: "Today", description: "All sessions from today (default)" }
    ],
    multiSelect: false
  }
]
```

If "From a start date" → ask for the date. If sessions from prior conversations are in scope, first try
`python "${CLAUDE_PLUGIN_ROOT}/scripts/session_parser.py" --project-root . --since <start-date>` to load
real session data for the range. If it reports `no_session_files_found` or a parse error, and the user
names a specific Codex session file, try
`python "${CLAUDE_PLUGIN_ROOT}/scripts/codex_session_parser.py" --session-file <path>` instead. If
neither produces usable events, fall back to asking the user to paste in relevant transcript excerpts
or summaries — Claude cannot read past conversation history directly, and not every machine retains
session files for the requested range.

## Sites That Restate This

Every site below must match this procedure. If you change it here, update all of them in the same pass.
Paths are relative to `plugins/analysis-kit/`. Each site's own skill-specific addendum (a clause this
skill alone needs beyond the shared procedure) stays inline in that skill's own Phase 1 — only the
shared procedure itself lives here.

- `skills/analyzing-tool-and-framework-use/SKILL.md` Phase 1 — no addendum, procedure only
- `skills/analyzing-governance-and-conflicts/SKILL.md` Phase 1 — no addendum, procedure only
- `skills/analyzing-actor-behavior/SKILL.md` Phase 1 — addendum: actor identity (role, `is_subagent`)
  and rough turn-taking are derivable from `session_parser.py`'s normalized event list
- `skills/mining-recurring-patterns/SKILL.md` Phase 1 — addendum: `session_parser.py`'s output also
  feeds Phase 4's skill-level usage ranking
- `skills/analyzing-plugin-components/SKILL.md` Phase 1 — procedure only; this skill's own Phase 1 adds
  further *sequential* steps after it (a timezone pitfall note, the narrow-scope gap-awareness check,
  the sibling-scope-overlap check), not an inline addendum to the procedure itself
- `skills/mining-review-learnings/SKILL.md` — deliberately **not** a site. Its own Phase 1 cites this
  file only to distinguish its merge-date PR filter from this shared session/conversation scope
  procedure — it never resolves a session scope itself, so it restates nothing from here to keep in
  sync.
