# Actor Behavior Taxonomy

## Agent-Behavior Signals

- **Finding accuracy** — did the agent's findings hold up, or were they later contradicted by a direct check?
- **Dispatch appropriateness** — was a purpose-built agent available for the task, or was a broad `general-purpose`/`Explore` dispatch used where a narrower option existed?
- **Scope discipline** — did the agent stay within the task it was given, or did it expand scope unprompted?
- **Confidence calibration** — did the agent mark genuinely uncertain findings as unverified, or assert them with false confidence?
- **Follow-through** — did the agent complete the dispatched task, or return partial/abandoned work without saying so?

## Human-Behavior Signals

- **Correction rate** — how often did the human have to fix or redirect agent output, and how severe were the corrections (phrasing vs. wrong conclusion)?
- **Decision friction** — did the same question or choice require multiple rounds of back-and-forth before resolving?
- **Unprompted contribution** — did the human do work or make a decision no agent proposed?
- **Approval pattern** — did the human approve gate questions quickly and consistently, or repeatedly push back on the same class of request (a signal the gate itself may be miscalibrated, not a human-behavior defect)?

## Common Anti-Patterns

- **Correction-count inflation** — counting every minor phrasing tweak as equivalent to a substantive correction. Weigh by what was actually fixed.
- **Attributing a systemic issue to one actor** — if the same failure pattern recurs across multiple agents, it's more likely a shared root cause (a missing gate, an ambiguous instruction) than several independent actor failures.
