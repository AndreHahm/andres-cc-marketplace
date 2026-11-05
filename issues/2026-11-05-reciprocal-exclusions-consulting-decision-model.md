## Summary
`consulting-decision-model` (decision-kit) excludes three sibling skills by name, but none of them names it back.

## Environment
- **Product/Service**: git-kit `cross-model-review`; codex-kit `codex-peer-review` and `codex-verify`
- **Region/Version**: after `feature/decision-kit` merges

## Reproduction Steps
1. Read "When NOT to Use" in `consulting-decision-model`: it names all three siblings.
2. Search each sibling's `SKILL.md` for `consulting-decision-model`: there are no matches.

## Expected Behavior
Each sibling's "When NOT to Use" carries its half of the criterion, as `resolve-activation-overlap-bidirectionally` asks.

## Actual Behavior
The exclusion runs one way, so a request landing on a sibling has nothing that defers to `consulting-decision-model`.

## Proposed Change
Add one line to each sibling, then sync the `.claude` mirrors:

| Sibling | Keeps | Defers to `consulting-decision-model` |
|---|---|---|
| `cross-model-review` | A diff | One action or choice Claude is about to execute |
| `codex-peer-review` | A design or recommendation to present | One action or choice Claude is about to execute |
| `codex-verify` | A written plan or document | One step of a plan that Claude is about to execute |

## Impact
**Low** - R36 ADVISORY. No live misfire is recorded. `authority-reviewer` rated the one-way exclusion Major in the decision-kit QA run because no live collision had been ruled out.

## Additional Context
Blocked until `feature/decision-kit` merges, because the target skill does not exist on `main` yet.
