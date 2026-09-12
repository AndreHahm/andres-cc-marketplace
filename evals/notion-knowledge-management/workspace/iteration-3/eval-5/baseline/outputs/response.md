# Q3 Goal Proposal: Self-Serve Onboarding

## What I'd do first

Before drafting a goal from scratch, I'd check your Notion workspace for context so I'm not
duplicating or contradicting something that already exists:

1. **Search for an existing goals/OKR space** — something like a "Company Goals," "Q3 2026 OKRs,"
   or "Roadmap" database, to see the format other goals use (title, owner, key results, status,
   linked projects) so this one matches the house style instead of introducing a one-off shape.
2. **Search for "onboarding"** across the workspace — a PRD, a project brief, past retro notes, or
   a Slack-synced page — to check whether self-serve onboarding already has a spec, a named owner,
   or prior discussion I should align the goal to rather than re-deriving from nothing.
3. **Check for a Q2 goals page** to see whether self-serve onboarding was already in flight last
   quarter (a carryover) or is genuinely new for Q3 — that changes whether the goal should read as
   "ship" or "finish."

Since I don't have a live connector in this environment to actually run those searches, here's the
goal drafted from reasonable assumptions, flagged explicitly below, so you can correct anything
that doesn't match reality before I create the actual page.

## Assumptions (please correct any of these)

- "Self-serve onboarding" means a new user can go from signup to first meaningful value with no
  sales call, no manual account setup, and no support ticket required.
- This is a cross-functional effort (product + engineering + design, possibly support/docs).
- "Shipped" means live in production for all new signups, not just an internal beta or a flag
  enabled for a design-partner subset.
- Q3 2026 runs through end of September.

## Proposed goal

**Goal:** Ship self-serve onboarding so new users can activate without any manual/sales-assisted
setup.

**Why it matters:** Every new account currently requires a manual step (sales call, CS setup, or
support intervention) before a user reaches value. That caps how fast we can grow top-of-funnel and
adds a fixed cost to every new signup regardless of deal size. Removing that bottleneck is a
precondition for any self-serve or PLG motion.

**Owner:** *(needs a name — proposing whoever owns onboarding/activation today, or product lead if
unowned)*

**Target date:** September 30, 2026

**Key Results:**
1. A new user can complete signup → account setup → first core action with zero manual
   intervention (support ticket, sales call, or CS onboarding call).
2. Time-to-first-value for self-serve signups drops to under **[X] minutes/hours** — needs a real
   number from current activation data; I'd pull this from analytics/mixpanel/amplitude rather than
   guess.
3. **[X]%** of new signups in the last two weeks of Q3 activate without any human touch, up from a
   current baseline of **[Y]%** — again, needs the real baseline before this is a meaningful target.
4. Support/CS ticket volume tagged "onboarding" or "account setup" drops by **[X]%** quarter-over-quarter.

**Risks / open questions:**
- Is there a hard dependency (billing self-serve, SSO/security review, a pricing-page rebuild) that
  could block "fully self-serve" even if the onboarding flow itself is done?
- Does support need a parallel workstream (updated docs, in-app help) so ticket volume doesn't just
  move rather than shrink?
- Is there an existing partial build (a beta flag, a design-partner cohort) this should build on top
  of, which would change scope from "build" to "generalize and launch"?

## Next step

If this direction looks right, the natural place for it to live is your Notion goals/OKR database
(or wherever Q3 goals are tracked) as its own entry — with the Key Results above turned into
whatever your workspace uses for sub-items or tracked metrics, and the owner/date fields filled in
for real rather than left as placeholders. I'd also link it to the onboarding project page/PRD if
one exists, so the goal and the execution plan reference each other instead of drifting apart.

Since I can't reach Notion directly in this environment, I'm handing you the drafted goal above —
tell me the actual owner, the current activation baseline numbers, and which database this should
go into, and I'll fold that into a version ready to paste in (or, in a session with the real
connector, create the page and pull the numbers myself).
