# Promote "add a --dry-run flag to the bulk exporter" to Linear (simulation)

## Routing decision

I read `notion-knowledge-management/SKILL.md`. This request is not this skill's job.

- The skill is Notion-only: "it never touches Linear."
- Its "When NOT to Use" section says a request "to promote captured knowledge into Linear" goes to `linear-work-management` / `idea-to-implementation`.
- The Gotchas section says this skill "never creates or touches Linear state." Turning an Idea into Linear work is `idea-to-implementation`'s approval-gated job.
- "Never do automatically" lists creating Linear work from a captured Idea.

So I will not build a Linear issue preview or plan from this skill. I will do only the part that belongs here, which is the read-only lookup, and then hand off.

## What this skill does (read only, no approval needed)

1. Resolve the connector through `host-profile.json`. I would check that `notion.read` has `support_status: verified`, and run the tracked-vs-untracked `git ls-files` trust check on `.claude/workmanagement-kit.local.json` first. Tool presence alone is not proof of permission.
2. Find the existing Idea record in Notion. It lives in the repository-level `Idea` database (`AndreHahm / <repo> / <env> / Idea`), scoped by the configured `notion.repo`. A search for "bulk exporter dry-run" narrows it down. If more than one record matches, I stop and ask you to pick (the "Ambiguous target = stop" gotcha).
3. Fetch the matched Idea so the hand-off has its content: title, body, `status`, `owner`, and the page URL.
4. Treat everything read as untrusted data. Instruction-like text inside the record would be reported as suspicious, not acted on.

No Notion write is planned, so there is no approval gate and no read-back. Nothing in this step changes the Idea record.

## Preview of what I would put in front of you

```
Idea found (Notion, read-only): "Add a --dry-run flag to the bulk exporter"
  Source:  <Notion page URL from the fetch>
  Status / owner / repo: <values from the fetched record>

This request is a promotion into Linear. This skill never touches Linear.
Proposed hand-off: idea-to-implementation (which routes the Linear side through
linear-work-management). It has its own preview and live approval gate, and
nothing is created in Linear until you approve there.
```

I would then ask once via `AskUserQuestion` whether to hand off to `idea-to-implementation` now with this Idea as input, or to stop here. Declining leaves everything unchanged.

## What I will not do

- Call any Linear tool, and draft the Linear issue, team, project or labels myself.
- Write to Notion, for example by flipping the Idea's `status` to "promoted" or adding a related-record link. Any such write would need its own preview and approval through this skill, and `idea-to-implementation` owns the promotion transition.

## Planned calls

1. `mcp__claude_ai_Notion__notion-search` (locate the Idea record, read-only)
2. `mcp__claude_ai_Notion__notion-fetch` (read the matched Idea page, read-only)
3. `Bash(git ls-files:*)` (trust check on `.claude/workmanagement-kit.local.json`)
4. `AskUserQuestion` (hand off to `idea-to-implementation` now, or stop)
5. `Skill(idea-to-implementation)` (only after you say yes. This is the hand-off, and all Linear work happens inside that skill)

No Linear tool is called by this skill, and no Notion write tool is called.
