# Typed failures

Shape: `{ "ok": false, "category": "<name>", "detail": "<evidence>" }` on stdout, exit 2. A caller error
uses the same shape with category `usage` and exit 1, and nothing has been sent. SIGINT, SIGTERM or
SIGHUP during a run prints `dispatcher_error` and exits 130, 143 or 129.

`detail` is written by the dispatcher, with one exception: for `non_zero_exit` it ends with the last 500
characters of the vendor's stderr, redacted with codex-kit's `redactSecrets` before it is shortened (a
vendor killed by a signal reads "was killed by SIGKILL" rather than an exit code).
That text comes from the vendor, may echo the model, and is untrusted like every envelope field.

## Reused from codex-kit's `FAILURE_CATEGORIES`

`cli_unavailable`, `unsupported_cli_version`, `timeout`, `non_zero_exit`, `missing_final_message`,
`invalid_json`, `schema_validation_failure`, `semantic_validation_failure`. codex-kit's own error
taxonomy is canonical for their meaning; this plugin uses them for the same conditions.
`unsupported_cli_version` is raised before sending when the installed devin or agy is not the probed
version and the local file does not set `allow_unprobed_version` for it; an unprobed pi only gets an
`inspection_limits` note. It does not emit codex-kit's `auth_unavailable` or
`isolation_profile_unavailable`: a vendor's auth error surfaces as `non_zero_exit`.

## Added by this plugin

| Category | When | Sent to the vendor? |
|---|---|---|
| `unsupported_platform` | The dispatcher runs on Windows, where its timeout cannot kill the vendor's process group; checked before the run directory is created | No |
| `codex_kit_unavailable` | codex-kit is not installed (or opted in as a sibling), or fails the ownership checks | No |
| `vendor_not_allowed` | Vendor not enabled in the untracked local file; the local file is tracked, or not owned by the user, or writable by others; or a pi `--model` that is neither the configured model nor listed in the local file's `vendors.pi.models` | No |
| `secret_paths_unconfirmed` | A secret-named target or diff-header path without `--secret-paths-confirmed` | No |
| `input_too_large` | One argument exceeds 120 000 bytes (a backstop: no adapter puts the review content on the command line) | No |
| `tool_denied` | agy output has no usable `structured_output` and a non-empty `denied_actions` | Yes |
| `dispatcher_error` | An internal error, an invalid shipped settings file, or SIGINT/SIGTERM/SIGHUP during the run | Interrupted: maybe; otherwise no |

For the reused categories, `cli_unavailable` and `unsupported_cli_version` mean nothing was sent;
`non_zero_exit`, `missing_final_message`, `invalid_json`,
`schema_validation_failure` and `semantic_validation_failure` mean the diff was sent. `timeout` means it
was sent, except when its detail says "nothing was sent" (the `--version` probe used the whole budget):
a caller reads `detail`, not only the category.

## Reporting

A caller reports the vendor and the category, keeps every other reviewer's finished envelope, and
continues. A typed failure is never counted as a clean review. When data has already left the machine,
a report must not say the vendor saw nothing.
