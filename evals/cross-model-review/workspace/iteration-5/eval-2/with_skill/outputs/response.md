# Answer: Preflight step 6's grep flag

## What the skill specifies

The skill does **not** call for plain `grep`. It explicitly requires `grep -E` (extended regex mode).
This is stated in two places:

1. **Preflight step 6** itself (SKILL.md lines 158–162):

   > "**Check whether the diff itself touches the Codex dispatcher scripts this skill is about to
   > execute** — `grep -E` (extended regex — plain `grep`'s default basic mode treats `(`/`)`/`?` as
   > literal characters and silently fails to match either intended path, verified: plain `grep` exits
   > 1 against `plugins/codex-kit/scripts/lib/codex-exec.mjs`, `grep -E` exits 0) for
   > `plugins/codex-kit/(.*/)?scripts/` against the **unscoped** changed-file list..."

   The skill is explicit here: it names `grep -E`, gives the reason (BRE vs. ERE metacharacter
   handling), and even states a verified, concrete test result for exactly the path named in the
   question — `plugins/codex-kit/scripts/lib/codex-exec.mjs` — confirming plain `grep` exits 1 (no
   match) against it while `grep -E` exits 0 (match).

2. **The Quality gates checklist** at the end of the file (line 477–478) restates this as a
   standalone, checkable gate:

   > "- [ ] Preflight step 6's dispatcher-trust grep is always run with `-E` — never plain `grep`,
   >   which silently fails to match the extended-regex pattern"

So the skill's answer to "plain grep or grep with a flag" is unambiguous: **`grep -E`, never plain
`grep`**, and the skill itself flags plain `grep` as a documented failure mode to avoid.

## Would plain grep (no flags) actually match `plugins/codex-kit/scripts/lib/codex-exec.mjs`?

**No — and the skill's own reasoning for why is correct.**

Plain `grep` (no `-E`/`-P`) uses POSIX **Basic Regular Expressions (BRE)** by default. In BRE, the
characters `(`, `)`, and `?` are **not** metacharacters — they are literal characters unless
backslash-escaped (`\(`, `\)`, `\?`). Only `.`, `*`, `^`, `$`, and bracket expressions retain their
special meaning by default in BRE.

The pattern in question is:

```
plugins/codex-kit/(.*/)?scripts/
```

Under **extended** regex (`-E`), this means: literal `plugins/codex-kit/`, then an *optional* group
(`(...)?`) containing "any characters followed by a slash," then literal `scripts/`. That optional
group is exactly what lets the pattern match both a nested path
(`plugins/codex-kit/skills/<name>/scripts/*.mjs`) and the flatter, no-extra-segment path
(`plugins/codex-kit/scripts/lib/codex-exec.mjs`), per the group being optional.

Under plain BRE `grep`, however, the same literal characters `(`, `)`, and `?` in the pattern are
searched for **as literal text**, not as grouping/quantifier syntax. So plain `grep` treats the
pattern as: literal `plugins/codex-kit/(`, then any characters (`.*`, which *is* still special in
BRE) followed by a literal `/`, then literal `)?scripts/`. In other words, it looks for a literal
open-parenthesis `(` immediately after `plugins/codex-kit/`, and a literal `)?` immediately before
`scripts/` in the text being searched.

The target string `plugins/codex-kit/scripts/lib/codex-exec.mjs` contains no literal `(` character
at all (there's no parenthesis anywhere in a normal file path), so there is nothing in the subject
string that can satisfy the literal `(` the BRE pattern is now looking for right after
`codex-kit/`. The match therefore fails — plain `grep` exits 1 (no match) against this path, exactly
as the skill states.

## Summary

- The skill specifies `grep -E` (extended regex), explicitly and in two locations: Preflight step 6's
  own prose (lines 158–162) and the Quality gates checklist (lines 477–478).
- Plain `grep` (BRE, no flags) would **not** match `plugins/codex-kit/(.*/)?scripts/` against
  `plugins/codex-kit/scripts/lib/codex-exec.mjs`, because BRE treats `(`, `)`, and `?` as literal
  characters rather than grouping/optional-quantifier syntax, so the pattern ends up requiring a
  literal `(` and `)?` substring that doesn't exist in the path. This is precisely the failure mode
  the skill calls out by name, including the verified exit-code claim (plain `grep` exits 1, `grep -E`
  exits 0) for this exact file.
- This distinction matters functionally to the skill's own stated purpose for step 6: the optional
  `(.*/)?` group is what lets the pattern also catch the shared `codex-exec.mjs` executable (imported
  by both dispatch scripts) and not just the deeper `skills/<name>/scripts/*.mjs` paths (lines
  168–171) — using plain `grep` here would silently fail to flag a diff that modifies that shared file,
  undermining the dispatcher-trust check the step exists to perform.
