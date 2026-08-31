## Summary
`marketplace-inventory`'s (and `plugin-inventory`'s) import-grading command records each scoring
history entry's `report_path` as a workstation-specific absolute path, not portable across checkouts.

## Context
- **Product/Service**: `plugin-devkit`'s `marketplace-inventory` skill (and `plugin-inventory`'s
  equivalent), `.claude-plugin/marketplace-inventory.json`
- **Related work**: found via an automated Devin review on `workmanagement-kit`'s PR #255

## What Happened

`marketplace-inventory`'s import-grading command writes each `scoring_history`/
`security_scoring_history` entry's `report_path` field as a literal absolute filesystem path from
whatever machine/checkout ran the import. `.claude-plugin/marketplace-inventory.json` currently
contains a real example:

```
"report_path": "C:/Dev/Repos/andres-cc-marketplace/.claude/worktrees/workmanagement-kit-wave1-scaffold/.claude/output/plugin-grader/workmanagement-kit-2026-08-31T04-34-07Z.json"
```

This is a per-session worktree path that won't exist on the main checkout, a fresh clone, or another
contributor's machine. This makes `report_path` useless as committed evidence for anyone reading the
inventory from a different checkout — `report_sha256` (also recorded on the same entry) is the only
actually-portable piece of evidence; `report_path` only works for whoever happened to run the grading
pass, on that same machine, before the worktree/output directory gets cleaned up.

## Proposed Fix

Record `report_path` as repo-relative (e.g. `.claude/output/plugin-grader/<file>.json`, a stable
relative location regardless of which checkout/worktree ran the grading), or drop the field entirely
and rely on `report_sha256` plus the grading report's own content as the portable record.

## Impact
**Low** — no functional gap in the inventory's own scoring data (`report_sha256` still provides a
portable integrity check), but the `report_path` field is misleading to any reader who isn't on the
exact machine/checkout that produced it.

## Additional Context
Found by an automated Devin PR review on `workmanagement-kit`'s PR #255, flagged as an analysis
finding (not a blocker for that PR) since the fix belongs in `marketplace-inventory`/`plugin-inventory`'s
own import-grading scripts — a different plugin (`plugin-devkit`) — not in any file that PR's own
changes touch.

References: `plugins/plugin-devkit/skills/marketplace-inventory/` (and `plugin-inventory`'s
equivalent), `.claude-plugin/marketplace-inventory.json`'s real current content for a live example.
