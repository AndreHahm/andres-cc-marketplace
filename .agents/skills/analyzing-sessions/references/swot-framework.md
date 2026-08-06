# SWOT Framework

## Quadrant Prompts

Ask these questions when evidence is thin for a quadrant. Adapt to the component category.

**Strengths** — what the component did well in this session:
- What outputs were accepted without correction?
- What steps ran without needing a retry or override?
- Which gates or checks produced genuine value?

**Weaknesses** — where the component fell short:
- What did the component miss that it was responsible for catching?
- What steps produced wrong output, required correction, or were skipped?
- What thresholds, patterns, or checks were absent but needed?

**Opportunities** — what would make the component more effective:
- What check could be added to catch the observed failure earlier?
- What workflow step is missing from the happy path?
- What existing behavior could be tightened (lower threshold, stricter pattern)?

**Threats** — what external factors could cause future failure:
- What upstream files or components does this one depend on? Could they drift?
- What session conditions are this component not designed to handle?
- What happens if a dependency changes without this component being updated?

## Category-Specific Patterns

### Skills
- Strengths: correct trigger recognition, accurate pre-analysis, sound CREATE→LINK→DELETE content-move sequencing (see `skill-refiner-interactive/references/movement-pattern.md` for this specific pattern's full definition — create the destination, verify it, only then delete the source)
- Weaknesses: a finalization signal (e.g. a skill's own completion marker) emitted before required gates passed; an initial scan step missed reference sizes; a threshold configured too loose
- Opportunities: add missing gate, lower threshold, expand scan scope
- Threats: upstream size-limits.md changes break threshold alignment; a reviewer step not invoked after an editing step that should have triggered it

### Sub-agents
- Strengths: findings were accurate and high-value; severity assignments were consistent
- Weaknesses: false positives from unverifiable findings; non-deterministic coverage (judgment-based, not checklist-driven)
- Opportunities: add explicit checklist item for the missed check; add fast-path mode
- Threats: cost discourages use; caller skips the agent if the invoking skill declares complete first

### Commands
- Strengths: produced expected artifact with correct format
- Weaknesses: missing validation step, no confirmation gate before destructive action
- Opportunities: add pre-flight check, add dry-run mode
- Threats: relies on file paths that may change if plugin structure evolves

### Workflow-skills
- Strengths: multi-step coordination succeeded; handoff between phases was clean
- Weaknesses: a phase was skipped under time pressure; output not validated before next phase consumed it
- Opportunities: add a gate between phases; add explicit success criteria per phase
- Threats: chain violations (workflow links to reference instead of being self-contained)

### Rules
- Strengths: rule was loaded and applied consistently; violations were flagged at the right severity
- Weaknesses: rule text is ambiguous; rule targets the wrong scope; rule was not loaded when needed
- Opportunities: tighten rule language; add example violations; change scope or trigger
- Threats: rule becomes stale if the pattern it targets evolves in the codebase

## Common SWOT Anti-Patterns

- **Strength-washing**: listing design features as strengths when they weren't exercised in the session. Only count observed behavior.
- **Opportunity inflation**: listing every possible enhancement as an opportunity. Only list what would have changed the session outcome.
- **Threat conflation**: filing a weakness (internal failure) as a threat (external risk). Keep them separate.
