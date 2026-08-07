# Task
User request: "I want to build a new plugin but I'm not sure where to start."

# Skill Followed
`using-plugin-devkit` — this request names no specific plugin-devkit skill or pipeline ("build a new plugin", "not sure where to start"), which is exactly the trigger condition for this front-door skill. Proceeding through its phases as documented, without deviation.

`$ARGUMENTS` for this invocation = "I want to build a new plugin but I'm not sure where to start."

---

## Phase 1: Pick an Entry Point

Per the skill, this phase is a mandatory `AskUserQuestion` call — the user's wording is used only to pre-highlight an option, never to skip the question. Since this is a blind, non-interactive test, I am not actually invoking the tool; below is the exact call I would make.

**AskUserQuestion call:**

- **Question:** "What are you trying to do with plugin-devkit?"
- **Options:**
  1. **Build something new** *(pre-highlighted/recommended)* — "A plugin or component from scratch, or resuming from an existing Concept Card/Plan. Routes to `plugin-lifecycle-upstream`. (For one already-well-understood single component, the lighter path is going straight to the matching Design skill instead — but that's not what's described here.)"
  2. **QA or audit an existing plugin** — "Rule compliance, structural validation, a weighted quality score, or all three combined. Routes to `plugin-lifecycle-downstream`."
  3. **Fix or improve something based on a finding** — "Acting on a retro or comparison result, or an on-demand self-check. Routes to `plugin-lifecycle-maintenance`."
  4. **Not sure / something else** — "Describe the actual need in a follow-up instead of forcing it into one of the three pipelines."

**Why option 1 is pre-highlighted:** the user's own words — "build a new plugin" — map directly onto the "Build something new" option's description ("a plugin or component from scratch"). Nothing in the request suggests an existing plugin needs auditing or a known finding needs fixing, so options 2 and 3 don't match. The user also isn't expressing confusion about *whether* to use plugin-devkit, only *where to start within it* — so option 4 ("not sure / something else") is a fallback, not the best match; the skill exists precisely to resolve "where to start" via option 1–3 routing.

### Assumption (labeled)
Since there is no real user to answer, I assume the pre-highlighted answer is selected: **"Build something new."** This is the most plausible answer given the request text says "build a new plugin" almost verbatim. Continuing under this assumption.

**Phase 1 exit condition met:** exactly one of the three pipelines is selected — `plugin-lifecycle-upstream`.

---

## Phase 2: Confirm Before Dispatch

Per the skill, even an unambiguous Phase 1 answer must still be confirmed before dispatch — this gate is never skipped.

**AskUserQuestion call:**

- **Question:** "Run `plugin-lifecycle-upstream` for this?"
- **Options:**
  1. **Run it** *(recommended)* — proceed to dispatch `plugin-lifecycle-upstream` now.
  2. **Change my answer** — go back to Phase 1 and pick a different entry point.
  3. **Cancel** — stop here, nothing is dispatched.

**Why "Run it" is recommended:** the Phase 1 answer ("Build something new") was a strong, low-ambiguity match to the user's literal wording, and the user has not described an existing plugin, a known finding, or a specific already-designed single component — so there's no signal pointing toward a lighter alternative (e.g. going straight to `skill-development`) instead of the full pipeline. A full "not sure where to start" build request is exactly what `plugin-lifecycle-upstream`'s Ideate→Plan→Design→Build→Test pipeline is for.

### Assumption (labeled)
Assuming the user selects **"Run it."** Continuing under this assumption.

**Phase 2 exit condition met:** confirmation obtained to dispatch `plugin-lifecycle-upstream`.

---

## Phase 3: Dispatch

This is the point where, per the skill's Phase 3 instructions, I would invoke:

> `Skill(plugin-lifecycle-upstream)`, passing `$ARGUMENTS` through as its own argument — i.e. "I want to build a new plugin but I'm not sure where to start."

I am **not** actually invoking this skill (per the test instructions) — this is the stopping point. From here, `plugin-lifecycle-upstream` would take over and manage its own Ideate/Plan/Design/Build/Test phases and gates; `using-plugin-devkit`'s job is complete once dispatch happens.

---

## Summary of routing decision

| Phase | Action | Result |
|---|---|---|
| 1 | AskUserQuestion: which of 3 pipelines (or "not sure") | Assumed: "Build something new" |
| 2 | AskUserQuestion: confirm dispatch of `plugin-lifecycle-upstream` | Assumed: "Run it" |
| 3 | Invoke `Skill(plugin-lifecycle-upstream)` with `$ARGUMENTS` passed through | Not actually invoked (test stop point) |

No step was skipped and no answer was inferred silently — both AskUserQuestion gates are explicit per the skill's own "Gotchas" section ("This skill never decides anything on its own"), and the two calls above are exactly what would be issued to a real user in a live run.
