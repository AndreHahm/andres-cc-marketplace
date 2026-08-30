# Promotion Hierarchy Mapping

How Notion knowledge types typically map onto Linear hierarchy levels when promoted via
`idea-to-implementation`. These are starting points, not fixed rules — the actual proposed
hierarchy always depends on what the source record and the user's own answers imply, never a
mechanical lookup from this table.

## Typical Mappings

| Notion source | Typical Linear target | Notes |
|---|---|---|
| Idea | A single Issue, or a small Project with a few Issues | Most Ideas are scoped narrowly enough for one Issue; propose a Project only when the Idea clearly implies multiple independent pieces of work |
| Accepted Decision | Usually an Issue (the decision's follow-through action) | A Decision that itself doesn't imply new work (e.g. "we will not pursue X") produces no Linear promotion at all |
| Proposed Goal | A Linear Goal, optionally with a new Roadmap placement | A proposed Goal accepted without an existing Roadmap needs the user to say which Roadmap (or a new one) it belongs to — never guess |

## Worked Examples of Ambiguous Cases

**An Idea that implies ongoing work, not a bounded task.** ("We should regularly review X.") This
doesn't map cleanly to a single Issue — present this ambiguity to the user directly and ask
whether they want a recurring-review Issue, a standing Project, or to defer promotion until the
idea is more concrete.

**A Decision that supersedes an already-promoted Idea's Linear work.** If the Decision reverses or
supersedes an Idea that already has linked Linear Issues, the promotion preview must show the
existing linked work and ask explicitly whether to close/cancel it, not silently leave it running
alongside the new Decision's own implications.

**A proposed Goal with no clear Roadmap fit.** Present the existing Roadmaps as options alongside
"create a new Roadmap" rather than picking the most-recently-created one by default — a Roadmap
placement is a material scope decision, not a formality.
