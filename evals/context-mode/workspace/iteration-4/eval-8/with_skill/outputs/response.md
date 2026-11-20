# Response: "Which context mode is active?"

## Command I would run (plan-only, not executed)

Your message asks which mode is active, so by Instructions step 1 the value is `status`. That is in the
closed set, so step 2 allows running the script. In this marketplace's own sessions `CLAUDE_PLUGIN_ROOT`
is empty, so I use the `.claude/` mirror path from the worktree root:

```bash
python3 "$PWD/.claude/skills/context-mode/scripts/set_mode.py" status
```

(With a populated `CLAUDE_PLUGIN_ROOT` it would be
`python3 "${CLAUDE_PLUGIN_ROOT}/skills/context-mode/scripts/set_mode.py" status`.)

Expected output, since review mode is saved for this session:

```
Active context mode: review
```

`status` only reads the saved state. It does not set, change or clear the mode, and it does not reprint
the profile.

## Reply to the user

The active context mode is **review**. That covers the PR phase, from opening the PR through the last
review round, including fixing triaged findings. I am following the review profile for the rest of this
session. `CLAUDE.md` and `.claude/rules/` still take precedence over it.

To reprint the full profile, use `/context-mode refresh`. To clear the mode, use `/context-mode off`.
Switching to a different mode means writing a handoff and starting a fresh session, or running
`/context-mode replace <mode>` yourself if you want to override it.

## Steps followed

1. Read `plugins/context-kit/skills/context-mode/SKILL.md` in the worktree, and checked the `status`
   branch of `scripts/set_mode.py` to get its exact output wording.
2. Step 1: a plain request asking which mode is active maps to the value `status`. No mode is set from it.
3. Step 2: `status` is in the closed set, and `CLAUDE_PLUGIN_ROOT` is empty here, so I chose the mirror-path
   command above. I did not run it.
4. Step 3: stated which mode is active, using the saved review mode from the scenario.
5. Wrote nothing except this file and changed no state.
