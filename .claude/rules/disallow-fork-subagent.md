# Disallow the Fork Subagent

## When this applies

Any point in a session where the `Agent` tool is about to be invoked with `subagent_type: "fork"`, for
any task, anywhere in this repository.

## Rule

Never invoke `Agent` with `subagent_type: "fork"` in this repository, for any task. This is an absolute
prohibition, not a case-by-case judgment call — it applies regardless of task size, urgency, or how much
the forked agent would otherwise reduce context usage. Where background or parallel work is genuinely
needed, dispatch a fresh (non-fork) `subagent_type` instead — `general-purpose` or a more specific agent
type — even though a fresh agent starts without inherited context and needs a self-contained prompt
written for it, per the `Agent` tool's own prompt-authoring guidance.

## Incorrect

```
Agent({ subagent_type: "fork", description: "...", prompt: "..." })
```
Dispatched anywhere in this repo, for any task — including one that looks like pure research or
"intermediate output I don't need to keep."

## Correct

```
Agent({ subagent_type: "general-purpose", description: "...", prompt: "<self-contained prompt with full context, since a fresh agent has none>" })
```
Or, when a matching skill exists for the task, dispatch that skill instead per
[[prefer-skills-over-ad-hoc-work]].

## Why

Reported directly by this repo's owner (2026-09-25): the `fork` subagent type has repeatedly failed to
reliably use this repo's own skills or follow its `.claude/rules/*.md`/CLAUDE.md instructions, and its
generated output has consequently been unreliable. This is a specifically bad combination with why fork
is normally attractive: it exists to keep a forked agent's own tool output *out of* the coordinator's
context ("don't peek" — the coordinator is explicitly told not to read the fork's transcript mid-flight),
which means a fork skipping this repo's rules and skills is not visible for review until its final
summary lands, by which point any rule-violating or buggy work may already be done. Until fork can be
verified to reliably load and follow this repo's skills and rules, using it here is a net loss regardless
of the token/context savings it would otherwise offer.

## Enforcement

Policy gate, no backing hook. This falls outside
`.claude/rules/require-security-review-before-new-gate.md`'s own scope — that rule targets a *new
mechanism* with its own pass/fail check logic (an authentication/permission gate, a bypass-attestation
protocol); this is a blanket prohibition with no conditional check to review, closer to a categorical
tool restriction than a new gate. Nothing in this repo mechanically blocks a `subagent_type: "fork"` call
at the tool-invocation layer; compliance depends on the acting session recognizing and honoring this rule
before dispatching `Agent`.
