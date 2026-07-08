# Self-Critique and Self-Reflection Framework

## Self-Critique Question Sets

Self-critique targets concrete execution failures — not hypothetical improvements.

### Universal questions (apply to every category)
- What did this component produce that was incorrect, incomplete, or later corrected?
- What condition should have triggered this component but didn't (or vice versa)?
- What step was defined in the component's workflow but not executed in this session?
- What assumption turned out to be wrong?

### Skills
- Did the skill emit its completion marker before all required gates passed?
- Did pre-analysis catch all size, chain, and pattern violations — or were some found only later by a reviewer?
- Were BATCH 2 questions asked for every finding the pre-analysis flagged?
- Did the skill invoke all required sub-skills (e.g., plugin-rulebook before finalizing)?

### Sub-agents
- Did any finding require external knowledge to verify that the agent didn't have?
- Were findings labeled Unverified when they should have been, or asserted as Major/Critical when uncertain?
- Did the agent read all relevant files (including `workflows/*.md`) or only files linked from SKILL.md?

### Commands
- Was the command output validated before it was used downstream?
- Were destructive actions (deletions, overwrites) confirmed before execution?
- Did the command handle the case where expected input files were absent?

### Workflow-skills
- Did each phase produce its exit artifact before the next phase started?
- Was any phase skipped under time or context pressure?
- Did the workflow link to a `references/` file as an action step (chain violation)?

### Rules
- Was the rule text unambiguous when applied to the observed case?
- Was the rule loaded at the right point in the workflow (not too late to affect the outcome)?
- Did the rule produce a correct severity assignment for each violation?

## Self-Reflection Question Sets

Self-reflection targets systemic patterns and alternative approaches — not point fixes.

- If this component were redesigned from scratch knowing what happened in this session, what would change first?
- What pattern repeated across multiple components? Does it point to a shared root cause?
- Which failure would have been caught by a gate that doesn't yet exist?
- What did the user have to do manually that the component should have done automatically?
- What would a reviewer catching this failure say is the root cause — design flaw, missing check, or wrong threshold?

## Rationalizations to Reject

These thoughts signal a weak critique. Reject them and push for a concrete finding:

- "It mostly worked" — identify what the "mostly" hides
- "That was an edge case" — edge cases are exactly what gates exist for
- "The user caught it" — if the user had to catch it, the component failed
- "It was good enough for this session" — if a reviewer would flag it, it is not good enough
- "The reviewer would have caught it anyway" — the reviewer is a safety net, not the intended detector
