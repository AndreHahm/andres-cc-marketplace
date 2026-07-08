# Argument Consistency (R22)

Checks that `argument-hint` and `arguments` frontmatter accurately describe the argument placeholders a SKILL.md or command file actually consumes in its body.

## Background: how argument substitution works

- `$ARGUMENTS` — the full raw input string, as typed after the command/skill name.
- `$ARGUMENTS[N]` / `$N` — a single positional argument, **0-based**: `$0`/`$ARGUMENTS[0]` is the first argument, `$1`/`$ARGUMENTS[1]` the second, and so on. `$N` is shorthand for `$ARGUMENTS[N]`.
- `$name` — a named argument, only resolved when `name` appears in the frontmatter `arguments` list; the list's order determines which position each name maps to (first name = position 0, second = position 1, ...).
- `argument-hint` — a free-form autocomplete string, typically written as ordered bracketed tokens (e.g. `[pr-number] [priority] [assignee]`). It doesn't feed substitution directly, but by convention its bracket order should match the order the body actually consumes positions in.

**The most common bug this rule catches:** treating `$1` as "the first argument" (1-based) instead of the second (0-based). If a file's `argument-hint` lists N bracketed tokens and the body uses `$1` through `$N` instead of `$0` through `$N-1`, every argument is shifted by one position — this is a wrong-position Critical, not a cosmetic issue.

## Detection Procedure

1. **Read the frontmatter.** Extract:
   - `argument-hint` — parse bracketed tokens `[...]` in the order they appear; each is a declared "slot."
   - `arguments` — parse the space-separated string or YAML list; each name is a declared "slot," in list order.
   - If both are present, prefer `arguments` for name-level checks (it's used for actual substitution); use `argument-hint`'s bracket order as a secondary cross-check on position.

2. **Scan the body for placeholders actually consumed:**
   - `$ARGUMENTS` (bare) — consumes "everything," not a specific slot.
   - `$ARGUMENTS[N]` or bare `$N` (digit immediately after `$`, not preceded by a backslash) — consumes slot N (0-based).
   - `$name` where `name` matches a declared `arguments` entry — consumes that name's slot.
   - Also check worked examples/invocation samples in the body prose (e.g. "`/deploy api staging` → deploys `api` to `staging`") — these describe the *intended* slot order even when the instructions only reference `$ARGUMENTS` generically.

3. **Classify:**
   - **No placeholders found anywhere in the body** → the file doesn't accept arguments; `argument-hint`/`arguments` being empty is correct (OK), and either being non-empty is a stale declaration (Critical — see below).
   - **Placeholders found, but `argument-hint` and `arguments` are both absent/empty** → Warning.
   - **A placeholder references a position ≥ the number of declared slots, or a `$name` not present in `arguments`** → Critical — missing argument (the body needs a slot that isn't declared).
   - **A declared slot (bracket token or name) is never referenced by any placeholder or worked example in the body** → Critical — stale/orphaned argument.
   - **The body's actual position for a slot disagrees with where `arguments`/`argument-hint` declares it** (most often the 0-based-vs-1-based shift described above) → Critical — wrong argument position.

## Worked Examples

**OK — declared and consumed consistently:**
```yaml
argument-hint: [pr-number] [priority]
arguments: [pr-number, priority]
```
Body: `Review PR #$pr-number with priority $priority.` (equivalently `$0`/`$1`) — both slots declared, both consumed, correct order.

**Warning — accepts arguments, nothing declared:**
```yaml
description: Summarize the given text
```
Body: `Summarize: $ARGUMENTS` — the body clearly accepts free-form input but there's no `argument-hint` to tell the user that, and no autocomplete hint.

**Critical — missing argument:**
```yaml
argument-hint: [file-path]
arguments: [file-path]
```
Body: `Review @$file-path for issues, categorized by $1.` — `$1` (second position) is consumed but only one slot (`file-path`) is declared.

**Critical — stale/orphaned argument:**
```yaml
argument-hint: [environment] [version]
arguments: [environment, version]
```
Body: `Deploy the app to $environment.` — `version` is declared but never referenced anywhere in the body.

**Critical — wrong argument position (the 0-based/1-based shift):**
```yaml
argument-hint: [pr-number] [priority] [assignee]
```
Body: `Review PR #$1 with priority $2. Assign to $3.` — three slots are declared via `argument-hint`, but the body reads them as `$1`/`$2`/`$3` (second/third/fourth position) instead of `$0`/`$1`/`$2` (first/second/third). Every argument the user types lands one position later than intended, and whatever fills `$3` was never declared at all (compounding into a missing-argument Critical too).
