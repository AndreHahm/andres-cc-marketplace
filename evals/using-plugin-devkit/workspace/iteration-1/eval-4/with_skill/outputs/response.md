# using-plugin-devkit — session transcript

**User task:** "I'm working on plugin-devkit stuff but honestly not sure what I need right now."

`$ARGUMENTS` = "working on plugin-devkit stuff but honestly not sure what I need right now" — vague, and its own wording ("not sure what I need") leans toward the fourth Phase 1 option, but per the skill a vague `$ARGUMENTS` is not the same as an unanswered question, so Phase 1 still runs.

---

## Phase 1: Pick an Entry Point

**AskUserQuestion call (as I would issue it):**

```
Question: "What are you trying to do with plugin-devkit?"
Options:
  1. Build something new
     - a plugin or component from scratch, or resuming from an existing Concept Card/Plan
     - → plugin-lifecycle-upstream
     - (Note: for one already-well-understood single component, the matching Design
       skill directly is lighter than the full pipeline.)
  2. QA or audit an existing plugin
     - rule compliance, structural validation, a weighted quality score, or all three
     - → plugin-lifecycle-downstream
     - (Note: for just a compliance check, use plugin-rulebook directly; for just a
       score, use plugin-grader directly.)
  3. Fix or improve something based on a finding
     - acting on an analyzing-sessions retro or a plugin-comparison result, or an
       on-demand self-check
     - → plugin-lifecycle-maintenance
     - (Note: for a single already-known fix, edit directly or use the matching Design
       skill; for a lightweight single-change "should this propagate" call, use
       skill-maintenance instead.)
  4. Not sure / something else
     - describe the actual need in a follow-up instead of forcing it into one of the
       three pipelines
```

Pre-highlighted option: none of 1–3 is clearly indicated by the phrasing — the user's own words ("honestly not sure what I need right now") most closely match option 4, so that option is pre-highlighted, per the skill's instruction to let `$ARGUMENTS` shape which option is pre-highlighted without skipping the question itself.

**Assumed answer (this is a blind, non-interactive test — no real user is on the other end):**

> **Assumption:** the user picks **"Not sure / something else"** — this is the most plausible answer given the task text explicitly says "not sure what I need right now," with no hint at build/QA/fix intent to justify assuming one of the other three instead.

---

## Phase 2: Confirm Before Dispatch

Per the skill: *"On 'Not sure / something else' from Phase 1, skip this phase entirely — there's nothing to confirm."*

Phase 2 is skipped.

---

## Resolution

Since the "not sure" branch was taken, this skill does not dispatch a pipeline. Instead, per the skill's own instructions, the next step is to ask what the actual need is, in plain terms, rather than guessing or forcing the request into one of the three lifecycle pipelines.

**Follow-up question to the user (plain terms, not another structured picker):**

> No problem — let's narrow it down without guessing. A few plain-language pointers that might help you describe it:
>
> - Are you starting something new (a new plugin, or a new skill/agent/command/hook inside an existing plugin)?
> - Are you checking the health of something that already exists (does it follow the rules, is it well-structured, how good is it)?
> - Did something surface a specific problem you now want to act on (a retro finding, a comparison against another plugin, a bug someone hit)?
> - Or is it something else entirely — e.g. just documentation, settings, permissions, or a naming question?
>
> Whatever the shape of it, just describe what's going on in your own words and I'll point you at the right skill (or pipeline) from there.

---

## Outcome

- **Phase 1:** ran; assumed selection = "Not sure / something else."
- **Phase 2:** skipped (per skill rule for the "not sure" branch).
- **Phase 3 (dispatch):** not reached — no pipeline was invoked, consistent with the skill's design that this front door "never decides anything on its own" and stops at naming the right entry point (or, here, admitting none was yet identifiable and asking for more detail).
- **Next action:** waiting on the user's plain-language description of the actual need before routing to any specific plugin-devkit skill or pipeline.
