This isn't a job for the `antigravity` skill I have loaded — that skill is explicitly scoped to *ongoing, per-task delegation* (routing individual scaffolding/test/migration/search tasks to Gemini via `agy-delegate`, `agy-job`, etc.), and its own "When NOT to Use" section calls out exactly your case by name:

> One-time migration of an existing Claude Code setup onto agy (skills, memory, MCP servers, permissions) — use the sibling `migrate-to-antigravity` skill instead; this skill is for ongoing delegation, not migration.

So I'm not going to force this through `agy-delegate` — that would just delegate a single ad-hoc prompt to Gemini rather than actually performing a structured, verifiable migration of your setup. What you want is the sibling **`migrate-to-antigravity`** skill, which is purpose-built for the one-time move. That skill isn't available to me in this session, so here's how to proceed:

1. **Invoke the right skill.** In a session where it's installed, just ask directly: "migrate my Claude Code setup to Antigravity" — that phrasing is its documented trigger, and it will walk through moving your setup rather than running one delegated task.

2. **What it should cover, based on what you listed:**
   - **Skills** — your `.claude/skills/` (and any plugin-shipped skills) need to be translated into whatever Antigravity's equivalent extension/prompt mechanism is; this isn't a file copy, since Claude Code skill frontmatter (`name`, `description`, `allowed-tools`) doesn't have a 1:1 Antigravity equivalent.
   - **Memory** — project/user memory (CLAUDE.md, session memory, any `.claude/memory` state) needs an explicit export/import step; don't assume it silently carries over.
   - **MCP servers** — your MCP server configs (in `.claude.json` / `.mcp.json` or project settings) should be re-declared in Antigravity's own config format; credentials should be re-entered rather than copied in plaintext.
   - **Permissions** — your `settings.json` allow/deny/ask rules don't map automatically; they need to be re-expressed in whatever permission model Antigravity uses.

3. **After migration, verify before relying on it.** Once `migrate-to-antigravity` finishes, don't take a "migration complete" report at face value — check that:
   - Antigravity actually reads and applies at least one migrated skill correctly.
   - MCP servers connect (test one call per server).
   - Permission rules produce the same allow/deny behavior on a couple of known cases.
   - Nothing sensitive (API keys, tokens) got copied into a tracked/shippable file in the process.

4. **Going forward:** once the setup lives on Antigravity, this `antigravity` skill (the one I do have) is what you'd use afterward for day-to-day delegation — handing Claude Code specific scaffolding, test-generation, migration-script, or search tasks to run via `agy-delegate`/`agy-job` — not for the one-time setup move itself.

If you'd like, tell me which specific piece (skills, memory, MCP servers, or permissions) you want to start with, and if `migrate-to-antigravity` genuinely isn't installed anywhere you have access to, I can instead help you draft the individual re-configuration steps by hand.
