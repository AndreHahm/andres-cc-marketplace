# Response to user: "how full is my context right now"

## Reply to the user

I can't measure my own context window from here, so I need a real reading from Claude Code. Please run `/context` and paste its output into this chat.

Once you share it, I'll read only the token counts, percentages and category labels, and map the percentage to a status:

| Usage | Status | Action |
|-------|--------|--------|
| < 40% | HEALTHY | No action needed |
| 40-<80% | MONITOR | Awareness nudge at 65% (one nudge only); consider /compact soon |
| 80-<90% | WARNING | Run /compact or /clear |
| >= 90% | CRITICAL | Immediate action required |

I'll then give the report (status, observable indicators, assessment, recommendations) and the remediation options that fit that status.

If you'd rather not run `/context` right now, I can give a rough estimate from what I can observe in this session (turn count, file reads, tool output volume, loaded skills). That estimate would be labelled as an estimate, not a measurement. Below CRITICAL I won't recommend /compact or /clear on an estimate alone; I'd ask for the `/context` output first.

## Steps followed

1. Read `plugins/context-kit/skills/context-window-analysis/SKILL.md` in the worktree, in full.
2. Read `references/context-window-examples.md` from the same skill folder, because Step 3 of the skill says to use it for the report template and tier examples.
3. Followed Step 1 (ask for `/context` output first, since the skill treats it as the reliable source) and Step 2 (the percentage decides status when `/context` output exists; indicators are only the fallback).
4. Ran no commands and no scripts, changed no git state, and read nothing under `evals/`. The only file written is this output.
