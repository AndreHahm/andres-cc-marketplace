---
name: skill-stocktake
description: >-
  Audits Claude skills and commands for quality, freshness, and overlap. Use
  when running a skill audit, doing a stocktake of all skills, reviewing which
  skills to keep or retire, checking for stale or redundant skills, or
  evaluating skill quality across a project. Supports Quick Scan (changed
  skills only, 5–10 min) and Full Stocktake (complete review, 20–30 min).
allowed-tools: Read Agent WebSearch Skill
---

# skill-stocktake

Audits all Claude skills and commands using a quality checklist + AI holistic judgment. Supports two modes: Quick Scan for recently changed skills, and Full Stocktake for a complete review.

**Core principle:** Evaluation is blind — the same checklist applies to all skills regardless of origin. Archive/delete operations always require explicit user confirmation.

## Quick Start

1. **First run (Full Stocktake):** invoke `/skill-stocktake` from your project root — no `results.json` exists yet, so Full Stocktake runs automatically
2. **Subsequent runs (Quick Scan):** invoke `/skill-stocktake` — detects `results.json` and scans only changed skills
3. **Force full re-scan:** invoke `/skill-stocktake full`

## When to Use

- Periodic quality reviews of your skill library (monthly or after major skill additions)
- Before publishing or sharing skills with a team
- When skills feel stale, overlapping, or confusing to use
- After a batch of new skills has been created

## When NOT to Use

- For deep improvement of a single skill — use `/skill-refiner-interactive` instead
- For creating new skills to fill gaps identified by the stocktake — use `skill-development` instead
- For individual skill editing or quick fixes

## Scope

The command targets the following paths **relative to the directory where it is invoked**:

| Path | Description |
|------|-------------|
| `~/.claude/skills/` | Global skills (all projects) |
| `{cwd}/.claude/skills/` | Project-level skills (if the directory exists) |

**At the start of Phase 1, the command explicitly lists which paths were found and scanned.**

### Targeting a specific project

To include project-level skills, run from that project's root directory:

```bash
cd ~/path/to/my-project
/skill-stocktake
```

If the project has no `.claude/skills/` directory, only global skills are evaluated.

## Modes

| Mode | Trigger | Duration |
|------|---------|---------|
| Quick Scan | `results.json` exists (default) | 5–10 min |
| Full Stocktake | `results.json` absent, or `/skill-stocktake full` | 20–30 min |

**Results cache:** `~/.claude/skills/skill-stocktake/results.json`

## Quick Scan Flow

Re-evaluate only skills that have changed since the last run (5–10 min).

1. Read `~/.claude/skills/skill-stocktake/results.json`
2. Run: `bash ~/.claude/skills/skill-stocktake/scripts/quick-diff.sh \
         ~/.claude/skills/skill-stocktake/results.json`
   (Project dir is auto-detected from `$PWD/.claude/skills`; pass it explicitly only if needed)
3. If output is `[]`: report "No changes since last run." and stop
4. Re-evaluate only those changed files using the same Phase 2 criteria
5. Carry forward unchanged skills from previous results
6. Output only the diff
7. Run: `bash ~/.claude/skills/skill-stocktake/scripts/save-results.sh \
         ~/.claude/skills/skill-stocktake/results.json <<< "$EVAL_RESULTS"`

## Full Stocktake Flow

### Phase 1 — Inventory

Run: `bash ~/.claude/skills/skill-stocktake/scripts/scan.sh`

The script enumerates skill files, extracts frontmatter, and collects UTC mtimes.
Project dir is auto-detected from `$PWD/.claude/skills`; pass it explicitly only if needed.
Present the scan summary and inventory table from the script output:

```
Scanning:
  ✓ ~/.claude/skills/         (17 files)
  ✗ {cwd}/.claude/skills/    (not found — global skills only)
```

| Skill | 7d use | 30d use | Description |
|-------|--------|---------|-------------|

### Phase 2 — Quality Evaluation

Launch a **general-purpose** subagent. Substitute `[INVENTORY]` with the Phase 1 scan table, and `[CHECKLIST]` with the 4-item evaluation checklist below.

```text
Agent(
  subagent_type="general-purpose",
  prompt="
Evaluate the following skill inventory against the checklist.

[INVENTORY — paste Phase 1 scan table here]

[CHECKLIST — paste the 4-item checklist below]

Return JSON for each skill:
{ \"verdict\": \"Keep\"|\"Improve\"|\"Update\"|\"Retire\"|\"Merge into [X]\", \"reason\": \"...\" }
"
)
```

**Chunk guidance:** Process ~20 skills per subagent invocation. Save intermediate results to `results.json` (`status: "in_progress"`) after each chunk. After all skills: set `status: "completed"` and proceed to Phase 3.

**Resume detection:** If `status: "in_progress"` is found on startup, resume from the first unevaluated skill.

**Evaluation checklist:**

```
- [ ] Content overlap with other skills checked
- [ ] Overlap with MEMORY.md / CLAUDE.md checked
- [ ] Freshness of technical references verified (use WebSearch if tool names / CLI flags / APIs are present)
- [ ] Usage frequency considered
- [ ] Rule compliance verified — invoke `plugin-rulebook` skill for naming, tool-scoping, language, and formatting checks
```

**Verdict criteria:**

| Verdict | Meaning |
|---------|---------|
| Keep | Useful and current |
| Improve | Worth keeping, but specific improvements needed |
| Update | Referenced technology is outdated (verify with WebSearch) |
| Retire | Low quality, stale, or cost-asymmetric |
| Merge into [X] | Substantial overlap with another skill; name the merge target |

**Evaluation dimensions** (holistic AI judgment — not a numeric rubric):
- **Actionability**: code examples, commands, or steps that let you act immediately
- **Scope fit**: name, trigger, and content are aligned; not too broad or narrow
- **Uniqueness**: value not replaceable by MEMORY.md / CLAUDE.md / another skill
- **Currency**: technical references work in the current environment

**Reason quality:** The `reason` field must be self-contained and decision-enabling — never write "unchanged" or "superseded" alone. For bad/good examples by verdict type, see `references/evaluation-guide.md`.

### Phase 3 — Summary Table

| Skill | 7d use | Verdict | Reason |
|-------|--------|---------|--------|

### Phase 4 — Consolidation

1. **Retire / Merge**: present detailed justification per file before confirming with user:
   - What specific problem was found (overlap, staleness, broken references, etc.)
   - What alternative covers the same functionality (for Retire: which existing skill/rule; for Merge: the target file and what content to integrate)
   - Impact of removal (any dependent skills, MEMORY.md references, or workflows affected)
2. **Improve**: present specific improvement suggestions with rationale:
   - What to change and why (e.g., "trim 430→200 lines because sections X/Y duplicate python-patterns")
   - User decides whether to act; to action improvements, invoke `/skill-refiner-interactive` on the target skill
3. **Update**: present updated content with sources checked
4. Check MEMORY.md line count; propose compression if >100 lines

## Results File

Results are saved to `~/.claude/skills/skill-stocktake/results.json`. See `references/results-schema.md` for the full JSON schema and field reference.

**Key requirement:** `evaluated_at` must be the actual UTC completion time — obtain via `date -u +%Y-%m-%dT%H:%M:%SZ`. Never use a date-only approximation like `T00:00:00Z`.

## Testing & Validation

After a stocktake run, verify:

1. **Consistency** — re-run Quick Scan on an unchanged skill library; expect "No changes since last run."
2. **Reason quality** — spot-check 3 reasons; confirm each names specific evidence, not vague labels
3. **Schema integrity** — validate `results.json` has `evaluated_at`, `mode`, `batch_progress`, and `skills` keys
4. **Completeness** — confirm `batch_progress.total` equals `batch_progress.evaluated` when `status: "completed"`
5. **Scope accuracy** — confirm the Phase 1 summary correctly lists which paths were found and skipped

**Quality gates:**
- [ ] All Retire / Merge verdicts have explicit user confirmation before any deletion
- [ ] `results.json` `status` is `"completed"` before presenting the Phase 3 summary
- [ ] WebSearch was used for any skill referencing versioned CLI tools, APIs, or specific flags

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/evaluation-guide.md` | Reason quality examples per verdict type |
| `references/results-schema.md` | Full JSON schema and field reference for `results.json` |
| `plugin-rulebook` skill | Active rule configuration and compliance check (naming, tool-scoping, language, formatting) |

## Notes

- Archive / delete operations always require explicit user confirmation
- No verdict branching by skill origin
