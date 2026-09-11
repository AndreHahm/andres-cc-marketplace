## Drift check: AND-7 ↔ Notion link

**What I found:** AND-7's `notion-link` field points to `3ccce061-0b0c-8187-b6e0-db08a5ee6a0a`. Looking that ID up directly in Notion returns "Page not found" — the stable ID no longer resolves.

**Classification: Broken link.**

Per the skill's Gotcha, a broken link doesn't automatically mean the underlying Notion page is gone — it can also mean the *link itself* is stale while the record still exists elsewhere (moved, ID changed, etc.). So before treating this as "the page was deleted," the right move is to re-resolve within the owning system (Notion) rather than take the failed lookup at face value. That's exactly the check I just did: a direct-by-ID fetch against Notion, which is the strongest form of re-resolution available — and it came back negative.

Beyond that, I have nothing else to go on: no cached title, no other identifying metadata about the original page, and no information on *why* it stopped resolving (deleted vs. renamed vs. moved). So I can't take this further on my own — a search-based guess at "which Notion page did this used to point to" isn't a re-resolution, it's an invented answer, and this skill is explicit that repairs must never be guessed into place (no timestamp-based or best-guess resolution).

**Why I'm not just fixing it:** The only concrete repair I could make unilaterally — clearing AND-7's `notion-link` field — is a bare link/reference field edit, which wouldn't normally need approval. But clearing it isn't obviously the right fix; it could just as easily be wrong if the page still exists under a different ID and a relink is possible. Since I can't tell which of those is true, and an `Unknown`/unresolvable case is supposed to get a structured handoff rather than a silent resolution, I'm stopping here rather than picking one.

**How would you like to proceed?**

1. **Clear the link** — blank out AND-7's `notion-link` field now, leaving it unlinked until a new target is identified.
2. **You provide the correct/replacement Notion page** — if you know where this content ended up (a new URL/ID, or a page title I can search for), give it to me and I'll write that ID into AND-7's `notion-link` field (still just a bare link-field update, no approval needed beyond this confirmation).
3. **Leave it as-is for now** — flag it as a known broken link without touching AND-7, if you want to investigate on the Notion side first.

One more thing worth naming: I only touched the Linear-side `notion-link` field for this check — I did not query further Notion (search, page history) or touch anything execution-side, since that's outside this repair's scope. Let me know which of the above you want, and I'll apply it.
