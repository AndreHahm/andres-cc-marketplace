# Response

This request ("capture what we learned from finishing the export migration project") is not one `notion-knowledge-management` handles. The skill's When NOT to Use section routes "capture what we learned from this" and "capture this outcome" to **`status-and-learning`**. That skill drafts the Outcome/Learning content from Linear facts first. It calls `notion-knowledge-management` only to execute the Notion write once the content is drafted and you have approved it.

So I am stopping here and handing this to `status-and-learning`. I have not drafted a preview of the Outcome/Learning record, and I have not guessed any "lessons". The owning skill drafts it from the project's real Linear facts. Anything I wrote now would be invented, and it would bypass that skill's drafting step.

## What happens next

1. `status-and-learning` gathers the export migration project's facts from Linear (read-only) and drafts the Outcome/Learning content.
2. It shows you that draft.
3. Only then does `notion-knowledge-management` build the Outcome/Learning record, shown as a preview with a live `AskUserQuestion` approval gate. Creating that record is a write, so it needs approval with no exception. After the write it reads the record back and records the transition.

Before that write, `notion.repo` must be set and match a `repo` option. If it is not, the write stops rather than guessing.

## Planned calls

- `Skill(status-and-learning)` (hand-off to the owning skill; nothing else is executed in this turn)
- No Notion tool calls from this skill in this turn (no `mcp__claude_ai_Notion__*` call)
- No Linear tool calls from this skill in this turn
