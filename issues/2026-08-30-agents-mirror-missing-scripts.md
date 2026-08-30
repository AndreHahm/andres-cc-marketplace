## Summary

No skill's `.agents/` mirror copy in this repo includes a `scripts/` directory — confirmed for
`merge-pr`, `commit`, and `starting-work`, none of which have `.agents/skills/<name>/scripts/` even
though the canonical `plugins/git-kit/skills/<name>/scripts/` has one for each.

## Environment

- **Product/Service**: git-kit plugin's `.agents/` Codex-facing mirror convention
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps

1. Compare `.agents/skills/merge-pr/` against `plugins/git-kit/skills/merge-pr/` in this repo.
2. `plugins/git-kit/skills/merge-pr/scripts/smoke_test.py` exists; `.agents/skills/merge-pr/scripts/`
   doesn't exist at all — `find .agents/skills/merge-pr -type f` returns only `SKILL.md` and
   `references/`.
3. Same gap confirmed for `.agents/skills/commit/` (no `scripts/`, despite
   `plugins/git-kit/skills/commit/scripts/` existing) and `.agents/skills/starting-work/`.

## Expected Behavior

Either `.agents/` mirrors include referenced `scripts/` files (so a Codex-context reader following a
SKILL.md's own "re-run this smoke test" instruction, or its Reference Guide table pointer, can
actually find the script), or `.agents/`'s own documented scope explicitly excludes scripts, and any
SKILL.md `Reference Guide` table entry pointing at one is understood not to apply to that mirror.

## Actual Behavior

Every checked `.agents/` skill mirror omits `scripts/` entirely, while the corresponding SKILL.md
(identical across all three mirror copies, including `.agents/`) references it in its Reference Guide
table as if it were present in every mirror.

## Error Details

~~~
N/A -- not a runtime error, a missing file relative to a documented reference.
~~~

## Visual Evidence

N/A

## Impact

**Low/Medium** — no functional break for Claude Code (which reads `plugins/`/`.claude/`, never
`.agents/`), but a Codex-context reader following the documented Reference Guide pointer in any
skill's `.agents/` copy hits a dead reference for every skill that has a `scripts/` directory.

## Additional Context

Found by Devin's automated review of PR #245 (`merge-pr` readiness-gate disclosures), which flagged
`.agents/skills/merge-pr/`'s missing `scripts/smoke_test.py` specifically. Triage during that PR
confirmed this is a repo-wide gap in the `.agents/` mirror convention, not specific to `merge-pr` —
no established policy currently exists for whether `.agents/` should mirror `scripts/` at all, and no
sync tool (`marketplace_ci`'s `check-codex-exports`/`convert-codex-exports`) covers this directory
tree — that tooling only manages `.codex/agents/*.toml` exports, a separate, unrelated mirror. See also
#162, a related but distinct `.agents/` staleness issue (a stale reference file blocking a secret
scan) — this issue is about the missing-`scripts/` gap specifically, not that one.

## Review Finding Source

- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/245
- **Head SHA at time of finding**: `36b4739a1d4d0b053a195367fbf3bb73b75939da`
- **Thread**: https://github.com/AndreHahm/andres-cc-marketplace/pull/245#discussion_r3888815498
- **Reviewer**: Devin (`devin-ai-integration[bot]`)
- **Stated severity**: 🟡 (Devin's own "bug" kind badge; no explicit Critical/Major/Minor label given)
