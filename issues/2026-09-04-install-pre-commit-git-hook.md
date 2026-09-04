## Summary
`.pre-commit-config.yaml` was added to this repo but the pre-commit git hook has never actually been installed — no commit has ever been gated by it.

## Environment
- **Product/Service**: This repo's local dev tooling (`pre-commit`, `uv`)
- **Region/Version**: N/A

## Reproduction Steps
1. Run `find .git/hooks -iname pre-commit` — returns nothing.
2. Check recent commit history — every commit so far went through raw `git commit`.
3. Run `uv run pre-commit run --files <changed files>` manually — this works and reports pass/fail, but it's a manual invocation, not the real git hook.

## Expected Behavior
`uv run pre-commit install` has been run, so `.git/hooks/pre-commit` exists and every `git commit` in this repo is actually gated by the configured hooks (gitleaks, linters, standard hygiene checks).

## Actual Behavior
No git hook is installed. The hook configuration exists and has been validated via manual `uv run pre-commit run --files/--all-files` invocations, but nothing enforces it automatically at commit time yet.

## Error Details
~~~
$ find .git/hooks -iname pre-commit
(no output)
~~~

## Visual Evidence
N/A

## Impact
**Medium** — No commits are currently protected by the configured checks (secret scanning, linting, standard hygiene), even though the tooling exists. Not urgent (nothing is actively broken), but the intended protection isn't live yet.

## Additional Context
Before running `uv run pre-commit install`, the standard auto-fixing hygiene hooks (`trailing-whitespace`, `end-of-file-fixer`, `mixed-line-ending`, `check-executables-have-shebangs`) need a one-time full-repo cleanup pass first. A `--all-files` dry run showed `trailing-whitespace` alone currently finds violations in 24 pre-existing files across `.agents/`, `.claude/`, `evals/`, and `plugins/` (the dry run was reverted before anything was committed, to avoid mixing an unrelated repo-wide cleanup into other work).

Separately, for context only (not blocking this issue): `markdownlint`'s pre-commit hook is already deliberately scoped to `docs/**` only — before that scoping decision, a full-repo run found ~910K findings across 3,654 files, which is why it's scoped down now. `shellcheck` also has its own pre-existing backlog (87 findings across 26 shell scripts). Neither is part of the hygiene-hook set this issue covers, and markdownlint's hook is already scoped away from most of the repo, so neither should block this work.

**Acceptance criteria:**
1. Run the auto-fixing hygiene hooks (`trailing-whitespace`, `end-of-file-fixer`, `mixed-line-ending`, `check-executables-have-shebangs`) across the whole repo once, review the diff for sanity, commit it as its own standalone cleanup commit.
2. Run `uv run pre-commit install` so the hook actually gates future commits.
3. Verify with a real test commit that it now blocks a violation and passes a clean commit as expected.

**Scope note:** this should be its own separate branch/PR — not bundled with other marketplace-ci tooling work.
