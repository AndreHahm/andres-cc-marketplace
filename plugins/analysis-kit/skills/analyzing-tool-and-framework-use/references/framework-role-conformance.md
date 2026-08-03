# Framework Role-Conformance

This checklist applies to any detected framework that pairs an authoritative **Governing Method** (owns goals, scope, specifications, architecture, decision records, state, gates, approvals, closure) with a subordinate **Execution Companion** (assists with discussion, planning, implementation, verification, shipping prep — but never governs). Not every framework in `assets/framework-signatures.json` defines this pairing; skip Phase 4 of `SKILL.md` entirely for one that doesn't.

## Generic Checks

Apply these regardless of which specific framework was detected — adapt the wording to the project's own artifact names.

### Authority checks

Detect whether the execution companion:

* introduces a new project goal;
* alters approved scope or non-goals;
* invents requirements;
* treats its own derived requirements file as authoritative;
* changes governing-method state outside an approved transition;
* claims a gate has passed without governing-method evaluation;
* approves a specification, decision record, release, or breaking change;
* treats its own phase completion as governing-method phase completion;
* treats its own "ship" action as change closure;
* modifies governing artifacts to fit its own generated output.

### Artifact checks

Compare the execution companion's derived artifacts with authoritative governing-method artifacts for:

* duplicated or contradictory requirements;
* extra or omitted scope;
* changed priorities;
* invented dependencies;
* conflicting state or completion claims.

### Process checks

Detect:

* execution before the governing method's pre-build readiness gate;
* shipping before the governing method's completion-verification gate;
* auto-advance behavior;
* uncontrolled transition from discussion/exploration to production changes;
* companion-generated plans not reviewed against governing-method plans;
* repeated correction of companion-generated scope.

## Per-Framework Notes

| Framework | Confidence | Notes |
|---|---|---|
| GG-SAD (as Governing Method) + GSD (as Execution Companion) | Medium | Sourced from this project's own concept draft (`.ggsad/config.yaml`, `.planning/` as GSD's derived-artifact directory, `/gsd-ship` as GSD's own ship command). Not independently verified against GG-SAD's or GSD's own published documentation — treat as a working draft, not a confirmed spec. |
| GSD (standalone, no detected governing method) | N/A | If GSD is detected without a governing method also being detected, the generic checks above don't apply — there's no authoritative artifact set to compare against. Report GSD as a standalone execution companion only, and note that role-conformance analysis needs a governing method to be meaningful. |
| OpenSpec, Speckit, BMAD | Unconfirmed | No role-conformance rule set has been written for these yet — their entries in `assets/framework-signatures.json` only support detection (marker paths), not conformance checking. Phase 4 must be skipped for these until a rule set is added here, based on the real tool's actual documented governance model. |
| Any framework not in `assets/framework-signatures.json` (the "other frameworks" case) | N/A | No detection support and no rule set. `SKILL.md`'s Phase 2 records the user's stated framework name as a finding only. |

## Extending This File

Adding real conformance checks for a new framework requires reading that framework's own documentation first — do not infer its governance model from its name or from GG-SAD's own model by analogy. A framework that looks similar on the surface (goal-gated, spec-driven) can define entirely different gate names, artifact ownership rules, or companion boundaries.
