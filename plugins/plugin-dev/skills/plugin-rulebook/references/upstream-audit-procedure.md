# Upstream Audit Procedure

The `plugin-rulebook` is the **leading source** for all plugin component rules. Upstream sources do not overwrite the rulebook automatically — when an upstream source changes, audit the rulebook to identify gaps, then resolve each gap explicitly with the user.

## Audit Procedure

When a tracked upstream source changes:

1. Read the changed upstream source.
2. Compare each affected rulebook rule against the upstream change and list all gaps.
3. Before presenting a gap to the user, check `{REPO_ROOT}/.claude/plugin-rulebook-audit-decisions.md` — if the same gap was already decided, apply the prior decision without asking again.
4. For each new (undecided) gap, present the user with:
   - The rule ID and upstream source name
   - A one-line description of the difference
   - Three choices: **1. Keep plugin-rulebook** / **2. Keep `<upstream-source>`** / **3. Keep both**
5. Apply the chosen resolution:
   - Choice 1 → overwrite the upstream source with the rulebook's version
   - Choice 2 → update the rulebook rule to match the upstream source
   - Choice 3 → preserve both; record the intentional divergence
6. Append each decision to `{REPO_ROOT}/.claude/plugin-rulebook-audit-decisions.md`:

```
## <YYYY-MM-DD> — <rule-id> vs <upstream-source>
Gap: <one-line description of the difference>
Decision: Keep rulebook | Keep <upstream-source> | Keep both
Rationale: <user's reason, or "none given">
```

7. Update `_meta.last_reviewed` in `${CLAUDE_SKILL_DIR}/assets/settings.json`.

## Tracked Upstream Sources

| Upstream source | Rules affected |
|---|---|
| `skill-development/references/size-limits.md` | R13, R18 — line count and code block thresholds |
| `skill-reviewer` severity-tier logic | R13, R18 — tier boundary alignment |
| Platform frontmatter field list | R5 — forbidden field list |
| Platform tool-scoping syntax | R6 — format and scope rules |
| Platform `description`/`when_to_use` combined listing cap | R21 — combined max_length threshold (the 80/1024/512 sub-limits are internal policy layered on top; only the 1536 combined cap is platform-anchored) |
| Platform `\$ARGUMENTS`/`$N`/`$name` substitution semantics (0-based positional indexing) | R22 — detection procedure and the "positional placeholders are 0-based" reminder |

**Last reviewed:** 2026-07-02 — see `assets/settings.json → _meta.last_reviewed` for the authoritative date.
