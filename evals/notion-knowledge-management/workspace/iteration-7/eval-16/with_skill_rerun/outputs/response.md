This request belongs to `linear-work-management`, not to `notion-knowledge-management`.

`notion-knowledge-management` only handles Notion knowledge records (Ideas, Decisions, proposed Goals, Notes, Research, Reports, Outcome/Learning). It never touches Linear. Its "When NOT to Use" section sends "act in Linear" requests to `linear-work-management`, and says to name the owning skill and stop. So I am not drafting an issue preview here, because that skill drafts it and gets your approval.

What happens next: dispatch `linear-work-management` with your request ("the export times out for large accounts"). It owns the issue preview and its approval gate.

If you also want this written down as a Notion Idea or Note, say so and I will handle that separately. It would be a different write with its own preview and approval.

## Planned calls

- `Skill(linear-work-management)`: hand off the request. No Notion or Linear tool is called by this skill.
