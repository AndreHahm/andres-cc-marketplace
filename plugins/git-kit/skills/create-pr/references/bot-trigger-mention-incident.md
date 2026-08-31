# No Literal Bot-Trigger Mentions — Incident Narrative

Full incident behind `create-pr`'s "No literal bot-trigger mentions" Best Practice and step 2/5's
matching checks — extracted here (R13/R30) so the SKILL.md body carries only the rule statement and a
pointer, not a third copy of the same narrative `commit`'s SKILL.md already carries in full.

## What happened (PR #257, 2026-08-31)

A fix adding `@codex full review` recognition to `await-codex-review.yml` used that phrase literally in
its own commit message and PR title. Codex's connector read the title/message as a task addressed to it
rather than a diff to review, attempted out-of-band work instead of reviewing, and its own reply comment
then self-retriggered `await-codex-review.yml`'s wait-loop by containing that same substring — verified
from the actual GitHub Actions run history (a `pull_request`-triggered wait was cancelled by a new
`issue_comment`-triggered run whose trigger comment was Codex's own). Amending the PR title (and the
underlying commit message — see `commit`'s matching Best Practice) to describe the phrase in prose
instead of reproducing it literally resolved it: a subsequent manual `@codex review` comment triggered a
normal review and the check passed.

## Round 2, same date

An independent Codex fresh-eyes pass (via `cross-model-review`) caught the first version of this fix
banning *any* `@<word>` mention outright, which would also have blocked an ordinary `@username`/`@team`
mention notifying a human collaborator (e.g. requesting a reviewer). Narrowed to bot-trigger-shaped
mentions specifically — a `@<bot-account>` handle immediately followed by a command-like word — with the
human-mention carve-out stated in the SKILL.md rule itself.

## Round 3, PR #258, 2026-08-31

Two more findings from this exact change's own automated review:

- **Devin** flagged the incident narrative being restated at nearly every touch point across
  `commit`/`create-pr`/`github-issue-lifecycle` as a simplicity/drift risk (per this repo's own
  `AGENTS.md`/`CLAUDE.md` guidance). This file is the fix — one canonical narrative, referenced instead
  of re-narrated, and it also resolved `create-pr/SKILL.md`'s own R13 line-count threshold this
  duplication had pushed past.
- **Codex** found step 5's bypass-attestation reason text (posted verbatim via `gh pr comment` in step
  d) was never checked against the same bot-trigger rule the PR title/body already were — a reason
  spelling out the trigger phrase would have reproduced the self-retrigger risk through that flag
  instead. Fixed by extending the check to the reason text before step d runs.

No fresh `skill-tester` eval re-run for any of the three rounds — the fix throughout is prose guidance
with no executable logic to simulate; each round was verified by re-observing the real PR/GitHub Actions
state after applying it.
