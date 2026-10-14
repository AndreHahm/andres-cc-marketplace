# Idea write: "Add a --dry-run flag to the bulk exporter" (area: tooling)

**Result: I am not writing this record. I'm stopping and reporting the gap. Nothing was written and nothing was previewed for approval.**

## What I checked

1. **Routing.** An Idea captured through `plugin-integration-intake` is a record this skill (`notion-knowledge-management`) writes. It is not a Linear action and not an Outcome/Learning, so it is in scope. The Idea is already approved at intake. This skill's own gate still applies to the Notion write itself: a record preview, then `AskUserQuestion`.
2. **Host profile (`host-profile.json`).** `notion.read` and `notion.write` both read `support_status: "unconfigured"`, `verified_at: null`, `connector: null`. No `.claude/workmanagement-kit.local.json` exists in this checkout, so there is no override to trust-check. The connector tools being callable is not proof of permission or scope. No write may proceed on the assumption that a sanctioning check happened.
3. **Idea database ID.** `notion.databases.prod` is empty, as you said (`test` is empty too). The Idea database sits in the repository-level scope, `AndreHahm / <repo> / prod / Idea`, and it has not been resolved or adopted by stable ID. I will not find it by searching for a title and writing to the best match: a title is a hint, never proof.
4. **`repo` property.** `notion.repo` ships `null` and nothing overrides it. `repo` is required on every record and must come from `notion.repo`. A null value means stop and report. I won't infer it from the checkout, directory or git remote.
5. **Bootstrap.** `references/bootstrap-steps.md` is explicit: a write delegated by `plugin-integration-intake` against a database that is not resolved yet stops and reports the gap. It never starts Bootstrap on its own, because the only approval you have seen at that point is a record preview. Bootstrap runs only on your direct request.

## Why a preview/approval prompt would be wrong now

An approval prompt would put a write in front of you that has no target database, no verified `notion.write` operation and no `repo` value. Approving it would not make it valid, and it would imply a Bootstrap I'm not allowed to start from a delegated write. I'm reporting the blockers instead.

## Draft of the record (for reference only, not an approval request, not written)

| Property | Value |
|---|---|
| title | Add a --dry-run flag to the bulk exporter |
| area | tooling |
| body | **Missing.** Idea requires `body`, and the hand-off gave only title and area. Intake must supply it, or I ask you. I won't invent one. |
| source | `plugin-integration-intake` (the submitting plugin's request) |
| authority | `notion` |
| status | per the Idea schema's initial status (not defined beyond the shared set) |
| owner / date | filled at write time |
| repo | **BLOCKED**: `notion.repo` is null |
| transition-id | absent on the create write (creation-write exception) |

## What is needed to unblock (your decision)

1. Verify and configure `notion.read` / `notion.write` in `.claude/workmanagement-kit.local.json`. It must be gitignored and untracked, since a tracked copy is ignored by the trust check.
2. Run Bootstrap on a direct request from you to resolve or adopt the prod Idea database (stable ID, full parent chain ending at the workspace root) and record `notion.databases.prod`. Bootstrap shows its own plan-level preview and needs its own approval. This includes asking you for the repository name for `notion.repo`.
3. Supply the Idea `body`.

Once those are in place I would re-run the write: preview the record, ask for approval through `AskUserQuestion`, call `notion-create-pages`, read back with `notion-fetch`, then record the transition.

Next step (your choice): start Bootstrap now, or leave the Idea pending at intake until setup is done.

## Planned calls

- None. No Notion or Linear tool is called in this run, because the write is blocked before any call is justified.
- (Local, read-only checks already done: `Bash` `git ls-files` on `.claude/workmanagement-kit.local.json`, which found nothing tracked.)
- Planned only after unblocking: `AskUserQuestion` (record-preview approval), `mcp__claude_ai_Notion__notion-create-pages` (create the Idea), `mcp__claude_ai_Notion__notion-fetch` (read-back).
- Not planned: `mcp__claude_ai_Notion__notion-search` to guess the database, `mcp__claude_ai_Notion__notion-create-database`, `mcp__claude_ai_Notion__notion-update-data-source` and `mcp__claude_ai_Notion__notion-move-pages` (Bootstrap only, on your direct request), and any Linear tool.
