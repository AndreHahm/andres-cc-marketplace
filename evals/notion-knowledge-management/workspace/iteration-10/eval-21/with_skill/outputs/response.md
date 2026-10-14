# Bootstrap (prod): stopped, no plan to approve

Bootstrap is a direct request, so I am allowed to run it. I am not putting a plan in front of you for approval, because the Idea database blocks it. I will not write, rename, move or alter anything in Notion.

## Calls I would make (read-only, no approval needed)

1. `Read` of `host-profile.json` and `versioned-configuration.json` at the plugin root, plus `.claude/workmanagement-kit.local.json`. Before honoring the override file, I run `Bash(git ls-files:*)` on it for the tracked-vs-untracked trust check. A tracked copy falls back to the shipped `unconfigured` defaults.
2. `mcp__claude_ai_Notion__notion-search` for the prod environment pages and databases: the org-level page `AndreHahm / prod`, the repo-level page `AndreHahm / andres-cc-marketplace / prod`, and the seven layout databases.
3. `mcp__claude_ai_Notion__notion-fetch` on every hit, to get its stable ID and full parent chain up to the workspace root page's ID. A title is only a hint. More than one match for a target means I stop and ask you.
4. `mcp__claude_ai_Notion__notion-fetch` on each database's data source, to read its properties. You report that Idea has `Name`, `Status` and `Area` and no `repo` property.

`notion.repo` is 'andres-cc-marketplace', so there is no need to ask you for the repository name. That value is recorded through `.claude/workmanagement-kit.local.json`.

## Finding

- The Idea database at the layout path would be adopted by its stable ID, never recreated.
- Its data source has no `repo` property at all, because it predates the org-level migration. Under Bootstrap step 4, that **stops the plan**.
- Bootstrap only manages the options of an existing `repo` select. It never adds the property. The guard hook denies `ADD COLUMN`, so I will not attempt:
  - `notion-update-data-source` with `ADD COLUMN "repo" ...`
  - `notion-create-database` to replace Idea
  - any workaround such as a rename plus recreate
- Record writes stay blocked by the required-property check until the property exists.

## What you need to do

Add a `repo` select property to the Idea data source yourself, outside the kit. This is the one-time migration step. After that, tell me and I re-fetch the Idea data source and continue.

## Why I am not showing the rest of the plan

The skill says the missing property stops the plan. A partial plan for the other databases would invite approval of a Bootstrap that cannot finish. Once the property is added, I would build one plan covering all of the following, and ask for plan-level approval through `AskUserQuestion` before any change:

- each candidate, with its stable ID and parent chain;
- for every `notion-update-data-source` option change (adding the 'andres-cc-marketplace' `repo` option), the data source ID, the exact `ALTER COLUMN "repo" SET SELECT(...)` string, and the option list before and after;
- for every `notion-move-pages` move, the source ID, its current parent ID and the new parent ID, which must be the same-environment org-level page `AndreHahm / prod`;
- renames: old and new titles, for both the database and its data source;
- any database to be created: its title, parent and schema.

Right before any option-change call, I would re-read the current `repo` options and send a strict superset of them. Afterwards I would fetch again and confirm that every existing option ID is still present and exactly one option was added.

## Question for you

`AskUserQuestion`: "The Idea database has no `repo` property. How do you want to proceed?"
- "I added it, re-check": re-fetch the Idea data source and continue to the plan.
- "Stop here": end Bootstrap with no changes.

(The tool also offers a free-text "Other" option.)

Tools planned: Read, Bash(git ls-files), notion-search, notion-fetch, AskUserQuestion. No Notion write tool (create-database, update-data-source, update-page, move-pages, create-pages) would be called.
