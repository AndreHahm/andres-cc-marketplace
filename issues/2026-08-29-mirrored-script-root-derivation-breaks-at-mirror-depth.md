## Summary
A script deliberately shipped as a byte-identical copy at more than one directory depth (this repo's `plugins/<name>/` ↔ `.claude/` mirror convention) must resolve its own root by discovery, not a fixed parent-directory-count assumption — this bug class isn't named as a convention anywhere yet.

## Environment
- **Product/Service**: `analysis-kit` plugin (source instance: 11 skills' `scripts/smoke_test.py`)
- **Region/Version**: this repo, found during PR #108 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A script derives its own "plugin root" (or similar base path) as a fixed number of `.parent` calls from its own file location (e.g. `SKILL_DIR.parent.parent`).
2. That expression is correct only when the script runs from one specific location — e.g. `plugins/analysis-kit/skills/<skill>/scripts/smoke_test.py`.
3. The same script is also shipped as a byte-identical copy under `.claude/skills/<skill>/scripts/smoke_test.py` (this repo's mirror convention).
4. Run the mirror copy: the same parent-count expression now resolves to `.claude` instead of `plugins/analysis-kit`, which has no matching `scripts/`/`references/` directory.

## Expected Behavior
A script shipped as a byte-identical mirror at more than one depth should resolve its own root by discovery (e.g. walk up parent directories to find `.git`), so the same logic is correct regardless of which copy is actually running.

## Actual Behavior
Every one of the 11 mirrored `smoke_test.py` copies false-failed its own structural checks (`check_referenced_scripts_exist`, `check_reference_guide_files_exist`) while the canonical copies passed — the mirrored copies could never provide the before-commit validation they were meant to.

## Impact
[Severity: Medium] The specific instance was already fixed in PR #108 (commit `4c2db7d`), verified live across all 22 copies (11 skills × 2 trees) after switching to `.git`-discovery-based root resolution. This issue is about the *general* convention: no `.claude/rules/*.md` file currently states "a script shipped at more than one directory depth must resolve its own root by discovery, not a parent-count assumption" — any future mirrored script (in this or another plugin) could reintroduce the same bug.

## Additional Context
Mined from PR #108's own review history (`devin-ai-integration[bot]`; 16 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #108` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/108#discussion_r3842195788

Related but distinct from issue #122/#105 (which track the *duplication* of these scripts' shared body logic across many copies) — this issue is specifically about the root-resolution bug shape, not the duplication itself.
