# Dispatch Test Scenarios

Concrete scenarios behind the `review-adapter-dispatch` contract. The 45 tests in
`tests/rva-dispatch.test.mjs` cover these 36 scenarios against fake vendor binaries; no real vendor is
called.

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
   agy `--input-format stream-json --mode plan --sandbox -p=`), its environment lacks an unrelated caller variable and
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
    printing a non-JSON line or a `result` event whose `result` is `null` → `invalid_json`; agy events
    with no `result` event → `missing_final_message`.
14. agy's stream-json `result` with `SUCCESS`, an empty response and `denied_actions` → `tool_denied`;
    one with `structured_output` → a validated envelope; a non-`SUCCESS` result, even with
    `structured_output` → `missing_final_message`.
15. agy's prompt, with a diff over 130 000 bytes, reaches agy as one stream-json `user` line on stdin and
    never in its argv, and is not refused (it used to exceed the 120 000-byte argument cap). U+2028 and
    U+2029 in the diff are escaped, so they cannot end that line.
16. `--dry-run` → the fake vendor is never spawned (that every gate runs before the dry-run return is
    read from the code, not asserted).
17. codex-kit not installed, installed at a relative path, or writable by others →
    `codex_kit_unavailable`; the sibling codex-kit is used only with the local opt-in, and only when
    the plugin is a checkout's `plugins/reviewadapters-kit` (a copy elsewhere, or a `.claude/` mirror
    inside a checkout named `plugins`, finds no sibling).
18. The dispatcher run from a plugin path with a space and a non-ASCII character still prints JSON.
19. The `rva-review-diff` command's `rva-prepare.mjs` (tested here because it feeds this contract) lists
    a deleted secret-named file and both rename sides, refuses a changed file named outside the path
    charset, and refuses an empty diff.
20. A `models` list in the shipped settings does not let a caller's pi `--model` through →
    `vendor_not_allowed`; only the local file's `vendors.pi.models` can.
21. A `.claude` directory that is a symbolic link, or writable by others → `vendor_not_allowed`. A
    `.claude` directory swapped for another private one between the directory check and the file open:
    on Linux the file is still read from the checked directory; on the by-path fallback the swap is
    refused.
22. A vendor whose `--version` hangs, with `--timeout-ms` below the probe's own 15 s limit → `timeout`
    with "nothing was sent" within that budget, for pi, devin and agy alike (not
    `unsupported_cli_version`); the vendor never gets the diff.
23. The dispatcher on Windows (simulated by forcing `process.platform`), real run and dry run →
    `unsupported_platform`; no vendor is spawned.
24. A file named `git` in the reviewed checkout, reachable through a relative `PATH` entry (`.`) or an
    absolute `PATH` entry inside the checkout, is never run by the dispatcher or `rva-prepare.mjs`,
    including with `--cwd` a subdirectory (the dispatcher refuses it with `usage` before running git).
25. A vendor's `PATH` holds no entry inside the reviewed checkout.
26. A vendor CLI installed as a link to a shim that picks the tool by the name it was called as (Volta
    style) is run under its own name and returns an envelope.
27. A finding whose text quotes the marker words still parses: only a line that is exactly a marker
    counts, and marker text inside a longer line is not a marker.
28. A vendor that writes more than the 16 MiB stdout capture limit after a marked block →
    `missing_final_message` ("more than 16 MiB"), never that earlier block.
29. A caller environment with `GIT_DIR` or `GIT_INDEX_FILE` pointing elsewhere cannot make a git-tracked
    local file look untracked → `vendor_not_allowed`.
30. `rva-prepare.mjs` run from a plugin inside the repository under review refuses, since the diff could
    have changed the reviewer instructions; the effective timeout (agy's `--print-timeout`) is the shipped
    limit for a larger request, a smaller local `timeout_ms` takes effect, and a larger one does not raise it.
31. Path containment holds for a repository at the filesystem root (`/`), where a prefix test would
    contain nothing, and a git variable in another letter case (`Git_Dir`) is dropped from git's
    environment too.
32. `rva-prepare.mjs` runs no `core.fsmonitor` hook from the reviewed repository's own config while git
    builds the diff.
33. `rva-prepare.mjs` on Windows (simulated by forcing `process.platform`) refuses before creating a
    temp directory, for a prepare run and a cleanup run alike.
34. `--cleanup` removes a prepared directory only with the token its own prepare run printed: another
    run's token, a malformed token or no token is refused and the directory is kept.
35. An input file (instructions, diff or target paths) named like a key or a credentials file
    (`id_rsa`, `credentials.json`, an uppercase `ID_ED25519_SK`, `id_rsa_work`, `.ppk`, `auth.json`,
    `hosts.yml`, `.envrc`), or a link with an ordinary name to such a file, is refused as `usage` before
    it is read, even with `--secret-paths-confirmed`; no vendor is spawned. A `.pub` key is not refused.
36. An input file inside `~/.ssh` (or another listed key or credentials directory under the home
    directory) is refused as `usage`, whatever its name.
