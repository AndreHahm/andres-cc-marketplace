## Summary
`skill-development` should name `prompt-library` back: the pointer between the two skills is one-way (plugin-rulebook R36, reciprocal exclusions).

## Environment
- **Product/Service**: Claude Code plugin marketplace (`andres-cc-marketplace`)
- **Region/Version**: branch `feature/promptlibrary-kit-wave0` (promptlibrary-kit Wave 0)

## Reproduction Steps
1. Open `plugins/promptlibrary-kit/skills/prompt-library/SKILL.md`. Its When NOT to Use and Quality gates send content that needs scripts or tools to `skill-development`.
2. Open `plugins/plugin-devkit/skills/skill-development/SKILL.md` and search for `prompt-library`.

## Expected Behavior
Per `plugin-rulebook` R36 (Reciprocal Exclusions, ADVISORY) and `.claude/rules/resolve-activation-overlap-bidirectionally.md`, `skill-development` names `prompt-library` back and states its half of the distinguishing criterion, not a bare see-also:
- `skill-development` creates skills: content that needs scripts, tools or bundled files.
- `prompt-library` stores plain reusable instruction text in a project catalog.

Its When NOT to Use (or description) should say to use `prompt-library` when the content is plain reusable instruction text with no script or tool needs. Mirror copies stay in sync, and an R36 re-check comes back clean.

## Actual Behavior
`skill-development` never mentions `prompt-library`, so a request that is really "save this reusable text" has no pointer away from skill creation.

## Impact
**Low** - Advisory finding; documentation consistency only, no functional break.

## Additional Context
Found during the promptlibrary-kit Wave 0 work. Suggested labels: `t: documentation`, `a: ai-setup`.
