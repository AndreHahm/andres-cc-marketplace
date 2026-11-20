# Response: `/context-mode refresh` (review mode saved, long session)

## Command I would run

The argument is `refresh`, which is exactly one value in the closed set (`admin`, `review`, `ship`, `refresh`,
`status`, `off`), so it is passed to the script. This is the marketplace's own session, where
`CLAUDE_PLUGIN_ROOT` is empty and the skill loads from the `.claude/` mirror, so from the worktree root I would run:

```
python3 "$PWD/.claude/skills/context-mode/scripts/set_mode.py" refresh
```

(In an installed-plugin session it would be `python3 "${CLAUDE_PLUGIN_ROOT}/skills/context-mode/scripts/set_mode.py" refresh`.)

`refresh` only reads the saved state file and reprints its profile. It does not write the state or change the mode,
and it never uses `replace` or `off`.

## Expected script output (exit 0)

Because `review` is saved for this session, the script prints the announce line followed by the generic posture
and the review profile:

```
[Context-Mode] review active for this session. Follow the profile below until the mode is changed; CLAUDE.md and .claude/rules/ still outrank it.

# Generic Posture (every mode)
... (generic.md: CLAUDE.md and .claude/rules/ outrank this; AskUserQuestion for any choice or gate;
smallest change; read before modifying; short commit messages; never silently override or skip a phase;
end with the next actionable step)

---

# Review Mode
... (review.md: posture, repo-specific routing, known recurring defect classes, anti-patterns)
```

## Reply to the user

The review mode is still active for this session. I reprinted its profile, so it is current again in context.
`CLAUDE.md` and `.claude/rules/` still outrank it. From here on I follow it:

- **Finding vs fixing:** I fix only the findings we triaged and chose for this PR, and I check the same file for the
  same pattern before I call a fix complete. When I review someone else's code, I only report findings.
- **Severity:** I report findings as blocking, important or nit, each with `file:line`, why it matters and a
  suggested fix. A Critical or Major finding is never silently deferred and merged.
- **Evidence:** I read the full diff before commenting, and I check each finding against the current tree.
- **Approvals:** I don't submit an approval without showing you the findings and confirming first. I never approve
  with an open Critical or Major finding.
- **Routing:** reviewer actions go through `collaborating-on-a-pr`, triage across rounds through
  `handling-review-findings`, plugin components through the matching `*-reviewer` or `plugin-auditor` plus an actual
  `plugin-rulebook` invocation, and scripts through `scripts-reviewer`.
- **Defect classes I check explicitly:** stale state checks before side effects, unverified tool behavior, fixes
  that skip sibling occurrences, unswept canonical values (R20), absolute claims in precision docs, and closed scope
  lists that were not revisited.
- **Verbosity:** medium.

Next step: continue the current review round where we left off. Any gate still open, such as a pending triage
decision or a reviewer trigger, still runs through `handling-review-findings`.

(If the script had reported "No context mode is active for this session", I would tell you that no mode is saved,
for example because the session id changed, and that you can set one with `/context-mode review`. I would not set
one myself.)

---

## Steps followed (note)

1. I read `plugins/context-kit/skills/context-mode/SKILL.md` in the worktree, plus `references/generic.md`,
   `references/review.md` and `scripts/set_mode.py`, to know what `refresh` prints.
2. Instructions step 1: the argument is `$ARGUMENTS` = `refresh`.
3. Step 2: the value is exactly in the closed set, so I chose the mirror-path command, because `CLAUDE_PLUGIN_ROOT`
   is empty in this marketplace's own sessions. This was a plan-only run, so I did not execute the command.
4. Step 3 and "Refresh and restore": I stated plainly that review mode is active and that `CLAUDE.md` and
   `.claude/rules/` outrank it, then summarized the reprinted profile.
5. Step 4 (refusal or rejection) does not apply, because `refresh` never changes the mode. I covered the
   no-saved-state branch.
