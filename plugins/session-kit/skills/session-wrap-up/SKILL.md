---
name: session-wrap-up
description: >-
  End-of-session ritual that audits git status informationally, captures
  learnings, and produces a session summary with next-session context. Use
  when the user says "wrap up", "done for the day", "finish coding", or wants
  to end a coding session with a clean summary. For creating a persisted
  handoff document a fresh agent can load later, use session-handoff instead
  -- this skill suggests it as a follow-up, not a replacement.
allowed-tools: Bash(git status:*) Bash(git diff:*)
---

# Session Wrap-Up

End your coding session with intention.

## When to Use

- Ending a session, saying "wrap up", "done for now", "finish coding"
- Wants a consistent close-out: what changed, what was learned, what's next

## When NOT to Use

- Creating a persisted handoff document for a fresh agent to load later — use `session-handoff`
  instead; this skill suggests it as a follow-up rather than duplicating it
- Running quality gates (lint/typecheck/test) before committing — use `git-kit`'s `commit` skill
  instead. This skill only *reads* git state informationally; it never re-runs project checks, and
  never assumes a specific toolchain (npm, uv, or otherwise)

## Workflow

### Step 1: Changes Audit (informational only)

```bash
git status
git diff --stat
```

Note uncommitted changes and any TODOs left in code touched this session. If uncommitted changes
exist, mention that `git-kit`'s `commit` skill is how to actually commit them and run its quality
gates — don't offer to run lint/typecheck/test here.

### Step 2: Learning Capture

What mistakes were made? What patterns worked well? Format each as `[LEARN] Category: Rule`.

Categories: Navigation, Editing, Testing, Git, Quality, Context, Architecture, Performance.

### Step 3: Next Session Context

What's the next logical task? Any blockers? What context needs to be preserved?

### Step 4: Summary

One paragraph: what was accomplished, current state, what's next.

### Step 5: Suggest a Handoff

If this session did substantial work (5+ file edits, complex debugging, an architecture decision),
suggest: "Consider creating a handoff document to preserve this context — say 'create handoff' when
ready." (points at the `session-handoff` skill; do not create the handoff yourself here)

## Guardrails

- Do not skip any workflow step.
- If uncommitted changes exist, use `AskUserQuestion` to ask whether to commit (via `git-kit`) or leave
  them — never a printed "(yes/no)" prompt, and don't decide silently.

## Output

- Modified file list with uncommitted changes highlighted (informational)
- Captured learnings, if any
- One-paragraph session summary
- Next-session resume context
- Handoff suggestion, if warranted

After completing the ritual, use `AskUserQuestion` to ask: "Ready to end session?" — never a printed
"(yes/no)" prompt.

## Testing & Validation

Eval suite: `evals/session-wrap-up/` — 2 scenarios, `skill-tester` Quick Workflow blind comparison.
Eval 1 (informational audit, 4/4 assertions) passed fully. Eval 2 (declining a lint/commit request,
3/4 assertions) recorded one assertion failure that the run's own `grading.json` documents as a
test-harness sandboxing gap, not a skill defect — the test agent's tool access let a dispatched
`git-kit:commit` call actually execute rather than being intercepted by the eval harness; the skill's
own documented behavior (audit informationally, route lint/commit requests to `git-kit`, never run them
itself) was followed correctly. This is a fixed, non-branching prose ritual with no scripts and no
conditional logic beyond "uncommitted changes exist or not", so the eval scope is correspondingly
narrow.

**Last dated run record:** `evals/session-wrap-up/workspace/iteration-1/eval-{1,2}/with_skill/grading.json`,
2026-09-02. `scripts/smoke_test.py` structural self-check also passing as of the same date.

**Verify this skill activates on:**
- "wrap up"
- "done for the day"
- "finish coding"

**Verify it does NOT activate on:**
- "create a handoff" / "save state" (no ritual, just the document) → `session-handoff`
- "run lint and commit this" → `git-kit`'s `commit` skill

**Quality gates:**
- [ ] Never runs or suggests project-specific quality-gate commands (lint/typecheck/test) — that stays `git-kit`'s job
- [ ] git status/diff output is treated as informational context for the summary, never re-run as a gate
