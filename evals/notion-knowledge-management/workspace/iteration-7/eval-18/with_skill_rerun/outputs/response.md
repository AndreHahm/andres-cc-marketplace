# Response

This request belongs to `status-and-learning`, not `notion-knowledge-management`.

"Summarize this week's progress on the export migration to Notion" asks for a dated progress
snapshot of completed work. `notion-knowledge-management`'s When NOT to Use section routes a request
to summarize completed work to `status-and-learning`. That skill drafts the content from Linear
facts first, and calls `notion-knowledge-management` only to execute the Notion write afterward.

Per the skill's routing rule, I name the owning skill and stop here. I am not drafting or sketching
a preview of the progress Report in this skill. `status-and-learning` drafts it.

What happens next, in `status-and-learning` (not run here):
1. It reads the export migration's Linear facts for the week, read-only.
2. It drafts the progress content and shows you the preview.
3. If the result is written to Notion, it hands the drafted content to `notion-knowledge-management`.
   That skill then applies its own approval gate (`AskUserQuestion`) before creating the record,
   plus read-back.

No Notion or Linear tool is called by this skill for this request.

## Planned calls

- `Skill` (name: `status-and-learning`) as the hand-off. This is the only call.
- No `mcp__claude_ai_Notion__*` call and no Linear call from `notion-knowledge-management` for this request.
