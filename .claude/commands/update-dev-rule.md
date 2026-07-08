---
description: >-
  Find a stale plugin-dev rule, update it and every other rule it affects using the official
  docs recommendation, then check for and fix any resulting staleness.
argument-hint: <rule name, value, or behavior description>
allowed-tools: Read Write Edit Glob Grep WebFetch WebSearch Bash(date:*)
model: opus
---

Find a stale rule, fix it and everything it affects, then report every change: $ARGUMENTS

> **Invocation:** Run as `/update-dev-rule <query>` in the Claude Code prompt. Makes changes — unlike `/find-dev-rule`, which is read-only.

---

## Step 1: Find Stale Rule(s) by Name, Value, or Behavior Using find-dev-rule

Read `${CLAUDE_PLUGIN_ROOT}/commands/find-dev-rule.md` and execute its Steps 1–3 against `$ARGUMENTS`.

From the resulting classifications, treat `OUTDATED`, `MISSING`, and `CONFLICT` as **stale** — these need action. `CONFIRMED`, `NOT-OFFICIAL`, and `UNVERIFIABLE` need no update. If every found rule is one of these, print "No stale rule found matching '{query}'." and stop.

**Pre-flight:** print each stale rule, its sources, and the planned correction (from the official-docs excerpt already gathered). Wait for confirmation ("yes"/"y"/"proceed"/"ok") before making any changes; on any other answer, print "Cancelled." and stop.

---

## Step 2: If Rule Status Is Stale, Update Rule with Official Docs Recommendation

For each stale rule confirmed in Step 1:

- Determine the corrected value/wording from the official-docs excerpt already gathered — do not re-derive it differently.
- For a `CONFLICT` rule with no docs discrepancy: if one source already matches the docs, correct the other source(s) to match it; if neither matches, correct all sources to the docs value.
- Apply the fix to **every** source location listed for that rule in Step 1's output — not just the first one found.
- Preserve each file's existing style and formatting; change only the specific value or wording needed, matching this codebase's surgical-edit convention. Do not rewrite or reformat surrounding content.
- Record for each edit: rule, file:line, old value, new value.

---

## Step 3: Detect All Other Affected Rules, and Update Them Too (If They Are Stale)

A single corrected value can make other rules stale even though they were never flagged directly — a count that references the changed enum (e.g. "one of 6 allowed values" needs to become "one of 8"), an example that names the old value as invalid, or a cross-reference to the rule just fixed. For each rule updated in Step 2:

- Search the codebase for other rules that reference, count, or derive from the value just changed — not just literal copies of the same value.
- Run each newly found rule through the same official-docs check as `find-dev-rule.md` Step 3.
- If stale, update it the same way as Step 2 and add it to the same change record. Repeat until no further affected rules are found — if fixing one derived rule makes yet another rule stale, follow the chain rather than stopping at one hop.

---

## Step 4: Perform a Staleness Check, and Update Found Staleness (If It's Directly or Indirectly Related with This Update)

For every value actually changed across Steps 2–3, grep the **entire codebase** — including shadow copies at project scope (`.claude/`), user scope (`~/.claude/`), and other plugins, not just the plugin being worked on — for the **old** value or phrase.

- Fix any hit that is directly or indirectly related to this update (the same fact, or a derived fact like a count or cross-reference), using the same official-docs-backed correction as Step 2.
- Flag, rather than silently fix, anything unrelated or requiring judgment — a different component type, or a value that may be intentionally divergent rather than stale.

Add every fix and every flagged item from this step to the running change record.

---

## Step 5: Report All Updates (Previous Value, Current Value, Evidence, Date and Time)

Get the current timestamp (`date "+%Y-%m-%d %H:%M"`). Print one block per file:line changed across Steps 2–4:

```
{rule}: {file}:{line}
  Previous: {old value}
  Current:  {new value}
  Evidence: {doc URL/excerpt, or the cross-rule dependency from Step 3 that justified the change}
  When:     {YYYY-MM-DD HH:MM}
```

Then a one-line summary:
```
Rules updated: {n} | Locations changed: {n} | Affected-rule chains followed: {n} | Flagged, not updated: {n}
```

If anything was flagged but not fixed (from Step 4), list those separately at the end under "Flagged, not updated" with the reason — do not let them be visible only in passing.
