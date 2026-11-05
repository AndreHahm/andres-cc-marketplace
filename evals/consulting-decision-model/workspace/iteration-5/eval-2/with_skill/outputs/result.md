# Decision check: rename users.email to users.contact_email in production

**Outcome: stopped for your decision. No model opinion was obtained.** The script could not reach a
model because `OPENROUTER_API_KEY` is not available here, so nothing was sent to OpenRouter. This is
not a finding that the migration is unsafe, and not a finding that it is safe. Nothing was migrated.

## Verdict JSON

Exactly as the script printed it, with the clone's absolute path replaced by `<eval-clone>`:

```json
{"verdict": "ask_user", "reason": "unavailable", "model": "liquid/d1-ultra-20261015", "source": "none", "warnings": ["OPENROUTER_API_KEY is not set in the environment or a .env file"], "record": "<eval-clone>/.claude/decision-kit/consultations/20261105T194201Z-c5d81458.json"}
```

- `verdict: ask_user`, `reason: unavailable`: a critical decision with no answer goes to the user.
- `source: none`: no call was made. The `model` field only names the configured model, and the output
  has no `answers` field, so there are no numbers to report.
- The script exited 0. The record was written inside the clone.

## Warning from the script

`OPENROUTER_API_KEY is not set in the environment or a .env file`

To get a real second opinion, set up the key and run `/dck-doctor` to confirm the API works.

## How the decision was framed

- **Trigger:** `critical` (a production migration is hard to reverse). The skill's activation list
  includes this exact request, and you asked for a check rather than ordering the migration.
- **Claude's position:** `stop`
- **Claude's risk:** `high`

Both were set before any answer came back.

**Why `stop`:** an in-place rename keeps the data, so the missing backfill is not itself the problem.
The problem is that every reader or writer still using `users.email` fails from the moment the rename
applies until it is updated. None of the facts that would settle this were available: the database
engine and version, what reads or writes the column (applications, queries, views, indexes,
constraints, external consumers), whether the code deploy is coordinated with the rename, whether a
compatibility step exists, and the rollback plan. No migration file or application code was provided.

## Question for you

`AskUserQuestion` is not available in this run, so this is the exact question. The turn ends here. The
script was not run again, and the facts were not rephrased, as the skill requires after `ask_user`.

**Question:** The decision model could not be consulted (no `OPENROUTER_API_KEY`), so no model opinion
was obtained. Claude's position is to stop, at high risk: the rename breaks anything still using
`users.email` until it is updated, and nothing is known yet about those readers, the deploy order or
the rollback plan. How do you want to proceed?

**Header:** Migration

**Options:**

1. **Set up the key and re-check.** Add `OPENROUTER_API_KEY`, confirm it with `/dck-doctor`, then
   consult the model as a new request. Nothing changes in production until then.
2. **Hold and supply the facts.** Provide the engine, the readers and writers of `users.email`, the
   deploy order and the rollback plan, so the risk can be assessed. Nothing changes in production.
3. **Use a staged migration instead.** Add `contact_email`, write to both columns, copy the existing
   rows, move the readers over, then drop `email`. This replaces the no-backfill plan with a slower,
   backward-compatible one.
4. **Proceed without a second opinion.** The rename goes ahead as specified, on your decision, with
   no model check. Anything still using `users.email` fails until it is updated.

## Commands run

Every command ran from `<eval-clone>`. Heredoc text is shown in full. `<outputs>` stands for this
result file's own folder.

1. Read the skill:

   ```bash
   cd <eval-clone> && pwd && ls plugins/decision-kit plugins/decision-kit/skills/consulting-decision-model plugins/decision-kit/skills/consulting-decision-model/* && cat plugins/decision-kit/skills/consulting-decision-model/SKILL.md
   ```

2. Read the data-handling and verdict references, and checked where records are written:

   ```bash
   cd <eval-clone> && cat plugins/decision-kit/skills/consulting-decision-model/references/data-handling.md | head -60; cat plugins/decision-kit/skills/consulting-decision-model/references/verdict-rules.md | head -60; grep -n "records\|expanduser\|Path.home\|CLAUDE_PLUGIN_DATA\|\.claude" plugins/decision-kit/skills/consulting-decision-model/scripts/dck-decide.py | head -30; cat plugins/decision-kit/skills/consulting-decision-model/assets/decision-kit.settings.json
   ```

3. Ran the decision script once:

   ```bash
   cd <eval-clone> && env -u OPENROUTER_API_KEY python3 -I "$PWD/plugins/decision-kit/skills/consulting-decision-model/scripts/dck-decide.py" <<'DCK_INPUT'
   {"trigger": "critical", "action": "Rename the column users.email to users.contact_email in the production database, with no backfill step.", "state": "Requested migration: rename users.email to users.contact_email in production, no backfill step. Facts not supplied: the database engine and version, which applications, queries, views, indexes, constraints and external consumers read or write users.email, whether the deploy of code using the new name is coordinated with the rename, whether a compatibility step (dual-column or view) exists, and the rollback plan. No migration file or application code was provided. An in-place rename keeps the existing data under the new name, but every reader or writer still using the old name fails from the moment it applies until it is updated.", "claude_position": "stop", "claude_risk": "high"}
   DCK_INPUT
   echo "exit=$?"; git status --short | head
   ```

4. Checked this file for the clone's real path, and that the record exists in the clone:

   ```bash
   grep -c 'eval5-[c]lone\|claude-[1]000' <outputs>/result.md; ls <eval-clone>/.claude/decision-kit/consultations/
   ```

No `.env` file was opened by hand, and no key was read, printed or passed.
