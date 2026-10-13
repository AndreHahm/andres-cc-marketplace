# Bootstrap Notion databases: prod, repo andres-cc-marketplace (simulation)

No Notion or Linear tool was called. Below are the calls I would make and the preview I would show.

## Step 0: preconditions (read-only)
1. Read `host-profile.json`. Confirm `notion.read` and `notion.write` have `support_status: verified`. A callable Notion connector is not proof of permission. If they read `unconfigured`, I stop and send you to Foundational Setup.
2. Run `git ls-files .claude/workmanagement-kit.local.json` (the trust check). A tracked copy is ignored and the shipped `unconfigured` defaults apply. An untracked copy is honored.
3. Read `versioned-configuration.json`. Today `notion.repo` is null and `notion.databases.prod` is `{}`, so nothing is recorded yet.

## Step 1: discovery (reads only, no approval needed)
- `notion-search` for the pages `AndreHahm / prod` and `AndreHahm / andres-cc-marketplace / prod`. I would not pick one by title alone. If more than one page matches either title, I stop and hand the choice to you.
- `notion-fetch` on each page, then on each child database. I record each database's stable ID and read both its database title and its data-source name, because these can differ.
- Check each database for the required `repo` select property and whether `andres-cc-marketplace` is an option.
- `notion-query-data-sources` only if I need to see whether the Outcome-Learning database already holds rows. Rows would matter for the move decision.

## Step 2: plan, mapped to your findings

| Scope | Type | Finding | Proposed action |
|---|---|---|---|
| Org `AndreHahm / prod` | Note | exists | **Adopt** by stable ID |
| Org `AndreHahm / prod` | Research | exists | **Adopt** by stable ID |
| Org `AndreHahm / prod` | Outcome-Learning | **not there**; found only at the repository-level path | **Move candidate**, your decision (see below) |
| Repo `AndreHahm / andres-cc-marketplace / prod` | Idea | exists | **Adopt** |
| Repo | Decision | exists | **Adopt** |
| Repo | Proposed Goal | exists | **Adopt** |
| Repo | Report | exists | **Adopt** |

Nothing needs creating, unless the checks in Step 1 show a database lacks the `repo` select property. In that case I would add it, with `andres-cc-marketplace` as an option, via `notion-update-page` or `notion-update-data-source`. That is a schema change, so it is listed in the plan and approved separately.

### The Outcome-Learning database
It sits at the old repository-level path, but Outcome-Learning is an organization-level type. Per the skill, I report it as a move candidate. I never move it, or recreate it, silently. I would ask you with `AskUserQuestion`, one question at a time:

1. **Outcome-Learning: how to handle it?**
   - Move it to `AndreHahm / prod` (`notion-move-pages`, and the title becomes `AndreHahm / prod / Outcome-Learning`). Existing rows are preserved. Its `repo` values keep rows distinguishable once it is shared.
   - Leave it where it is and adopt it by ID at the repository path. The config would then point at a non-standard location.
   - Create a new empty org-level database and leave the old one. This leaves two databases for the same type, so I would not recommend it.

   I would recommend the move, but I would not choose for you. I would not do anything with this database until you answer.

## Step 3: preview put in front of you (before any write)

```
Notion bootstrap plan, environment: prod, repo: andres-cc-marketplace

ORGANIZATION level  (page: AndreHahm / prod, id <resolved>)
  note              adopt   id <note-db-id>      title "AndreHahm / prod / Note"
  research          adopt   id <research-db-id>  title "AndreHahm / prod / Research"
  outcome-learning  MOVE?   id <ol-db-id>  from AndreHahm / andres-cc-marketplace / prod
                            to AndreHahm / prod       (awaiting your decision)

REPOSITORY level  (page: AndreHahm / andres-cc-marketplace / prod, id <resolved>)
  idea              adopt   id <idea-db-id>
  decision          adopt   id <decision-db-id>
  proposed-goal     adopt   id <goal-db-id>
  report            adopt   id <report-db-id>

Schema checks:  `repo` select property present on all 7?  <result>
                option "andres-cc-marketplace" present?    <result>
                database title vs data-source name match?  <result>
Config write:   .claude/workmanagement-kit.local.json (untracked)
  notion.repo = "andres-cc-marketplace"
  notion.databases.prod = { note, research, outcome-learning, idea, decision,
                            proposed-goal, report -> stable IDs }
Creates: 0 databases.  Moves: 1 (pending approval).  Schema edits: <0..n>.
Content scan: no credentials, tokens or personal data (only IDs and titles).
Deletes: none (this skill has no delete operation).
```

Then `AskUserQuestion` for plan-level approval: "Approve this exact bounded set of changes?" Options: Approve as shown / Approve without the move / Revise / Cancel.

## Step 4: after approval (calls I would make)
1. `notion-move-pages` for the Outcome-Learning database, only if you chose the move.
2. If the database title and data-source name differ, `notion-update-data-source` for the name and `notion-update-page` for the title, so both are renamed. Then `notion-fetch` the parent page to verify the child listing.
3. Add the `repo` property or option where missing.
4. Write the stable IDs and `notion.repo` into `.claude/workmanagement-kit.local.json`. The shipped `versioned-configuration.json` stays unchanged.
5. **Read back**: `notion-fetch` every database by ID and confirm parent page, title, `repo` options and location. On a timeout or unknown result I read the current state first and never blindly retry. Then record the transition per `FOUNDATION_CONTRACTS.md`'s Transition Contract, including its creation-write exception where it applies.

## Not done
- No Linear action.
- No write before your approval.
- No silent move or recreate of Outcome-Learning.
- No lookup by title alone.
