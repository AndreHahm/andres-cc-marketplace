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
  others (group write is allowed only for a private group that only you belong to, on Linux, when GNU coreutils
  `ls` shows no extended ACL); otherwise every vendor is refused.
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
| `review-adapter-dispatch` | Skill (not model-invoked) | Runs one optional reviewer model on a reviewer instruction file and a diff, with the diff inline and no tools, and returns codex-kit's validated findings envelope or a typed failure. Other components and CI scripts run its dispatcher script directly; never asks anything itself. |
| `rva-review-diff` | Command | Review a diff with one optional model (agy, pi or devin), after an egress confirmation. |
| `rva-guard-checkout-scripts` | Hook (`PreToolUse`, Bash and PowerShell) | Denies a Bash or PowerShell command that names one of this plugin's scripts anywhere but the installed copy's `scripts/` directory. See "Running from a checkout". |

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
- **The egress confirmation is model-enforced.** The command and the skill pre-approve the dispatcher
  with any arguments, so no permission prompt stands between Claude and a dispatch. The command's
  "Send this diff?" question is a step Claude follows, not a permission check, and a vendor's output or
  a diff that steers Claude could in principle skip it. Enable only vendors you accept receiving a diff.
- The validated envelope uses the same schema as codex-kit's `codex-review-bridge`, so a caller handles
  every vendor the same way.

## Running from a checkout

The plugin runs only from an installed copy. A copy inside the repository you review (a `.claude/`
mirror, or `plugins/` in this marketplace's own checkout) could be the reviewed change's own code, and it
would run with your vendor login. This marketplace no longer mirrors the plugin into `.claude/`
(issue #762). Three checks enforce it:

- **The hook** (`hooks/hooks.json`) loads from the installed copy in the plugin cache, outside any
  checkout, and denies a Bash or PowerShell command naming `rva-prepare.mjs`, `rva-dispatch.mjs` or the
  other scripts (in any letter case) unless every such word is a literal absolute path into the installed
  copy's `scripts/`. It takes that copy from its own location, never from an environment variable, and
  also denies when the copy itself lies inside the repository the session has open (as with
  `--plugin-dir` pointed at a checkout). Use Read or Grep, not Bash, to look at a copy. When you work on
  this plugin with it installed, the hook also denies `git add` or `git diff` on a script by file name:
  name the directory instead (`git add plugins/reviewadapters-kit/scripts/`), or disable the plugin.
- **`rva-prepare.mjs` and `rva-dispatch.mjs`** refuse when their own plugin root lies inside the
  repository under review.
- **The command's step 1 and the skill** stop on an empty plugin root or one inside the checkout.

Only the hook sits outside the checkout. Its limits:

- **The installed copy is only as trusted as its source at install or update time.** If you added this
  marketplace from a local directory, installing or updating while an unreviewed branch is checked out
  there copies that branch's scripts, the hook included, into the cache. Install from a clean clone or a
  pinned ref.
- It reads the command text with POSIX-shell quoting, so a command that builds a script name at run time
  is not seen, and only the Bash and PowerShell tools are covered. That includes every form the shell
  expands before the program starts: a glob or brace pattern (`node .claude/scripts/rva-dis*.mjs`,
  `rva-{dispatch,x}.mjs`), a `cd` then `node *`, such a pattern inside a `bash -c` or `eval` string, and
  `$'...'` escape sequences that spell a letter as a code point. The guard catches an accidental run
  from a checkout, not a command written to evade it; a text check cannot model shell expansion reliably.
- It checks the script's path, not the rest of the command line: `node --import <file>`, `NODE_OPTIONS`
  or a project `settings.json` `env` block can still load other code into the installed script.
- A plugin copy in another worktree of the same repository (for example the main checkout, seen from a
  worktree inside it) is not recognized as part of the open repository.
- It is registered with `onError: "warn"`, so a hook that fails to start (no `node`, a timeout) lets the
  command through with a warning.
- A checkout you open already controls its own `CLAUDE.md`, rules, project hooks and `settings.json`,
  which no plugin can override.

**Without installing the plugin**, add the same hook at user level, outside every checkout, in
`~/.claude/settings.json`, pointing at a copy you trust (not one inside a repository you review; quote
the path if it contains a space). The guard then allows only that copy's scripts:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          {
            "type": "command",
            "command": "node /path/to/trusted/reviewadapters-kit/scripts/rva-guard-checkout-scripts.mjs",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

## Language

**JavaScript** (Node.js ES modules, `.mjs`, no npm dependencies). New scripts in this plugin stay in
JavaScript. Tests, from the repository root: `node --test "plugins/reviewadapters-kit/tests/*.test.mjs"`
(75 tests: 67 pass and 8 skip on Linux with Node 24; on Windows, Node 22, 17 pass and 58 skip, since the
POSIX fixtures skip there and `tests/rva-windows.test.mjs` covers Windows). Name the files: on Node 22 and
24, `node --test` on the directory path fails. The `Plugin Node tests` CI job runs them on every pull
request.

## Windows

Supported since issue #770, with the same rules read from Windows' own mechanisms:

- **Privacy checks read owners and DACLs** through Windows PowerShell from `%SystemRoot%\System32` (never
  from `PATH`), run from `%SystemRoot%` with only `SystemRoot`, `windir` and the system module path in its
  environment, and with plain .NET calls on the raw security descriptor. A path passes when you own it and
  no allow entry gives any account but you, SYSTEM, Administrators or TrustedInstaller (or CREATOR OWNER
  and OWNER RIGHTS, which stand for the owner) the right to write, delete or change its permissions.
  AppContainer capability SIDs count as other accounts, deny entries are not subtracted, and an ACL that
  cannot be read, a missing DACL or a conditional entry fails closed.
- **Every directory above a checked file** must be owned by you, SYSTEM, Administrators or
  TrustedInstaller and let no other account delete, rename or re-permission an entry. The DACL is read by
  path, not from the open handle, and this is what keeps another account from swapping the path between
  the check and the read.
- **The temp directory must be private**, inheritable entries included, since Windows has no sticky bit;
  it and the directories above it may belong to you, SYSTEM, Administrators or TrustedInstaller, and the
  directories above it may let others add entries, not delete, rename or re-permission them. Each run
  directory then gets a protected DACL (you, SYSTEM and Administrators, nothing inherited) before anything
  is written into it, since `chmod` does not change who can read a file on Windows. A default
  `%TEMP%` often grants other accounts access (sandbox users, AppContainer capabilities), and then every
  run stops with `unsafe_temp_dir`. Create a private directory directly under your profile and point
  `TMP` and `TEMP` at it for Claude Code (a directory under `%LOCALAPPDATA%` fails as well when an
  AppContainer has full control of `%LOCALAPPDATA%`):

  ```bat
  mkdir "%USERPROFILE%\rva-tmp"
  icacls "%USERPROFILE%\rva-tmp" /inheritance:r /grant:r "%USERNAME%:(OI)(CI)F" "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F"
  ```

- **The local allow-list and its `.claude` directory** follow the same rule. A repository outside your
  profile (under `C:\Dev`, say) usually inherits Modify for Authenticated Users, so the file enables
  nothing until its directory is made private the same way (`icacls "<repo>\.claude" /inheritance:r
  /grant:r ...`, as above).
- **Vendors run only from an `.exe` or `.com`.** npm installs a CLI as a `.cmd` shim, which only runs
  through `cmd.exe`, whose quoting and `%VAR%` expansion this plugin does not trust with an argument
  list: such a vendor fails with `cli_unavailable` naming the shim. agy and devin ship as `.exe`.
- **The timeout kills the vendor's process tree** with `taskkill /T /F`. After a normal exit, the processes
  the vendor started and left running are ended too, found by their parent's process id and a start
  time between the vendor's start and exit; one that re-parented itself is not found, and a process that
  reuses a helper's id between the query and the kill would be killed in its place.
- **No `O_NOFOLLOW`:** after a file is opened, its path must not be a link and must name the same file
  (volume and file id) as the handle, so a link swapped in and back is caught. A junction in a directory
  above is not, as on POSIX. A filesystem that reports no file id (0) is refused; on ReFS, whose file ids
  are 128-bit, uniqueness of the 64-bit id Node reads is not verified.
- **The environment is trusted** as on POSIX: `SystemRoot` (which must be a drive path equal to `windir`),
  `USERPROFILE` (where codex-kit's plugin registry is read, the role `HOME` plays on POSIX) and `TMP`/`TEMP`
  (checked as above) come from whatever started Claude Code.
- **Step 1 of the command** runs in Git Bash, the Bash tool on Windows, and compares a `C:\...` plugin root
  in the `/c/...` form `pwd` prints. Prepare prints paths with forward slashes.

## Known limitations

- **Windows** is supported with the limits in "Windows" above.
- **PATH inside the reviewed checkout.** `git` and the vendor CLIs are never taken from a relative `PATH`
  entry or from inside the checkout, and vendors get only the other entries. The `node` that runs the
  scripts is found by your shell before any check runs, so keep `PATH` free of entries inside a
  checkout you review (direnv's `PATH_add`, `node_modules/.bin`).
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
