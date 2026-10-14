# Bootstrap plan: Notion databases, `prod` environment (simulation)

No Notion or Linear tool was called. Everything below is the plan I would put in front of you, plus the calls I would make. Nothing is created, changed or moved until you approve the plan.

## 1. Preconditions (checked before any connector call)

- **Host profile.** `host-profile.json` ships with `notion.read` and `notion.write` at `support_status: "unconfigured"`. Having the Notion tools in this session is not proof of permission. I would check the effective profile first. If `notion.write` is not `verified` for the approved workspace, I stop and report that, and no write happens.
- **Override trust check.** I would run `git ls-files .claude/workmanagement-kit.local.json` before honoring that file. It does not exist in this worktree today. A tracked copy would fall back to the shipped defaults. The stable IDs below would be stored in this override, not in the skill and not in the shipped `versioned-configuration.json`.
- **`notion.repo`** ships `null`. You gave the repository name `andres-cc-marketplace`. I take that as your answer to the "ask for the repository name" step and would record it as `notion.repo` in the override, not guess it from the checkout. I show it in the plan so you can correct it.
- **Stable IDs only.** All databases are resolved by stable ID or direct fetch, never by title text or the parent page's child listing. Two databases can share a name.

## 2. Read-only discovery (no approval needed)

1. Search for the two parent pages: `AndreHahm / prod` (organization level) and `AndreHahm / andres-cc-marketplace / prod` (repository level).
2. Fetch each parent page, then each database, to get its ID, data source ID, title, data source name and `repo` select options.
3. Targets: Note and Research under the org page; Idea, Decision, Proposed Goal, Report and Outcome-Learning under the repo page.
4. If more than one database could match any target, I stop and hand the choice to you. I do not pick by name.

## 3. Findings and proposed bootstrap plan (what I would show you)

Layout from the skill and `FOUNDATION_CONTRACTS.md`:

- Organization level, page `AndreHahm / prod`, titled `AndreHahm / prod / <Type>`: `note`, `research`, `outcome-learning`.
- Repository level, page `AndreHahm / andres-cc-marketplace / prod`, titled `AndreHahm / andres-cc-marketplace / prod / <Type>`: `idea`, `decision`, `proposed-goal`, `report`.

| Record type | Correct scope | Where it is now | Proposed action |
|---|---|---|---|
| note | org | org page (exists) | Adopt by ID |
| research | org | org page (exists) | Adopt by ID |
| outcome-learning | org | repo page only (old path) | **Move candidate**: move to the org page, rename, adopt |
| idea | repo | repo page (exists) | Adopt by ID |
| decision | repo | repo page (exists) | Adopt by ID |
| proposed-goal | repo | repo page (exists) | Adopt by ID |
| report | repo | repo page (exists) | Adopt by ID |

No database needs to be created. I would not call `notion-create-database`: a new Outcome-Learning database at the org level would orphan the existing one and its rows.

Exact bounded changes I would ask approval for, in order:

1. **Move** the Outcome-Learning database from `AndreHahm / andres-cc-marketplace / prod` to `AndreHahm / prod` (`notion-move-pages`). This moves the existing database, rows included, so other repositories can share it.
2. **Rename both names** of that database to `AndreHahm / prod / Outcome-Learning`: the database title (`notion-update-page`) and the data source name (`notion-update-data-source`). They are separate fields that can differ, and the parent's listing shows the database title. I would verify the org page's listing afterward.
3. **`repo` option on each adopted database.** All seven carry the required `repo` select. For each database whose `repo` select lacks `andres-cc-marketplace`, add that option (`notion-update-data-source`). This is likely for Note, Research and Outcome-Learning, the shared org databases. It is listed as a schema change for approval, and only where discovery shows it missing.
4. **Write config.** Store the seven stable IDs under `notion.databases.prod` (`note`, `research`, `outcome-learning`, `idea`, `decision`, `proposed-goal`, `report`) and `notion.repo = "andres-cc-marketplace"` in `.claude/workmanagement-kit.local.json`. The `test` map stays untouched because this run is `prod` only.

Not planned: any edit of the four repo-level databases beyond the `repo` option, any record creation, and anything in Linear.

## 4. Approval gate (via `AskUserQuestion`, not a free-text prompt)

I ask these one at a time and wait for each answer:

1. **Outcome-Learning.** "The Outcome-Learning database exists only under `AndreHahm / andres-cc-marketplace / prod`, but the layout puts it at the organization level. What should I do?"
   - Move it to `AndreHahm / prod` and rename both names (recommended)
   - Keep it at the repo level for now (adopt in place, flag as a layout deviation)
   - Create a new one at the org level (the existing one stays and is not adopted)
2. **Repository name.** "Record `andres-cc-marketplace` as `notion.repo`?" Yes / No, use a different name.
3. **Plan approval.** The full plan above: the move, the two renames, the `repo` option additions (with the exact list once discovery shows which databases lack it), and the override write. Approve / Change something / Cancel.

Because nothing was fetched in this simulation, the database IDs, which `repo` options are missing, and whether any name collision exists are unknown. The final preview would fill them in from discovery.

## 5. Execution and read-back (after approval only)

1. `notion-move-pages` for Outcome-Learning, then fetch it to confirm its parent is the org page.
2. `notion-update-page` (title) and `notion-update-data-source` (data source name) for Outcome-Learning. Fetch both and the org page listing to confirm they read `AndreHahm / prod / Outcome-Learning`.
3. `notion-update-data-source` per database that lacks the `repo` option. Fetch each schema to confirm the option exists.
4. Write the override file with the stable IDs.
5. Re-fetch all seven databases by stored ID and confirm parent page, title and `repo` option. On a timeout or unknown result, read current state before any retry and never repeat a move or schema change blindly.
6. Report the seven IDs and the final layout. Bootstrap creates no record, so no transition evidence is written.

## Planned calls

- `Bash` (`git ls-files .claude/workmanagement-kit.local.json`, the override trust check)
- `Read` (host profile, versioned configuration, local override if present)
- `mcp__claude_ai_Notion__notion-search`
- `mcp__claude_ai_Notion__notion-fetch`
- `AskUserQuestion` (Outcome-Learning choice, repository name, plan approval)
- `mcp__claude_ai_Notion__notion-move-pages` (Outcome-Learning, after approval)
- `mcp__claude_ai_Notion__notion-update-page` (Outcome-Learning database title, after approval)
- `mcp__claude_ai_Notion__notion-update-data-source` (Outcome-Learning data source name; `repo` option additions where missing, after approval)
- `Write` (`.claude/workmanagement-kit.local.json`, after approval)

Not called: `mcp__claude_ai_Notion__notion-create-database`, `mcp__claude_ai_Notion__notion-create-pages`, `mcp__claude_ai_Notion__notion-query-data-sources`, any Linear tool, and the splitter script (no long text involved).
