---
title: Check Git Status Before Discarding Changes
impact: CRITICAL
---

# Check Git Status Before Discarding Changes

Before running any command that discards uncommitted changes (`git checkout -- <path>`,
`git restore`, `git reset --hard`), Claude MUST first run `git status` and `git diff` on the
target path to see exactly what is currently uncommitted. A phrase like "discard my last edit"
names an *intent*, not a precise git selector — never assume it maps to "wipe the whole file's
working-tree state" without first confirming that's all there is to lose.

## Incorrect

Jumps straight to the destructive command because the user said "last edit," without checking
what's actually sitting uncommitted in the file:

```
User: discard my last edit to src/utils.py
Assistant: git checkout -- src/utils.py
```

If `src/utils.py` also carried other uncommitted changes — an earlier edit from the same session,
a change from a different tool call, anything not yet committed — `git checkout --` destroys all
of it at once, irreversibly, when the user only asked for one edit to be undone.

## Correct

Checks status and diff first, confirms what would actually be lost, and only then acts —
scoping the action to what was asked, or asking the user when the working tree holds more than
"the last edit":

```
User: discard my last edit to src/utils.py
Assistant: git status src/utils.py
Assistant: git diff src/utils.py
# Diff shows two unrelated hunks: an earlier refactor (lines 10-20) and a newer
# change (lines 45-50) — more than just "the last edit" is uncommitted.
Assistant: "src/utils.py has two separate uncommitted changes, not one — an edit to
  lines 10-20 and one to lines 45-50. Which one is 'your last edit'? Discarding the
  whole file would wipe both."
```

If the diff shows exactly one change matching what the user described, proceed with the
discard — the check is what justifies running the destructive command, not a reason to stall
on every request.

## Enforcement

No automated hook backs this rule — `git checkout --`/`git restore`/`git reset --hard` are
legitimate commands in many contexts, and nothing can mechanically distinguish "the user meant
to wipe everything uncommitted here" from "the user meant only their last edit." Compliance
depends on agent discipline at execution time, the same disclosed-limitation model
`recheck-state-before-side-effecting-action.md` uses for its own pre-action state check.

## Why

Discarding uncommitted work is irreversible outside editor undo history, and "my last edit" is a
natural-language description, not a git ref — a working tree can accumulate more than one
uncommitted change to the same file before a discard is ever requested. Running the destructive
command without first looking treats the whole file as the unit of discard by default, with no
way to recover whatever else was silently lost along with it.
