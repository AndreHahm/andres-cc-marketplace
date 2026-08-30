# merge-pr Step 1 — headRefName Validation Analysis

This is a simulated exercise. No `gh`/`git` commands were run. This describes exactly what
`merge-pr`'s SKILL.md step 1 instructs, applied to three hypothetical `headRefName` values
returned one at a time from `gh pr view $ARGUMENTS --json ...`.

## The validation regex

Per SKILL.md step 1:

> **Validate `headRefName` and `baseRefName` immediately, before either is used anywhere else
> in this skill**: both must match `^[A-Za-z0-9._/@+=-]+$` — if either doesn't, stop and tell
> the user rather than proceeding.

Allowed characters: letters, digits, `.`, `_`, `/`, `@`, `+`, `=`, `-`. This allowlist is
deliberately narrower than `git check-ref-format`'s own rules (which permit shell
metacharacters like `;&|$` and backticks/parens in ref names), and deliberately wider than a
plain `[A-Za-z0-9._/-]` set, which would reject genuinely valid, shell-safe branch names like
`feature+api`, `user@topic`, `release=next`.

## Per-value results

### (a) `feature+api`

**Passes.** Every character (`f e a t u r e + a p i`) is a letter or `+`, both in the allowed
set. Validation succeeds, and this value is used as-is later in the skill (e.g. interpolated
into `git ls-remote --heads origin <headRefName>` at step 7 if it's the branch being deleted
after merge).

### (b) `user@topic/release=next`

**Passes.** Every character is a letter, `@`, `/`, or `=` — all explicitly in the allowed set
(`@`, `/`, and `=` are called out by name in the SKILL.md text as additions beyond the plain
`[A-Za-z0-9._/-]` set specifically because they're Git-valid and shell-safe). Validation
succeeds.

### (c) `feat/x;rm -rf /`

**Fails.** Two characters are outside the allowed set:
- `;` — a shell metacharacter (command separator), not in `[A-Za-z0-9._/@+=-]`
- ` ` (space) — also not in the allowed set

**What happens next:** per step 1's instruction, the skill stops immediately and tells the
user that the PR reference could not be validated — it does **not** proceed to use this value
in any later `Bash` command (not step 2's branch-protection call if it were `baseRefName`, not
step 7's `git ls-remote --heads origin <headRefName>` / `gh api -X DELETE
repos/{owner}/{repo}/git/refs/heads/<branch>` calls). This is exactly the scenario the
validation step exists to catch: `git` itself permits `;`, `&`, `|`, `$`, backticks, and
parens in ref names, so without this narrower allowlist gate, a malicious or malformed
`headRefName` like this one could reach a shell context unsafely the first time it's
interpolated into a command (e.g. producing something like `git ls-remote --heads origin
feat/x;rm -rf /` if naively substituted). Because the check runs "immediately, before either
is used anywhere else in this skill," no such interpolation is ever attempted — the skill
halts at step 1 and reports the failure to the user instead of continuing to steps 2 onward.

## Summary table

| headRefName | Matches `^[A-Za-z0-9._/@+=-]+$`? | Result |
|---|---|---|
| `feature+api` | Yes | Passes — skill proceeds normally |
| `user@topic/release=next` | Yes | Passes — skill proceeds normally |
| `feat/x;rm -rf /` | No (`;` and space are disallowed) | Fails — skill stops at step 1, tells the user, never interpolates the value into any later `Bash`/`gh` command |
