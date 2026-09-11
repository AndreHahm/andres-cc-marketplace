# Promoting "Unified Notification Routing Platform" from Notion to Linear

This is a narrative of the workflow I would actually follow to promote a multi-team notification-routing
platform idea from a Notion Idea record into Linear, using ordinary judgment and the standard Notion/Linear
tools available to me — no specialized skill, methodology, or bridge-caller procedure assumed. Because the
task is explicitly large and ambiguous, I treat "request an independent review before finalizing" as a hard
gate: I stop and get a second set of eyes on the proposed Linear structure before I create anything, rather
than creating records first and asking forgiveness later.

---

## Step 1 — Locate and read the source Idea in Notion

I start by searching Notion for the idea. I'd use `notion-search` (or `notion-fetch` if I already have a
URL) with a query like "notification routing" / "notification platform idea" to find the record. For this
exercise, I'm inventing a plausible page since I don't have a real one to read. Here is the Idea record I'm
treating as ground truth for the rest of this workflow:

> **Notion page: "Idea — Unified Notification Routing Platform"**
> **Status:** Proposed | **Owner:** Priya Anand (Platform Infrastructure) | **Last edited:** 2026-08-22
>
> **Problem statement:**
> Four teams — Platform Infrastructure, Growth Engineering, Mobile, and Customer Support Tools — each
> maintain their own bespoke notification pipeline (email, push, SMS, in-app, Slack webhook fan-out). This
> has caused: (1) duplicated delivery/retry logic maintained four separate times, (2) inconsistent handling
> of user opt-in/opt-out preferences across channels (a user can be unsubscribed from email marketing but
> still get a duplicate push for the same event), (3) no unified delivery observability — support has no
> way to see whether a given notification actually reached a user, and (4) onboarding a new channel (e.g.
> WhatsApp) currently requires four separate integration efforts.
>
> **Proposed solution:**
> Build a central Notification Routing Service that all teams publish events to, backed by a single
> Preference Center as the source of truth for channel opt-in/opt-out, with pluggable channel adapters
> (email, push, SMS, in-app, Slack, and future channels), plus delivery observability tooling for support
> and on-call.
>
> **Rough scope notes (unstructured, from a working session):**
> - Platform Infra owns the core routing engine + rules DSL + retry/dead-letter handling
> - Growth Eng owns unifying today's three different preference stores into one Preference Center
> - Mobile owns migrating push + SMS adapters onto the new routing core (mobile currently owns the only
>   SMS integration)
> - Support Tools owns a delivery-observability dashboard + a "replay this notification" tool for support
>   agents
> - Rough sequencing: design/contract first, then core service, then one pilot channel migration, then
>   remaining channels, then legacy pipeline decommission
> - No committed dates yet; sponsor wants "meaningful progress this half," decommission is explicitly a
>   stretch goal not a commitment
> - Open question in the doc itself: "Do Mobile and Support Tools need dedicated projects, or does this
>   fold into their existing roadmap projects?" — flagged by the author as unresolved

That last line matters a lot: even the source document admits its own team/project boundaries are
unresolved. That's a strong signal this needs a second opinion before I lock in a structure, not just a
signal about size.

## Step 2 — Extract the structure implied by the idea, without over-fitting to Notion's shape

Per my own judgment (not a scripted "inspiration vs. structure" rule, just ordinary care), I treat this
Notion page as the *content* to promote, not as a literal template Linear must mirror. The page is a loose
working doc with an explicit open question about team/project boundaries — I should reshape it into
something that makes sense as Linear's own Goal → Project → Milestone hierarchy, informed by the doc's
scope notes, not by blindly turning every bullet into a record.

From the content, I read out:
- **One cross-team outcome** ("stop four teams reinventing notification delivery, with a single
  preference source of truth and observability") → maps to a Linear **Goal** (Linear's cross-team,
  cross-project grouping object — some workspaces label this "Initiative").
- **Four team-scoped bodies of work**, each with a clear owning team and a distinct deliverable → maps to
  four candidate **Projects**, one per team, each linked to the Goal.
- **A rough phase sequence** (design → core service → pilot migration → remaining migrations →
  decommission) → maps to **Milestones** inside the relevant Projects, not separate Projects of their own.

## Step 3 — Draft the proposed Linear structure (not yet created)

I draft this as a proposal, explicitly unsent to Linear yet:

**Goal:** *Unified Notification Routing Platform* (H2 2026)
- Description: cross-team goal to replace four bespoke notification pipelines with one routing service,
  one preference center, and unified delivery observability. Links back to the Notion source page.
- Target: end of H2 2026 for MVP; full legacy decommission explicitly called a stretch goal, not a
  committed target — I carry that caveat into the Goal description verbatim so it isn't silently promoted
  to a hard deadline.

**Project 1 — Routing Core Service** (Team: Platform Infrastructure)
- Milestones: M1 Design & contract finalized, M2 Core service MVP live in staging, M3 Retry/dead-letter
  handling complete, M4 Production rollout (v1)

**Project 2 — Preference Center Unification** (Team: Growth Engineering)
- Milestones: M1 Audit of 3 existing preference stores complete, M2 Unified schema + migration plan
  approved, M3 Preference Center live as source of truth, M4 Legacy preference stores deprecated

**Project 3 — Channel Adapter Migration: Push & SMS** (Team: Mobile)
- Milestones: M1 Push adapter migrated to routing core (pilot channel), M2 SMS adapter migrated, M3 Legacy
  mobile notification code removed

**Project 4 — Delivery Observability & Support Tooling** (Team: Customer Support Tools)
- Milestones: M1 Delivery-status dashboard MVP, M2 "Replay notification" tool for support agents, M3
  On-call runbook + alerting wired to dashboard

This is a reasonable first-pass structure, but I flag several things I am **not** confident about, precisely
because the source doc says so itself:

1. Whether Mobile and Support Tools warrant *dedicated new* Projects, versus folding this work into their
   existing roadmap Projects — the doc raises this and doesn't answer it. I picked "dedicated Projects" as
   the default because it keeps cross-team goal tracking clean, but that's a judgment call, not a fact from
   the source.
2. Whether email/in-app/Slack adapter migration needs its *own* Project (Platform Infra? Growth?) or folds
   into Routing Core Service — the doc never assigns an owner for those three channels at all.
3. Sequencing/dependency risk: Preference Center Unification (Growth) is a hard dependency for Routing Core
   Service's retry/opt-out logic, but they're modeled as two independent, team-owned Projects with no
   stated cross-project dependency — worth someone with real context flagging if that's wrong.
4. No committed dates exist in the source beyond "this half" — I should not invent specific quarter-end
   dates for Milestones without someone confirming they're real commitments, not placeholders.

## Step 4 — Stop and request independent review before finalizing

This is the point where I do not proceed straight to creating Linear records. Given the explicit request
for an independent review, and given that I have no dedicated "reviewer" tool or automated second-opinion
mechanism available to me in this baseline setup, I handle it as follows, using ordinary judgment:

**4a. I do not silently self-approve my own draft.** Even though I could technically call
`save_project`/`save_milestone` right now, doing so would mean I'm the only party who has looked at a
structural decision the source document itself flagged as unresolved. I treat "large and ambiguous, please
get a second opinion" as a real instruction, not a soft suggestion.

**4b. I surface the draft plan to the user directly, in full**, exactly as drafted in Step 3, together with
the four open questions from Step 3, and I ask explicitly — via a structured question, not free text —
whether they want to:
   - (a) approve the draft as-is and let me proceed to creating it in Linear,
   - (b) have me route it to a specific teammate/stakeholder (e.g. Priya Anand as the doc's owner, or each
     of the four team leads) for actual review before I create anything, or
   - (c) revise specific parts of the structure themselves first.

   Concretely, this looks like an `AskUserQuestion`-style prompt:
   > "This spans 4 teams and the source doc itself leaves team/project boundaries unresolved. Before I
   > create the Goal/Projects/Milestones in Linear, how do you want the independent review handled?
   > 1. I proceed once you personally approve the draft below.
   > 2. I post the draft as a comment on the Notion Idea page, tagging Priya Anand (doc owner) and the
   >    four team leads, and wait for at least one substantive reply before creating anything.
   > 3. Something else — tell me who should review this and how."

**4c. If the user asks me to loop in a stakeholder (option 2 above)**, the concrete mechanism I'd use,
without any specialized tooling, is: add a comment on the Notion Idea page itself (`notion-create-comment`)
containing the full draft structure from Step 3, tagging Priya Anand and the four team leads by name, and
asking for explicit sign-off or corrections — particularly on the four open questions. I would not create
any Linear record until that comment thread has either an explicit approval, or the user tells me to
proceed anyway with a stated reason (e.g. "Priya is out this week, use your best judgment on open question
1, but don't guess on the dates"). If the user tells me to proceed without waiting on the stakeholder
thread, I still leave the comment in place as a durable trace that review was requested and note in my
final report to the user that this shortcut was taken and why.

**4d. If the user reviews it themselves (option 1)**, I walk them through the four open questions one at a
time rather than as a single wall of text, and update the draft based on their answers before moving to
Step 5. For this simulated exercise, I assume the user reviews it and responds:
- Q1 (Mobile/Support Tools dedicated Projects vs. folding into existing roadmaps): "Keep them as dedicated
  Projects — this is different enough from their regular roadmap work that visibility matters more than
  minimizing project count."
- Q2 (owner for email/in-app/Slack adapters): "Fold those three into Routing Core Service as additional
  milestones — no team has claimed them, and Platform Infra already owns the core service, so they're the
  reasonable default owner until someone else claims it."
- Q3 (Preference Center dependency): "Correct, add an explicit note on Routing Core Service's M3 milestone
  that it's blocked on Preference Center Unification's M2 — don't create a formal cross-project blocking
  relationship yet since Linear's dependency tracking across teams is clunky, just document it in both
  places."
- Q4 (dates): "Don't put specific quarter-end dates on anything yet — leave Milestone target dates unset
  and note in each description that dates are pending team capacity planning."

I incorporate all four answers into the working draft before proceeding — this is the actual "independent
review" resolution for this run: a human (the user, standing in for the doc owner/team leads) reviewed the
ambiguous parts and made the calls I was not in a position to make unilaterally.

## Step 5 — Finalize the structure after review

Revised structure after incorporating the review feedback:

- **Goal: Unified Notification Routing Platform** (H2 2026) — description includes a link back to the
  Notion source page, and an explicit note that legacy-pipeline decommission is a stretch goal.
- **Project 1 — Routing Core Service** (Platform Infrastructure)
  - M1 Design & contract finalized
  - M2 Core routing engine MVP live in staging
  - M3 Retry/dead-letter handling complete *(blocked on Preference Center Unification M2 — noted in
    description, not a formal Linear dependency)*
  - M4 Email/in-app/Slack adapters migrated onto routing core
  - M5 Production rollout (v1)
  - No target dates set; description notes dates pending capacity planning.
- **Project 2 — Preference Center Unification** (Growth Engineering)
  - M1 Audit of 3 existing preference stores complete
  - M2 Unified schema + migration plan approved
  - M3 Preference Center live as source of truth
  - M4 Legacy preference stores deprecated
- **Project 3 — Channel Adapter Migration: Push & SMS** (Mobile)
  - M1 Push adapter migrated (pilot channel)
  - M2 SMS adapter migrated
  - M3 Legacy mobile notification code removed
- **Project 4 — Delivery Observability & Support Tooling** (Customer Support Tools)
  - M1 Delivery-status dashboard MVP
  - M2 "Replay notification" tool for support agents
  - M3 On-call runbook + alerting wired to dashboard

## Step 6 — Confirm the final structure once more before writing

Before calling any create/write tool, I restate this final structure back to the user in compact form and
ask for an explicit go/no-go — this is a separate, smaller confirmation from the Step 4 review request: the
review in Step 4 was about resolving ambiguity; this checkpoint is about confirming I correctly incorporated
that resolution before an irreversible-ish action (creating five new tracked records other people will see
and start planning against). I do not skip this just because Step 4 already happened — the two checkpoints
serve different purposes and collapsing them risks silently shipping a misreading of the feedback.

## Step 7 — Create the records in Linear

Once I have explicit go-ahead, I create the records in dependency order (Goal first, since Projects
reference it; Milestones last, since they reference their parent Project):

1. **Goal** — create "Unified Notification Routing Platform," description includes the Notion page link,
   the stretch-goal caveat on decommission, and the names of the four owning teams.
2. **Teams** — before creating Projects, I'd confirm each of the four teams (Platform Infrastructure,
   Growth Engineering, Mobile, Customer Support Tools) actually exists as a Linear team with the exact
   names/keys the workspace uses (via a team lookup), rather than assuming my invented names match — a
   mismatched or misspelled team reference is a common, easy-to-avoid failure at this step.
3. **Projects** — create the four Projects, each linked to the Goal and assigned to its owning team, each
   with a description summarizing its scope and linking back to the Notion Idea page and to the Goal.
4. **Milestones** — create each Project's milestones in order, each with a short description; dates left
   unset per the review feedback, with a note that they're pending capacity planning.

## Step 8 — Close the loop back in Notion

After the Linear records exist, I update the Notion Idea page (or add a comment) with:
- Links to the newly created Goal and all four Projects in Linear.
- A note that the team/project boundary question and the dependency between Routing Core Service and
  Preference Center Unification were resolved during promotion, with who decided what (crediting the
  reviewer, not silently absorbing the decision as if I'd made it).
- The page status updated from "Proposed" to something like "In Progress — promoted to Linear," if the
  workspace has that status option, so the idea doesn't look orphaned or duplicated.

## Step 9 — Final report to the user

I summarize for the user: what was created (1 Goal, 4 Projects, 16 Milestones total, across 4 teams), what
ambiguity existed in the source and how each point was resolved (crediting their review decisions
specifically), what was deliberately left open (Milestone target dates, formal cross-project dependency
linking), and the direct Linear links plus the Notion page link, so they can verify everything themselves
rather than taking my summary as the source of truth.

---

## Why I gated on review here specifically

I want to be explicit about the judgment call underlying Step 4, since nothing forced this pause
mechanically: the source Idea document itself contained an unresolved, author-flagged open question about
team/project boundaries, the request named this as "large and ambiguous" up front, and the action being
gated — creating five permanent, team-visible tracked records that four different teams will start planning
against — is expensive to silently redo or unwind once other people have started referencing it. Those three
factors together are why I chose to block on a real second opinion (either the user directly, or the
doc owner/team leads via a tagged Notion comment) rather than resolving the open questions with my own
best guess and disclosing the guess after the fact. A smaller, unambiguous idea with a single obvious owner
would not warrant the same ceremony — the gate is proportionate to the actual ambiguity and blast radius
here, not a default I'd apply to every promotion.
