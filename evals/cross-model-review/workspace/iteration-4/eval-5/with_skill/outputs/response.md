# Confidence tier: Low / contested — refutation always wins over Phase 1 agreement

## Answer

The skill assigns this finding **Low / contested**, not High. Explicit Phase 2 refutation overrides Phase 1 agreement between the two models, full stop. The skill states this resolution rule explicitly, by name, precisely to cover the scenario in the question.

## Where the skill says so

### 1. The explicit tie-breaking sentence in Phase 3

`## Phase 3 — Synthesize and report (no auto-fix)` contains the exact rule, stated as a general principle before the tier list is even introduced:

> "Merge, dedupe (same file + overlapping lines + same root cause = one finding), assign confidence.
> **An explicit Phase 2 refutation always wins, regardless of Phase 1 agreement** — if both models
> independently raised the same issue in Phase 1 but a Phase 2 pass then explicitly refutes it (e.g.
> tracing additional evidence that disproves it), the finding drops to Low/contested; Phase 1 agreement
> alone never keeps it at High once refuted. Apply the tiers below in this order — Low/contested first:"

This is worded almost identically to the scenario in the question — both models raising the same issue in Phase 1, followed by a Phase 2 pass that explicitly refutes it by tracing additional evidence — and states the resolution in plain terms: the finding **drops to Low/contested**, and Phase 1 agreement **never** keeps it at High once refuted.

### 2. The tier definitions themselves, and their evaluation order

The skill doesn't just state the rule once in prose — it structures the tier list itself so the refutation check is evaluated *before* the agreement check, and says so explicitly ("Apply the tiers below in this order — Low/contested first"):

> - **Low / contested** — a Phase 2 pass explicitly **refuted** the finding, whether it was raised by
>   one side or independently by both in Phase 1. Keep it, show both sides (including the original
>   Phase 1 agreement if there was one), let the human judge. Never silently drop a contested finding.
> - **High** — both models' Phase 1 passes independently raised the same underlying issue with no
>   subsequent Phase 2 refutation, OR one raised it in Phase 1 and the other's Phase 2 pass explicitly
>   confirms it.

Note the High tier's own wording: it requires "no subsequent Phase 2 refutation" as part of its own definition — so a refuted finding structurally cannot qualify for High even on its own terms, independent of the ordering instruction. The Low/contested tier explicitly folds in the "raised by... both in Phase 1" case, which is exactly the question's scenario, and its handling instruction is to **keep and show both sides**, not drop it — "including the original Phase 1 agreement if there was one" is the skill's own parenthetical acknowledging this exact case.

### 3. A critical-severity carve-out doesn't apply here, but is worth noting

Immediately after the tiers:

> "A `severity: critical` finding is never silently dropped regardless of confidence tier — surface
> it with its tier clearly marked, even at Low/contested."

This confirms the mechanism is "keep at Low/contested and surface transparently," never "silently drop" — a refuted finding stays visible in the report at whatever severity it carries, just tagged with the lower confidence tier, so the human reviewer still sees it and can judge for themselves.

### 4. Quality gate checklist confirms this as a mandatory, testable behavior

The `## Testing & Validation` → `**Quality gates:**` checklist restates the rule as a checkable gate, using near-identical language to the Phase 3 prose:

> "- [ ] A finding both models raised in Phase 1 but a Phase 2 pass later explicitly refuted is always
>       reported at Low/contested — Phase 1 agreement alone never keeps it at High once refuted"

This is listed as one of the skill's own self-verification criteria, meaning a run that instead reported such a finding as High would be considered a skill failure, not an acceptable interpretation.

### 5. A concrete test scenario in the same section

The `**Concrete scenarios to check:**` list includes:

> "4. A finding raised in Phase 1 by only one side and explicitly refuted in that side's Phase 2 pass →
>    reported as Low/contested with both sides shown, never dropped."

This scenario is the single-sided variant (one model raises it, the *other's* Phase 2 challenger refutes it), not the exact both-agreed variant from the question — but it's governed by the same "whether it was raised by one side or independently by both in Phase 1" clause in the Low/contested tier definition, and demonstrates the same underlying mechanism: refutation controls the outcome regardless of how the finding originated in Phase 1.

## How the skill resolves the tension conceptually

The skill's opening framing explains *why* this ordering makes sense, not just *that* it applies:

> "A finding's confidence comes from whether it survives that cross-examination. This kills the two
> failure modes of solo LLM review: self-ratification (a model won't critique its own work) and
> confident false positives."

Phase 1 agreement between two independently-reviewing, different-vendor models is meaningful signal (it rules out one model's idiosyncratic error), but it is explicitly *not* the same as correctness — the skill's own closing line under Phase 3 makes this the skill's stated philosophy:

> "Convergence between the models is not correctness — the job here is to surface a ranked,
> cross-examined list, not to declare the diff clean."

Phase 2's challenger pass exists specifically to add a second, adversarial check *on top of* Phase 1 agreement — tracing additional evidence a fresh-eyes pass wouldn't necessarily have surfaced. If that adversarial check produces an explicit refutation backed by new evidence, the skill treats that as stronger, more specific signal than mere initial agreement, which could itself just be two models sharing the same blind spot (the "confident false positives" failure mode the skill exists to catch). So the resolution is not "average the two signals" or "let the higher one win" — it is a strict, ordered override: refutation invalidates the High-confidence path outright and forces Low/contested, while still preserving the original agreement in the report ("show both sides") so the human — who does the final judging per Phase 3's closing instruction ("End by asking which findings, if any, to fix") — has the full history to weigh, rather than either side's verdict being silently hidden.

## Summary

| Aspect | Skill's answer |
|---|---|
| Assigned tier | **Low / contested** |
| Governing rule | Phase 3, "An explicit Phase 2 refutation always wins, regardless of Phase 1 agreement" |
| Tier definition | Low/contested tier explicitly covers "raised by one side or independently by both in Phase 1" then refuted |
| Evaluation order | Tiers applied "Low/contested first" — refutation checked before agreement |
| Disclosure | Never silently dropped; both sides (original agreement + refutation) shown; even `critical` severity stays visible at this tier |
| Enforced by | A dedicated quality-gate checklist item, plus concrete scenario #4 |
