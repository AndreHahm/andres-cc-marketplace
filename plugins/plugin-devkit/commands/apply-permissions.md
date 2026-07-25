---
description: >-
  Write confirmed permission entries from verify-permissions into settings.local.json
  (default) or settings.json (explicit promotion only), gated by tiered confirmation.
argument-hint: "--report <path>"
allowed-tools: Read Write Edit Bash(mkdir:*) Bash(date:*)
model: sonnet
---

Apply a verified permission classification report by writing confirmed entries to the appropriate settings file(s): $ARGUMENTS

> **Invocation:** Run as `/apply-permissions --report ...` in the Claude Code prompt. This command cannot be invoked via `Skill()` — it must be triggered as a slash command or followed manually.

> **Pipeline:** Step 3 of 3 (final). Reads a classification report from `/verify-permissions` and writes the confirmed entries.

**Output file policy:** creates a fresh timestamped backup of every file it is about to write (`.claude/settings.local.json.bak-<timestamp>`, and `.claude/settings.json.bak-<timestamp>` if any entry is promoted) before writing anything.

---

## Step 1: Parse Arguments and Load Report

| Argument | Required | Default | Notes |
|---|---|---|---|
| `--report` | Yes | — | Path to a `verify-<timestamp>.md` report from `/verify-permissions` |

If `--report` is missing or doesn't exist, stop and print:
```
Usage: /apply-permissions --report <path-to-verification-report>

No verification report found. Run /verify-permissions first.
```

Read the report fully. Parse the **New Candidates** table (pattern, classification, reason) and the **Existing Entries Requiring Reclassification** table (file, current bucket, pattern, recommended bucket, reason).

## Step 2: Present and Confirm

Group the report's rows into:
- **Safety fixes** — every row in Existing Entries Requiring Reclassification (all move an entry toward more caution: `allow`→`ask`, `allow`→`deny`, or a rare `deny`/`ask`→`allow` the report explicitly flagged as over-restrictive) plus every New Candidate classified `ask` or `deny`.
- **New allow entries** — New Candidates classified `allow`. This is the autonomy-increasing direction, kept separate from the safety fixes above.

Ask via `AskUserQuestion` as up to three separate questions, in increasing order of consequence — never bundle a later tier into an earlier yes/no:

1. Only if Safety Fixes is non-empty: "Apply N safety fixes (move existing entries toward ask/deny, add ask/deny entries for risky candidates)?" — recommend yes.
2. Only if New Allow Entries is non-empty: "Also add N new allow entries for low-risk candidates (reduces future permission prompts for these commands)?" — recommend yes, but state this trades a small amount of friction reduction for a small amount of standing autonomy; a genuine choice.
3. Only if any row's target file is `settings.json` (a user-requested promotion, not the default target): "Also write N entries to the shared, version-controlled settings.json — this affects every developer and CI, not just this machine?" — no default recommendation.

If all answers decline, state "No changes made." and stop.

## Step 3: Backup

Get the current timestamp (`date "+%Y%m%d-%H%M%S"`). Copy `.claude/settings.local.json`'s exact current content to `.claude/settings.local.json.bak-<timestamp>`. If any confirmed row targets `settings.json`, also back it up the same way before touching it.

## Step 4: Write

For each confirmed row, add or move the entry in the correct file's `permissions.allow`/`ask`/`deny` array:
- New entries default to `.claude/settings.local.json` unless the user confirmed promotion to `.claude/settings.json` in Step 2's third question.
- A reclassified existing entry is removed from its current bucket and added to its recommended bucket, in the same file it was already in — reclassification never moves an entry between `settings.local.json` and `settings.json` on its own; that's a separate, explicit promotion decision.

Preserve array order and existing JSON formatting/indentation for everything else untouched, matching `trim-permissions`' own write discipline. Validate every rewritten file is well-formed JSON before considering the write complete — if parsing fails, restore from the backup and report the failure instead of leaving a broken file in place.

## Step 5: Report

```
Backups: .claude/settings.local.json.bak-<timestamp> [, .claude/settings.json.bak-<timestamp>]
settings.local.json — allow: {before}→{after}, ask: {before}→{after}, deny: {before}→{after}
settings.json        — allow: {before}→{after}, ask: {before}→{after}, deny: {before}→{after}  (only if touched)
Applied: {n} safety fixes, {n} new allow entries, {n} promoted to settings.json
Declined: {n}
```

If the resulting `settings.local.json` now has 3 or more entries that look like exact duplicates or are subsumed by a broader pattern just added, note it as a one-line suggestion: "Consider running `/trim-permissions` to clean up N newly-redundant entries." — do not run it automatically.
