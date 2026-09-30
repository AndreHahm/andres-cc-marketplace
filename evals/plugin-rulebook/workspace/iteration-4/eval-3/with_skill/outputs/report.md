# R27 check: commands/git-commit.md (plugin git-kit, registered prefix `git`, status active)

**Verdict: PASS. R27 does not flag this file.**

## Reasoning
1. R27 (ADVISORY, never REQUIRED) applies to command file basenames, since commands have no `name` field. The basename here is `git-commit`.
2. The expected form for a command is verb-first (`references/component-naming-grammatical-form.md`; `references/naming-conventions.md`).
3. git-kit has a registered R33 prefix `git` and is active, so R33 is in scope. The rule says to check the filename portion after the prefix: `<prefix>-<rest>`, where `<rest>` must start with a verb. The prefix is stripped before the check.
4. Stripping `git-` leaves `commit`, which is a verb. `git` is not expected to be a verb. The name is verb-first after the prefix, so it conforms.
5. Contrast: with no registered prefix, the full basename `git-commit` would be checked and `git` (a noun) would not be a verb, so R27 could raise an ADVISORY. The registered prefix is what prevents that false positive.

## Related notes
- The frontmatter `name: git-commit` is not the R27 check target for commands. The basename is.
- R33 (prefix required) is satisfied for this file because the name starts with `git-`.
- Other rules (R4 kebab-case, R8 description) were not part of this task.
