# Dispatch Test Scenarios

Concrete scenarios behind the `review-adapter-dispatch` contract. `tests/rva-dispatch.test.mjs` runs
them against fake vendor binaries; no real vendor is called.

1. Vendor not in the local allow-list, or a pi `--model` that is neither the configured model nor listed
   in `vendors.pi.models` (another provider, a bare id, another id on the same prefix) →
   `vendor_not_allowed`; a listed model passes.
2. The local file is tracked by git, also under another letter case, or is writable by others →
   `vendor_not_allowed`; a tracked copy setting `dev_sibling_codex_kit` does not enable the sibling
   codex-kit.
3. A secret-named target path without `--secret-paths-confirmed` → `secret_paths_unconfirmed`.
4. A diff header naming a path missing from the target list → usage error; a removed line shaped like a
   header is not taken for one. `diffHeaderPaths` unit cases: deletion with `\ No newline`, rename,
   blank context line, quoted path, truncated hunk, header lines hidden in an over-full hunk, no header,
   unprefixed `---`/`+++`.
5. Instruction file inside a target path → usage error naming that check.
6. An input file writable by others, or `--cwd` below the top level → usage error.
7. Repeated, `=`-form, unknown or value-less flags, a model starting with `-`, a vendor named
   `__proto__`, a timeout not in plain digits → usage errors; a timeout above the limit is clamped.
8. Vendor binary not on PATH (a PATH holding only git), or only inside the reviewed repository →
   `cli_unavailable`.
9. Each vendor's recorded argv carries its isolation flags (pi `--no-tools`, devin `--prompt-file`,
   agy `--mode plan --sandbox`), its environment lacks an unrelated caller variable and
   `XDG_RUNTIME_DIR`, and an unprobed version (`fake 1.0`) is noted in `inspection_limits` when the
   local file allows it. Without that opt-in, an unprobed pi is still only noted, while devin and agy
   are refused with `unsupported_cli_version` and never spawned with the diff.
10. The shipped Devin config denies read, grep, glob and find; Devin's argv never carries the diff.
11. A fake vendor that sleeps past the timeout → `timeout`, and its child process is gone afterwards.
12. A vendor that exits while a helper holds stdout → still a finished run, not a timeout.
13. Marked pi/devin output → validated envelope; no markers, malformed JSON, wrong keys, or a sole
    finding citing an out-of-scope file → `missing_final_message`, `invalid_json`,
    `schema_validation_failure`, `semantic_validation_failure` (when only some findings are out of scope,
    codex-kit drops those and notes it in `inspection_limits`); non-zero exit → `non_zero_exit`; agy
    printing `null` → `invalid_json`.
14. agy `SUCCESS` with an empty response and `denied_actions` → `tool_denied`.
15. An agy prompt over 120 000 bytes → `input_too_large`.
16. `--dry-run` → the fake vendor is never spawned (that every gate runs before the dry-run return is
    read from the code, not asserted).
17. codex-kit not installed, installed at a relative path, or writable by others →
    `codex_kit_unavailable`; the sibling codex-kit is used only with the local opt-in, and only when
    the plugin sits in a `plugins/` directory (a copy elsewhere finds no sibling).
18. The dispatcher run from a plugin path with a space and a non-ASCII character still prints JSON.
19. The `rva-review-diff` command's `rva-prepare.mjs` (tested here because it feeds this contract) lists
    a deleted secret-named file and both rename sides, refuses a changed file named outside the path
    charset, and refuses an empty diff.
