# Conflict Taxonomy

## Categories

### Agent-vs-agent

Two agents dispatched in the same scope reach contradictory conclusions about the same subject (e.g. one says a check passed, another says the same check failed). Detection: cross-reference agent findings that touch the same file, component, or claim.

### Rule-vs-rule

Two of the project's own `.claude/rules/*.md` files give contradictory guidance for the same situation. Detection: for each rule pair with overlapping scope (same file type, same trigger condition), check whether following one would violate the other.

### Spec-vs-code

An in-scope implementation contradicts an explicit statement in a spec, plan, or architecture document read during the session (e.g. a stated non-goal was implemented anyway). Detection: surface-level only — flag an observed contradiction, don't build a full requirement-to-implementation graph.

### Session-vs-session

A prior session's persisted report (if in scope) states a decision or finding that this session's actions contradict without acknowledging the change. Detection: compare this session's decisions against the prior report's stated conclusions on the same topic.

## Severity Guidance

- A conflict that produced incorrect shipped output is more severe than one caught and corrected within the same session.
- A conflict between two rules is a defect in the rules themselves (report it as a governance finding, not an agent-behavior finding) — see `analyzing-actor-behavior` for actor-level behavior instead.
