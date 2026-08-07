# using-plugin-devkit — Response Transcript

**User task:** "I want to audit my plugin for quality issues but I'm not sure which plugin-devkit tool handles that."

This request names no specific plugin-devkit skill or pipeline — a bare "I'm not sure which tool handles that" — so it matches `using-plugin-devkit`'s own "When to Use" criteria exactly. Following the skill's phases in order, without deviation.

---

## Phase 1: Pick an Entry Point

Per the skill: `AskUserQuestion` — question "What are you trying to do with plugin-devkit?" (pre-highlight the option matching `$ARGUMENTS`, if any).

`$ARGUMENTS` here is effectively "audit my plugin for quality issues," which maps most directly to the second option, so that option is pre-highlighted.

### AskUserQuestion call #1 (as I would make it)

```
question: "What are you trying to do with plugin-devkit?"
options:
  1. label: "Build something new"
     description: "A plugin or component from scratch, or resuming from an existing
       Concept Card/Plan → plugin-lifecycle-upstream. For one already-well-understood
       single component, skip straight to the matching Design skill instead
       (skill-development, agent-development, command-development, hook-development,
       rule-development) — the pipeline's overhead isn't worth it for one obvious skill."

  2. label: "QA or audit an existing plugin"   [PRE-HIGHLIGHTED / RECOMMENDED]
     description: "Rule compliance, structural validation, a weighted quality score, or
       all three combined → plugin-lifecycle-downstream. For just a compliance check on
       one component, use Skill(plugin-rulebook) directly; for just a score with no
       separate Validate step, use plugin-grader directly."
     # Recommended because the user's own wording — "audit my plugin for quality
     # issues" — matches this option's description almost verbatim.

  3. label: "Fix or improve something based on a finding"
     description: "Acting on an analyzing-sessions retro or a plugin-comparison result,
       or an on-demand self-check → plugin-lifecycle-maintenance. For a single
       already-known fix, edit directly or use the matching Design skill; for a
       lightweight single-change 'should this propagate' decision, use skill-maintenance
       instead."

  4. label: "Not sure / something else"
     description: "Describe the actual need in a follow-up instead of forcing it into
       one of the three pipelines."
```

**Assumption (labeled, since this is a blind non-interactive test):** the user picks **option 2, "QA or audit an existing plugin,"** consistent with their stated wording. Proceeding under this assumption.

**Phase 1 exit condition met:** exactly one of the three pipelines selected — `plugin-lifecycle-downstream`.

---

## Phase 2: Confirm Before Dispatch

Per the skill, this phase is mandatory even though Phase 1's answer seems unambiguous — a wrong pipeline caught here is free.

### AskUserQuestion call #2 (as I would make it)

```
question: "Run plugin-lifecycle-downstream for this?"
options:
  1. label: "Run it"   [RECOMMENDED]
     description: "Proceed to dispatch plugin-lifecycle-downstream now."
  2. label: "Change my answer"
     description: "Go back to Phase 1 and pick a different entry point."
  3. label: "Cancel"
     description: "Stop here without dispatching anything."
```

**Assumption (labeled):** the user selects **"Run it."** Proceeding under this assumption.

---

## Phase 3: Dispatch

Per the skill: invoke the confirmed pipeline via `Skill`, passing `$ARGUMENTS` through as its own argument if the pipeline accepts one. Let it run to completion — `plugin-lifecycle-downstream` manages its own phases (Validate → Audit → Report → optional Fix), gates, and reporting from here.

**This is the point where `Skill(plugin-lifecycle-downstream)` would be invoked**, passing through the original context ("audit my plugin for quality issues"). Per the test instructions, I am not actually invoking it — stopping here, at the moment `using-plugin-devkit`'s own job (Phases 1–2) is complete and control would hand off to the dispatched pipeline.

**Phase 3 exit condition met:** the dispatched pipeline has taken over (hypothetically, under the assumed answers above).

---

## Summary of what this skill run determined

- Entry point selected: **QA or audit an existing plugin**
- Pipeline chosen: **`plugin-lifecycle-downstream`**
- Confirmed via Phase 2 gate before any dispatch
- Handoff point: `Skill(plugin-lifecycle-downstream)` — not actually invoked in this blind test, per test harness instructions
