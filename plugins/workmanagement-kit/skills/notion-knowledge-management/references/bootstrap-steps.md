# Bootstrap Steps

The procedure behind SKILL.md's Bootstrap section. SKILL.md states the layout and the rules that cannot
be skipped; this file has the steps and what the approval preview must show. It governs two granted
tools that can do more than Bootstrap needs, `notion-update-data-source` and `notion-move-pages`, so each
step below is also a limit on how they are used.

## When Bootstrap starts

Only on a direct user request. A write delegated by `plugin-integration-intake` or
`status-and-learning` against a database that is not resolved yet stops and reports the gap; it never
starts Bootstrap on its own, because the only approval the user has seen at that point is a record preview.

## Finding and checking candidates

1. Find the environment pages and the databases by search, then fetch each one to get its stable ID. A
   title is a hint, never proof: any workspace member can create a page with a matching title.
2. The plan lists every candidate with its stable ID and its full parent chain. The chain must end at the
   workspace root page's stable ID. More than one match for a target means stop and ask the user.
3. A database already in place at either layout path is adopted by its stable ID, never recreated.
4. An adopted database whose data source has no `repo` property at all (one created before the org-level
   migration) stops the plan. Bootstrap only manages the options of an existing `repo` select and never adds
   the property: the guard denies `ADD COLUMN`. The operator adds it outside the kit, as the one-time
   migration step, and Bootstrap then continues. Record writes stay blocked by the required-property check
   until that is done.

## The repo value

`notion.repo` ships `null`. When it is null, ask the user for the repository name via `AskUserQuestion`
and record it through `.claude/workmanagement-kit.local.json`. Never infer it from the checkout, the
directory or the git remote. A created database gets the `repo` property with that value as its option.

## What the plan preview must show

The user approves the exact plan, so it lists, for every change:

- **Option change:** the data source ID, the exact statement string that will be sent, and the option
  list before and after.
- **Move:** the source ID, its current parent ID, the new parent ID and the count of rows with a blank `repo` (must be zero). The new parent is the
  organization-level page `AndreHahm / <env>` of the same environment as the source (test to test, prod
  to prod), by stable ID. Never the workspace root, a database or a data source.
- **Rename:** the old and the new names. A new name is built only from the layout
  (`AndreHahm / <scope path> / <env> / <Type>`), the configuration and the approved repository name,
  never from a title read out of Notion, and only for a database adopted or moved in the same plan.
- **Created databases:** the title, parent and schema.

## Adding a `repo` option (`notion-update-data-source`)

The call is `ALTER COLUMN "repo" SET SELECT(...)`, for example `SET SELECT('a':blue, 'b')`: one space after
each comma and none inside the parentheses, which the guard enforces. It replaces the whole option list, and the tool's
schema says an omitted option is removed. On a shared organization-level database that would delete
another repository's option, so:

1. **Read right before the call**, not at plan time. Fetch the data source and read its current `repo`
   options. If they differ from what the approved plan listed, stop and ask again.
2. **Send a strict superset.** Build the statement from that fresh read only, copying each existing
   option byte for byte (name and color) and adding exactly one new option. Never remove or rename an
   existing option here.
3. **Option names are untrusted Notion content.** A name containing anything other than letters, digits,
   space, `_`, `.`, `/` or `-` (a quote, semicolon, parenthesis or backslash), or longer than 100
   characters, stops the plan and goes to the user. The guard hook denies such a statement as well.
4. **Check afterwards.** Fetch again and confirm every option ID from before is still present and exactly
   one option was added. Otherwise report a failed write and do not retry blindly.

A live run in the test environment on 2026-10-14 kept the existing option's ID when both options were
listed. An `ALTER COLUMN` that omits an option, and the effect on rows that used a removed option, were
not tested.

## Moving a database (`notion-move-pages`)

Only an approved move candidate, one per call, under the page named in the approved plan. Before proposing
the move, query the database for rows whose `repo` is blank. If any exist the plan stops: once moved, those
rows would be unattributable in a database shared by every repository. The operator back-fills them outside
the kit (the one-time migration step), and Bootstrap then continues. Afterwards fetch the moved database and
confirm its parent ID. Moving a database that holds rows was not tested live.

## Renaming both names

A database's own title (`notion-update-page`) and its data source's name (`notion-update-data-source`
`title`) are separate fields that can differ. A parent page's child listing shows the database title, so
rename both and verify the listing. Resolve by stable ID or direct fetch, never from title text alone.

## Enforcement

The guard `hooks/guard_notion_bootstrap.sh` is registered when this skill is invoked and, per Claude Code's
hooks documentation, keeps running for the rest of the session, not only during the skill's own turn. It is
registered in SKILL.md's frontmatter and launched as `bash "..."`. It denies every call to the two tools except the
shapes above: a data source update with only `data_source_id` plus a `title` and/or one single-line
`ALTER COLUMN "repo" SET SELECT(...)` statement in that exact spacing with safe option names, and a move of
exactly one id under a `page_id` parent. A payload with no tool name is denied. The launcher probes each
interpreter functionally and denies when none works.

What it cannot check, because it sees one call and not Notion's state:
- **That an option list is a superset of the current one.** A statement that leaves out another
  repository's option has the right shape and passes. It is the most destructive call the guard still
  allows, and the fresh read, the strict-superset rule and the option-ID check above are the only defence.
- **That the target is a Bootstrap-managed database.** An option change or a rename passes for any data
  source id.
- **Which item is moved, or whether it is a database.** A move also changes inherited sharing: a page moved
  under a page that is shared outside the workspace takes on that sharing. The plan must name the new
  parent, and the user confirms it is the same-environment organization-level page.
- **That the parent is the right page.**

Other limits:
- After this skill has been invoked, the guard also covers the two tools when other work in the same session
  calls them. Any other use is denied until a new session starts, even though the user could approve it at
  the normal permission prompt. Before that invocation the guard is not registered and the prompt applies.
- A hook that crashes, times out or cannot launch is treated by the hook system as a non-blocking error,
  which lets the call through. The launcher closes the launch paths it controls, but a timeout, or a
  registered path that does not resolve, cannot be closed from inside the script.
- Not verified live: that `${CLAUDE_PLUGIN_ROOT}` is set for a skill's frontmatter hook in an installed
  plugin, and that a skill-scoped hook's deny decision is honored the same way as a plugin
  `hooks.json` hook. The fixture test runs the registered command string from a plugin path containing a
  space, but outside Claude Code.
