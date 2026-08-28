---
name: github-issue-creator
description: >-
  Convert raw notes, error logs, voice dictation, or screenshots into crisp GitHub-flavored markdown issue reports. Use when the user pastes bug info, error messages, or informal descriptions and wants a structured GitHub issue. Supports images/GIFs for visual evidence.
allowed-tools: Write, Read
---

# GitHub Issue Creator

Transform messy input (error logs, voice notes, screenshots) into clean, actionable GitHub issues.

**Not for filing directly on GitHub** — this skill only writes a local markdown draft under `issues/`; it
has no `Bash`/`gh` access. A request framed as filing a real issue as part of the full create lifecycle
(dedup-check first, verify after, initial impact analysis) is `github-issue-lifecycle`'s job — it
delegates the drafting step back here, then files the approved draft live itself. A bare one-off
`gh issue create` with no lifecycle framing is `gh-operations`' job.

## Output Template

Use the structure in `assets/issue-template.md` for every generated issue — see the Examples section below for what it looks like filled in.

## Output Location

**Create issues as markdown files** in `issues/` directory at the repo root. Use naming convention: `YYYY-MM-DD-short-description.md`

## Guidelines

**Be crisp**: No fluff. Every word should add value.

**Extract structure from chaos**: Voice dictation and raw notes often contain the facts buried in casual language. Pull them out.

**Infer missing context**: If user mentions "same project" or "the dashboard", use context from conversation or memory to fill in specifics.

**Placeholder sensitive data**: Use `[PROJECT_NAME]`, `[USER_ID]`, etc. for anything that might be sensitive. Raw notes, error logs, voice dictation, and screenshots commonly carry more than just those two — also redact or flag email addresses (`[EMAIL]`), tokens/API keys (`[REDACTED_TOKEN]`), internal hostnames (`[INTERNAL_HOST]`), session IDs (`[SESSION_ID]`), and absolute filesystem paths containing usernames (`[LOCAL_PATH]`) before writing the generated issue file.

**Match severity to impact**:
- Critical: Service down, data loss, security issue
- High: Major feature broken, no workaround
- Medium: Feature impaired, workaround exists
- Low: Minor inconvenience, cosmetic

**Image/GIF handling**: Reference attachments inline. Format: `![Description](attachment-name.png)`

## Examples

**Input (voice dictation)**:
> so I was trying to deploy the agent and it just failed silently no error nothing the workflow ran but then poof gone from the list had to refresh and try again three times

**Output**:
```markdown
## Summary
Agent deployment fails silently - no error displayed, agent disappears from list

## Environment
- **Product/Service**: Azure AI Foundry
- **Region/Version**: westus2

## Reproduction Steps
1. Navigate to agent deployment
2. Configure and deploy agent
3. Observe workflow completes
4. Check agent list

## Expected Behavior
Agent appears in list with deployment status, errors shown if deployment fails

## Actual Behavior
Agent disappears from list. No error message. Requires page refresh and retry.

## Impact
**High** - Blocks agent deployment workflow, no feedback on failure cause

## Additional Context
Required 3 retry attempts before successful deployment
```

---

**Input (error paste)**:
> Error: PERMISSION_DENIED when publishing to Teams channel. Code: 403. Was working yesterday. Reported by jane.doe@acme.com, running from C:\Users\jdoe\projects\teams-agent with token YOUR_API_KEY_HERE.

**Output**:
~~~markdown
## Summary
403 PERMISSION_DENIED error when publishing to Teams channel

## Environment
- **Product/Service**: Copilot Studio → Teams integration
- **Region/Version**: [REGION]

## Reproduction Steps
1. Configure agent for Teams channel
2. Attempt to publish

## Expected Behavior
Agent publishes successfully to Teams channel

## Actual Behavior
Returns `PERMISSION_DENIED` with code 403

## Error Details
```
Error: PERMISSION_DENIED
Code: 403
```

## Impact
**High** - Blocks Teams integration, regression from previous working state

## Additional Context
Was working yesterday - possible permission/config change or service regression. Reported by [EMAIL],
running from [LOCAL_PATH] with token [REDACTED_TOKEN].
~~~

## Testing & Validation

**Verify this skill activates on:**
- "turn this error log into a GitHub issue"
- "here's a voice note about a bug, write it up as an issue"
- "I have a screenshot of a bug, create an issue for it"
- pasted stack trace + "write this up as a structured issue"

**Verify it does NOT activate on:**
- "create a PR for this" → `create-pr`
- "review this PR and leave comments" → `collaborating-on-a-pr`
- "who owns this file/path" → `manage-codeowners`
- "list open issues on this repo" → `gh-operations`
- "work this issue through create/dedup/verify and file it for real" → `github-issue-lifecycle`; it
  delegates drafting back to this skill, then files the result itself
- "just run `gh issue create` with this text, no dedup/verification needed" → `gh-operations`'s raw
  one-off `gh issue create`; this skill only drafts a local markdown file, never files a live issue

**Quality gates:**
- [ ] Every generated issue follows the structure in `assets/issue-template.md` — never a freeform format
- [ ] Output is always written as a markdown file in `issues/` at the repo root, named
      `YYYY-MM-DD-short-description.md` — never elsewhere
- [ ] Severity is always matched to impact per the documented Critical/High/Medium/Low definitions —
      never assigned arbitrarily
- [ ] Sensitive data (project names, user IDs, emails, tokens/API keys, internal hostnames, session IDs,
      absolute filesystem paths, etc.) is always placeholdered (`[PROJECT_NAME]`, `[USER_ID]`, `[EMAIL]`,
      `[REDACTED_TOKEN]`, `[INTERNAL_HOST]`, `[SESSION_ID]`, `[LOCAL_PATH]`) — never left as real values
      pulled from raw input
- [ ] Image/GIF references always use the `![Description](attachment-name.png)` inline format
- [ ] Missing context is only inferred from conversation/memory already available — never fabricated
