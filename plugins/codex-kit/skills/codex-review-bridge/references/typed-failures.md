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
| `schema_validation_failure` | Valid JSON, but doesn't match the canonical envelope schema |
| `semantic_validation_failure` | Schema-valid, but failed a `semantic-validation.md` check (bad citation, wrong verdict, etc.) |
| `incomplete_inspection` | Codex disclosed it couldn't inspect part of the requested scope |

Every typed failure includes a `detail` string with the concrete evidence (truncated stderr, the specific semantic check that failed, etc.) — never just the category name alone.
