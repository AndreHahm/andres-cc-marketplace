# Agent Teams vs. Subagents

Agent Teams are multiple independent Claude Code sessions sharing a task list with direct peer-to-peer communication — a different mechanism from the subagents this skill otherwise covers. **Experimental** as of this writing; don't recommend it as a plugin's primary architecture.

## How This Differs From Everything Else in This Skill

| | Subagents (this skill's main subject) | Agent Teams |
|---|---|---|
| Context | Returns a result to the caller, then exits | Fully independent session, stays alive |
| Communication | To the dispatching agent only | Direct peer-to-peer between teammates |
| Token cost | Lower (summarized return) | Higher (full independent instances) |
| Definition | A plugin-shipped `agents/*.md` file | Not a plugin component — a runtime session mode |

Agent Teams are **not** something a plugin declares in its manifest or ships as a file — there's no `agents/*.md`-equivalent for a team. A plugin can only *document* the recommendation to use one; it cannot bundle or configure one the way it bundles a subagent.

## Enabling

Experimental — requires an explicit opt-in:

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

## When a Plugin Might Recommend Agent Teams

- Parallelizable tasks with independent subtasks (e.g. "refactor these 5 files")
- Multi-perspective analysis needing different viewpoints held simultaneously (one teammate on UX, one on security)
- Complex research needing extensive information gathering from multiple angles at once

If the plugin's own workflow already fits the subagent model (a caller dispatches, waits, gets a result back), stay with subagents — Agent Teams add session-management complexity (only one team per session, no nesting, no resumption for in-process display mode) that isn't worth it unless the task genuinely needs peer-to-peer coordination.

## Limitations

- Only one team per session
- Teammates cannot spawn sub-teams (no nesting)
- The session that starts the team is always the lead
- In-process display mode teams cannot be restored after `/resume`

## See Also

- `references/delegation.md` — subagent delegation patterns (the mechanism this skill actually builds)
