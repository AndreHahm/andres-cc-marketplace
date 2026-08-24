# Review: Draft Workflow Skill SKILL.md Body

## Summary

The draft is a single prose paragraph masquerading as a "Steps" section. For a workflow skill —
one whose whole job is to reliably drive a multi-step, partially risky process (a deployment) —
this body has several structural problems that would make it unreliable or unsafe to follow.

## Findings

### 1. Steps are not actually enumerated
The "## Steps" heading promises a step-by-step procedure, but the body is one flowing sentence/
paragraph ("First... Then... After deploying..."). There's no numbered or bulleted list, so there
are no clear, discrete, checkable steps an agent (or a human) can execute and verify one at a time.
A workflow skill should give steps as a literal ordered list, each one an unambiguous unit of work.

### 2. Vague, non-actionable instructions
- "check the current state of the deployment" — check *how*? Which command, which system, which
  URL/dashboard/API? No tool, script, or check is named.
- "if everything looks good" — no criteria define "good." This is a judgment call with nothing to
  judge against, which is especially risky as the gate before a deploy action.
- "proceed to deploy" — deploy *how*? No command, script, or mechanism named.
- "verify the deployment succeeded" — no success criteria (health check? status code? log line?
  smoke test?) are given.
- "notify the team" — no channel, mechanism, or message content specified (Slack? email? which
  channel/list?).

Every verb in this skill names an outcome, not an action. As written, an agent following this
skill has to invent the actual mechanics at each step, which defeats the purpose of having a
documented procedure at all.

### 3. Broken / missing reference
`[rollback-procedure.md](references/rollback-procedure.md)` is linked but the file does not exist
in the skill's directory. This is a dead link. Worse, it's the *only* place failure/rollback
handling is supposed to live — so as it stands, this skill has **no actual failure-handling
content at all**, just a pointer to nothing. For a deployment workflow, that's a significant gap:
the one scenario that most needs explicit, careful instructions (something going wrong during or
after a deploy) is entirely unaddressed.

### 4. Failure trigger condition is ambiguous
"See rollback-procedure.md ... if it fails" — *what* fails? The initial state check, the deploy
step itself, or the post-deploy verification? Each of those failing plausibly calls for a
different response (e.g., "don't deploy" vs. "roll back a live deploy" are very different
actions). The skill doesn't distinguish between them.

### 5. No pre-deploy safety gate beyond vague judgment
"if everything looks good, proceed to deploy" is the only gate before an irreversible/risky action
(deploying to what is presumably a shared or production environment). There's no explicit
confirmation step, no named criteria, and no mention of prerequisites (permissions, environment
target, credentials) needed to safely take this action.

### 6. No structure separating phases
Given this is a multi-phase operation (pre-check → deploy → verify → notify → possible rollback),
the body would benefit from either numbered steps or subheadings per phase, each with its own
concrete instructions. Collapsing all of this into one paragraph makes it hard to scan, hard to
resume from a specific step if interrupted, and hard to maintain (e.g., editing just the "verify"
step later means editing prose in the middle of a sentence).

### 7. No indication of idempotency / partial-failure handling
If the process is interrupted after "deploy" but before "verify," there's no guidance on what
state that leaves things in or what to do next. A real deployment workflow skill should say
whether steps are safe to re-run and what to do if the skill is resumed mid-procedure.

## Recommendation

Rewrite as a numbered step list where each step names a concrete action (a specific command, script,
or tool call) and explicit pass/fail criteria, add a real inline (or correctly-linked, actually-
existing) rollback/failure section that specifies which step's failure triggers it, and add an
explicit confirmation checkpoint before the deploy step given its risk. If `references/rollback-procedure.md`
is intended content, it needs to actually be created before the skill ships — a workflow skill
should not point to a promised-but-missing file for its only failure-handling path.
