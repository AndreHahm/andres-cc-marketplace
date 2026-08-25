# Evidence Routing (Entry Route B)

Use this reference when conception starts from observed session behavior or artifacts rather than a rough
idea. Session evidence **seeds** the concept — it never defines its scope on its own, and it never
becomes approved work without an explicit human decision.

## Evidence Sources

- session-analysis reports and their prioritized suggestions;
- build handoff reports and reverified open items;
- validation, grading, comparison, security, completeness, or consistency findings;
- user corrections, repeated clarification, tool or permission friction, and abandoned work;
- durable planning artifacts produced during prior sessions.

## The 6-Step Evidence-Handling Procedure

1. **Identify the observed behavior and its source.** Record which artifact, session, or report each
   piece of evidence comes from — never carry forward an unsourced claim.
2. **Recheck that the issue or opportunity still exists in the current marketplace.** Do not promote an
   artifact's open item or conclusion without checking the current target — a finding that was true when
   the source report was written may already be resolved.
3. **Separate symptoms from the underlying user need.** A repeated friction point (e.g. "the user had to
   ask twice") often points at a deeper need (e.g. "the description doesn't state the trigger clearly")
   rather than being the need itself — state both, and prefer designing against the underlying need.
4. **Merge duplicate evidence that supports the same concept.** Multiple observations pointing at the same
   root cause become one normalized observation, not separate line items competing for attention.
5. **Discard stale, already-resolved, or non-actionable observations.** Record why each was discarded
   (stale / resolved / duplicate / non-actionable / out of scope) rather than silently dropping it —
   a decision to discard is itself a recorded decision.
6. **Obtain explicit approval before promoting evidence into a planned change.** Evidence is data, not a
   mandate — the human always decides whether the candidate concept actually gets promoted into a
   Conception Brief.

## Fallback

If evidence is insufficient to classify or define the concept after Steps 1-5, fall back to the same
focused interview Entry Route A (from scratch) uses — do not require the user to run a full retrospective
unless the desired concept explicitly depends on retrospective coverage. Most evidence-derived concepts
classify as Enhance, Repair, or Consolidate rather than Create.

## Human Selection Gate

Never promote a candidate concept automatically, regardless of how strong the evidence looks.

When this skill is invoked directly (not via `plugin-lifecycle-maintenance`'s workflows), this is the
only selection gate that runs: present the candidate via `AskUserQuestion` and record the decision
(Promote / Revise / Merge / Defer / Reject / Retain), the decision owner, and the rationale.

When this skill is invoked as the Conceive step inside `plugin-lifecycle-maintenance`'s
`improve-a-plugin`/`enhance-a-plugin` workflows, the human has already picked which finding(s) to act on
at that workflow's own `AskUserQuestion` gate before Conceive ever runs — this section's gate is not a
second, redundant ask on the same already-approved evidence. **This skill still produces exactly one
classification and one candidate concept per invocation, matching its own one-candidate-per-invocation
contract (SKILL.md, Entry Route B)** — if separating symptoms from underlying need in Step 1 (normalize)
surfaces a second, genuinely distinct concept hidden inside the same evidence item, do not fold it into
this invocation's own brief: classify and brief the primary concept the caller actually asked about, and
report the second one back to the caller as a separately-discovered candidate for its own future
invocation, not as an additional output of this run.
