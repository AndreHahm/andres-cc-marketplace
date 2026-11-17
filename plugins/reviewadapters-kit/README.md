# reviewadapters-kit

Run an optional reviewer model (Antigravity `agy`, Pi `pi` or Devin `devin`) on a diff, with the diff
inline and no tools, and get codex-kit's validated findings envelope back, so a review pipeline such as
`cross-model-review` can add a third or fourth vendor beside Claude and Codex. One dispatch contract for
callers and CI, plus a command that reviews the current diff with one vendor after an egress
confirmation. Every vendor is off until enabled in an untracked local allow-list.

Status: `1.0.0-alpha.1`. git-kit's `cross-model-review` does not call this plugin yet; that wiring is a
later change under issue #541.

## Installation

```bash
/plugin install reviewadapters-kit@andres-cc-marketplace
```

Requirements:

- **codex-kit**, declared in `plugin.json` as a dependency. The dispatcher imports its envelope validator
  and secret-filename check from the installed `codex-kit@andres-cc-marketplace`. Only when none is
  installed, and only with `"dev_sibling_codex_kit": true` in the local file (see below), does it use the
  codex-kit next to this plugin in a marketplace checkout.
- **Node.js** and `git` on `PATH`.
- The CLI of each vendor you enable (`agy`, `pi` or `devin`), already logged in. The flags were verified
  against agy 1.5.9, pi 1.5.0 and devin 3000.12.57. Another pi version still runs, with a note in the
  result's `inspection_limits`. Another agy or devin version is refused before anything is sent
  (`unsupported_cli_version`), unless the local file sets `allow_unprobed_version` for that vendor
  (see below).

## Enabling a vendor

Every vendor is off in the shipped `reviewadapters-kit.settings.json`. Enable one in
`.claude/reviewadapters-kit.local.json` at the top level of the repository you review:

```json
{ "vendors": { "pi": { "enabled": true, "model": "nvidia/nvidia/nemotron-3-ultra-550b-a55b" },
               "devin": { "enabled": true } } }
```

- **The file must stay untracked.** If git tracks it, the dispatcher refuses every vendor
  (`vendor_not_allowed`). A tracked file can be changed by anyone with write access, including by the
  change under review. The check ignores case, and any git error counts as tracked.
- **The file must stay private.** It and its `.claude` directory must be owned by you and not writable by
  others (group write is allowed only for a private group that only you belong to); otherwise every vendor is refused.
- The local file can also lower `timeout_ms` (shipped: 600000) and pin a `model` per vendor. A higher
  timeout is ignored. For pi, the model's first segment picks the provider that receives the diff, so
  pin `vendors.pi.model` locally if you do not want the provider to follow the shipped default.
- `vendors.pi.models` (local file only) lists extra pi models a caller may pick with `--model`. Any other
  `--model`, including another id under the same provider, is refused (`vendor_not_allowed`).
- `"allow_unprobed_version": true` under `agy` or `devin` (local file only) lets that vendor run when
  the installed CLI is not the verified version.
- `"dev_sibling_codex_kit": true` is read from the local file only, with the same tracked-copy refusal.

A CI job enables a vendor by writing this file at job time, never by committing it.

## Usage

Review the working tree's tracked changes (staged and unstaged, against `HEAD`) or a git range with one
vendor. Untracked files are not included.

```text
/reviewadapters-kit:rva-review-diff <agy|pi|devin> [git-range]
```

The command first does a dry run, then asks you to confirm the egress. It names the vendor's recipient,
the model, and the file count and size; it does not list the changed paths. If a changed file has a
secret-like name, a second question lists those files by name. Then it runs the review and reports the
findings.

## Components

| Name | Type | Purpose |
|---|---|---|
| `review-adapter-dispatch` | Skill (not model-invoked) | Runs one optional reviewer model on a reviewer instruction file and a diff, with the diff inline and no tools, and returns codex-kit's validated findings envelope or a typed failure. Invoked by other components and CI scripts; never asks anything itself. |
| `rva-review-diff` | Command | Review a diff with one optional model (agy, pi or devin), after an egress confirmation. |

Both run the shared entry point `scripts/rva-dispatch.mjs`; the command also runs `scripts/rva-prepare.mjs`
to write the diff and its inputs into a private temporary directory, and to clean it up. The skill's `SKILL.md` documents its flags,
gates and output; `references/typed-failures.md` lists every failure type.

## Data egress and isolation

- **The diff leaves the machine.** Each enabled vendor receives the reviewer instructions, the list of
  changed paths and the full diff text. Nothing else from the repository is sent.
- **No tools.** pi and devin run with their tools, extensions, skills and MCP servers turned off; agy
  runs in plan mode with its sandbox and relies on headless tool refusal. Every vendor runs in a private
  temporary directory with a reduced environment (`XDG_RUNTIME_DIR` is not passed, so a vendor that
  reads its login from a session keyring may fail to authenticate). The diff is wrapped as data, never
  as an instruction.
- **The diff is never a command-line argument.** Each vendor reads the prompt from a private `0600`
  file: pi and devin by file name, agy as standard input. Other users on the same machine therefore
  cannot read it from the process list.
- **Mechanical gates** before anything is sent: the allow-list, a check for secret-named paths (refused
  unless the caller confirmed them), a size cap and a timeout that kills the whole process group. The
  secret check looks at file names only; it does not scan the diff's content for secrets.
- The validated envelope uses the same schema as codex-kit's `codex-review-bridge`, so a caller handles
  every vendor the same way.

## Language

**JavaScript** (Node.js ES modules, `.mjs`, no npm dependencies). New scripts in this plugin stay in
JavaScript. Tests, from the repository root: `node --test plugins/reviewadapters-kit/tests/` (32 tests,
verified on Node 26).

When you change the shipped `reviewadapters-kit.settings.json` in this marketplace, copy it unchanged to
`.claude/reviewadapters-kit.settings.json` at the repository root as well. The mirrored scripts in
`.claude/scripts/` read that copy, and the mirror sync does not update it.

## Known limitations

- **POSIX only.** Process-group cleanup and the file ownership checks need Linux or macOS. Windows is not
  supported: the dispatcher refuses to run there (`unsupported_platform`) before anything is written or
  sent.
- Open minor findings, accepted for this release:
  - The secret-path check matches file names, not a secret-looking directory segment.
  - The diff is not checked against the `--cwd` repository's own `git diff`.
  - agy runs without a `--settings` override.
  - The codex-kit locator does not check the ancestor directories of the installed copy.
  - The local file is read more than once per run instead of once.
  - The tracked-file check reads the index only, so a file removed with `git rm --cached` counts as
    untracked.
  - The `--version` probe runs without the vendor's isolation flags.
  - Unrecognized diff lines outside a hunk are ignored rather than refused.
  - Vendor output over 16 MiB is truncated and reported as `invalid_json` or `missing_final_message`
    instead of a dedicated failure type.

## License

Apache-2.0. See [LICENSE](./LICENSE).
