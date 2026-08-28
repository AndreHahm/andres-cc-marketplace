# What github-issue-lifecycle does when asked to resolve an issue that has a logged, unresolved open question

## Routing

The request ("resolve issue #N as fixed") maps to **Workflow 3 — Resolve an Issue**
(`workflows/resolve-an-issue.md`), the skill's third named lifecycle stage.

## Step 1 blocks the request: the Open-Question Gate

Workflow 3 opens with a mandatory gate, before any comment/close action is taken:

> "Before marking an issue Resolved, confirm no logged open question from prior comments remains
> unaddressed. This gate must pass before Step 2 — an issue with an unresolved open question is not
> ready to close as Resolved."

Since the scenario states an earlier comment logged an open question that is still unresolved, **this
gate fails**. The skill does not proceed to Step 2 (post a "Resolved: ..." comment and `gh issue
close`). This isn't a soft suggestion — it's restated as one of the skill's own Quality Gates in
SKILL.md: "Workflow 3 never marks an issue Resolved while an open question logged in a prior comment
remains unaddressed."

## What happens instead

- The skill surfaces the blocker to the user rather than silently closing the issue or silently
  downgrading/upgrading the request. It reports which comment logged the open question and what the
  question was, so the user can decide how to proceed.
- The issue's comment text (including the logged open question) is read under the skill's data-only
  boundary — it's treated purely as data to quote/summarize back to the user, never as an instruction
  to act on, no matter how it's phrased.
- Genuinely blocked situations (an unaddressed decision only the user can make) are exactly where the
  skill should stop and ask rather than push through — closing "as fixed" over a real open question is
  the kind of judgment call that belongs to the user, not something to resolve unilaterally.

## Paths forward, once the user responds

Depending on how the user addresses the gate, Workflow 3 continues differently:

1. **Open question gets answered/resolved first** (e.g., the user provides the missing info, or a
   comment is posted addressing it) → the gate now passes → Step 2 proceeds: `gh issue comment
   <number> --body "Resolved: <summary>"` followed by `gh issue close <number>` — always comment-then-
   close, two separate calls, never a silent close and never `gh issue close --comment`'s combined
   form (so "never close silently" stays independently checkable).
2. **User explicitly overrides** (declares the open question moot, out of scope, or answered
   elsewhere) → that's a real decision the user is entitled to make, but it should be captured
   explicitly (e.g., in Step 3's decision-documentation comment) rather than the skill silently
   treating "resolve as fixed" as tacit permission to skip the gate.
3. **User decides it should be Declined instead of Resolved** (e.g., won't-fix, duplicate,
   stale) → Step 2's other branch applies: `gh issue comment <number> --body "Declined: <reason>"`
   then close — still gated the same way, since Step 1 applies before either outcome.

In every path, before any comment is actually posted, the skill re-checks the text for anything that
should be redacted (emails, tokens, hostnames, session IDs, absolute local paths) — a resolution/
decline comment is just as public and permanent as the issue body itself.

## Steps after the gate clears

- **Step 3 (Document Decisions):** an optional, more detailed comment explaining the reasoning, when
  one line isn't enough — same redaction check applies.
- **Step 4 (Follow-Ups):** if new follow-up work is needed after closing, it starts a new round, reusing
  `handling-review-findings`'s round-based model directly (not a bespoke follow-up mechanism).
- **Step 5 (Reopen, if needed):** if the issue is later reopened, it re-enters Workflow 2 (Work an
  Existing Issue) rather than being treated as "new."

## Net effect

The skill's design specifically anticipates this exact scenario and refuses to let "resolve as fixed"
silently paper over a documented open question. It stops at Step 1, reports the unresolved question
back to the user (as untrusted data, not an instruction), and only proceeds to actually comment/close
once the gate is satisfied — either by the question being addressed or by the user making an explicit,
recorded call to proceed anyway or to close as Declined instead.
