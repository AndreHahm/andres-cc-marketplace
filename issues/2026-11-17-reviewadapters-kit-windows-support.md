# reviewadapters-kit: support Windows (timeout kill and DACL-based privacy checks)

## Summary
reviewadapters-kit refuses to run on Windows. Supporting it needs a process-tree kill for the vendor
timeout and owner/write checks based on Windows DACLs instead of POSIX mode bits.

## Environment
- **Product/Service**: reviewadapters-kit (`/rva-review-diff`, `review-adapter-dispatch`)
- **Region/Version**: current `main` plus the issue #765 hardening
- **Browser/OS**: Windows (win32)

## Reproduction Steps
1. On Windows, run `/rva-review-diff`, or `node scripts/rva-prepare.mjs --cwd <repo>`.
2. Or run `node scripts/rva-dispatch.mjs ... --dry-run`.

## Expected Behavior
Prepare, dispatch and cleanup run end to end on Windows. A vendor that hangs is killed together with
its child processes when the timeout expires. The privacy checks refuse a file or directory that
another user can write to.

## Actual Behavior
- `rva-prepare.mjs` refuses win32 ("rva-review-diff runs on Linux and macOS only; nothing was
  prepared").
- `rva-dispatch.mjs` refuses win32 with the typed failure `unsupported_platform`: its timeout kills the
  vendor's POSIX process group (`scripts/rva-run.mjs`), and Windows has no process groups.
- The checks in `scripts/rva-codex-kit.mjs` read POSIX mode bits and return early on win32:
  `ownedAndPrivate`, `ownedTreeProblem`, `unsafeTempDir`, and the Linux-only extended-ACL check
  `mayHaveExtendedAcl`.
- Step 1 of `commands/rva-review-diff.md` resolves the plugin root with POSIX shell builtins
  (`pwd -P`, `cd --`).

## Error Details
~~~
{"ok":false,"category":"unsupported_platform","detail":"the dispatcher runs on Linux and macOS only (its timeout needs POSIX process groups); nothing was sent"}
~~~

## Visual Evidence
None.

## Impact
**Medium**: Windows users cannot use the plugin. The refusal is deliberate and fails safe (nothing is
sent), and Linux and macOS are unaffected.

## Additional Context
Work needed:
1. A process-tree kill for the vendor timeout (for example a job object, or `taskkill /T /F`), plus
   the equivalents of the SIGINT/SIGTERM/SIGHUP cleanup.
2. DACL-based owner and write-access checks in place of mode bits, for: the dispatcher's input files,
   codex-kit's imported files, the reviewer-instructions tree up to the plugin root, the local config
   file and its `.claude` directory, and the temp directory.
3. A Windows-safe way for the command's step 1 to resolve and compare the plugin root.

Raised while fixing security-review minor m4 (an ACL can grant write access that mode-bit checks do not
see) in the PR for issue #765. That PR scoped the ACL check to Linux and tracks Windows here.
macOS ACLs are a separate documented limit and are not part of this issue.
