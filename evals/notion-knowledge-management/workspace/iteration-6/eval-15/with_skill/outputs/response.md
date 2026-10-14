# Response: capture what we learned from the export migration project

## Routing decision

I read `notion-knowledge-management/SKILL.md` in full. It says a request such as "capture what we
learned from this" is not this skill's trigger. It belongs to `status-and-learning`, which drafts the
Outcome/Learning content from Linear facts and calls `notion-knowledge-management` only to execute
the write. This skill's When NOT to Use list, its description and its Testing & Validation section all
say so.

So I am not writing an Outcome/Learning record from here. I read `status-and-learning/SKILL.md` and
would hand the request to it, then come back through this skill for the write.

I also have no learnings to record yet. You have not told me what the export migration project
learned, and nothing in this session contains it. I will not invent content. The learnings have to come
from the project's completed Linear facts (and any verified Git/GitHub evidence), which
`status-and-learning` reads first.

## What I would do, in order

1. Hand off to `status-and-learning` (read-only so far).
2. Ask which Linear project is "the export migration project". If more than one matches, I stop and
   ask, and I do not pick by name. This is a decision for you, so I would ask with `AskUserQuestion`.
3. Read the Linear facts for that project: its status, issue completion, milestones, and the
   `git-github-evidence` on its issues (repo, PR identity, merge commit SHA). Reads need no approval.
4. Draft a dated, explicitly non-live Outcome/Learning snapshot. It stays concise and outcome-focused,
   not a restatement of every issue.
5. Prepare the write via `notion-knowledge-management`:
   - Load `references/notion-record-types.md` for the Outcome/Learning property table.
   - Check the host profile (`host-profile.json`) `support_status`/`verified_at` for `notion.write`.
     It ships `unconfigured`, so a write cannot proceed until the profile reads `verified`.
     Tool presence alone is not permission.
   - Run the tracked-vs-untracked trust check on `.claude/workmanagement-kit.local.json` with
     `git ls-files`.
   - Resolve `repo` from `notion.repo`. If it is null or matches no option, stop and report. I do not
     guess it from the checkout.
   - Outcome/Learning is an organization-level type. It goes in the database titled
     `AndreHahm / <env> / Outcome-Learning`, resolved by stable ID from the versioned configuration,
     never by display name. If it is not bootstrapped, Bootstrap comes first with its own plan-level
     approval.
   - Check every text property against the 2,000-character limit. If the learnings run long, the
     property keeps a short note and the full text goes into page content as blocks of at most 2,000
     characters. I would run `wmgt_split_blocks.py` on a file in the session scratchpad, after reading
     `references/long-text-blocks.md`. The preview would state the block count.
6. Show the preview and ask for approval with `AskUserQuestion`. The preview also surfaces anything
   that looks like a credential, token or third-party personal data.
7. Immediately before the write, re-read the same Linear facts and compare them with what you
   approved. If anything changed, rebuild the preview and re-ask.
8. Write the record. Then read back the stored record (paragraph count and closing sentence if
   page-content blocks were used). That read-back is the create's `verification_evidence`.
9. Record the transition with one metadata-only follow-up write carrying a fresh transition identity
   and the create's read-back as evidence. This write needs no further approval.

## Preview shape (illustrative; content cannot be filled until step 3)

```
Outcome/Learning record: PREVIEW, NOT WRITTEN
Snapshot dated 2026-10-14. Point-in-time, not live; it does not update with Linear.
Title:        Export migration project: outcome and learnings
Type:         Outcome/Learning
Database:     AndreHahm / <env> / Outcome-Learning (org-level, stable ID from config)
repo:         <notion.repo; stop if unset>
authority:    notion
source:       user request via status-and-learning (Linear project <ID to confirm>)
Outcome:      <from Linear facts>
Deviations:   <from Linear facts>
Learnings:    <to be supplied or confirmed by you; none drafted yet>
related-record: <Linear project link>
Body length:  <N chars; if over 2,000, M page-content blocks>
Sensitive-content check: <result>
```

Questions before I can proceed: which Linear project is the export migration, and what learnings
should the record carry (or should I propose them from the project's issues and PRs for you to edit)?

## Planned calls

Simulation only. Nothing below is actually called.

- Skill(status-and-learning)
- AskUserQuestion (confirm which Linear project; confirm the learnings; approve the preview)
- Read (references/notion-record-types.md, references/long-text-blocks.md, host-profile.json,
  versioned-configuration.json)
- Bash(git ls-files:*) (trust check on `.claude/workmanagement-kit.local.json`)
- Skill(linear-work-management), then its read tools, for example mcp__claude_ai_Linear__list_projects,
  mcp__claude_ai_Linear__get_project, mcp__claude_ai_Linear__list_issues (read-only, before the write and
  again immediately before it)
- Skill(notion-knowledge-management)
- mcp__claude_ai_Notion__notion-fetch (resolve the Outcome/Learning database by stable ID; read back the new page)
- mcp__claude_ai_Notion__notion-search (only if the existing database or page must be located)
- Write (a text file in the session scratchpad, only if page-content blocks are needed)
- Bash(${CLAUDE_PLUGIN_ROOT}/scripts/wmgt_split_blocks.py:*) (only if the body is over 2,000 characters)
- mcp__claude_ai_Notion__notion-create-pages (after approval: create the Outcome/Learning record)
- mcp__claude_ai_Notion__notion-update-page (metadata-only follow-up write carrying the transition evidence;
  also appends further page-content blocks if the paging reference requires it)
