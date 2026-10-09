# Walkthrough: two query submissions to plugin-integration-intake (simulated dry run)

Files read: SKILL.md, references/intake-payload-schema.md, references/wmgt-intake-batch-contract.md, references/wmgt-intake-query-update-contract.md. No scripts run, no Linear/Notion calls made, no files written except this one.

Both submissions are `operation: "query"`, so no `AskUserQuestion` approval is required (nothing is written). I would ask the person no questions in either flow. The optional classifier question applies only to ambiguous mappings, and neither mapping is ambiguous.

## Common step: Unknown-source check (runs for each submission, three steps in order)

1. Allowlist `^[a-z0-9][a-z0-9-]*$` on the raw values.
   - `workledger-kit` passes.
   - `syncing-open-items` passes.
2. Read only the `name` field of each manifest.
   - Tool: `Glob("plugins/*/.claude-plugin/plugin.json")`, then `Read` of each manifest, using only `name`.
   - Expected: exactly one manifest has `name == "workledger-kit"` (case-sensitive, whole-string), say in `plugins/workledger-kit/`. Zero or several matches would mean unknown source.
3. Resolve the skill against the matched directory.
   - Tool: `Glob("plugins/workledger-kit/skills/syncing-open-items/SKILL.md")`
   - Expected: exactly one hit, string-equal to that literal path. The installation facts confirm the skill exists.
   - This is an existence check only. `source_plugin` and `source_skill` stay caller-asserted claims.

Then the malformed-content check on the envelope:
- `operation: "query"` is valid.
- `target_system: "linear"` is valid.
- `keys` replaces `content`, with no `content` or `records` alongside it.
- `suggested_mapping.linear_target: "acme/widgets"` is an `owner/repo` slug, as required for a query.

## Submission 1: `keys: ["security"]`

Result: **malformed content, structured handoff. No Linear search, no slug resolution call, no scratch file.**

Reasoning: a query key must be a structured dedup key `<owner/repo>|<source-ref>|<fingerprint>`. `"security"` has no `|` parts and is a free-text phrase. The contract states "a free-text phrase, a short string or a wildcard can never be queried" and that such a key "makes the envelope malformed". The skill's order of checks puts malformed content before any lookup, so the key is rejected before any Linear call.

Structured handoff returned to the caller (illustrative shape):

```json
{
  "status": "rejected",
  "reason": "malformed_content",
  "operation": "query",
  "detail": "keys[0] \"security\" is not a structured dedup key. Required form: <owner/repo>|<source-ref>|<fingerprint>, first part equal to the resolved slug (acme/widgets), source-ref 1-100 chars with no | CR LF, fingerprint matching ^[A-Za-z0-9._-]{8,64}$.",
  "queried": false
}
```

I would not guess a key, wildcard it, run a fuzzy text search for "security", or browse the team's Issues. It is a whole-envelope rejection. The batch has one invalid key, and the contract says an unfit key makes the envelope malformed, so I would not partially process it.

## Submission 2: `keys: ["acme/widgets|pr#12|a1b2c3d4"]`

### Key validation
- First part `acme/widgets`, lowercased, equals the slug in `linear_target` (pending resolution below). OK.
- `<source-ref>` is `pr#12`: 5 characters, no `|`, CR or LF. OK.
- `<fingerprint>` is `a1b2c3d4`: 8 characters, matches `^[A-Za-z0-9._-]{8,64}$`. OK.
- Count is 1, within 1 to 50.

### Slug-to-team resolution
- Delegated to `linear-work-management`, which holds the Local Override trust check that intake cannot run itself:
  `Skill(linear-work-management)` with args roughly: "resolve repository slug `acme/widgets`, operation `linear.read`, test_run absent (false)".
- Expected return:
  - The slug normalizes to `acme/widgets` and matches `^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*$`.
  - It is an exact key of `linear.repositories`.
  - Environment is production, team `T-PROD`.
  - Local Override trust check passed.
  - `T-PROD` is in `linear.read` `team_ids` ([T-PROD]), so it is in scope.
  - `linear.read` is verified, with a non-null `verified_at`.
- Any rejection (unknown repo, out of scope, null team, unverified) would end the flow with a structured handoff.

### The lookup (through `linear-work-management`, query contract)
- `Skill(linear-work-management)` with args roughly: "search team T-PROD Issues with the full key string `acme/widgets|pr#12|a1b2c3d4` as the search term, small result limit (e.g. 10); return id, title, status, description."
- Expected underlying connector search, with the full key as the term and team T-PROD. Returns two hits:

| id | title | status | first line of description |
|---|---|---|---|
| ISS-41 | Follow up on flaky test | Backlog | `dedup_key: acme/widgets\|pr#12\|a1b2c3d4` |
| ISS-77 | Notes about acme/widgets\|pr#12\|a1b2c3d4 | (not shown) | something other than the tracking line |

### Exact-match filter (the model applies it; the search is fuzzy)
Keep a hit only if the first line of its description, after stripping trailing whitespace and `\r` and comparing the repository part case-insensitively, is exactly `dedup_key: <key>`.
- **ISS-41:** first line is `dedup_key: acme/widgets|pr#12|a1b2c3d4`, which equals `dedup_key: ` + key. **Match.**
- **ISS-77:** the key text appears only in the title, and the description's first line is something else. A key in a title, a comment or later in the description is not a match. **Dropped.**

### Result returned to the caller (IDs only)

```json
{ "results": [ { "key": "acme/widgets|pr#12|a1b2c3d4", "match_count": 1, "ids": ["ISS-41"] } ] }
```

- No title ("Follow up on flaky test"), no status ("Backlog"), no description, and no mention of ISS-77 is returned. The contract returns only `{key, match_count, ids}`, with at most 3 IDs.
- ISS-77 is not counted in `match_count`. The caller is not told that a fuzzy hit existed.
- A caller that needs the title or status must read the Issue through `linear-work-management` with the user present.

### Disclosure and residuals
- No approval was asked, because nothing was written. There is no hash and no scratch file for a query.
- Honest residual to state if asked: ISS-41's and ISS-77's titles and descriptions did enter the shared model context during the search. "IDs only" limits what is returned to the caller, not what the shared context saw.
- Exact-match behavior of Linear's text search is unverified against the live connector. The first-line check is what makes the match exact. If it could not be applied, I would report "no match" and say so.
- I would add the best-effort note that Linear was consulted for 1 key. It would go in a later approval preview, if a related submission arrives. Nothing links the two submissions.

## Summary

| Submission | Outcome |
|---|---|
| 1: `["security"]` | Rejected as malformed content (free-text, not a structured dedup key). Structured handoff, no Linear call. |
| 2: `["acme/widgets\|pr#12\|a1b2c3d4"]` | Valid. Resolved to production team T-PROD. Search returned 2 hits and the first-line filter kept only ISS-41. Returned `{key, match_count: 1, ids: ["ISS-41"]}`. ISS-77 is excluded as a title-only match. No approval needed. |
