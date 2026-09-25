# Prefer AskUserQuestion Over a Plain-Text Question

## When this applies

Any point — while authoring a plugin component's confirmation-gate logic, or in Claude's own live
conversational replies — where the next step requires a decision only the user can make between two or
more concrete, mutually exclusive options: a proceed/cancel gate, a pre-flight confirmation, a genuine
design fork ("approach A or B?"), or any other point where a reply would otherwise end in a plain prose
question.

## Rule

Use the `AskUserQuestion` tool instead of ending a reply with a plain-text question, and instead of a
component's own printed "Proceed? [yes/no]" free-text prompt, whenever:
- There are 2 to 4 concrete, mutually exclusive options to choose from — the tool's own schema caps
  options at 4 per question, so a choice with more real options needs to be narrowed to the 4 most
  likely ones (the tool always offers the user an "Other" free-text fallback beyond the listed options,
  so narrowing never actually forecloses a choice), and
- The choice is the user's to make — not a judgment call Claude itself can make and disclose.

This applies in two contexts:

1. **Authoring**: when writing or editing a skill/command/agent's confirmation-gate logic (a
   "Pre-flight" step, a "Wait for confirmation" instruction, a dry-run summary before a destructive or
   expensive action), specify `AskUserQuestion` explicitly — never a printed prompt with free-text
   matching (e.g. "type yes to continue").
2. **Conversational**: when Claude itself reaches a fork with concrete, mutually exclusive options
   during a live discussion — even inside an otherwise-exploratory "let's discuss before starting"
   exchange — use `AskUserQuestion` directly rather than ending the text reply with a plain question.
   This applies even right after having used the tool correctly earlier in the same conversation — one
   correct instance doesn't establish the habit for the rest of the session; check every reply that ends
   in a real fork before sending it.

**Exception:** don't force `AskUserQuestion` onto an open-ended, unbounded question that can't
reasonably be enumerated as 2-4 concrete choices — that class of question is legitimately conversational
prose, not a decision gate.

## Incorrect

Ending a reply with a plain-text fork instead of the tool, even when the two options are already
concrete and mutually exclusive:

```
Want me to trigger round 3, or hold here?
```

## Correct

The same fork, routed through the tool:

```
AskUserQuestion({
  questions: [{
    question: "Trigger review round 3, or hold here?",
    header: "Next step",
    options: [
      { label: "Trigger round 3", description: "Kick off another review round now." },
      { label: "Hold here", description: "Stop triggering rounds; move on." }
    ]
  }]
})
```

## Why

This preference existed only as a cross-session memory record, reinforced three separate times: an
original flag during component-authoring review (a dev-rules pipeline command's own printed "Proceed?
[yes/no]" free-text prompt instead of the tool); broadened on 2026-08-06 after Claude presented a real
design fork ("thin router vs. fuller guided pipeline") as a plain-text question at the end of a message
instead of via the tool; and recurred on 2026-08-25 mid-`handling-review-findings`, ending a reply with
"Want me to trigger round 3, or hold here?" instead of `AskUserQuestion`, despite having used the tool
correctly for the exact same review-round-trigger scenario one turn earlier in the same session — the
user called it out sharply ("Why you don't use AskUserQuestion?????"). The memory record's own text
flagged that "this convention should probably become a checked rule... rather than a one-off fix," but
that follow-up was never done until now.

Cross-session memory is recalled only "when memories seem relevant" — a judgment call, not a guarantee.
A preference that lives only there can be silently skipped in any turn where the model doesn't happen to
judge it relevant enough to recall, which is exactly what kept happening here. This rule closes that gap
by making the preference an always-loaded, force-injected instruction instead of a recall-dependent one.

## Enforcement

Policy gate, no backing hook. Whether a given reply "should have" used `AskUserQuestion` instead of
ending in plain text is a judgment call about live conversational output — there is no
`PreToolUse`/`PostToolUse` hook that can inspect a text reply before it is sent and determine whether it
constituted a decision-gate fork. Compliance depends on the author's/Claude's own attention in the
moment, the same disclosed-limitation model `.claude/rules/require-security-review-before-new-gate.md`
and similar policy-only rules in this repo already use.
