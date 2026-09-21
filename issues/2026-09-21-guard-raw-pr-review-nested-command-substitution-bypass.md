## Summary
`guard-raw-pr-review.sh`'s `gh api` span-extraction stops at the first unquoted `;`/`&`/`|` byte, so a
raw `gh api .../replies` call built with a nested `$(...)` command substitution whose own body contains
one of those bytes (e.g. a `--jq` filter with a pipe) is silently allowed through with no marker
handshake, even though the same call typed with a literal, already-resolved ID is correctly denied.

## Environment
- **Product/Service**: `plugins/git-kit/hooks/scripts/guard-raw-pr-review.sh` (mirrored under
  `.claude/hooks/scripts/`)
- **Region/Version**: this repo, found live during this session (2026-09-21) while replying to review
  findings on PR #364 — an entirely ordinary, non-adversarial command shape, not a deliberate bypass
  attempt

## Reproduction Steps
1. Run, with no prior marker handshake (`write-git-kit-marker.sh gh-pr-review ...`), a `Bash` command
   that resolves a review comment's ID via a nested `gh api --jq` lookup before replying to it:
   ```bash
   gh api repos/OWNER/REPO/pulls/N/comments/$(gh api repos/OWNER/REPO/pulls/N/comments --jq '.[] | select(.user.login == "some-bot") | .id')/replies -f body="..."
   ```
2. The guard's `API_SPANS=$(grep -oE "${API_SPAN_PREFIX_RE}[^;&|]*" <<< "$COMMAND_FLAT")` step walks
   forward from the outer `gh api` and stops at the first `;`/`&`/`|` byte it finds anywhere in the
   command text — including inside the nested `$(...)`'s own `--jq '.[] | select(...) | .id'` filter,
   which contains two literal pipes.
3. The extracted span is truncated to `gh api repos/OWNER/REPO/pulls/N/comments/$(gh api
   repos/OWNER/REPO/pulls/N/comments --jq '.[]` — the outer command's own `/replies` suffix, which
   `REPLIES_RE` needs to match, never appears in the span the guard actually checks.
4. Live-verified by extracting the guard's own `API_SPAN_PREFIX_RE`/`COMMAND_FLAT`/`REPLIES_RE` logic
   into a standalone repro and running it against the exact command above: the single extracted span is
   `gh api repos/.../pulls/364/comments/$(gh api repos/.../pulls/364/comments --jq '.[]`, and `REPLIES_RE`
   reports no match against it.
5. The equivalent command with a literal, already-resolved ID (`gh api repos/.../comments/4060828704/replies
   -f body="..."`, no `$(...)`) *is* correctly matched and would be denied without the marker handshake —
   confirming the gap is specific to the nested-substitution shape, not a general REPLIES_RE defect.

## Expected Behavior
A raw `gh api repos/{owner}/{repo}/pulls/{n}/comments/{id}/replies` call should be denied when it lacks
the marker handshake, regardless of whether `{id}` is typed as a literal value or resolved via a nested
`$(...)`/backtick command substitution.

## Actual Behavior
The call is silently allowed through with no marker check and no warning whenever the ID (or any other
part of the endpoint) is resolved via a nested construct whose own body contains an unquoted `;`/`&`/`|`
byte before the guard's span extraction reaches the outer `/replies` text.

## Error Details
~~~
(no error — the failure mode is a silent allow, not a crash or a visible warning)
~~~

## Impact
**High.** This is a real bypass of a hard-block security guard, not a false positive (over-denial) —
the opposite, more dangerous direction from issues #176/#180. It's already disclosed in this exact
file's own header comment as an accepted, unclosed residual ("an unquoted nested construct... arguably
the more likely shape in practice, since a `gh api` endpoint is often built by interpolation rather than
typed literally... Neither case is closed here, since doing so needs real shell tokenization, not a
character-class cut") — so this issue promotes a known-but-untracked prose disclosure into an actionable
item, rather than reporting a secret vulnerability. Not Critical: `route-through-git-kit-lifecycle-skills.md`
already documents the marker-handshake mechanism generally as "a policy guardrail, not a security
boundary... stops accidental bypass... not a deliberately adversarial agent." What elevates this above a
purely theoretical residual is that the reproduction above is exactly the "accidental" case this guard is
supposed to catch — an ordinary, natural way to write a reply command (resolving a target ID via a
`--jq` lookup) — not a deliberately crafted adversarial payload; the accidental-bypass protection the
hook is meant to provide doesn't reliably hold even for good-faith usage.

## Additional Context
Confirmed single-file scope: `grep -l "API_SPAN_PREFIX_RE\|API_SPANS" plugins/git-kit/hooks/scripts/*.sh`
returns only `guard-raw-pr-review.sh` — the sibling guards (`guard-raw-commit.sh`,
`guard-raw-branch-create.sh`, `guard-raw-pr-ops.sh`, `guard-raw-destructive-cleanup.sh`) don't share this
exact `gh api`-endpoint span-extraction mechanism, so this residual isn't verified to affect them (not an
overclaim — just not checked, since they don't use this pattern at all per the grep above).

Not a duplicate of #180 (same "quoted/nested construct needs real tokenization" root cause, but scoped to
`guard-raw-destructive-cleanup.sh` specifically, and about the opposite direction — a benign
`--format='...'` listing being incorrectly *denied*, not a guarded action being incorrectly *allowed*) or
#176 (a different evasion mechanism — line-continuation splitting across `grep` records — already closed
by this file's `COMMAND_FLAT` normalization).

Per this file's own header comment, closing this properly needs real shell tokenization rather than
another character-class patch, matching the same conclusion #180 already reached for the sibling file —
this issue exists to keep the decision point tracked and visible (fix vs. formally accept as a documented
tradeoff), not to mandate a specific resolution.
