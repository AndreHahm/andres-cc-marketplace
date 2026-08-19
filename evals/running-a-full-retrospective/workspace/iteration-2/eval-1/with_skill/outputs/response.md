# Task: "run a full retrospective and consolidate the findings, then fix what it finds"

This maps to the `running-a-full-retrospective` skill. Below is exactly what I would do, in order,
for Phase 1 (Pick Analyses and Scope), followed by a short note on how the later phases the user's
request implies ("then fix what it finds") are actually handled per the skill's own stated flow.

## Before Phase 1: routing check

The request names no specific analysis type and explicitly asks for several analyses consolidated
into one list ("run a full retrospective ... consolidate the findings") — this is exactly
`running-a-full-retrospective`'s trigger, not `starting-an-analysis` (single type) or
`reviewing-analysis-findings` (cross-checking reports that already exist). I'd invoke
`Skill(running-a-full-retrospective)` directly.

The skill's own guardrail applies immediately: **this must run interactively in the live
conversation thread** — no `Agent`/forked/background dispatch for Phase 2 or Phase 5, and if
`AskUserQuestion` isn't available when Phase 5 would start, I stop and say so rather than
substituting my own judgment.

## Phase 1: Pick Analyses and Scope

The skill requires two things asked "in one guided pass," with the 5-analysis question split across
two `AskUserQuestion` questions in the **same call** (hard cap is 4 options per question; a single
5-option question fails outright with `InputValidationError`). Scope is asked once, reused verbatim.

I would issue one `AskUserQuestion` call containing three questions: two for analysis selection
(3 options + 2 options, per the skill's own suggested split — 3 in the first, the remaining 2 plus a
"None of these" filler in the second), and one for scope. Concretely:

```json
{
  "questions": [
    {
      "question": "Which analyses should run (part 1 of 2)? Select any that apply.",
      "header": "Analyses A",
      "multiSelect": true,
      "options": [
        {
          "label": "Plugin components",
          "description": "analyzing-plugin-components — SWOT/self-critique per skill, agent, command, rule active in the range; improvement backlog grouped by component."
        },
        {
          "label": "Tool & framework use",
          "description": "analyzing-tool-and-framework-use — inventories external tools actually invoked, detects dev framework(s) in use, evaluates role-conformance."
        },
        {
          "label": "Actor behavior",
          "description": "analyzing-actor-behavior — assesses subagent decision quality/consistency, human vs. agent contribution, and cross-agent handoff patterns."
        }
      ]
    },
    {
      "question": "Which analyses should run (part 2 of 2)? Select any that apply.",
      "header": "Analyses B",
      "multiSelect": true,
      "options": [
        {
          "label": "Governance & conflicts",
          "description": "analyzing-governance-and-conflicts — rule/boundary/convention conformance, agent-vs-agent and rule-vs-rule conflicts, recurring mistakes."
        },
        {
          "label": "Recurring patterns",
          "description": "mining-recurring-patterns — repeated action sequences/loops, recall gaps, repeated-question patterns, subagent token/time usage."
        },
        {
          "label": "None of these",
          "description": "Don't add any analyses from this group."
        }
      ]
    },
    {
      "question": "What scope should every chosen analysis run over? (used verbatim for all of them — not re-asked per type)",
      "header": "Scope",
      "multiSelect": false,
      "options": [
        {
          "label": "This conversation",
          "description": "Scope every chosen analysis to the current session only."
        },
        {
          "label": "Today",
          "description": "Scope every chosen analysis to today's date."
        },
        {
          "label": "Custom date/range",
          "description": "I'll type a specific date or date range to use as the shared scope."
        }
      ]
    }
  ]
}
```

Notes on why it's structured this way:
- The first two questions together cover all 5 analysis-kit skills named in the SKILL.md, each
  option's description drawn from that skill's own one-line purpose, per the skill's instruction.
- `multiSelect: true` on both analysis questions, since the user can pick any combination across the
  two groups (e.g. "Plugin components" from group A + "Recurring patterns" from group B).
- The scope question is asked exactly once in this same call (not per analysis type), with a
  "Custom" escape hatch since scope can be "a date string, 'today', or 'this conversation'" per the
  skill — a fixed 3-option list can't enumerate arbitrary date strings, so the third option lets the
  user supply free text via the tool's custom-answer affordance.
- All three questions go out in **one** `AskUserQuestion` call (batched), since they're all part of
  "Phase 1: Pick Analyses and Scope" — the skill frames this as "asked in two ≤4-option batches... and
  confirm scope once, up front," i.e. one guided pass, not three separate round trips.

Once the user answers, I'd resolve the selections into a concrete list, e.g. if they picked "Plugin
components," "Recurring patterns," and scope "This conversation," that becomes: run
`analyzing-plugin-components` and `mining-recurring-patterns` over "this conversation."

## Phase 2 (for context, not this eval's focus)

For each chosen analysis type, in the order selected: a direct `Skill(<analysis-name>)` tool call —
never `Agent`/forked — letting each run to completion and recording its persisted report path
before moving to the next.

## Phase 3 (for context)

Read every persisted report, deduplicate findings by subject, classify severity (P1
Critical/P2 Major/P3 Minor), tag each finding with its target plugin/component, and persist the
consolidated report. **The skill explicitly stops here** — this is a complete deliverable on its own;
it does not auto-continue into Phase 4 (optional cross-check) or Phase 5 (fix loop) in the same turn.

## On "...then fix what it finds"

The user's phrasing bundles a fix pass into the same request, but the skill's own control flow does
not allow that to happen automatically: Phase 3 is a hard stop, and Phase 5 (the guided
one-topic-at-a-time fix loop) only begins "in a later turn, once the user asks to continue." So the
correct behavior is: complete Phases 1–3 (pick analyses/scope, dispatch, consolidate) and hand the
user the prioritized report, then explicitly note that the fix pass is available as a next step they
can trigger — not silently proceed into fixing within the same turn. This also respects
`disclose-before-overriding-decisions.md`: skipping straight to fixes without the stated checkpoint
would be silently bypassing a gate the skill's own documentation names as required.

(Phase 4's optional cross-check and Phase 5's fix loop are out of scope for this eval per the supplied
SKILL.md excerpt — "Not needed for this task — out of scope for this eval" — so no further detail is
given for those phases here.)
