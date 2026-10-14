# Bootstrap Notion databases, prod (simulation)

I read SKILL.md and `references/bootstrap-steps.md` from the worktree. This is a direct user request, so Bootstrap may start. No Notion or Linear tool is called here. Below are the calls I would make and the plan I would show you.

## Step 0: configuration and trust check

1. `Bash(git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json")` checks that the local override file is untracked. Only exit 1 ("did not match") lets me honor its contents. A tracked or unverifiable result means I fall back to the shipped `unconfigured` defaults.
2. I read `host-profile.json`. As shipped, `notion.read` and `notion.write` are `support_status: "unconfigured"`. If the override does not raise them to `verified`, I stop and report that no write is sanctioned. Having the connector tool callable is not proof of permission. The plan below assumes they read `verified`.

## Step 1: the repository name is unknown, so I ask

`notion.repo` is `null`, and I must not infer it from the checkout, directory or git remote. I would call `AskUserQuestion`:

- Question: "What is the repository name to write into the `repo` select property for prod?"
- Header: "Repo name"
- Options: a "Type the repository name" option and a "Stop, I will set it in config first" option. The tool's "Other" free-text fallback carries the typed name.

Everything below uses `<repo>` for the answer. I do not proceed until you give a name. The name must contain only letters, digits, space, `_`, `.`, `/` or `-`, and be at most 100 characters. Otherwise the plan stops. I would record it in `.claude/workmanagement-kit.local.json` under `versioned_configuration.notion.repo`.

## Step 2: read-only discovery (no approval needed)

- `mcp__claude_ai_Notion__notion-search` finds the page `AndreHahm / prod`, the repository page `AndreHahm / <repo> / prod`, and any databases titled `AndreHahm / prod / <Type>` or `AndreHahm / <repo> / prod / <Type>`.
- `mcp__claude_ai_Notion__notion-fetch` on each candidate gets its stable ID, full parent chain and schema. The chain must end at the workspace root page `AndreHahm`. A title match is only a hint, and more than one match for a target means I stop and ask you.
- For each of the three organization-level databases (Note, Research, Outcome-Learning) I fetch the data source and read the current `repo` options, which here should be only `other-repo`, with their option IDs.
- For the four repository-level databases (Idea, Decision, Proposed Goal, Report) I fetch each data source and check that it has a `repo` select and whether it contains the option `<repo>`.
- I also look for any organization-level type that exists only at the old repository-level path. That would be a move candidate. I expect none, since you described Note, Research and Outcome-Learning as already at the organization level.

## Step 3: plan preview (what you would approve)

IDs are shown as placeholders because nothing is read in this simulation.

**Adopt (no recreate, no changes beyond what is listed below)**

| Scope | Database | Stable ID | Parent chain |
|---|---|---|---|
| org | AndreHahm / prod / Note | `<id>` | AndreHahm / prod -> AndreHahm (root) |
| org | AndreHahm / prod / Research | `<id>` | same |
| org | AndreHahm / prod / Outcome-Learning | `<id>` | same |
| repo | AndreHahm / `<repo>` / prod / Idea | `<id>` | AndreHahm / `<repo>` / prod -> AndreHahm (root) |
| repo | ... / Decision | `<id>` | same |
| repo | ... / Proposed Goal | `<id>` | same |
| repo | ... / Report | `<id>` | same |

**Option changes (3 organization-level data sources, `notion-update-data-source`)**

For each of Note, Research and Outcome-Learning:

- Data source ID: `<ds-id>`
- Options before: `other-repo` (id `<opt-id>`)
- Options after: `other-repo` (unchanged, same ID), plus `<repo>` (new)
- Exact statement to send: `ALTER COLUMN "repo" SET SELECT('other-repo' <existing color>, '<repo>')`

`SET SELECT` replaces the whole list. Dropping `other-repo` would delete another repository's option on a shared database, so the statement is a strict superset. It copies `other-repo` byte for byte (name and color) from a fresh read and adds exactly one option. No `DROP COLUMN`, type change or `in_trash`.

**Repository-level databases:** if any of the four lacks a `<repo>` option, it gets the same single-option addition, listed in the same format. If they already carry it, they are not touched.

**Moves:** none planned. **Renames:** none planned, since adopted names already follow the layout. If a title or data source name differs from the layout, the old and new names would be listed here.

**Created databases:** none.

**Config written after approval:** the stable IDs go in `versioned_configuration.notion.databases.prod` in `.claude/workmanagement-kit.local.json`, and `notion.repo` is set to `<repo>`. Nothing goes in the tracked `versioned-configuration.json`.

Then `AskUserQuestion`: "Approve this exact Bootstrap plan for prod?" with options "Approve plan", "Change the plan" and "Cancel". Nothing in Notion changes before this approval.

## Step 4: execution after approval

For each option change, one at a time:

1. Re-read right before the call: `notion-fetch` on the data source. If the live options differ from the approved plan, I stop and ask again.
2. Build the statement from that fresh read only, check the option name against the safe-character rule, then call `notion-update-data-source`. The skill's guard hook (`guard_notion_bootstrap.sh`) allows only this shape.
3. Read back with `notion-fetch`. Every prior option ID (`other-repo`) must still be present and exactly one option (`<repo>`) added. Otherwise I report a failed write and do not retry blindly.

Then I save the IDs and `notion.repo` to the local override file with `Write`. Last, I verify the parent pages' child listings via `notion-fetch`.

## Limits I would tell you about

- The guard hook cannot check that an option list is a superset of the current one. The fresh read, the strict-superset rule and the option-ID check above are the only defence.
- Nothing here is guessed. The repository name comes only from your answer.

## Planned calls

- `Bash` (`git ls-files` trust check on the local override file)
- `Read` (host profile, versioned configuration, override file)
- `AskUserQuestion` (repository name)
- `mcp__claude_ai_Notion__notion-search`
- `mcp__claude_ai_Notion__notion-fetch`
- `AskUserQuestion` (plan approval)
- `mcp__claude_ai_Notion__notion-update-data-source` (3 org-level `repo` option additions, plus any repo-level one that lacks `<repo>`)
- `mcp__claude_ai_Notion__notion-fetch` (fresh read before and read-back after each option change, and the child-listing check)
- `Write` (`.claude/workmanagement-kit.local.json`)
