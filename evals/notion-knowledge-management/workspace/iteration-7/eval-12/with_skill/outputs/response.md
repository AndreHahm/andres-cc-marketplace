# Bootstrap Notion databases, prod environment (simulation)

I read SKILL.md, `references/notion-record-types.md` and the Foundation Contracts sections on versioned configuration. No Notion or Linear tool was called. Below are the calls I would make and the plan I would show you.

## Step 0: stop and ask for the repository name

`notion.repo` is null and you have not told me the repository name. The skill says not to guess it from the checkout, the folder name or the git remote. I would ask first, before any plan or schema change:

AskUserQuestion: "What is the repository name to record as `notion.repo` for the prod bootstrap? This becomes an option on every database's `repo` select, and I will not infer it from the checkout." Header: "Repo name". I cannot enumerate real options, so the free-text "Other" answer carries the name. I would not pre-fill a guess.

Nothing below runs until you answer. Say the answer is `<repo>`. I would record it through `.claude/workmanagement-kit.local.json` (`notion.repo`), not in the tracked `versioned-configuration.json`.

## Step 1: connector and trust checks (read-only)

- Bash(git ls-files `.claude/workmanagement-kit.local.json`): the tracked-vs-untracked trust check. If the override file is tracked, I ignore its claims and fall back to the shipped `unconfigured` defaults.
- Read `host-profile.json`. It ships with `notion.read` and `notion.write` as `unconfigured`. If the override does not make both `verified`, I stop and report that the writes are not sanctioned. Tool presence does not count as permission.

## Step 2: read existing structure (read-only, no approval needed)

I resolve everything by stable ID or direct fetch, never by title text alone.

- notion-search for `AndreHahm / prod` (organization-level page).
- notion-fetch on that page to list its child databases and capture stable IDs and data source IDs.
- notion-search for the repository-level page `AndreHahm / <repo> / prod`, then notion-fetch on it to list Idea, Decision, Proposed Goal and Report.
- notion-fetch on each of the 7 databases and data sources. I check: (a) the database title and the data-source name, which are separate fields; (b) whether a `repo` select exists; (c) its current options; (d) the rest of the schema against `references/notion-record-types.md`.
- If an organization-level type is also found at the old repository-level path, it is a move candidate. If more than one database could match a target, I stop and hand the choice to you instead of picking by name.

## Step 3: the plan I would put in front of you

Nothing in it is written until you approve it. Values are what I expect to find; Step 2 confirms them.

**Organization-level page `AndreHahm / prod`** (shared by all repositories). All three are adopted by stable ID, not recreated:

| Type | Expected title | Action |
|---|---|---|
| note | `AndreHahm / prod / Note` | Adopt. Add `repo` option `<repo>`. |
| research | `AndreHahm / prod / Research` | Adopt. Add `repo` option `<repo>`. |
| outcome-learning | `AndreHahm / prod / Outcome-Learning` | Adopt. Add `repo` option `<repo>`. |

The schema change, per database, via notion-update-data-source:
`ALTER COLUMN "repo" SET SELECT('other-repo', '<repo>')`

That call replaces the whole option list, so I list the existing `other-repo` together with the new option so it is not dropped. After the call I read back each data source and confirm both options are present.

**Repository-level page `AndreHahm / <repo> / prod`.** All four are adopted:

| Type | Expected title | Action |
|---|---|---|
| idea | `AndreHahm / <repo> / prod / Idea` | Adopt |
| decision | `AndreHahm / <repo> / prod / Decision` | Adopt |
| proposed-goal | `AndreHahm / <repo> / prod / Proposed Goal` | Adopt |
| report | `AndreHahm / <repo> / prod / Report` | Adopt |

For each, if Step 2 shows the `repo` select is missing or lacks `<repo>`, the plan lists that as an extra schema change (keeping any existing options). I will not assume they already carry it.

**Renames, only if Step 2 shows a mismatch.** A database's title (notion-update-page) and its data source's name (notion-update-data-source) are separate fields. If either differs from the convention, both are renamed and I verify the parent page's child listing.

**Creates:** none expected, since all seven databases exist.
**Moves:** none unless Step 2 finds a type at the old path. Such a move is listed separately and needs your explicit approval.
**Config recorded (local override only):** `notion.repo = "<repo>"` and the seven stable IDs under `notion.databases.prod` (`note`, `research`, `outcome-learning`, `idea`, `decision`, `proposed-goal`, `report`). The `test` map is untouched.

Approval gate: AskUserQuestion, "Apply this bootstrap plan?" with Approve as shown, Change something, Cancel. The `repo` option additions are schema changes approved together with the rest of the plan.

## Step 4: after approval

1. notion-update-data-source once per data source needing the `repo` option (3 org-level, plus any repo-level ones found).
2. notion-update-page and notion-update-data-source for approved renames; notion-move-pages only if a move was approved.
3. Read back with notion-fetch on every changed data source (options, titles) and report any mismatch rather than assuming success. After a timeout or unknown result I read current state before any retry.
4. Write the IDs and `notion.repo` to `.claude/workmanagement-kit.local.json`, and record the transition per the shared contract.

No Linear calls at any point. No records are created; this is schema and config only.

## Planned calls

- AskUserQuestion (repo name, then plan approval)
- Bash (`git ls-files` trust check on `.claude/workmanagement-kit.local.json`)
- Read (host-profile.json, versioned-configuration.json, override file)
- mcp__claude_ai_Notion__notion-search
- mcp__claude_ai_Notion__notion-fetch
- mcp__claude_ai_Notion__notion-update-data-source (after approval: add the `repo` option, rename data sources if needed)
- mcp__claude_ai_Notion__notion-update-page (after approval, only if a title rename is needed)
- mcp__claude_ai_Notion__notion-move-pages (only if a move candidate is found and approved)
- Write (`.claude/workmanagement-kit.local.json`, after approval)
