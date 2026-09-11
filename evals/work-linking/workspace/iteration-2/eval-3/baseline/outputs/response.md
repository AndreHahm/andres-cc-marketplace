Here's what I'd do to repair this, and a couple of things worth flagging before I just quietly pick a fix:

**What's known:**
- AND-7's `notion-link` field points to Notion page ID `3ccce061-0b0c-8187-b6e0-db08a5ee6a0a`.
- That ID now returns "Page not found" in Notion.
- Nothing tells us *why* — could be a hard delete, a move to a different parent (which can sometimes change how a page resolves), a permissions change that hides it from this integration, or the page ID was simply mistyped/mis-recorded when the link was first created.

**Why I'm not just clearing or replacing the field outright:**
A dead ID is ambiguous by nature — I can't tell from the ID alone whether the source page is truly gone or just relocated/inaccessible. Silently blanking the field would destroy the only breadcrumb pointing at the original idea; silently swapping in a "best guess" replacement page risks linking AND-7 to the wrong document. Both are worse than leaving it broken until we know which case we're in.

**What I'd actually do, in order:**

1. **Search Notion for the likely source page**, rather than trusting the dead ID alone — by the idea/title text associated with AND-7 (issue title, description, any comments that reference the idea by name), and by recency around when AND-7 was created or linked. A moved or renamed page will usually still turn up this way even though its old ID no longer resolves.
2. **If a clear match is found:** confirm it looks like the right page (title, content, timestamps line up with what AND-7 describes), then update AND-7's `notion-link` field to the new page ID/URL. I'd note in a Linear comment that the link was repaired and from what old ID, so there's an audit trail.
3. **If no confident match is found:** don't guess. I'd flag the broken link explicitly — e.g. a comment on AND-7 stating the stored Notion ID no longer resolves and no replacement page could be confidently identified — and ask you (or whoever owns the Notion workspace) to either point me at the correct page or confirm the idea page was deleted outright, in which case the right fix is removing/clearing the stale `notion-link` field with a note explaining why, not leaving a dead ID silently in place.
4. **If multiple plausible matches turn up**, I'd list them and ask you to pick rather than choosing on your behalf.

So, concretely, the next step is a Notion search for the idea content this issue was about — do you have the idea's title or any other identifying detail I should search on, or would you like me to search using AND-7's own title/description as the query?
