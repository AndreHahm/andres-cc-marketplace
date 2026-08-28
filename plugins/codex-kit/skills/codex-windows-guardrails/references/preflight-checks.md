# Pre-Flight Checks

A platform check, then three scope checks, run by `scripts/guarded-dispatch.mjs` before `codex exec`
is ever invoked. The scope checks operate on the caller's `target-paths` and `instruction-file` —
they narrow what gets *sent* to Codex, nothing about what Codex does once it's running.

## 0. Platform

Refuses outright unless `process.platform === "win32"`, before anything else runs — no argument
parsing, no config resolution. This script exists only because Windows has no working sandbox;
every other platform has a real sandboxed profile through `codex-review-bridge`'s own CLI, so this
script being invoked there at all is a routing mistake that must never widen into an unrestricted
`danger-full-access` dispatch just because a real sandbox happened to be available on that host.

Typed failure category: `platform_unsupported`.

## 1. Repository-Boundary

Every `target-paths` entry (not the instruction file — see check 3) must first exist on disk, then
resolve inside the repository root:

- Reject a target-paths entry that doesn't exist (`fs.existsSync`) before doing anything else with
  it. A misspelled or already-deleted target must not silently reach dispatch — `walkFiles`'s own
  ENOENT-is-safe-to-skip handling (needed elsewhere for a legitimately-absent scratch instruction
  file) would otherwise let a nonexistent target sail through both this check and the secret scan,
  reaching a real `danger-full-access` run with nothing inspectable: a zero-finding envelope that
  looks like a clean audit of nothing.
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

Typed failure category: `target_path_not_found` for a missing entry, `repository_boundary_violation`
for an existing entry outside the root. Detail: the specific entry that failed (the caller's own
original argument, not necessarily its canonicalized form — useful for the caller to recognize which
of its own inputs was rejected).

## 2. Secret-File

Walks the **actual filesystem** under the **whole repository root** — not just the caller's
`target-paths` (`fs.readdirSync`, recursive, skipping `.git`) — and tests every resulting file's
basename against the same 19-pattern list
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

**Deliberately the whole repository root, not just `target-paths`.** An earlier draft scoped this
walk to only the caller's declared `target-paths`, matching the repository-boundary and
instruction-containment checks' own scoping. That scope mismatch was itself the gap: `runCodexExec`
below grants `sandbox: "danger-full-access"` with `cwd: repoRoot` — Codex can read anything under
the repository root regardless of what the caller narrowed `target-paths` to. A caller declaring a
small review scope left every other secret file under the root unscanned but still fully readable
by the dispatched process. The other two checks stay `target-paths`-scoped correctly, since they
bound what gets *sent into the prompt*, not what the process can *read* — only the secret scan needs
to match the actual access grant rather than the narrower review scope.

Typed failure category: `secret_file_in_scope`. Detail: the matched file's repo-relative path and
which pattern it matched — never the file's contents.

**Documentation-about-secrets exemption (issue #78).** A match against one of the four *loose*
bare-substring patterns (`*secret*`, `*credential*`, `*password*`, `*token*` — never the exact-
filename/extension patterns like `id_rsa`/`.pem`/`.key`/`.env`) is exempted from blocking when ALL
of the following hold:

- The matched name is the file's **own basename** — not a symlink target's basename riding the
  symlink's own path. `walkFiles` checks a file symlink under both its own name and its real
  target's name (see check 2's symlink handling above); the exemption gates on which name actually
  matched, so a symlink whose real target is credential-shaped (e.g. `id_rsa`) can never be waved
  through just because the link itself sits at a documentation-shaped path.
- The file's repo-relative path has a `references/` or `docs/` path segment (case-insensitive) and
  ends in `.md`, `.mdx`, `.txt`, or `.rst`.
- The file's **content** contains no secret-shaped string — checked two ways. First, the same
  pattern set `scripts/lib/codex-exec.mjs`'s `redactSecrets` already uses to redact CI-persisted
  failure details (bearer tokens, `AKIA`-prefixed AWS keys, `TOKEN=`/`KEY=`/`SECRET=`/`PASSWORD=`/
  `API...=`-shaped assignment lines, PEM blocks, etc.). Second, a local, additional check scoped to
  only this gate: a `CREDENTIAL=`/`AUTH...=`-shaped assignment line — `redactSecrets`'s own generic
  assignment pattern doesn't recognize those two words (it was designed for a different purpose,
  redacting CI-persisted stderr text, not gating whether documentation content is secret-free), so a
  real secret named that way could otherwise pass `redactSecrets(content) === content` undetected.
  Found live via `cross-model-review` (issue #78): this exact evasion shape was used, for legitimate
  teaching purposes, in this repo's own `secrets-and-credentials.md` before the additional check
  existed. Deliberately NOT fixed by broadening `redactSecrets` itself — that function has its own,
  different caller (CI-log redaction) with its own blast radius. Both checks together are a real, if
  narrow, exception to the "filename-pattern-only" limitation below — but scoped to only the small,
  already-exempted-by-path-and-extension set of files, never a whole-repo content scan. A file that
  fails to read is treated as NOT exempt (fails closed to the block below) rather than silently
  trusted.

Motivating case: `references/secrets-and-credentials.md` — a documentation file *about* secrets, not
itself a credential — was permanently blocking this script's whole-repo scan (and therefore the
entire Windows fallback dispatch path) before this exemption existed. **The exemption's path/
extension gate alone does not resolve this for a file whose own content contains illustrative
secret-shaped strings** — confirmed live (2026-08-28, `cross-model-review`): `skill-development`'s
own `secrets-and-credentials.md` failed `secret_file_in_scope` even though it satisfied the path/
extension gate, because a doc that *teaches* what a secret looks like is exactly the kind of file
most likely to contain realistic example values for illustration, and those match the same
`redactSecrets` patterns a real credential would. Two of its three identical copies were then
rewritten to teach the same lessons without any `redactSecrets`-matching content (see "Known
limitations" below for the full account, including why the third copy — `.agents/` — was
deliberately left unfixed, and why that alone still blocks the whole-repo scan today regardless).

**Same limitation as the source list, outside the narrow exemption above**: filename-pattern-only. A
credential-shaped string embedded in an otherwise-unflagged file's *content* is not caught by this
check — the content scan described above only ever runs on the small set of files the path/extension
exemption already carved out, not on every file under the repository root.

## 3. Instruction-Containment

The instruction file must not resolve inside any `target-paths` entry — the exact rule
`codex-review-bridge`'s own `bridge-invoke.mjs` already enforces. This script reuses the *rule*, not
the function: `bridge-invoke.mjs`'s exported `isWithin` is not imported here — `guarded-dispatch.mjs`
defines its own `isInsideRoot`/`canonicalPathsEqual` (a win32-aware equivalent this script's own
Windows-only platform needs on top). The two implementations must be kept in sync by hand; see
`SKILL.md`'s "Public API beyond the CLI" for the full export/consumer breakdown. **This is deliberately a different check from
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
- **The documentation-about-secrets exemption's content-scan can't tell an illustrative example
  from a real secret, in general.** Confirmed live (2026-08-28) against this exemption's own
  motivating file (`skill-development`'s `secrets-and-credentials.md`): a reference doc that teaches
  what a secret looks like, using realistic example values for illustration, failed
  `secret_file_in_scope` even though it satisfied the path/extension exemption — the content-scan
  (see check 2 above) matched those example values the same way it would match a real credential.
  Fixed in two rounds, both `cross-model-review`-verified: first, two of the three prior identical
  copies were rewritten to avoid `redactSecrets`'s own trigger words; then a live Codex finding
  showed that rewrite had itself used a naming evasion (`*_CREDENTIAL`/`*_AUTH` variable names,
  neither recognized by `redactSecrets`'s own generic assignment pattern) that would let a REAL
  secret named the same way through undetected — closed by the additional local
  `CREDENTIAL`/`AUTH` check documented in check 2 above, and a second doc-rewrite round to match.
  Both fixes verified directly against the pattern logic (`redactSecrets(content) === content` and
  the new pattern both clean) and via a live dispatch. The third copy, at
  `.agents/skills/skill-development/references/secrets-and-credentials.md`, was deliberately left
  unfixed — `.agents/` is documented elsewhere in this repo as a stale mirror outside the automated
  `sync-plugin-mirrors` tooling, and fixing it would require a manual, tooling-bypassing copy.
  Because `checkSecretFiles` scans the **whole repository root**, not just the caller's declared
  scope, this stale `.agents/` copy alone still blocks the Windows fallback dispatch path for the
  whole repo today, confirmed live: a dispatch targeting only the now-fixed `plugins/plugin-devkit/`
  copy still fails with `secret_file_in_scope` on the `.agents/` copy instead, since directory
  traversal reaches it first. Not fully resolved even for the two fixed copies — the general
  "content-scan can't distinguish an illustrative example from a real secret" limitation still
  holds for *any* trigger word not yet anticipated (this round closed `CREDENTIAL`/`AUTH`
  specifically because a real, live case used them; a future evasion using some other word not on
  either list would face the identical gap), and for any *other* documentation-about-secrets file
  elsewhere in this repo (or added in the future) whose own examples happen to be realistic-looking.
  Narrowing the content-scan to tolerate clearly-fenced/labeled example values, or trying to
  exhaustively enumerate every possible credential-suggestive word, would itself be a new, fragile,
  open-ended detection surface — left as a known, disclosed gap rather than chased indefinitely.

## Why dangerous-command isn't a fourth pre-flight check

Repository-boundary, secret-file, and instruction-containment all validate something known *before*
dispatch (which paths are in scope). A dangerous command is a decision Codex's own agent loop makes
*during* its run — there is nothing to pre-validate, because the command doesn't exist yet at
pre-flight time. It is instead handled as an instructed request appended to the prompt
(`assets/dangerous-command-instructions.txt`, documented in `references/dispatch.md`, already listed
in `SKILL.md`'s Reference Guide) — a materially weaker guarantee than the three pre-flight checks
above, since the model could simply ignore it.
