## Summary
A `security-reviewer` pass dispatched against PR #380's round-5 tokenizer fixes to
`guard-raw-pr-review.sh` found 4 additional PowerShell-specific gaps in the same
`extract_api_span` scanner, plus 2 lower-severity residuals — all deliberately deferred rather
than shipped in that PR, since this environment has no live `pwsh` to verify a PowerShell-specific
fix against (every other fix in this file's history was live-verified against the real shell it
targets before landing), and the other two are pre-existing/cross-platform concerns better scoped
as their own follow-up than folded into an already-large round.

## Environment
- **Product/Service**: `git-kit`'s `plugins/git-kit/hooks/scripts/guard-raw-pr-review.sh` (mirrored
  at `.claude/hooks/scripts/guard-raw-pr-review.sh`), specifically the `extract_api_span` scanner
- **Region/Version**: this repo, found during a `security-reviewer` pass on PR #380's commit
  `d6b9677a` (branch `fix/guard-pr-review-tokenization-and-timeout`)

## Reproduction Steps / Findings

**1. PowerShell block comment (`<# ... #>`)** — a literal `;`/`&`/`|` inside a block comment isn't
a real separator in real PowerShell, and (unlike Bash's unbounded line comment) real PowerShell
code resumes normally right after the comment closes. The scanner doesn't recognize `<#`/`#>` at
all, so it could end a span early inside the comment, or fail to suppress a separator that's
actually inert comment text.

**2. PowerShell `--%` stop-parsing token** — everything after `--%` on the line is passed to the
program as a literal, unparsed string in real PowerShell. The scanner has no handling for it, so a
character after `--%` that looks like a separator isn't treated as literal.

**3. PowerShell here-strings (`@'...'@` / `@"..."@`)** — can contain a literal `;`/`&`/`|` that's
part of the string body, not a separator. Not modeled at all.

**4. PowerShell script-block arguments (`{ ... }`)** — a bare `{...}` script-block argument's own
`;` is literal content, not a separator, in real PowerShell. The scanner has no `{`/`}` nesting for
PowerShell at all (Bash's own `${...}` gap was fixed in this same PR; the PowerShell case is a
different, unverified construct).

**5. (M1, pre-existing, predates PR #380) Quoted/escaped `api` subcommand word skips prefix
matching entirely** — the `api`/`review`/`comment` word in each prefix regex must appear bare,
unquoted, and unescaped to match. A quoted (`"api"`/`'api'`), ANSI-C-quoted, or backslash-escaped
subcommand word (e.g. `gh \api ...`) produces no prefix match at all, so `find_api_spans` never
runs for that invocation — the whole span-scanning apparatus is silently skipped. Same gap exists
for the `pr review`/`pr comment` prefix regexes elsewhere in this file.

**6. (M2) Scan-cost-per-character model is unverified on other platforms** — the ~2.7s/50KB rate
this file's own size caps (`API_SPAN_MAX_LEN`, `api_span_budget_exceeded`) are sized against was
measured on one unspecified platform. Bash's own `${text:i:1}`/`${#text}` re-derive the string's
length on each call, and `out+=` reallocates — both plausibly super-linear in practice, and a
slower interpreter (e.g. Git Bash on Windows, a real target implied by this file's own PowerShell
handling) could see materially different per-character cost, risking the 15s hook timeout (which
fails OPEN under this hook's `onError: "warn"` registration) on a legitimate, non-adversarial input
near the cap.

## Expected Behavior
Items 1-4: PowerShell-specific constructs that hide or fabricate a separator should be handled the
same way this file already handles their Bash counterparts — either modeled correctly (verified
live against real `pwsh`), or denied outright (fail-closed) the same way `case`/heredoc/`#` inside
`$(...)` is denied outright in this same PR, per this file's own established "verify before
shipping, fail closed when verification isn't possible" discipline.

Item 5: the prefix regexes should recognize a quoted/escaped subcommand word as a match too (or a
normalization pass should strip surrounding quotes/escapes from a copy before prefix matching).

Item 6: the scan-time budget/cap sizing should be re-measured at the actual cap size on the slowest
realistically-supported platform, not trusted as a linear extrapolation from one unspecified
platform's measurement.

## Actual Behavior
Items 1-4 are unhandled — no `pwsh` was available in this session's environment to verify a fix
against any of them, so none was shipped in PR #380. Item 5 is a pre-existing gap outside the
scanner functions PR #380 touched. Item 6 is an unverified assumption baked into every size cap in
this file.

## Impact
**Major** (items 1-4, PowerShell) — same bypass-risk class as the Bash-side findings PR #380 did
fix (an early-stop or false-fabricated-separator letting a dangerous `gh api .../reviews` /
`.../replies` / `graphql` call slip past the scanner undetected), but currently unverified and
unfixed for the PowerShell path specifically.
**Major** (item 5) — a quoted/escaped subcommand word bypasses prefix matching entirely, skipping
every other protection in this file.
**Minor** (item 6) — a disclosed assumption, not a known-exploitable gap; risk is a false ALLOW only
if the hook actually times out on a legitimate platform, which fails open under `onError: "warn"`.

## Additional Context
- Found by `security-reviewer`, dispatched this session against PR #380's round-5 fixes (round 6).
  Full report delivered inline in that session; not separately persisted.
- PR #380: https://github.com/AndreHahm/andres-cc-marketplace/pull/380, fixing commit `d6b9677a`.
- The round-6 findings this issue does NOT cover (3 Critical Bash-side bugs: an ANSI-C
  misdetection regression, `${...}` nesting, and a `case`-pattern desync) were all fixed, live-
  verified against real bash, and shipped in `d6b9677a` — this issue is only the deliberately
  deferred remainder.
- Suggested follow-ups (not implemented as part of this issue):
  - Items 1-4: get access to a `pwsh` environment (or dispatch to a session that has one) to verify
    each construct's exact behavior before implementing a fix — this file's own history shows every
    fix needs live verification against the real shell it targets, not implementation from
    documentation/memory alone. A conservative fail-closed heuristic (deny outright on `<#`, `--%`,
    `@'`/`@"`, and a bare `{` at any depth for PowerShell) was drafted and shown to work correctly
    at the guard's own logic level in this session, but was reverted before shipping since it
    couldn't be cross-checked against real PowerShell semantics.
  - Item 5: extend `API_SPAN_PREFIX_RE` (and the sibling `pr review`/`pr comment` prefix regexes)
    to also match a quoted/escaped subcommand word, or add a normalization pre-pass.
  - Item 6: re-measure the scan rate at `API_SPAN_MAX_LEN` (131072 bytes) on Git Bash for Windows
    specifically, and adjust the cap if the measured rate is materially worse than 2.7s/50KB.
