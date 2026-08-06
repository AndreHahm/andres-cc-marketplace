---
name: "source-command-trim-permissions"
description: "Consolidate .Codex/settings.local.json's permission allowlist"
---

# source-command-trim-permissions

Use this skill when the user asks to run the migrated source command `trim-permissions`.

## Command Template

Consolidate `.Codex/settings.local.json`'s `permissions.allow`/`deny`/`ask` arrays: find exact duplicates, entries already covered by a broader wildcard pattern already in the same list, and likely one-off literal commands (tiered by confidence), then remove only what the user confirms.

> **Invocation:** Run as `/trim-permissions` in the Codex prompt. This command cannot be invoked via `Skill()` — it must be triggered as a slash command or followed manually.

**Output file policy:** creates a fresh timestamped backup (`.Codex/settings.local.json.bak-<timestamp>`) on every run before writing anything; rewrites only `.Codex/settings.local.json`'s three permission arrays — never touches `.Codex/settings.json` (shared, version-controlled) or any other permission scope.

---

## Step 1: Load

Read `.Codex/settings.local.json`. If it doesn't exist, state "No `.Codex/settings.local.json` found — nothing to trim." and stop. Parse `permissions.allow`, `permissions.deny`, `permissions.ask` (each may be absent — treat a missing array as empty, not an error).

## Step 2: Detect Categories

For each of the three arrays independently:

**A. Exact duplicates** — the identical string appears 2+ times. Always safe to reduce to one instance.

**B. Subsumed by a broader pattern already in the same array** — applies to `Bash(...)` entries only. An entry `Bash(<prefix> *)` (an open wildcard scope) makes any *other* entry redundant if that other entry's own content starts with `<prefix> ` (prefix followed by a space) — this applies whether the other entry is a fully-literal command or itself a narrower wildcard (e.g. `Bash(python3 *)` subsumes both a literal `Bash(python3 "/some/exact/path.py")` and the narrower wildcard `Bash(python3 -c ' *)`, since anything the narrower pattern matches, the broader one already matches too). Only flag a match when the shared prefix is character-for-character identical — never attempt fuzzy or semantic matching. `Bash(python *)` does **not** subsume `Bash(python3 ...)` — `python3` is not `python` followed by a space, it's a different literal command name.

**C. Likely one-off literal commands** (lower confidence — always its own separate category, never bundled with A/B) — any `Bash(...)` entry that does not end in a wildcard (` *)`) and is not already caught by category B. In practice this is most of a typical `settings.local.json`: fully-specified commands from a single past task (a `cp`/`mkdir`/`rm` naming an exact file or directory, a one-off `awk`/`grep`/`sed` invocation, a literal `echo` string). Sub-classify for the user's benefit when presenting, but treat as one category for the confirmation gate:

  - **Higher-confidence** (contains a UUID, a temp/scratchpad path like `AppData\Local\Temp\Codex\` or `/tmp/`, or a dated one-off directory name matching `-20\d\d-\d\d-\d\d`) — essentially certain to never recur verbatim.
  - **Lower-confidence** (any other non-wildcard entry, e.g. a plain version-check like `Bash(jq --version)` or a file-bound command with no obvious one-off marker) — probably a one-off, but a small number of these could still be reused verbatim in a future session.

  This category will typically be the large majority of the file's entries — that's expected, not a bug in the detection. It is never auto-removed regardless of size; the user sees the full breakdown before confirming.

## Step 3: Present and Confirm

Present each category (A, B, C-higher-confidence, C-lower-confidence) with its count and the actual entries (cap displayed entries at 15 per category with a "+N more" note if longer). Ask via `AskUserQuestion` as up to three separate questions, in increasing order of risk — never bundle a riskier tier into the same yes/no as a safer one:

1. "Remove exact duplicates and subsumed entries (A+B)?" — deterministic, recommend yes.
2. Only if C-higher-confidence is non-empty: "Also remove the N higher-confidence one-off entries (UUID/temp-path/dated-folder)?" — recommend yes.
3. Only if C-lower-confidence is non-empty: "Also remove the N lower-confidence one-off entries (any other non-wildcard command — review the list above first, a few could still be reused verbatim)?" — no default recommendation; present as a genuine choice.

If all answers decline, state "No changes made." and stop.

## Step 4: Backup and Rewrite

Get the current timestamp (`date "+%Y%m%d-%H%M%S"`). Copy the current file's exact content to `.Codex/settings.local.json.bak-<timestamp>` before any edit. Remove only the confirmed entries from the confirmed categories, preserving array order and existing JSON formatting/indentation for everything else untouched. Validate the result is well-formed JSON before considering the write complete — if parsing the rewritten content fails, restore from the backup and report the failure instead of leaving a broken file in place.

## Step 5: Report

```
Backup: .Codex/settings.local.json.bak-<timestamp>
permissions.allow: {before} → {after} entries ({removed} removed: {dup} duplicate, {subsumed} subsumed, {oneoff_high} higher-confidence one-off, {oneoff_low} lower-confidence one-off)
permissions.deny:  {before} → {after} entries (...)
permissions.ask:   {before} → {after} entries (...)
```
