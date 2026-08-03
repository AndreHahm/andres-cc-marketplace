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
- Were all required follow-up interview questions (e.g. a second batch of `AskUserQuestion` prompts) asked for every finding the pre-analysis flagged, not just the first batch?
- Did the skill invoke all required validation or gating sub-skills it depends on before finalizing its output?

### Sub-agents
- Did any finding require external knowledge to verify that the agent didn't have?
- Were findings labeled Unverified when they should have been, or asserted as Major/Critical when uncertain?
- Did the agent read all relevant files (including any `workflows/*.md`) or only files linked from its top-level definition?
- **If this dispatch was a general-purpose or broad exploratory agent, was there a narrower purpose-built agent, skill, or direct tool call that could have handled the task instead?** A broad, general-purpose dispatch carries the heaviest fixed cost of any dispatch option — full tool-schema injection plus re-deriving any task-specific procedure from scratch, with no cached, purpose-built knowledge of the task's own domain. Not every broad dispatch is a finding: a genuinely exploratory, multi-step search with no dedicated tool or agent for the task is a legitimate use, and flagging the dispatch choice alone (with no cheaper alternative actually available) is noise, not signal. Flag as a `P2 ENHANCE` only when a narrower alternative plausibly existed for the specific task that was dispatched.

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
- **(Skill/Sub-agent components only) Did every trigger phrase stated in the description or `## When to invoke` actually match at least one real invocation across the analyzed session range?** A phrase present but never once exercised is a candidate for removal, consolidation, or rewording (`REMOVE`/`ENHANCE`) — but distinguish a genuinely dead phrase from a legitimate rare/emergency-only trigger that simply hasn't come up yet in a short session range; flag with lower confidence (note it `⚠️ Unverified`, not a firm finding) when the analyzed range is short relative to the component's expected invocation frequency.
- **Did the user (or Claude) run the same or near-identical Bash command, background task, or subprocess 3+ times across the session** — a repeated manual pattern a dedicated agent or skill could have automated? Note the pattern, its repeat count, and what a dedicated component would do differently, as a candidate `ADD` suggestion — not just as a one-off observation buried in a single component's critique. This extends the "what did the user have to do manually" question above into a concrete, countable signal rather than a vague impression.

A suggestion proposing a **brand-new** component (from the pattern-mining axis above) has no existing `Component:` name to cite — write `Component: (proposed new agent/skill — see Detail)` and name the repeated pattern, its observed repeat count, and which existing component (if any) it's adjacent to, in `Detail`.

## Rationalizations to Reject

These thoughts signal a weak critique. Reject them and push for a concrete finding:

- "It mostly worked" — identify what the "mostly" hides
- "That was an edge case" — edge cases are exactly what gates exist for
- "The user caught it" — if the user had to catch it, the component failed
- "It was good enough for this session" — if a reviewer would flag it, it is not good enough
- "The reviewer would have caught it anyway" — the reviewer is a safety net, not the intended detector
