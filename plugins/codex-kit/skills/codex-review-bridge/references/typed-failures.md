# Typed failures

The bridge never returns an empty findings list to signal failure — every failure is one of the categories below, defined in `scripts/lib/codex-exec.mjs`'s `FAILURE_CATEGORIES` (shared with `codex-prompt-protocol/references/error-taxonomy.md`):

| Category | Meaning |
|---|---|
| `cli_unavailable` | Codex binary not found on PATH |
| `auth_unavailable` | Codex CLI not authenticated |
| `unsupported_cli_version` | Codex CLI rejected a flag this bridge sent — version mismatch |
| `isolation_profile_unavailable` | The requested execution profile (read-only sandbox, container, etc.) failed — **never silently substituted with `danger-full-access`** |
| `timeout` | Exceeded the caller-supplied timeout |
| `non_zero_exit` | Codex exited non-zero for an unclassified reason |
| `missing_final_message` | Codex exited 0 but wrote no `--output-last-message` file |
| `invalid_json` | The final-message file wasn't valid JSON |
| `schema_validation_failure` | Valid JSON, but doesn't match the canonical envelope schema — checked locally in `codex-exec.mjs`'s `findSchemaViolation` after parsing, not just trusted from Codex's own `--output-schema` enforcement |
| `semantic_validation_failure` | Schema-valid, but failed a `semantic-validation.md` check (bad citation, wrong verdict, etc.) |

**Not a failure category:** an earlier draft of this list also included `incomplete_inspection` for "Codex disclosed it couldn't inspect part of the requested scope" — removed, since the envelope schema already carries `inspection_limits` (a required array field) as informational metadata on a normal `ok: true` response. Codex disclosing a partial-inspection limit is not itself a failure condition; the caller reads `inspection_limits` from a successful envelope rather than branching on a failure category for it.

Every typed failure includes a `detail` string with the concrete evidence (truncated stderr, the specific semantic check that failed, etc.) — never just the category name alone.
