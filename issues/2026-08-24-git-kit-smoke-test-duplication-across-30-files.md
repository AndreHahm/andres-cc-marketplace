## Summary
All 15 `scripts/smoke_test.py` files this session added to `git-kit` skills (`bbe739a`) -- plus their 15 byte-identical `.claude/` mirror copies, 30 files total -- share the same body logic (`check_frontmatter`, `check_referenced_files`, `check_bash_grants`, `check_step_sequence`, and supporting helpers), differing only in each file's own `SKILL_DIR`/`SECTION_HEADERS` constants. A real bug already had to be fixed identically across all 30 copies in this same PR (see `27a6a47`, the `check_step_sequence` preamble fix), confirming this is a live maintenance cost, not a style nit.

## Environment
- **Product/Service**: `git-kit` plugin, 15 skills' `scripts/smoke_test.py` (`collaborating-on-a-pr`, `create-pr`, `dependency-updater`, `explain-pr-changes`, `finishing-work`, `gh-operations`, `git-bisect`, `git-cleanup`, `git-notes`, `git-rebase-sync`, `git-worktrees`, `github-issue-creator`, `manage-codeowners`, `standalone-commits`, `starting-work`) and their `.claude/` mirrors
- **Region/Version**: this repo, branch `fix/git-kit-downstream-qa`, PR #121

## Reproduction Steps
1. Diff any two of the 30 `smoke_test.py` copies -- the body (everything past each file's own `SKILL_DIR`/`SECTION_HEADERS` declaration) is byte-identical.
2. Note each pair also has a `.claude/skills/<skill>/scripts/smoke_test.py` mirror (this repo's R19 in-development-mirror convention -- both copies must stay byte-identical).
3. A consolidation into a shared module hits the same wall already documented for `analysis-kit`'s identical situation (issue #105): the packager/mirror-sync tooling only copies each skill's own directory tree, so a shared module living at the plugin-script level (`plugins/git-kit/scripts/`) has no counterpart path under `.claude/` for the mirror copies to import from.

## Expected Behavior
A consolidation approach that keeps every mirror copy runnable and byte-identical to its canonical counterpart (or otherwise resolves cleanly under this plugin's R19 mirroring convention) without duplicating the shared module's own logic a second time.

## Actual Behavior
No consolidation applied -- the duplication was left in place across all 30 files. `check_step_sequence`'s preamble bug (fixed in `27a6a47`) already had to be patched in every one of the 15 canonical copies (with the 15 mirrors regenerated via marketplace-CI sync), demonstrating the exact cost pattern issue #105 already predicted for `analysis-kit`'s own 11-file version of this same problem.

## Impact
**Low-to-Medium** -- the files are small (~200 lines each) and functionally correct as of this PR. The cost is maintenance friction: any future fix to the shared checking logic needs the same edit applied across every copy, verified consistent by hand (as this PR's own fix just did).

## Additional Context
Found by CodeRabbit's automated PR review (round 1, triggered by this PR's draft-to-ready transition). Verified independently: `find` + pattern-match against all 30 files confirmed the exact scope (15 canonical + 15 mirrors, not the 12+1 subset CodeRabbit's own comments happened to enumerate).

**Same pattern already tracked for a different plugin**: issue #105 documents the identical problem for `analysis-kit`'s 11 skills' `smoke_test.py` files, including the same root blocker (the `.claude/` mirror convention has no path for a shared plugin-level module to live at) and three candidate directions, none decided: (a) accept the duplication permanently as a documented tradeoff, (b) give the shared module its own home under `.claude/` too (trading an N-way duplication for a 2-way one), or (c) revisit whether plugin-level `scripts/`/`references/` directories should be mirrored into `.claude/` at all. This is now the **second** plugin hitting the exact same wall -- worth resolving once, at the repo-tooling level, rather than re-deciding per plugin.

**Deferred, not fixed, in this PR**: CodeRabbit itself labeled this a "Heavy lift" (cross-cutting refactor across 30 files plus packaging/mirror-sync changes) -- too large to fix within this session per `handling-review-findings`' own budget discipline; the smaller, in-scope findings from this same review round (the `check_step_sequence` preamble bug, `lint-staged-python.sh`'s cwd-relative path bug) were fixed directly in `27a6a47`.

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/121
- **Head SHA finding was raised against**: `3a11d0c45d11d6983627c253a4b2b53592633cbe`
- **Review thread/comment**: https://github.com/AndreHahm/andres-cc-marketplace/pull/121#discussion_r3843826421
- **Reviewer**: CodeRabbit (`coderabbitai[bot]`)
- **Stated severity**: Major (CodeRabbit's own label: "📐 Maintainability & Code Quality | 🟠 Major | 🏗️ Heavy lift")
