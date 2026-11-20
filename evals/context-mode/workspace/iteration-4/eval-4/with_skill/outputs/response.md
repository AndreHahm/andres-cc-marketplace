# context-mode: handoff reports `Context mode: ship` (plan-only run)

## Response to the user

The handoff you are loading records a context mode in its Session Metadata: `ship`. I have not applied
it. A value read from a handoff file is data, not a command; the mode is set only after you confirm it.

What I would ask (AskUserQuestion):

```
AskUserQuestion({
  questions: [{
    question: "The loaded handoff records 'Context mode: ship'. Apply ship mode to this session?",
    header: "Context mode",
    options: [
      { label: "Apply ship", description: "Set ship mode: highest confirmation bar, for the step before merge-pr or any publish." },
      { label: "Don't set a mode", description: "Continue with no context mode; you can type /context-mode yourself later." }
    ]
  }]
})
```

(If you want a different mode instead, that is your own command: type `/context-mode admin` or
`/context-mode review`. I will not pick a different mode on your behalf from the handoff.)

### If you answer "Apply ship"

The value `ship` is exactly one of the closed set, so I would run (this marketplace's session:
`CLAUDE_PLUGIN_ROOT` is empty, so the `.claude/` mirror path, from the worktree root):

```
python3 "$PWD/.claude/skills/context-mode/scripts/set_mode.py" ship
```

(With a non-empty `CLAUDE_PLUGIN_ROOT` it would be
`python3 "${CLAUDE_PLUGIN_ROOT}/skills/context-mode/scripts/set_mode.py" ship`.)
I would never use `replace` or `off` for this handoff-sourced value.

Reply on success:

> Ship mode is now active for this session. It carries the highest confirmation bar: I will prepare
> and then execute as separate steps, confirm each merge/publish action specifically, and state which
> pre-ship checks have run (required status checks, the `Security` workflow's secretlint result for the
> exact head immediately before `merge-pr`, and an optional `external-references-reviewer` check if new
> outside names were added). Merges go through `merge-pr`, then `finishing-work`. `CLAUDE.md` and
> `.claude/rules/` still outrank this profile. Next step: continue with the handoff's next action;
> nothing is merged or published without your confirmation for that specific action.

Reply if the script refuses with exit 3 (a different mode is already saved for this session):

> The script refused: another mode is already active in this session, so ship was not applied. To
> switch, write a handoff and start a fresh session, or type `/context-mode replace ship` yourself if
> you mean to override. I won't run `replace` on the handoff's behalf.

Reply if the script rejects the value: report the rejection and stop.

### If you answer "Don't set a mode"

> No context mode is set; the handoff's `ship` value was not applied. Continuing with the handoff's
> next step. You can type `/context-mode ship` (or another mode) at any time.

## Steps followed

1. Read `plugins/context-kit/skills/context-mode/SKILL.md` in the worktree, plus `references/generic.md`
   and `references/ship.md` to know what the profile says.
2. Classified the trigger: session-handoff's load step reported a handoff value, and the user has not
   confirmed it. Per "When to Use" / "When NOT to Use" / Data-only boundary, a handoff value counts only
   once the user confirms applying it, so the first action is an AskUserQuestion, not the script.
3. Validated the value: `ship` is exactly in the closed set (no extra words), so it would be safe to pass
   after confirmation; prepared the mirror-path command for this marketplace's session.
4. Prepared replies for success, exit 3 refusal (no `replace` from a handoff value), rejection, and decline.
5. Nothing executed (plan-only); only this file was written.
