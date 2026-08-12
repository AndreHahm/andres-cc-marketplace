# Error / failure taxonomy

Shared by every codex-kit component's error handling. This is the same category set `scripts/lib/codex-exec.mjs`'s `FAILURE_CATEGORIES` uses in code — this file is the human-readable reference for it.

| Category | Meaning | Typical trigger |
|---|---|---|
| `cli_unavailable` | Codex binary not found on PATH | `ENOENT` spawning `codex` |
| `auth_unavailable` | Codex CLI not authenticated | stderr matches "not authenticated" / "OPENAI_API_KEY" |
| `unsupported_cli_version` | Codex CLI rejected a flag this call sent | stderr matches "unknown option" / "unrecognized" |
| `isolation_profile_unavailable` | Requested sandbox/execution profile failed | stderr matches `CreateProcessAsUserW` / "sandbox" / "permission denied" / "access is denied" |
| `timeout` | Exceeded the caller-supplied timeout | process killed after `timeoutMs` |
| `non_zero_exit` | Non-zero exit for an unclassified reason | none of the above patterns matched |
| `missing_final_message` | Exited 0 but no `--output-last-message` file was written | file missing after exit |
| `invalid_json` | The final-message file wasn't valid JSON | `JSON.parse` failure |
| `schema_validation_failure` | Valid JSON, doesn't match the expected schema | schema check failure |
| `semantic_validation_failure` | Schema-valid but fails a semantic check | `dispatch.id`/`reviewer` mismatch, a cited path outside the allowed target scope or missing on disk, or a duplicate finding ID (the currently-implemented checks — see `codex-review-bridge/references/semantic-validation.md` for the full list and what's tracked as follow-up but not yet enforced) |

**Reference-chain exception (recorded):** the pointer above to `codex-review-bridge/references/semantic-validation.md` is a deliberate single-source-of-truth choice, not an incomplete inline copy — the implemented/not-yet-implemented split changes independently of this table and duplicating it here would recreate exactly the kind of drift R20 exists to catch (see this file's own history: `typed-failures.md` once carried a stale copy of a related example for this same reason). The row above already states the current implemented-check list inline; only the "what's tracked as follow-up" detail lives at the far end of the pointer.

**Not a failure category:** an earlier draft of this taxonomy also included `incomplete_inspection` for "Codex disclosed it couldn't inspect part of the requested scope." Removed from both this table and `scripts/lib/codex-exec.mjs`'s `FAILURE_CATEGORIES` — the envelope schema already carries `inspection_limits` (a required array field) as informational metadata on a normal `ok: true` response, so a partial-inspection disclosure is not itself a failure condition. Callers read `inspection_limits` from a successful envelope rather than branching on a failure category for it.

**Rule every component follows:** never convert a failure into an empty findings list or a silently "clean" result. Every failure is one of the categories above, with a `detail` string carrying concrete evidence (truncated stderr, the specific check that failed) — never just the bare category name.

**Scope — this table applies to `runCodexExec` callers, not `codex-companion.mjs` callers.** This is `scripts/lib/codex-exec.mjs`'s `FAILURE_CATEGORIES`, used by `codex-review-bridge` and anything else built on `runCodexExec` directly, returned as a structured `{ok: false, category, detail}` object. `codex-companion.mjs` — the script `codex-rescue`/`codex-verify`/`codex-research`/the review commands all invoke — never calls `runCodexExec` and has its own, separate error surface (`setup`/`auth`/`environment`/`bad-input`/`wrong-skill`/`prompt-empty`/`concurrency-conflict`/`recovery-impossible`/`unexpected-format`/`wait-timeout`/`silent-flag-corruption`/`transcript-missing`/`unknown`), documented in `invocation-protocol.md` §6 and surfaced as prose with next-step suggestions — a different category set, not a presentation-only variant of this one.
