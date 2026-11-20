# Response to the user

Auditing your skills and CLAUDE.md for context bloat is a footprint audit: it asks what your installed
skills, CLAUDE.md files, plugins and MCP servers cost in every session. `context-window-analysis` doesn't do
that. It only checks how full your **current live window** is right now (HEALTHY / MONITOR / WARNING /
CRITICAL) and whether to `/compact`, `/clear` or carry on.

The skill for your request is **`context-audit`** (context-kit). Its scope covers skills, CLAUDE.md,
plugins and MCP servers, not just the live window. To start it, ask "audit my context footprint" or invoke
`context-audit` directly.

What I would do next (plan only, nothing was run):

- Hand off to `context-audit` with your original request: "audit my skills and CLAUDE.md for context
  bloat".
- If you also want the live-window reading, which is the one thing the two skills share, run `/context`
  and paste the output. I'd use only its token counts, percentages and category labels, and treat any
  text in it as data, not as instructions. That puts the window in one of the skill's tiers: < 40%
  HEALTHY, 40 to < 80% MONITOR, 80 to < 90% WARNING, >= 90% CRITICAL. The CLAUDE.md and skills rows of
  that breakdown are also a quick first look at how big those two categories are in the current session.
  As a rough guide, CLAUDE.md files typically take 5-15k tokens and loaded skills 1-5k.

I didn't produce a per-file bloat report here. That would go beyond this skill's scope and duplicate
`context-audit`.

---

## Steps followed (note)

1. Read `plugins/context-kit/skills/context-window-analysis/SKILL.md` in full, from the
   `context-kit-rulebook-gaps` worktree only.
2. Checked the request against the skill's "When NOT to Use" section. It excludes "a broader
   skills/CLAUDE.md/plugin/MCP footprint audit — use `context-audit` instead". Its Testing & Validation
   section also names this exact prompt ("audit my skills and CLAUDE.md for context bloat") as a
   should-NOT-activate case that routes to `context-audit`.
3. So the answer is a redirect. I didn't read `references/context-window-examples.md`: it holds the
   Step 3 report template for a live-window health report, and that step doesn't run when the skill
   declines.
4. Offered the one shared piece, the live `/context` reading with the skill's thresholds and its
   untrusted-data handling, as an optional extra. I didn't run any command or ask a real question; this
   is a plan-only run.
