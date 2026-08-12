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

**Not a failure category:** an earlier draft of this taxonomy also included `incomplete_inspection` for "Codex disclosed it couldn't inspect part of the requested scope." Removed from both this table and `scripts/lib/codex-exec.mjs`'s `FAILURE_CATEGORIES` — the envelope schema already carries `inspection_limits` (a required array field) as informational metadata on a normal `ok: true` response, so a partial-inspection disclosure is not itself a failure condition. Callers read `inspection_limits` from a successful envelope rather than branching on a failure category for it.

**Rule every component follows:** never convert a failure into an empty findings list or a silently "clean" result. Every failure is one of the categories above, with a `detail` string carrying concrete evidence (truncated stderr, the specific check that failed) — never just the bare category name.

**Interactive vs. programmatic consumers:** components with a human in the loop (`codex-rescue`, `codex-verify`, `codex-research`, the review commands) surface these as prose error messages with next-step suggestions. `codex-review-bridge` and anything built on it return the category as a structured `{ok: false, category, detail}` object instead — same taxonomy, different presentation layer.
