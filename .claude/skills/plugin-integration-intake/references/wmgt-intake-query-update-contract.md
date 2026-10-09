# Intake Query and Update Contract

The `query` and `update` values of the envelope's `operation` field. Both are Linear only. They share the target
resolution, scratch files and hash binding described in `wmgt-intake-batch-contract.md` (a see-also: this file states
every rule it depends on below, in a line or two each). Like the batch
path, this is prose-enforced: the limits below narrow what a calling plugin can do, they do not authenticate it.

## Query (read-only, structured dedup key, IDs only)

A caller asks whether Linear already holds a record, for deduplication. It is the only read a calling plugin can
cause without a live approval, so it is deliberately narrow: it can confirm that a key it already knows exists, and
it cannot browse.

- Envelope: `operation: "query"`, `keys` (array of 1 to 50 strings) in place of `content`/`records`, and `suggested_mapping.linear_target` as an `owner/repo` slug (plus optional `test_run`).
- **Each key must be a structured dedup key** of the form `<owner/repo>|<source-ref>|<fingerprint>`, where the first part equals the **resolved** slug (both lowercased before comparing, since workledger-kit stores the repository as given), `<source-ref>` is 1 to 100 characters with no `|`, CR or LF (workledger-kit allows any other character there, including spaces and non-ASCII paths), and `<fingerprint>` matches `^[A-Za-z0-9._-]{8,64}$` (workledger-kit's own fingerprint is 8 hex characters). A key that does not fit, or whose first part is a different repository, makes the envelope malformed. A free-text phrase, a short string or a wildcard can never be queried.
- Resolve the slug through `linear-work-management` (it runs the Local Override trust check): lowercase it and drop one trailing `.git`, require an exact `linear.repositories` key (an unknown slug is rejected, never guessed or defaulted), pick the mapped production team (the test team only when the caller set `test_run`), and require that team to be in `linear.read`'s `team_ids`. Query needs `linear.read` `verified` with a non-null `verified_at`.
- **No live approval**, because nothing is written.
- Run the lookup through `linear-work-management`: search the resolved team using the **full key string as the search term** with a small result limit, then keep a result **only if the first line of its description is `dedup_key: <key>`** (compared after stripping trailing whitespace and `\r`, as workledger-kit's own reader does, and case-insensitively on the repository part; the tracking-line shape is in its `wlgr-open-item-format.md`). A key in a title, a comment or later in the description is not a match, and a fuzzy search hit that fails this check is "no match".
- Return, per key: `{key, match_count, ids}`. `ids` holds at most 3 stable Issue IDs. **No titles, descriptions, statuses or any other field are returned**; a caller that needs more reads the Issue through `linear-work-management` with the user present.
- State in a later approval preview, on a best-effort basis, that Linear was consulted and for how many keys. Intake keeps no link between a query and a later separate submission, so this is not enforced.

**What this does not guarantee.** The filter runs in the model, so every search hit's title and description enters
the conversation context the calling plugin shares; "IDs only" limits what is returned to the caller, not what the
shared context saw. A caller picks its own `linear_target`, so it can query any repository mapped in
`linear.repositories` whose team is in `linear.read`'s `team_ids`; `source_plugin` is unauthenticated and does not
limit this. `match_count` reveals only how many exact-key duplicates exist.

Exact-match behavior of Linear's text search has not been verified against the live connector. The first-line check
is what makes the match exact; if it cannot be applied, treat the result as "no match" and say so.

## Update (hash-bound, same gate as a write)

A caller asks to change existing Issues. It is a write, so it takes the full approval and the hash binding.

- Envelope: `operation: "update"`, `records` array of 1 to 1000, each exactly `{id, set}` where `id` is a stable Linear Issue ID and `set` holds only these fields from the Issue table in `linear-work-management/references/linear-entity-fields.md`: `title`, `status`, `labels`, `priority`, `owner`. Any other key in a record or in `set` makes the envelope malformed, including a caller-supplied `before` (the snapshot always comes from intake's own read), `team`, `dependencies`, `cycle`, the accumulating arrays `disposition-history`, `open-item-source` and `git-github-evidence`, and **`description`**.
- `description` is not updatable here, because an Issue's description holds its tracking line and evidence block. Description edits stay a direct request to `linear-work-management` with the user present.
- Resolve the slug through `linear-work-management` (it runs the Local Override trust check): lowercase it and drop one trailing `.git`, require an exact `linear.repositories` key (an unknown slug is rejected, never guessed or defaulted), pick the mapped production team (the test team only when the caller set `test_run`), and require that team to be in `linear.write`'s `team_ids`.
- **Scope check per record:** read each Issue through `linear-work-management` and confirm it belongs to the resolved team. An Issue in any other team is rejected as out of scope; an update never moves an Issue between teams.
- **Snapshot:** put each record's current `title` (as read by intake, never caller-supplied) and its current values for the fields in `set` into the submission file as `before`, so the hash binds what the person saw. The preview shows, for every record, the Issue's title, its ID and a before/after of the changed fields.
- **Closed states are refused.** An update whose `set.status` resolves to a completed or canceled workflow state (as the team's own workflow marks it, read through `linear-work-management`) makes the envelope malformed: closure semantics belong to `merge-to-completion`, and a single approve-all question cannot confirm a closure separately.
- Approval is one `AskUserQuestion` for the whole set, bound to the hash of a submission file kept in the session scratchpad (with a fresh `batch_id` inside it). Every chunk of at most 25 records is built only from `wmgt_batch_hash.py chunk` output. A resume is a new submission with a new `batch_id` and a fresh approval. Both scratch files are removed with `purge` at the end. The batch contract holds the full procedure.
- **Re-check before each write:** re-read the Issue immediately before writing it and confirm it still belongs to the resolved team. If it does not, or any field in `set` no longer equals its `before` value, do not write that record; report it as a conflict and carry on with the others. Linear has no conditional write, so a change landing between the re-read and the write is an accepted residual race.
- Read back each written Issue and report the result per record.

## Not in this contract

Native PR links, due dates, description edits, Report page-content blocks, classification requests and Notion
batches. Callers needing them keep their plan-mode fallback (see workledger-kit's `wlgr-kit-dependencies.md`).
