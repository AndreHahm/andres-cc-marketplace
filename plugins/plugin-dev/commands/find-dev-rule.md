---
description: >-
  Find a plugin-dev rule by name, value, or behavior across the codebase, show every place
  it's defined, and check its status against current official Claude Code documentation.
argument-hint: <rule name, value, or behavior description>
allowed-tools: Read Glob Grep WebFetch WebSearch
model: opus
---

Find a rule and check its status against official docs: $ARGUMENTS

> **Invocation:** Run as `/find-dev-rule <query>` in the Claude Code prompt. Read-only — makes no changes. Use `/update-dev-rule` to fix what this finds stale.

---

## Step 1: Find Rule(s) by Name, Value, or Behavior

`$ARGUMENTS` is the query — a field/rule name (e.g. "permissionMode", "R13"), a specific value (e.g. "magenta", "1024"), or a behavior description (e.g. "can subagents spawn nested subagents").

Choose search terms by query shape:
- **Name-shaped** (a field/identifier with no spaces): `Grep` the literal identifier.
- **Value-shaped** (a specific literal string or number): `Grep` that literal value.
- **Behavior-shaped** (a natural-language description): extract 2–4 keywords and `Grep` each; broaden with synonyms if the first pass returns too few hits.
- **Positional/argument-semantics queries** (the query concerns `arguments`, `argument-hint`, `\$ARGUMENTS`, or how positional substitution works): field-name/value greps only confirm the field *exists* — they miss whether worked examples use it *correctly*. Also grep for `$[0-9]` and `\$ARGUMENTS` usage inside SKILL.md/command-file bodies and reference examples, and check each hit against the platform's actual convention (0-based: `\$0` is the first argument) — a file can declare the right field and still demonstrate the wrong semantics.

Search across: `skills/*/SKILL.md`, `skills/*/references/*.md`, `agents/*.md`, `commands/*.md`, `hooks/hooks.json` and hook scripts, validator scripts (`*.sh`, `*.py`), `assets/settings.json` or similar structured config, and `.claude/rules/*.md`. Also check project-scope and user-scope shadow locations outside any plugin — `{CWD}/.claude/skills/`, `{CWD}/.claude/agents/`, `{CWD}/.claude/commands/`, `~/.claude/skills/`, `~/.claude/agents/`, `~/.claude/commands/` — the same rule name can exist as an independently-maintained copy there.

Group matches by distinct rule/topic — a query can match more than one unrelated rule; keep them separate. If nothing matches, print "No rule found matching '{query}'." and stop. Do not guess at a fuzzy match.

---

## Step 2: Display Found Rule(s) with Short Explanation

For each distinct rule found, display:

```
Rule: {name/topic}
Sources:
  {file}:{line} — {exact value/text stated there}
  ...
Explanation: {1-3 sentences on what this rule governs and why, from surrounding context — don't invent a rationale that isn't there}
```

If two or more sources state different values for what should be the same rule, say so here immediately as an internal conflict — don't wait for Step 3 to surface it.

---

## Step 3: Verify Rule Against Official Docs, and Display Status

For each rule, locate the current official Claude Code documentation covering it via `WebSearch`/`WebFetch` — do not answer from training-data memory, since schemas, enums, and behavior evolve across releases and a rule correct yesterday can already be stale today. Compare every source value from Step 2 against the docs and classify:

| Status | Meaning |
|---|---|
| `CONFIRMED` | Matches current official docs |
| `OUTDATED` | Official docs have changed since the rule was written |
| `MISSING` | Docs describe a field/value/behavior with no corresponding local rule at all |
| `CONFLICT` | Two or more local sources disagree with each other, regardless of what the docs say |
| `NOT-OFFICIAL` | Project-internal convention with no platform-doc equivalent — expected, not a defect |
| `UNVERIFIABLE` | No official documentation could be found covering this rule |

Display one compact status line per rule:
```
{rule name}: {STATUS} — {one-line reason, citing the doc excerpt or the disagreeing sources}
```

For `OUTDATED` or `MISSING`, include what the official docs currently say, so there's enough here to act on with `/update-dev-rule` without re-researching.
