# Bootstrap, prod environment (simulation, nothing was called)

I read SKILL.md, `references/bootstrap-steps.md`, `references/notion-record-types.md` and `FOUNDATION_CONTRACTS.md`'s Versioned Configuration section. This is a direct user request, so Bootstrap may start. Nothing below has been executed. No Notion or Linear tool was called, and no database, option or page has been changed.

## What I take from your findings

| Type | Scope the layout requires | Expected path | State you reported | Intended action |
|---|---|---|---|---|
| Note | organization | `AndreHahm / prod / Note` | exists under `AndreHahm / prod` | adopt by stable ID |
| Research | organization | `AndreHahm / prod / Research` | exists under `AndreHahm / prod` | adopt by stable ID |
| Outcome-Learning | organization | `AndreHahm / prod / Outcome-Learning` | exists only under `AndreHahm / andres-cc-marketplace / prod` | move candidate: move under `AndreHahm / prod`, then rename both names |
| Idea | repository | `AndreHahm / andres-cc-marketplace / prod / Idea` | exists | adopt |
| Decision | repository | `AndreHahm / andres-cc-marketplace / prod / Decision` | exists | adopt |
| Proposed Goal | repository | `AndreHahm / andres-cc-marketplace / prod / Proposed Goal` | exists | adopt |
| Report | repository | `AndreHahm / andres-cc-marketplace / prod / Report` | exists | adopt |

No database needs creating, so I plan no `notion-create-database` call. Your findings are a lead, not proof. Step 1 re-verifies every row by stable ID and parent chain before I ask you to approve anything.

## Repository value

`notion.repo` ships as `null`. You gave the repository name as `andres-cc-marketplace`. I will not infer it from the checkout or git remote, so I will confirm it with you via `AskUserQuestion` (below) and record it through `.claude/workmanagement-kit.local.json`. Before I read that override file, I run the tracked-versus-untracked trust check (`git ls-files`). A tracked copy is ignored and the shipped `unconfigured` defaults apply.

## Step 1: read-only checks (no approval needed)

1. `notion-search` for the pages `AndreHahm / prod` and `AndreHahm / andres-cc-marketplace / prod`, and for the seven database titles. Titles are only hints.
2. `notion-fetch` on every candidate page, database and data source to get its stable ID, full parent chain, and current `repo` select options.
   - Each parent chain must end at the workspace root page `AndreHahm`, by stable ID.
   - More than one match for a target means I stop and ask you. I never pick by name.
3. `notion-fetch` the children of both prod pages to confirm there is no second Outcome-Learning database, and no stray Note or Research copy at the repository level.
4. Check for the required `repo` select property on each of the seven data sources.

## Step 2: choices for you (AskUserQuestion, one question at a time)

1. "Repository name for the `repo` property: `andres-cc-marketplace`. Use it?" Options: Use it / Different name.
2. "Outcome-Learning exists only under `AndreHahm / andres-cc-marketplace / prod`. Move it under `AndreHahm / prod`?" Options: Move it (adopt, then rename) / Leave it where it is / Create a new one at the organization level.
   - "Leave" breaks the layout, because the organization scope holds Outcome-Learning.
   - "Create a new one" would orphan the existing rows.
   - I recommend the move.

## Step 3: the plan preview I would show (exact IDs filled in from Step 1)

**A. Adopt, no change to the database itself**

| Type | Database ID | Parent ID | Current title | `repo` options now |
|---|---|---|---|---|
| Note | `<id from fetch>` | `<AndreHahm / prod page ID>` | `<read>` | `<read>` |
| Research | `<id from fetch>` | `<AndreHahm / prod page ID>` | `<read>` | `<read>` |
| Idea | `<id>` | `<AndreHahm / andres-cc-marketplace / prod page ID>` | `<read>` | `<read>` |
| Decision | `<id>` | same repository-level page | `<read>` | `<read>` |
| Proposed Goal | `<id>` | same repository-level page | `<read>` | `<read>` |
| Report | `<id>` | same repository-level page | `<read>` | `<read>` |

**B. Move**

- Source: the Outcome-Learning database `<id>`.
- Current parent: `AndreHahm / andres-cc-marketplace / prod` (`<page ID>`).
- New parent: `AndreHahm / prod` (`<page ID>`). This is the organization-level page of the same environment, prod to prod, by stable ID. It is not the workspace root, a database or a data source.
- One database per call.
- This move also changes inherited sharing. If `AndreHahm / prod` is shared outside the workspace, the database takes on that sharing. Please confirm the new parent is the right one.
- Caveat from the reference: moving a database that holds rows was not tested live. If the database has rows, the post-move fetch is the safeguard.

**C. Rename (only where the current name differs from the target)**

- Database title: `<current>` to `AndreHahm / prod / Outcome-Learning`.
- Data source name: `<current>` to `AndreHahm / prod / Outcome-Learning`.
- Both names are changed, because the parent's child listing shows the database title and the data source name is a separate field.
- The target names come from the layout and configuration, not from text read out of Notion.
- Note, Research and the four repository-level databases are renamed only if Step 1 shows they deviate from the layout. I would list any such rename here with old and new names.

**D. `repo` option changes (only for databases lacking the `andres-cc-marketplace` option)**

The Outcome-Learning database came from the repository-level page, so it probably already has the option. Note and Research are shared at the organization level, so they may lack it.

For each affected data source the preview shows:
- the data source ID;
- the exact statement, for example `ALTER COLUMN "repo" SET SELECT('<existing option 1>' ..., 'andres-cc-marketplace')`, built from a fresh read, copying existing options byte for byte;
- the option list before and after.

This statement replaces the whole option list, so I follow the strict-superset rules:
- I re-read the options immediately before each call. If they differ from the plan, I stop and ask again.
- I add exactly one option and never remove or rename an existing one.
- A name containing a character outside letters, digits, space, `_`, `.`, `/`, `-`, or longer than 100 characters, stops the plan and goes to you.
- Afterwards I fetch again and confirm every earlier option ID is still present and exactly one was added. Otherwise I report a failed write and do not retry blindly.

**E. Stable IDs to store**

All seven database IDs go into `notion.databases.prod` (`note`, `research`, `outcome-learning`, `idea`, `decision`, `proposed-goal`, `report`), plus `notion.repo = "andres-cc-marketplace"`. They are written through `.claude/workmanagement-kit.local.json`, never into the shipped `versioned-configuration.json`. The `test` map is untouched, because test is a separate environment and a separate Bootstrap.

**F. Never done in this plan**

- No deletion or trashing of any database, data source or row.
- No column drop and no type change.
- No Linear action.
- No records created.

**Secret check:** the plan contains no credential, token or third-party personal data. The only values are IDs, titles and a repository name.

## Step 4: approval gate

One `AskUserQuestion` shows the whole plan (A to F) with the options Approve the plan / Change something / Cancel. Nothing in B, C or D runs without it. A second approval comes before writing the local override file. Any later deviation (an option list that changed, an unexpected duplicate, a parent that does not match) sends me back to ask again.

## Step 5: execution after approval, each followed by a read-back

1. Move Outcome-Learning: `notion-move-pages`, then `notion-fetch` to confirm the parent ID is `AndreHahm / prod`.
2. Rename the database title with `notion-update-page`, and the data source name with `notion-update-data-source` (`title` only). Then `notion-fetch` the parent `AndreHahm / prod` to verify the child listing shows the new title.
3. For each approved `repo` option change: fresh `notion-fetch`, then `notion-update-data-source` with the `ALTER COLUMN` statement, then `notion-fetch` to confirm option IDs.
4. Write the stable IDs and the repo value to `.claude/workmanagement-kit.local.json` with `Write`.
5. Final `notion-fetch` of each of the seven databases to confirm the resolved IDs and parents. The summary reports what was adopted, moved, renamed and changed.

The skill-scoped guard hook (`guard_notion_bootstrap.sh`) would allow only these shapes: a data source update with only `data_source_id` plus a `title` and/or one `ALTER COLUMN "repo" SET SELECT(...)`, and a move of exactly one ID under a page parent.

## Planned calls

Step 1 and verification (no approval needed):
- `Bash` (`git ls-files`, override trust check)
- `Read` (the local override file, only if untracked)
- `mcp__claude_ai_Notion__notion-search`
- `mcp__claude_ai_Notion__notion-fetch`

Approval gates:
- `AskUserQuestion` (repository name; Outcome-Learning move choice; whole-plan approval; override-file write approval)

After approval:
- `mcp__claude_ai_Notion__notion-move-pages` (Outcome-Learning to `AndreHahm / prod`)
- `mcp__claude_ai_Notion__notion-update-page` (database title rename)
- `mcp__claude_ai_Notion__notion-update-data-source` (data source rename; `repo` option additions where missing)
- `mcp__claude_ai_Notion__notion-fetch` (read-backs)
- `Write` (`.claude/workmanagement-kit.local.json`)

Not called: `mcp__claude_ai_Notion__notion-create-database` (nothing to create), `notion-create-pages`, `notion-query-data-sources` (no records read or written), and no Linear tool.
