## Summary
antigravity-kit and codex-kit have ambiguous, overlapping activation triggers with no reciprocal exclusion between them

## Environment
- **Product/Service**: Claude Code plugin marketplace (`andres-cc-marketplace`), `plugins/antigravity-kit/` and `plugins/codex-kit/`
- **Region/Version**: `antigravity-kit` v0.1.0

## Reproduction Steps
1. Install both `antigravity-kit` and `codex-kit`.
2. Ask "get a second opinion on this diff" (or "review this diff"), "do deep research on X", or "delegate this task to the CLI agent" — with no model/tool named.
3. Observe that either plugin's natural-language activation could plausibly fire, since neither plugin's activation description mentions the other.

## Expected Behavior
Per `.claude/rules/resolve-activation-overlap-bidirectionally.md`, two plugins with genuinely overlapping domains should carry an explicit, reciprocal textual exclusion: each side names the specific sibling and states the exact distinguishing criterion (here, which model/tool — Gemini/Antigravity vs. Codex).

## Actual Behavior
Neither plugin discloses the other's existence. `activation-reviewer` (dispatched during `plugin-lifecycle-downstream`'s Phase 5/6 audit of the antigravity-kit transfer) found 3 Major findings for this exact shape:
- "second opinion" / "review this diff" — overlaps `plugins/antigravity-kit/skills/antigravity/SKILL.md` and `plugins/codex-kit/skills/codex-peer-review/SKILL.md`
- "deep research on X" — overlaps `antigravity/SKILL.md` and `plugins/codex-kit/skills/codex-research/SKILL.md`
- "delegate this task" — overlaps `antigravity/SKILL.md` and `plugins/codex-kit/skills/codex-rescue/SKILL.md`

## Impact
**Medium** — a feature-behavior ambiguity (an ambiguous natural-language request could route to the wrong delegation plugin), not a crash or data-loss risk, but affects both plugins' correctness and could silently produce the wrong model's output for a request.

## Additional Context
Discovered and deferred during the `antigravity-kit` plugin transfer (branch `feat/add-antigravity-kit`), per an explicit decision to scope that PR in-plugin-only. Suggested fix direction (not a mandate): add a reciprocal "When NOT to Use"-style exclusion to `plugins/antigravity-kit/skills/antigravity/SKILL.md` and to the 3 named `codex-kit` skills, each naming the sibling and the distinguishing criterion, per the existing pattern already used for `antigravity`/`migrate-to-antigravity`'s own sibling exclusion and for `git-kit`'s `gh-operations`/`collaborating-on-a-pr` pair.
