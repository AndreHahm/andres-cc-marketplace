# Bootstrap (prod): plan, with the Note move blocked

Simulation only. No Notion call has been made. I read SKILL.md, `references/bootstrap-steps.md` and `references/notion-record-types.md`.

## Result up front

I will not move the Note database, and I will not put a move in the plan for approval. Bootstrap's move rule says the plan stops when any row has a blank `repo`. Once moved under the shared organization-level page `AndreHahm / prod`, those 12 rows would be unattributable in a database shared by every repository.

Having the `andres-cc-marketplace` option on the data source does not change this. The option only exists. None of the 12 rows has it set.

I also will not back-fill the 12 rows myself. The skill puts that back-fill outside the kit: you do it as the one-time migration step, and Bootstrap then continues. After that, I re-query the rows, confirm zero blank `repo` values, and only then propose the move.

## Calls I would make before showing you anything (all read-only, no approval needed)

1. `Bash`: `git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"`. This is the trust check on the local override. A tracked copy means I fall back to the shipped `unconfigured` defaults.
2. `Read`: `host-profile.json`, `versioned-configuration.json` and `FOUNDATION_CONTRACTS.md` at the plugin root. This confirms `notion.read`/`notion.write` are `support_status: verified`, and which type sits at which scope. Tool presence alone is not permission.
3. `mcp__claude_ai_Notion__notion-search`: find the `AndreHahm / prod` page, the `AndreHahm / andres-cc-marketplace / prod` page, and the five databases.
4. `mcp__claude_ai_Notion__notion-fetch`: fetch each hit to get its stable ID and full parent chain up to the workspace root page's ID. A title is only a hint. More than one match for a target means I stop and ask you.
5. `mcp__claude_ai_Notion__notion-query-data-sources`: query the Note data source for rows with blank `repo`. This is the check you already described. I re-run it freshly and expect 12 of 12 blank.
6. `mcp__claude_ai_Notion__notion-fetch`: fetch the Note data source to read its current `repo` options and check that the `andres-cc-marketplace` option is exactly present. No `ALTER COLUMN` is needed.

For `notion.repo`, you gave `andres-cc-marketplace`. It ships `null`, so I confirm it with you in the approval question below and record it in `.claude/workmanagement-kit.local.json` via `Write`. I do not infer it from the checkout or remote. The option name passes the safe-character check.

## Plan preview I would show you (prod)

Organization-level scope, page `AndreHahm / prod` (stable ID: from step 4):

| Type | Found at | Action |
|---|---|---|
| research | org-level path (you say it is fine) | Adopt by stable ID. No change. |
| outcome-learning | org-level path (you say it is fine) | Adopt by stable ID. No change. |
| **note** | **old repo-level path only**, `AndreHahm / andres-cc-marketplace / prod / Note` | **Stopped.** Move candidate, but 12 rows have a blank `repo`. No move, no rename, no option change proposed. |

Repository-level scope, page `AndreHahm / andres-cc-marketplace / prod`:

| Type | Action |
|---|---|
| idea, decision, proposed-goal, report | Adopt by stable ID, no change. |

If any "fine" database turns out to lack a `repo` select, that also stops the plan. Bootstrap never adds the property.

Note details:
- Data source ID: from step 6.
- Current parent ID: the repo-level `prod` page.
- Intended new parent, only after the back-fill: the `AndreHahm / prod` page, by stable ID. Never the workspace root, a database or a data source.
- Blank-`repo` row count: **12, must be 0**.
- Existing `repo` options: include `andres-cc-marketplace`. No option change.
- Rename after a future move: database title and data source name both become `AndreHahm / prod / Note`, built from the layout and not from Notion text. This is not proposed now.
- Created databases: none.

## What I would ask (one `AskUserQuestion`)

Question: "The Note database has 12 rows with a blank `repo`, so I can't move it. How do you want to proceed?"

Options:
1. **Stop here (recommended).** You back-fill `repo = andres-cc-marketplace` on the 12 rows outside the kit, then ask me to rerun Bootstrap. I re-query, confirm zero blanks, and propose the move.
2. **Record the other databases' stable IDs now.** Note stays unresolved until the back-fill. I store the IDs in `.claude/workmanagement-kit.local.json` and keep `notion.repo` = `andres-cc-marketplace`.
3. **Cancel.**

This approval gate covers any local config write. Nothing is written to Notion in either case.

## What I will not do

- Call `notion-move-pages` on the Note database now.
- Call `notion-update-data-source` or `notion-update-page` to change the 12 rows or the option list.
- Recreate Note at the org level. A database already in place is adopted, never recreated.
- Pick the Note database by its title alone.

After the back-fill and a clean re-query, a move proposal would be one `notion-move-pages` call for that one database under the `AndreHahm / prod` page. I would ask for plan-level approval first, then fetch the moved database afterward and confirm its parent ID.

Tools planned: Read, Bash (git ls-files --error-unmatch), AskUserQuestion, Write (local override only), mcp__claude_ai_Notion__notion-search, notion-fetch and notion-query-data-sources. I would not call notion-move-pages, notion-update-data-source, notion-update-page, notion-create-database or notion-create-pages.
