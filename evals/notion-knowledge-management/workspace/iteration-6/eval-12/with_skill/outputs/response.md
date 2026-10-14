# Notion Bootstrap, prod environment (simulation)

I read `notion-knowledge-management/SKILL.md`, `references/notion-record-types.md` and `FOUNDATION_CONTRACTS.md` (Versioned Configuration and Local Override sections). No Notion or Linear tool was called. Everything below is the plan I would put in front of you.

## Step 0: gate checks before any Notion call

1. **Local override trust check.** Run `git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"`.
   - Exit 1 ("did not match any file(s)"): the file is untracked, so its overrides may be honored.
   - Exit 0 or any other outcome: fall back to the shipped `unconfigured` defaults, and stop.
2. **Host profile.** Check that `notion.read` and `notion.write` show `support_status: "verified"` in the merged host profile. A callable Notion tool is not proof of permission. If they are not verified, I stop and report. Bootstrap writes do not proceed on the assumption that a check happened.

## Step 1: the repository name is unknown, so I ask you

`notion.repo` ships `null`. The skill says the name must not be guessed from the checkout. I will not infer it from the directory name, the git remote, or the sibling page title.

I would ask via `AskUserQuestion`:

> **Which repository name should this installation write into the `repo` property?**
> `notion.repo` is null, and I will not guess it from the checkout. Please give the exact name. It becomes the value of the required `repo` select on all seven record types, and I will record it through `.claude/workmanagement-kit.local.json`.
> Options (the tool also adds "Other" for free text):
> - "Use the name of the repository-level page I find" (I would show the candidate name read from the existing page title, for you to confirm. It is not auto-chosen.)
> - "Enter the name myself"

Nothing below proceeds until you answer. In the rest of this plan I write `<REPO>` for your answer.

## Step 2: read-only discovery (no approval needed)

Reads, previews and classification need no approval, so I would run these now:

- `notion-search` for the page `AndreHahm / prod`, the page `AndreHahm / <REPO> / prod`, and any `AndreHahm / prod / ...` or `AndreHahm / <REPO> / prod / ...` databases.
- `notion-fetch` on each hit, to get stable IDs (page, database and data source) and the current schema.

I resolve by stable ID or direct fetch, never from title text alone. If more than one page or database could match, I stop and hand the choice to you.

For each of the seven databases I record:
- its database ID,
- its data source ID,
- its database title and its data source name (these are separate fields and can differ),
- whether its `repo` select exists and which options it has.

## Step 3: the plan I would present for approval

All four lines below are bounded changes. Nothing is created, changed or moved yet.

### Organization-level page `AndreHahm / prod` (shared by every repository)

| Type | Database title expected | Action |
|---|---|---|
| note | `AndreHahm / prod / Note` | **Adopt** by stable ID, and **add select option `<REPO>`** to `repo` (currently only `other-repo`) |
| research | `AndreHahm / prod / Research` | **Adopt**, and **add option `<REPO>`** to `repo` |
| outcome-learning | `AndreHahm / prod / Outcome-Learning` | **Adopt**, and **add option `<REPO>`** to `repo` |

- The existing `other-repo` option is kept untouched. These databases are shared, so another repository's rows depend on it.
- Adding the option is a schema change, made with `notion-update-data-source` on each of the three data sources. It is listed in this plan and approved with it. I would not add it without approval.
- Nothing is recreated. The databases already exist, so I adopt them.

### Repository-level page `AndreHahm / <REPO> / prod`

| Type | Database title expected | Action |
|---|---|---|
| idea | `AndreHahm / <REPO> / prod / Idea` | **Adopt** |
| decision | `AndreHahm / <REPO> / prod / Decision` | **Adopt** |
| proposed-goal | `AndreHahm / <REPO> / prod / Proposed Goal` | **Adopt** |
| report | `AndreHahm / <REPO> / prod / Report` | **Adopt** |

- Every database carries the required `repo` select. If the fetch in Step 2 shows one of these four lacks a `repo` property, or lacks the `<REPO>` option, I add it as an additional schema change in this same plan. I do not assume it is already there.
- I would show you the actual result of that check in the preview, not just say it was fine.

### Checks that could change the plan

- If a database for an organization-level type (note, research, outcome-learning) is found only at the old repository-level path, it is a **move candidate** (`notion-move-pages`). I list it in the plan and move it only after you approve it. This is never done silently.
- If a database title or its data source name does not match the expected `AndreHahm / ...` form, I list a rename of **both** fields (`notion-update-page` for the title, `notion-update-data-source` for the data source name), then verify the parent page's child listing afterward.
- Whether anything is created at all: I would create nothing unless a database is missing, because all seven are said to exist.

### Local configuration

I would write the stable IDs and `notion.repo` into `.claude/workmanagement-kit.local.json` (the plugin's gitignored local override), not into the skill's own state:

```
versioned_configuration.notion.repo = "<REPO>"
versioned_configuration.notion.databases.prod = {
  note, research, outcome-learning,      # organization-level IDs
  idea, decision, proposed-goal, report  # repository-level IDs
}
```

- The `prod` map is filled independently of `test`. I do not touch `test` in this run.
- Real IDs belong only in the local override, never in tracked files. I would not echo them into any tracked location.
- Honoring that file again later is subject to the same untracked-file check as Step 0.

### Approval request

After showing the table above, I would ask via `AskUserQuestion`:

> Approve exactly these changes? (3 schema updates adding option `<REPO>` to `repo` on Note, Research and Outcome-Learning; 4 repository-level databases adopted with no change unless the check shows a missing `repo` property or option; local override written with these IDs.)
> - Approve the plan as listed
> - Change something (for example, skip a database)
> - Cancel

If you pick anything other than approve, no call is made.

## Step 4: execution, only after approval

1. `notion-update-data-source` on each of the three organization-level data sources, to add the `<REPO>` option to `repo`.
2. The same call on any repository-level data source the check showed was missing it. Any approved move or rename is done here too.
3. **Read back** each changed data source with `notion-fetch` and confirm `repo` now lists both `other-repo` and `<REPO>` for the organization-level ones. A call that returns without error is not proof. On a timeout or unknown result I read current state before any retry, and I never repeat a write blindly.
4. `Write` the verified IDs and `notion.repo` to the local override. No Linear tool is involved at any point.

No Idea, Note, Decision or other record is created in this run. This is Bootstrap only, so the record-creation approval gate is not triggered. The schema changes are covered by the plan approval above.

## Planned calls

1. `Bash` (`git ls-files --error-unmatch ...`, the trust check)
2. `Read` (the local override and the host profile / versioned configuration)
3. `AskUserQuestion` (repository name for `notion.repo`)
4. `mcp__claude_ai_Notion__notion-search`
5. `mcp__claude_ai_Notion__notion-fetch`
6. `AskUserQuestion` (plan approval)
7. `mcp__claude_ai_Notion__notion-update-data-source` (add the `repo` option; also data source rename if needed)
8. `mcp__claude_ai_Notion__notion-update-page` (only if a database title rename is needed)
9. `mcp__claude_ai_Notion__notion-move-pages` (only if an approved move candidate exists)
10. `mcp__claude_ai_Notion__notion-fetch` (read-back)
11. `Write` (the local override)

I would not call `mcp__claude_ai_Notion__notion-create-database`, `notion-create-pages`, or any Linear tool.
