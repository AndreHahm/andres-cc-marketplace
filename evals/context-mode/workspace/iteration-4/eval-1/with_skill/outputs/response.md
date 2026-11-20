# /context-mode ship: plan-only response

## Command I would run

The argument is `ship`. It is exactly one value from the closed set, with no other words or characters, so
it is passed to the script. In this marketplace's own sessions `CLAUDE_PLUGIN_ROOT` is empty (the skill loads
from the `.claude/` mirror), so I would run the mirror path from the worktree root:

```bash
python3 "$PWD/.claude/skills/context-mode/scripts/set_mode.py" ship
```

In an installed-plugin session, where `CLAUDE_PLUGIN_ROOT` is set, the command would be
`python3 "${CLAUDE_PLUGIN_ROOT}/skills/context-mode/scripts/set_mode.py" ship`.

Expected result: this is a fresh session with no saved mode, so there is no conflict and no refusal (exit 3
does not apply). The script checks `ship` against the closed set again, saves it to
`~/.claude/context-kit/mode-<hash of the session id>` so the post-compaction restore can find it, and exits 0
after printing `[Context-Mode] ship active for this session...` followed by the generic posture and the ship
profile. If `CLAUDE_CODE_SESSION_ID` were missing, it would still print the profile and add a note that the
mode was not saved.

## Reply to the user

**Ship mode is now active for this session.** I'll follow the ship profile until you change it. `CLAUDE.md`
and `.claude/rules/` still outrank it.

What this means for the rest of the session:

- **Highest confirmation bar.** This repo is public. I'll prepare first and execute as a separate step. Each
  merge, publish or post gets its own explicit confirmation through `AskUserQuestion`, even if a similar one
  was approved earlier.
- **Pre-ship checks.** I'll say which checks have run and which have not. I won't publish while a check that
  applies to the destination has failed or not run. For a PR merge, that includes every required status check.
- **Secrets.** Right before `merge-pr`, I'll read the `Security` workflow's secretlint result for the exact
  head being merged and tell you what it says. That check is not required by GitHub, so GitHub could merge
  without it:
  - Passed: the merge can go ahead.
  - Still running: I'll wait.
  - Failed: I'll stop until the finding is triaged.
  - No run for this head: I'll run secretlint on the changed files locally or ask you.

  For content outside a PR, I'll check it for secrets myself before it goes out.
- **External names.** If the content adds names of outside companies, products or repositories, I'll offer
  `external-references-reviewer` as an optional check and say whether it ran.
- **Routing.** Merges go through `merge-pr` and then `finishing-work`, never a raw `gh pr merge`. Marketplace
  and manifest changes go through `marketplace-development`. Plugin publishing goes through
  `plugin-lifecycle-downstream` and the inventory skills. I won't force-push a shared branch or push to
  `main` unless you ask for it explicitly.
- **Output.** My replies will be short, with these sections: What's shipping / Destination / Pre-ship checks
  (ran / not run) / Confirmation.

The mode is saved for this session, so it comes back after a compaction. `/context-mode refresh` prints it
again, `status` reports it and `off` clears it. Switching to another mode means writing a handoff and
starting a fresh session. The other route is to type `/context-mode replace <mode>` yourself to override.

**Next step:** tell me what is shipping (which PR to merge, or what to publish). I'll start with the pre-ship
checks for it.

---

## Steps followed

1. Read `plugins/context-kit/skills/context-mode/SKILL.md` in the worktree, plus the files it names:
   `scripts/set_mode.py`, `references/generic.md` and `references/ship.md`.
2. Instruction step 1: the argument is `ship`, and it came from the user's own typed `/context-mode` command,
   not from a prompt word, a hook tag or a handoff. No `AskUserQuestion` is needed.
3. Step 2: confirmed that `ship` is exactly in the closed set. Chose the `$PWD/.claude/` mirror path
   because `CLAUDE_PLUGIN_ROOT` is empty in this marketplace's own sessions. Nothing ran, because this is a
   plan-only run.
4. Predicted the script's behavior from its source: there is no saved mode, so it saves the mode, prints the
   profile and exits 0.
5. Step 3: stated plainly which mode is active, summarized the printed profile, and noted that `CLAUDE.md` and
   `.claude/rules/` outrank it.
6. Step 4 (refusal handling) did not apply, because no other mode was saved.
