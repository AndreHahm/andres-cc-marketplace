# Response to the user

This request is outside what `context-window-analysis` covers, so I won't run its live-window health check here.

You asked for an audit of your **skills and CLAUDE.md for context bloat**. That is a check of your overall footprint: what gets loaded into every session (CLAUDE.md files, skill descriptions, plugins, MCP servers). `context-window-analysis` answers a narrower question: how full the current context window is right now, and whether to `/compact`, `/clear` or keep going. Its own "When NOT to Use" section sends this kind of request elsewhere:

> A broader skills/CLAUDE.md/plugin/MCP footprint audit — use `context-audit` instead.

Its Testing & Validation section also names this exact phrase ("audit my skills and CLAUDE.md for context bloat") as a request it should not handle, and points it to `context-audit`.

**Recommended next step:** run the `context-audit` skill (context-kit). For example, say "run context-audit on my skills and CLAUDE.md". It checks the footprint of your skills, CLAUDE.md, plugins and MCP servers, which is what you asked for.

**When to come back to this skill:** if you also want to know how full your current session is (for example, responses feel slow, or you are deciding whether to compact now), say "how full is my context". I will then ask you to run `/context` and paste its output, and give you a HEALTHY / MONITOR / WARNING / CRITICAL reading with a recommended action.

---

# Steps followed (note for the eval)

1. Read `plugins/context-kit/skills/context-window-analysis/SKILL.md` in full, from the worktree path only.
2. Compared the request with the skill's "When to Use" and "When NOT to Use" sections. The request is a footprint audit of skills and CLAUDE.md, not a live-window health question. The second "When NOT to Use" bullet routes it to `context-audit`, and the Testing & Validation section lists this exact phrase under "Verify it does NOT activate on → `context-audit`".
3. So I did not run the skill's Workflow: I did not ask for `/context` output (Step 1), map a health tier (Step 2), or read `references/context-window-examples.md` (Step 3, which only applies when writing a health report).
4. Plan-only run: I did not call the Skill tool or dispatch `context-audit`. I named it as the next step for the user. No commands were run and no files were written except this one.
