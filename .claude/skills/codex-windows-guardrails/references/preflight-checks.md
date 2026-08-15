# Pre-Flight Checks

Three checks, run by `scripts/guarded-dispatch.mjs` before `codex exec` is ever invoked. All operate
on the caller's `target-paths` and `instruction-file` — they narrow what gets *sent* to Codex,
nothing about what Codex does once it's running.

## 1. Repository-Boundary

Every `target-paths` entry (not the instruction file — see check 3) must resolve inside the
repository root:

- Canonicalize via `fs.realpathSync`, resolving symlinks/junctions for every existing path
  component. For a not-yet-existing leaf, walk up to the nearest existing ancestor, canonicalize
  *that* (so an intermediate junction is still caught), then re-join the non-existent remainder —
  a bare try/catch that falls back to lexical `path.resolve` on *any* error would let a symlink or
  junction that can't be stat'd (a permission error, not just "doesn't exist yet") pass through
  uncanonicalized.
- Compare case-insensitively **only on Windows** (`process.platform === "win32"`) — Windows
  filesystems are case-insensitive by default, but applying that comparison unconditionally would
  wrongly treat two genuinely distinct directories as the same one on a case-sensitive filesystem.
- Reject if the canonicalized path does not start with the canonicalized repository root.

Typed failure category: `repository_boundary_violation`. Detail: the specific entry that failed
(the caller's own original argument, not necessarily its canonicalized form — useful for the caller
to recognize which of its own inputs was rejected).

## 2. Secret-File

Walks the **actual filesystem** under each `target-paths` entry (`fs.readdirSync`, recursive,
skipping `.git`) and tests every resulting file's basename against the same 19-pattern list
`git-kit`'s `plugins/git-kit/scripts/scan-staged-files.sh` uses:

- **Matched case-sensitively on non-Windows, case-insensitively on Windows** (`process.platform ===
  "win32"`) — the pattern *list* is identical to `scan-staged-files.sh`'s, but that script matches
  git path strings from any platform's checkout, while this check runs only on Windows against real
  NTFS filenames, where `.ENV`/`ID_RSA`/etc. are everyday valid names a case-sensitive-only match
  would miss. Same platform-gating principle `isInsideRoot` already applies to path comparison,
  applied here to filename matching.
- **Follows a symlinked/junction directory whose real target canonicalizes inside the repository
  root** (bounded by a visited-realpath set against cycles) — the repository-boundary check already
  treats such a junction as "inside" via its own `realpathSync` canonicalization; the secret-file
  check has to agree, or a junction becomes an unscanned blind spot for exactly the kind of file this
  check exists to catch. A symlink resolving outside the repo, or one that can't be resolved at all,
  is not followed; its own basename is still checked like any entry.

```
.env, .env.*, *secret*, *credential*, *.key, *.pem, *password*, *token*,
id_rsa, id_ed25519, id_ecdsa, id_dsa, service-account.json, *.p12, *.pfx, *.jks,
.npmrc, .pgpass, .netrc
```

**Deliberately not `git ls-files`.** An earlier draft of this check enumerated files via
`git ls-files <target>` — which only lists *tracked* files. A `.env` file is normally gitignored,
never tracked, so that enumeration systematically missed the single most common real-world secret
file. Confirmed live during Self-Review rework: a scratch repo with an untracked `.env` under a
directory target passed the `git ls-files`-based check silently, then correctly failed once the
check was rewritten to walk the real filesystem instead.

Typed failure category: `secret_file_in_scope`. Detail: the matched file's repo-relative path and
which pattern it matched — never the file's contents.

**Same limitation as the source list**: filename-pattern-only. A credential-shaped string embedded
in an otherwise-unflagged file's *content* is not caught by this check.

## 3. Instruction-Containment

The instruction file must not resolve inside any `target-paths` entry — the exact rule
`codex-review-bridge`'s own `bridge-invoke.mjs` already enforces, reused via its exported `isWithin`
function rather than reimplemented. **This is deliberately a different check from
repository-boundary** — the instruction file is expected to live in the session scratchpad, *outside*
the repository, per `.claude/rules/require-gitignored-scratch-locations.md`; checking it against the
repository root (as an earlier draft did) would reject the very instruction file the caller is
required to produce, every time.

## Known limitations, deliberately not fixed in this pass

- **First-match-wins, not accumulated.** Each check returns on its first violation rather than
  collecting every violation in scope. Matches `bridge-invoke.mjs`'s own style; a caller with several
  violations sees them one re-run at a time. Not fixed here — consistent with existing convention,
  low cost to a caller (re-run after each fix).
- **NTFS alternate-data-stream / trailing-dot filename evasion.** The secret-file patterns are
  anchored (e.g. `^\.env(\..*)?$`) and a basename like `.env:stream` or `id_rsa.` could theoretically
  evade them on NTFS, depending on how `path.basename` and the filesystem resolve such names —
  unverified, would need live testing on NTFS to confirm either way. Not fixed here; flagged as a
  known gap rather than silently left unmentioned.

## Why dangerous-command isn't a fourth pre-flight check

Repository-boundary, secret-file, and instruction-containment all validate something known *before*
dispatch (which paths are in scope). A dangerous command is a decision Codex's own agent loop makes
*during* its run — there is nothing to pre-validate, because the command doesn't exist yet at
pre-flight time. See `references/dispatch.md` for how this is instead handled as an instructed
request appended to the prompt, and why that's a materially weaker guarantee than the three checks
above.
