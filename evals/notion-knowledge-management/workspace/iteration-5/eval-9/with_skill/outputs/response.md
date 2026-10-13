# Record a Decision: transition history export moves to a background job (simulation)

## Outcome: write blocked, nothing sent, no approval requested

I followed `notion-knowledge-management` (Decision, Propose). I built the record and the preview below, but I will **not** ask for write approval and I make **no write call**. `notion.repo` is `null`, and `repo` is a required property on every record type.

- `references/notion-record-types.md`, Cross-Type Rules: `repo` is set from the configured `notion.repo`, "never from the record's content or a caller's message." If `notion.repo` is unset or matches no option, "stop and report instead of writing the record without it."
- `FOUNDATION_CONTRACTS.md`: `notion.repo` ships `null`, and a `null` value means "no Notion record write may proceed ... the kit never guesses a repository."

I will not infer a repo from the working directory or git remote (for example `andres-cc-marketplace`). I will not write the record without `repo`, and I will not use an `AskUserQuestion` approval to get around this. The approval gate covers the record content. It does not fill in a missing required configuration value.

A second blocker applies independently. The shipped `host-profile.json` has `notion.read` and `notion.write` at `support_status: "unconfigured"` and `verified_at: null`. The skill says tool presence is not proof of permission, and no write may proceed until an operation reads `verified`. Before honoring any `.claude/workmanagement-kit.local.json` override, I would run `git ls-files` on it. A tracked copy is ignored and the shipped `unconfigured` defaults apply. In this simulation the only resolved fact is `notion.repo = null`.

## What I need from you to unblock

1. Set `notion.repo` in `.claude/workmanagement-kit.local.json` (gitignored, untracked) to the repository name. It must equal an existing option of the `repo` select property in the Notion Decision database.
2. Make sure `notion.write` and `notion.read` are `verified` in the host profile override (Foundational Setup).

Once both are done, I re-run this request, show the preview again with `repo` filled, and ask for approval.

## Calls I would make once unblocked (none made now)

1. **Reads (no approval needed):**
   - `notion-search` / `notion-fetch` / `notion-query-data-sources` against the repository-level Decision database (`AndreHahm / <repo> / <env> / Decision`, resolved by stored ID). This checks for an existing or conflicting Decision on the export and confirms the `repo` option exists.
   - Optionally search for a related Idea or Report to fill `related-artifact`.
2. **Length check:** every text property must be 2,000 characters or fewer. All of them are well under in the preview below.
3. **Approval:** `AskUserQuestion` showing the preview below, because Propose is a gated write. The question also states that nothing in it looks like a credential, token or personal data.
4. **Write:** `notion-create-pages` into the Decision database with `decision-state = proposed`, `repo = <notion.repo>`, `authority = notion` and a `transition-id`.
5. **Read-back:** `notion-fetch` of the new page to confirm the stored properties. Then record the transition per the Transition Contract. This is a creation write, so the creation-write exception applies and `verification_evidence` lands on the next write to this record.
6. **Not made:** no Linear call. This skill never touches Linear, and promotion is `idea-to-implementation`'s separate gated job.

## Preview (as it would be shown for approval, if unblocked)

**Record type:** Decision (Propose, so state starts at `proposed`, not `accepted`)

| Property | Value |
|---|---|
| title | Move transition history export to a background job |
| context | The transition history export currently runs in the foreground. We are deciding to run it as a background job instead. *(Rationale beyond what you stated is not invented. Please confirm or add the reason, for example timeouts, latency or load.)* |
| alternatives | Keep the export synchronous (status quo). *(Add any other options you weighed. At least the status quo is listed.)* |
| consequences | The export no longer blocks the caller. Completion becomes asynchronous, so a way to learn the result is needed. *(Please confirm or edit.)* |
| decision-state | `proposed` |
| supersedes / superseded-by | none |
| related-artifact | none found yet (pending the read step) |
| source | user request |
| related-record | none |
| authority | `notion` |
| transition-id | assigned at write |
| owner | requesting user |
| date | 2026-10-13 |
| **repo** | **BLOCKED: `notion.repo` is `null`** |

Note: a Decision has no separate `status` field. `decision-state` is the only authoritative state.

Sensitive-content check: no credential, token or third-party personal data appears in this content.

Follow-up: moving this Decision from `proposed` to `accepted` is a separate gated write, and I would ask about it after the record exists.

## Summary

- Decision record drafted and previewed.
- Write halted because required `repo` cannot be resolved (`notion.repo = null`), and the host profile is `unconfigured`.
- No Notion or Linear tool was called.
- Next step is yours: configure `notion.repo` and the verified host profile, then re-run.
