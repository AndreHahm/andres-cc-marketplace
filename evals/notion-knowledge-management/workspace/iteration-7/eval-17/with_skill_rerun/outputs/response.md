# Response

This request is outside `notion-knowledge-management`. Its When NOT to Use section says that promoting captured knowledge into Linear belongs to `idea-to-implementation` (with `linear-work-management` owning the Linear side). The skill also says to name the owning skill and stop, without drafting a preview of the record that skill owns.

So I am not drafting a Linear issue or a plan here. `idea-to-implementation` drafts the issue and runs its own approval gate. This skill never touches Linear and never creates Linear work from a captured Idea.

What I would do next, once you confirm: hand off to `idea-to-implementation` for the 'add a --dry-run flag to the bulk exporter' idea. If the idea is not yet captured in Notion, I can capture it first through this skill. That capture is a Notion record creation, so it needs its own preview and live approval.

## Planned calls

- Skill(idea-to-implementation) (handoff only; it owns the preview, approval and Linear writes)
- No Notion or Linear tool call from this skill for this request
