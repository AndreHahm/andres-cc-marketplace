# Suggestion Taxonomy

## Priority Tiers

| Priority | Label | Definition | Example |
|---|---|---|---|
| P1 | Critical | Prevents correct behavior; causes wrong output or missed failures | Completion marker emitted before reviewer confirms clean |
| P2 | Major | Significantly degrades quality or coverage; fix soon | Pre-analysis doesn't scan `references/*.md` for size violations |
| P3 | Minor | Polish, optimization, or low-impact enhancement | Lower a threshold from 80 to 50 lines |

**Assignment rule:** If the observed failure shipped bad output to the user or a downstream component, it is P1. If it degraded quality but was caught and corrected, it is P2. If it was never noticed but would improve behavior, it is P3.

## Suggestion Types

| Type | When to use | Example |
|---|---|---|
| `FIX` | Corrects a behavior that is currently wrong | Fix: completion marker must not emit while any C/M finding remains |
| `ENHANCE` | Improves existing behavior without changing its purpose | Enhance: expand security scan to include substitution-variable audit |
| `ADD` | Adds a missing capability, gate, check, or section | Add: AskUserQuestion pattern detection to pre-analysis |
| `REMOVE` | Eliminates harmful, redundant, or misleading content | Remove: duplicate suggestion S03 (same fix as S01, different component) |
| `AUDIT` | Schedules a future review when a fix cannot be made now | Audit: recheck thresholds after the next relevant convention change |

## Merge Rules

Apply these before emitting the final suggestion list:

1. **Identical fix, different components** → emit one cross-cutting suggestion; list all affected components in `Detail`.
2. **Same root cause, different symptoms** → emit one suggestion targeting the root cause; reference the symptoms.
3. **P3 suggestions that restate a P1/P2 suggestion** → drop the P3; the higher-priority entry covers it.
4. **Two AUDIT suggestions for the same dependency** → merge into one; include all affected rules/components.

## Output Format

See SKILL.md's Phase 5 for the literal per-suggestion template (`[S##] [P1|P2|P3] [TYPE]` / `Source:` /
`Detail:`) — not repeated here to avoid two copies drifting apart. The examples below show it applied.

Example:
```
[S01] P1 FIX  Gate <completion-marker> on reviewer pass
Source: Weakness   Component: skill-improver
Detail: The finalize step must call its own reviewer sub-step and iterate until no C/M findings
remain before emitting the completion marker. Emitting early produces false closure and ships
unresolved issues.
```

## Cross-Cutting Suggestion Example

When the same pattern appears in multiple components:

```
[S07] P2 ADD  Missing-input warning in authoring guidelines
Source: Weakness   Component: skill-builder, skill-improver (input-validation scan)
Detail: Both skills lack author-facing guidance that unvalidated user-supplied paths are
silently accepted. Add a Gotcha in skill-builder and a matching check in skill-improver's
validation scan.
```

## Classification Checklist

Before finalizing each suggestion:
- [ ] Priority reflects actual session impact, not worst-case hypothetical
- [ ] Type matches the nature of the change (not every suggestion is a FIX)
- [ ] Detail names the specific file, section, or step to change
- [ ] Merged duplicates rather than emitting near-identical entries
- [ ] AUDIT suggestions include a trigger condition (when to audit, not just that it should be audited)
