---
description: >-
  Find a plugin-dev rule by name, value, or behavior across the codebase, show every place
  it's defined, and check its status against current official Claude Code documentation.
argument-hint: <rule name, value, or behavior description>
allowed-tools: Read Glob Grep WebFetch WebSearch Skill(upstream-sources-registry)
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

**Pre-flight (standalone invocation only):** Step 2 can surface more than one distinct rule, and each one triggers its own `Skill(upstream-sources-registry)`/`WebSearch`/`WebFetch` call below — an unbounded per-rule external-call fan-out. When this command is run directly (`/find-dev-rule <query>`), print the count of distinct rules found and wait for confirmation ("yes"/"y"/"proceed"/"ok") before proceeding; on any other answer, print "Cancelled." and stop. **Skip this pre-flight** when these Steps are being executed inline as part of `/update-dev-rule`'s own Step 1 — that command already gates the same fan-out with its own pre-flight immediately afterward, and a second prompt here would just double-confirm the identical action.

For each rule, invoke `Skill(upstream-sources-registry)` with the rule's topic to check whether a tracked source already covers it:
- If a tracked, enabled source matches, the registry returns either a fresh cached snapshot (no fetch needed) or runs its own freshness check and returns the current result — use that returned content as "the current official docs" for the comparison below.
- If no tracked source matches, fall back to `WebSearch`/`WebFetch` directly, same as before — an untracked topic is not itself grounds for `UNVERIFIABLE`, only an actual failed search is.

Do not answer from training-data memory in either path, since schemas, enums, and behavior evolve across releases and a rule correct yesterday can already be stale today. Compare every source value from Step 2 against the docs content obtained above and classify:

| Status | Meaning |
|---|---|
| `CONFIRMED` | Matches current official docs |
| `OUTDATED` | Official docs have changed since the rule was written |
| `MISSING` | Docs describe a field/value/behavior with no corresponding local rule at all |
| `CONFLICT` | Two or more local sources disagree with each other, regardless of what the docs say |
| `NOT-OFFICIAL` | Project-internal convention with no platform-doc equivalent — expected, not a defect |
| `UNVERIFIABLE` | No official documentation could be found covering this rule |

**Authority-tier gate:** when the registry path was used, it returns the source's `authority` tier alongside its content. A `changelog`/`informal`-tier source is corroborating evidence only — if that's the *only* source backing an `OUTDATED`/`MISSING` classification, classify it `UNVERIFIABLE` instead and note "informal-only, needs spec/guide corroboration." Only a `spec`/`guide`-tier source is sufficient to classify `OUTDATED`/`MISSING` on its own.

Display one compact status line per rule:
```
{rule name}: {STATUS} — {one-line reason, citing the doc excerpt or the disagreeing sources}
```

For `OUTDATED` or `MISSING`, include what the official docs currently say, so there's enough here to act on with `/update-dev-rule` without re-researching. If the registry path was used, also note which tracked source `id` and `authority` tier supplied the answer.
