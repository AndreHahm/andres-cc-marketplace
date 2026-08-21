## Summary
All 5 of `git-kit`'s `PreToolUse` guard hooks (`guard-raw-commit.sh`, `guard-raw-pr-ops.sh`, `guard-raw-branch-create.sh`, `guard-raw-pr-review.sh`, `guard-raw-destructive-cleanup.sh`) match their guarded `gh`/`git` subcommand using a prefix anchor limited to `(^|[;&|]|[[:space:]])` — start-of-string, a shell separator, or bare whitespace. This misses several ordinary, non-adversarial ways the guarded command can be legitimately prefixed, letting it bypass the guard with no marker check.

## Environment
- **Product/Service**: `git-kit`'s 5 `PreToolUse` guard scripts (`plugins/git-kit/hooks/scripts/`, mirrored under `.claude/hooks/scripts/`)
- **Region/Version**: this repo, found during a `security-reviewer` pass on `guard-raw-pr-review.sh`, branch `feat/review-findings-handling`, 2026-08-21

## Reproduction Steps
Against `guard-raw-pr-review.sh`'s `API_RE`/`pr review`/`pr comment` matching (same anchor class shared by the other 4 guards' own subcommand regexes):

1. `REPLY_ID=$(gh api repos/o/r/pulls/1/comments/2/replies -f body=x --jq .id)` — the guarded command sits immediately after `$(`, not after `^`/`[;&|]`/whitespace.
2. `` `gh pr comment 42 --body "..."` `` — backtick command substitution, same shape.
3. `/usr/bin/gh api repos/o/r/pulls/1/comments/2/replies -f body=x` — a path-qualified invocation; the char before `gh` is `/`, not a recognized prefix.
4. PowerShell: `& 'C:\Program Files\GitHub CLI\gh.exe' api repos/.../replies -f body=x` — the `&` call operator followed by a quote, not a recognized prefix either.

None of these require anything unusual — capturing a created resource's ID via `$(...)` is a completely ordinary scripting pattern, and both path-qualified and PowerShell call-operator invocations are normal ways to invoke `gh` in some environments/shells.

## Expected Behavior
The guard should recognize the guarded subcommand regardless of what character or shell construct immediately precedes it, as long as it's a genuine invocation of `gh`/`git` (not a substring inside an unrelated word).

## Actual Behavior
The current prefix class `(^|[;&|]|[[:space:]])` (or `\.exe` variants) doesn't match `(`, backtick, `/`, or `&` (PowerShell's call operator) as valid prefixes, so all 4 reproduction cases above bypass every branch and fall through to `exit 0` (allowed) with no marker check.

## Impact
**Medium** — none of these require adversarial intent; each is an ordinary way an agent or script might legitimately construct the guarded command, silently defeating the marker-handshake safeguard for that specific invocation shape. Consistent with `.claude/rules/route-through-git-kit-lifecycle-skills.md`'s own framing: "stops accidental bypass... not a deliberately adversarial agent" — this gap undermines even that narrower guarantee for these four shapes specifically.

## Suggested Fix (not prescriptive)
Replace the enumerated prefix class with a negated-identifier class, e.g. `(^|[^[:alnum:]_.-])gh(\.exe)?...`, which admits `(`, backtick, `{`, `&`, `;`, `|`, whitespace, and a trailing path separator in one construct — the same approach already used to fix the analogous *endpoint*-boundary gap in `guard-raw-pr-review.sh`'s `REPLIES_RE`/`GRAPHQL_RE` (see the commit fixing that file's C2 finding, same session). Apply consistently across all 5 guard scripts' own subcommand-prefix regexes, not just this one file, since the pattern (and the gap) is shared.

## Additional Context
Found alongside two other findings during the same security-reviewer pass on `guard-raw-pr-review.sh`:
- A genuine bypass (`gh`-to-`api` adjacency regression) was found and fixed in the same commit that surfaced this issue — see that commit's message for detail.
- A quoted-endpoint boundary bypass (`REPLIES_RE`/`GRAPHQL_RE`) was found and fixed in the same commit.
- This finding (prefix-class gap) was left unfixed and filed here instead, since it's shared across all 5 guard scripts rather than local to the one file already being changed, and fixing it properly means auditing all 5 at once rather than a one-off patch to a single file.
