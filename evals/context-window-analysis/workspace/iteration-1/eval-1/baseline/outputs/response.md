# How full is my context right now?

I don't have a built-in tool that reports an exact, live "percent full" number for my own context window — there's no API or command available to me that returns that figure directly, so I can't give you a precise measurement.

Here's what I can tell you honestly:

**What's contributing to context usage in this session:**
- A large project `CLAUDE.md` plus roughly 18 separate `.claude/rules/*.md` files were loaded as project instructions — these alone are substantial (each rule file runs several paragraphs to a page).
- A long user memory file (`MEMORY.md`) with ~35 bullet-point entries.
- A full listing of available skills (over 150 skill names with descriptions) and available subagent types (dozens, each with a multi-sentence description).
- MCP server instructions (Notion, Linear, Claude Docs, etc.).
- The conversation history itself so far (currently short — just this one request).

**A partial data point:** one of the system reminders in this session shows a `total_tokens` figure of about 14.9 million "tokens left." That's almost certainly a much larger budget than a single model context window (Claude's context windows top out at 1M tokens at most), so it likely reflects a broader session/task token allowance tracked by the harness rather than the immediate context window fill level — I can't confirm exactly what it measures from where I sit.

**Bottom line:** Given the size of the system prompt/instructions alone (project rules, memory, skill listing, MCP instructions), a meaningful amount of context is already committed before any real conversation content — my rough, non-precise guess is this is a low-to-moderate fraction of a typical context window, but I don't have a reliable way to give you an exact number or percentage. If you need an accurate reading, the most reliable approach would be a tool or command specifically designed to introspect token usage (e.g., a `/context` command or similar, if your Claude Code environment provides one) rather than relying on my own self-report.
