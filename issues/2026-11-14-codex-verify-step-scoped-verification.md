## Summary
codex-verify has no step-scoped mode: a request to verify one step of a plan reviews the whole document and returns a document-wide verdict.

## Environment
- **Product/Service**: codex-kit `codex-verify` (`SKILL.md` "When to Use", blind payload, verdict rule)
- **Region/Version**: found in PR #726 at head `00f0a4728b919c29aabd3ec2850d558acf8909ab`

## Reproduction Steps
1. Read `plugins/codex-kit/skills/codex-verify/SKILL.md` "When to Use" (lines 44-45): it accepts "verify step 3 of plan.md".
2. Read the blind payload (around lines 127-145): it tells Codex to review the entire document and names no step.
3. Read the verdict rule (around lines 322-338): any P1 issue anywhere fails the run.

## Expected Behavior
A request to verify one step returns a verdict on that step (and the steps it depends on), with the whole plan kept as context.

## Actual Behavior
The whole document is reviewed and the verdict is document-wide, so an unrelated broken step 8 can fail a request about step 3. PR #726 changed the skill text to say this plainly and points here.

## Error Details
~~~
None: a capability gap, not an error.
~~~

## Visual Evidence
None.

## Impact
**Low** - The verdict is stricter than asked, never looser: a step request can fail on an unrelated step, but a broken requested step still fails.

## Additional Context
Suggested fix: for an explicit step request, pass the step number and a scoped task instruction in the blind payload, keep the full plan as context, and make the verdict refer to the requested step and its dependencies; keep the existing whole-document path for ordinary verification. Add an eval scenario for it (see also #728).

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/726
- **Head SHA**: `00f0a4728b919c29aabd3ec2850d558acf8909ab`
- **Thread**: review comment 4571948459 (`plugins/codex-kit/skills/codex-verify/SKILL.md`, lines 44-45)
- **Reviewer**: Devin Review
- **Severity**: Minor (yellow)

Found in PR #726.
