# Finding codex-kit's validator

The dispatcher imports `ENVELOPE_SCHEMA`, `semanticallyValidate`, `isValidToken`, `isValidPathToken`
and `isWithin` from codex-kit's `skills/codex-review-bridge/scripts/bridge-invoke.mjs`, plus
`findSchemaViolation`, `redactSecrets`, `FAILURE_CATEGORIES` and `matchesSecretFilename` from
codex-kit's `scripts/lib/`. Importing a module runs its code, so where it comes from is a trust decision.

## Search order (first match wins)

1. **Installed plugin:** the `installPath` recorded under the exact key
   `codex-kit@andres-cc-marketplace` in `~/.claude/plugins/installed_plugins.json`, used only when it is
   an absolute path. A codex-kit installed from another marketplace is not used.
2. **Sibling in a marketplace checkout, opt-in only:** `<plugin-root>/../codex-kit`, used only when the
   untracked local file sets `"dev_sibling_codex_kit": true` and this plugin's own directory really is
   `plugins/reviewadapters-kit`. From a copy elsewhere (this repository's `.claude/` mirror, even inside a
   checkout whose directory is named `plugins`), the sibling path is one no plugin occupies. In a checkout under review the sibling is
   the reviewed branch's own code, so a change could rewrite the validator that judges it; the opt-in is
   for developing this marketplace itself, on a branch the developer trusts. The same tracked-copy
   refusal as for vendors applies (`references/trust-and-config.md`).

No variable of this plugin's own can point the import elsewhere: a variable is easier to set by accident,
or by another tool, than a file in one of these places. `~` is `os.homedir()`, which follows `$HOME` on
POSIX, so whoever sets `HOME` picks which `installed_plugins.json` is read; the ownership checks below
still limit what can be imported.

## Checks before import

On the resolved real path (symlinks resolved), every directory from codex-kit's root down to each
imported file, and every file in each imported file's directory (the imported modules load siblings
such as `cdx-process.mjs` and `cdx-token-shapes.json`):

- is owned by the current user;
- is not writable by others;
- is not writable by a group, unless that group is the user's own private group: the user's primary
  gid, named like the user, listed on exactly one `/etc/group` line with no members, and no other account
  in `/etc/passwd` using it as its primary gid. On a umask-002 system every checkout is group-writable this
  way, and refusing it would make the plugin unusable there. A group that `/etc/group` does not list (for
  example from LDAP) gets no exception; members another NSS source adds to a listed gid are not seen. The exception applies on Linux only, and only when GNU coreutils `ls`
  shows no extended ACL on the path (an ACL can grant write through the group bits). Elsewhere, on a host
  without GNU coreutils `ls`, or with an ACL, group write is refused. A macOS ACL on a path without group
  write is not checked.

Directories above codex-kit's root are not checked. A candidate whose files are missing is skipped;
a candidate that fails a check stops the search (it does not fall through to the next one). Any failure
→ `codex_kit_unavailable`, with the failing check named and the path omitted. On Windows, where these
POSIX bits do not apply, the check is skipped; the dispatcher itself refuses to run there
(`unsupported_platform`), so no envelope is ever produced on Windows.

## Version

`provenance.cli_version` holds the vendor CLI's version, not codex-kit's. The dispatcher does not pin a
codex-kit version; instead, a missing named export (codex-kit renamed or removed it) is
`codex_kit_unavailable`, never a partial run with a stand-in validator.
