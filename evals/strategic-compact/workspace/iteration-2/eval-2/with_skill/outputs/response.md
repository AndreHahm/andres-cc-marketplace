# Response to user: "We've been going for a while on this task. Should I compact now?"

The length of the session doesn't decide this on its own. What matters is where you are in the task. A manual `/compact` at a natural break keeps more useful context than auto-compact, which fires when the window is full, often in the middle of a step.

**Compact now if you've just reached a break point:**

| You just... | Why it's a good moment |
|---|---|
| Finished exploring and are about to start implementing | You rarely need the exploration context while writing code |
| Completed a milestone (feature works, tests pass) | The next phase can start with a clean slate |
| Finalized and wrote down a plan | The plan is saved, so the context can reset |
| Resolved a debugging session | Old debug traces clutter later work |
| Are switching to an unrelated task | Use `/clear` instead. Nothing from this task carries over. |

**Hold off if you're:**

- in the middle of an implementation (you'd lose code context and decisions),
- actively debugging (you'd lose diagnostic information),
- partway through a task that may still need earlier context, or
- in the middle of a code review (you'd lose the review thread).

**If you do compact:**

- `/compact` is quick and frees context at once, but it may lose some nuance. If `CONTEXT_KIT_PLANS_DIR` is configured, context-kit's hooks save the active plan's status and current task before compaction and restore them afterwards. This is a lightweight capture, not a full handoff.
- For complex work, first create a full handoff with session-kit's `session-handoff`, if it's installed. Say "create handoff" or "save state". It records the decisions made, what worked and what didn't, and next steps in `.claude/handoffs/`. Then compact or clear.
- If the next task is unrelated, use `/clear`.

**What I can't see from here:** this skill doesn't measure how full your context window is. If you want the actual percentage and what's using it, ask for a `context-window-analysis` read. The skill's hooks normally post a `[StrategicCompact]` suggestion on their own, at a tool-call threshold (by default 50, 100 and 150 calls, once real context is at least 50% full), after a milestone, or before a heavy skill starts. If one of those has appeared, that's a further reason to compact at the next break point.

To give you a clear yes or no, I need to know where you are right now:

```
AskUserQuestion({
  questions: [{
    question: "Where are you in the task right now?",
    header: "Task phase",
    options: [
      { label: "Just hit a break point", description: "Exploration done, a milestone reached, a plan written, or a bug fixed" },
      { label: "Mid-step", description: "In the middle of implementing, debugging or reviewing" },
      { label: "Switching tasks", description: "Moving to something unrelated to this task" },
      { label: "Not sure / check fullness", description: "Run a context-window-analysis read first" }
    ]
  }]
})
```

**The reply I would then give for each answer:**

- **Just hit a break point:** "Yes, compact now. For complex work, run session-handoff first ('create handoff'), then `/compact`."
- **Mid-step:** "Not yet. Finish the current step, such as getting the change working or the bug fixed, then compact. If auto-compact looks close, write down the key decisions first (for example with a handoff) so they survive."
- **Switching tasks:** "Use `/clear` rather than `/compact`. Nothing from this task needs to carry over. Create a handoff first if you plan to come back to it."
- **Not sure / check fullness:** "Let's get a live read with `context-window-analysis` first, then decide based on both how full the window is and where you are in the task."

---

## Steps followed

1. Read `plugins/context-kit/skills/strategic-compact/SKILL.md` in full at the worktree path. I didn't need the reference files: the SKILL.md points to them only for hook internals and state files, which this question doesn't involve.
2. Matched the request to the skill's "When to Use": deciding whether now is a good moment to compact.
3. Took the advice from the skill's "Optimal Compaction Points" and "Avoid Compaction During" tables and its "Compaction Options" section (`/compact`, `session-handoff`, `/clear`).
4. Followed the skill's "When NOT to Use" and the context-window-analysis relationship section: I didn't claim to know how full the window is and pointed to `context-window-analysis` for that.
5. The answer depends on the task phase, which I can't see, so I wrote out an `AskUserQuestion` with four options (following the repo rule that prefers it over a plain-text question) and the reply for each answer. This was a plan-only run: I executed nothing, and this is the only file written.
