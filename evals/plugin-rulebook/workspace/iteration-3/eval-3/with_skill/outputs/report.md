# R27 Check: commands/git-commit.md (git-kit, registered prefix 'git')

## Task

Apply plugin-rulebook's R27 (Component Naming: Grammatical Form) to a command file
`commands/git-commit.md` (frontmatter `name: git-commit`) belonging to plugin `git-kit`, which has
a registered R33 prefix of `git` in `marketplace-inventory.json`, status `active`.

## Reasoning

R27's scope for commands (per `SKILL.md`'s R27 entry and its full detail in
`references/component-naming-grammatical-form.md`) is: "Command: starts with a verb
(`create-plugin`, `review-rules`). For a command in a plugin that has an R33-registered prefix,
check the filename portion *after* the prefix — `<prefix>-<rest>`, where `<rest>` must start with
a verb (e.g. `git-commit.md` in a `git`-prefixed plugin: `commit` is the verb, `git` is not
expected to be one). For a plugin with no prefix registered yet, check the full basename as
before."

This is the exact worked example the reference file gives for this scenario (a `git`-prefixed
plugin's `git-commit.md` file).

Applying it step by step:

1. Confirm the R33 prefix applies: `git-kit` has a registered prefix `git` in
   `marketplace-inventory.json` with `status: active`. R27's command check branches on whether an
   R33-registered prefix exists for the owning plugin — it does here, so the prefix-stripped check
   path applies rather than checking the full raw basename.
2. Strip the registered prefix from the filename: the command file is `git-commit.md` (basename
   `git-commit`, frontmatter `name: git-commit`). Stripping the plugin's registered `git-` prefix
   from `git-commit` leaves `commit` as `<rest>`.
3. Check `<rest>` for verb-first form: `commit` is itself a verb (an instruction to perform a git
   commit), matching the same shape as the rule's own reference examples `create-plugin` and
   `review-rules`. `<rest>` therefore satisfies the "starts with a verb" requirement.
4. Do not evaluate `git` (the prefix) for verb-ness: the rule states explicitly that "`git` is not
   expected to be one [a verb]" — the prefix segment is excluded from the grammatical-form check
   once it's identified as the registered R33 prefix. A naive whole-basename read (ignoring the
   R33-prefix branch) might otherwise misread `git-commit` as noun-first (tool name `git` followed
   by `commit`) and incorrectly flag it — but that reading applies only to a plugin with no
   registered prefix, which is not the case here.

## Conclusion

R27 does not flag `commands/git-commit.md` as a violation. Once the registered `git-` prefix is
stripped per R27's explicit prefix-aware command-check branch, the remaining portion `commit` is a
verb, matching the required verb-first form for command files. This is a PASS under R27, not a
flagged violation — and even if it were borderline, R27 is ADVISORY-only per its own severity
("Never REQUIRED: this is an interpretive, judgment-based check"), never a blocking FAIL.
