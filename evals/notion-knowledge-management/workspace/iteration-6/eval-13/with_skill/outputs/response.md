# Record a Decision: move transition history export to a background job (simulation)

Skill used: `notion-knowledge-management`. This is a Decision record (a "record a decision" request), so it is in scope. It is not a Linear action and not a learning or outcome capture.

## Result: I would not write this record. The write stops at the `repo` check.

The skill requires every record to carry the `repo` select property, set from `notion.repo`. The value must equal an existing option. If `notion.repo` is unset or matches no option, the skill says to stop and report instead of writing (SKILL.md "Record Types and Properties"; `references/notion-record-types.md` Cross-Type Rules).

- `notion.repo` = `andres-cc-marketplace`
- The Decision database's `repo` select options = `other-repo` only
- `andres-cc-marketplace` is not among the options, so the value is unmatched.

I will not take any of these shortcuts:
- Writing the record without `repo`.
- Writing `repo = other-repo`. That would file this repository's Decision under another repository.
- Silently adding the option to the select as a side effect of the Decision write.

Adding the option is a schema change. The skill treats it as one that must be listed in a plan and approved. The skill documents it under Bootstrap, as `notion-update-data-source` on an adopted database whose `repo` select lacks the option. It is not part of an ordinary record write. Changing the schema without asking would also override the stop rule without disclosure.

## What I would do before stopping (read-only, no approval needed)

1. Check the host profile and local override. Read `host-profile.json`. Confirm `notion.read` and `notion.write` are `support_status: verified`, and that their scope covers this workspace. Before honoring `.claude/workmanagement-kit.local.json`, run the tracked-vs-untracked trust check (`git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"`). A tracked or unverifiable result falls back to the `unconfigured` defaults.
2. Confirm the options with a live read. Fetch the Decision database by its stored ID from `versioned_configuration.notion.databases.<env>.decision`. This also confirms the stale-looking options list is current. Never resolve by title.

If the live read shows `andres-cc-marketplace` is in fact present, the stop no longer applies and I would go on to the normal flow below.

## Question I would put to you (AskUserQuestion)

> The Decision database's `repo` select has only `other-repo`, but `notion.repo` is `andres-cc-marketplace`. How do you want to proceed?

| Option | What it does |
|---|---|
| Add the option, then record | I list a schema-change plan (add select option `andres-cc-marketplace` to the Decision database's `repo`, via `notion-update-data-source`) and ask you to approve that plan. After approval and a read-back showing the option exists, I return with the Decision preview for its own, separate approval. |
| Fix the config instead | `notion.repo` is wrong or the database is the wrong one. You correct the local override or point me at the right database. I write nothing now. |
| Stop here | Nothing is written. |

Approving the schema change does not approve the Decision write. The record still gets its own preview and approval.

## Preview of the Decision I would show once `repo` resolves (not written)

Decision database, repository level (`AndreHahm / andres-cc-marketplace / <env> / Decision`). Record type: Decision, which is record creation and needs the live approval gate.

| Property | Value |
|---|---|
| `title` | Move transition history export to a background job |
| `decision-state` | `proposed` |
| `context` | NEEDS INPUT. You gave the decision but not the reason. |
| `alternatives` | NEEDS INPUT. Required, even if only one option was seriously weighed. |
| `consequences` | NEEDS INPUT. |
| `repo` | `andres-cc-marketplace` (from `notion.repo`; valid only once the option exists) |
| `source` | user request |
| `authority` | `notion` |
| `owner` | AndreHahm |
| `date` | 2026-10-14 |
| `related-record` | none |
| `transition-id` | absent on the create write (creation-write exception) |

I would not invent `context`, `alternatives` or `consequences`. I would ask you for them, or offer a draft you can edit. No `status` property is set, because `decision-state` is the only authoritative state for a Decision. Each text property is checked to stay at or under 2,000 characters, so the splitter is not needed. The preview also scans for anything that looks like a credential or third-party personal data, and I would flag it if found.

A Decision is created in `proposed` state. If you want it `accepted` now, Accept is a second consequential step with its own approval. It appends to the history and never overwrites the proposal.

## After approval (also not run in this simulation)

1. `notion-create-pages` to create the Decision.
2. `notion-fetch` to read it back and confirm that `repo`, `decision-state` and `title` are stored as intended. Never assume success because the call returned. After a timeout or unknown result, read before retrying.
3. Record the transition per the Transition Contract. Because this is the creation write, the read-back is the create's `verification_evidence`. It is attached to the next write to this record, or to a terminal metadata write if there is none. The terminal metadata write needs no new approval.

No Linear action is taken. Turning this Decision into execution work would be `idea-to-implementation`'s job, with its own approval.

## Planned calls

Simulation only. Nothing below was actually called. The first three are read-only, and `AskUserQuestion` is what gates the rest.

1. `Read` (host-profile.json, FOUNDATION_CONTRACTS.md, `.claude/workmanagement-kit.local.json` if present)
2. `Bash` (`git ls-files --error-unmatch ":(top,literal).claude/workmanagement-kit.local.json"`, the trust check)
3. `mcp__claude_ai_Notion__notion-fetch` (the Decision database by stored ID, to read the live `repo` options)
4. `AskUserQuestion` (the proceed / fix config / stop choice above)

Only if you pick "Add the option, then record", and only after each is separately approved:

5. `mcp__claude_ai_Notion__notion-update-data-source` (add the `andres-cc-marketplace` option to the Decision database's `repo` select; schema change)
6. `mcp__claude_ai_Notion__notion-fetch` (read back the schema)
7. `AskUserQuestion` (approve the Decision preview, after collecting context, alternatives and consequences)
8. `mcp__claude_ai_Notion__notion-create-pages` (create the Decision)
9. `mcp__claude_ai_Notion__notion-fetch` (read back the created record)

No Linear tool is called.
